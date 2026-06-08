"""
Alpha信号批量生成器

根据注册表中的原语，自动为给定品种和周期批量生成因子值。
支持：
- 单品种全量因子计算
- 多品种并行计算
- 参数网格扫描（如 window=[5,10,20,60]）
- 结果输出为 pandas DataFrame（长格式 / 宽格式）
"""

from __future__ import annotations

import itertools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .registry import FACTOR_REGISTRY, PrimitiveMeta


# ---------------------------------------------------------------------------
# 参数网格生成
# ---------------------------------------------------------------------------

ParamGrid = Dict[str, List[Any]]


def _expand_param_grid(params: List[Tuple[str, type, Any]], grid: Optional[ParamGrid] = None) -> List[Dict[str, Any]]:
    if grid is None:
        return [{p[0]: p[2] for p in params}]
    keys = [p[0] for p in params]
    values = [grid.get(k, [p[2]]) for k, p in zip(keys, params)]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


# ---------------------------------------------------------------------------
# 单个原语计算
# ---------------------------------------------------------------------------

def _compute_primitive(
    meta: PrimitiveMeta,
    data: pd.DataFrame,
    params: Dict[str, Any],
    prefix: str = "",
) -> Optional[pd.Series]:
    func = meta.func
    if func is None:
        return None

    param_names = [p[0] for p in meta.params]
    kwargs = {k: v for k, v in params.items() if k in param_names}

    try:
        sig = func.__code__.co_varnames[: func.__code__.co_argcount]
    except Exception:
        return None

    args = []
    for arg_name in sig:
        if arg_name in kwargs:
            continue
        col_map = {
            "close": "close",
            "high": "high",
            "low": "low",
            "open_": "open",
            "volume": "volume",
            "open_interest": "open_interest",
            "spot": "spot",
            "future": "close",
            "near": "near",
            "far": "far",
            "am_close": "am_close",
            "pm_open": "pm_open",
        }
        col = col_map.get(arg_name)
        if col and col in data.columns:
            args.append(data[col].values)
        else:
            return None

    try:
        result = func(*args, **kwargs)
    except Exception:
        return None

    name_parts = [prefix + meta.name]
    for k in sorted(kwargs.keys()):
        name_parts.append(f"{k}={kwargs[k]}")
    name = "_".join(name_parts)

    return pd.Series(result, index=data.index, name=name)


# ---------------------------------------------------------------------------
# Alpha生成器
# ---------------------------------------------------------------------------

class AlphaGenerator:
    """批量生成因子信号。"""

    def __init__(
        self,
        primitives: Optional[List[str]] = None,
        param_grids: Optional[Dict[str, ParamGrid]] = None,
    ):
        self.primitives = primitives or list(FACTOR_REGISTRY.keys())
        self.param_grids = param_grids or {}
        self._results: Optional[pd.DataFrame] = None

    # --- 单品种计算 ---

    def generate(
        self,
        data: pd.DataFrame,
        prefix: str = "",
    ) -> pd.DataFrame:
        """
        对单品种 DataFrame 批量计算因子。

        Parameters
        ----------
        data : pd.DataFrame
            必须包含列: open, high, low, close, volume
            可选列: open_interest, spot, near, far, am_close, pm_open
        prefix : str
            因子名前缀，如 "MA_"

        Returns
        -------
        pd.DataFrame — 宽格式，每列一个因子
        """
        series_list: List[pd.Series] = []
        for name in self.primitives:
            meta = FACTOR_REGISTRY.get(name)
            if meta is None:
                continue
            grid = self.param_grids.get(name)
            param_sets = _expand_param_grid(meta.params, grid)
            for params in param_sets:
                s = _compute_primitive(meta, data, params, prefix=prefix)
                if s is not None:
                    series_list.append(s)
        if not series_list:
            return pd.DataFrame(index=data.index)
        df = pd.concat(series_list, axis=1)
        self._results = df
        return df

    # --- 多品种并行 ---

    def generate_multi(
        self,
        data_dict: Dict[str, pd.DataFrame],
        max_workers: int = 4,
    ) -> Dict[str, pd.DataFrame]:
        """
        对多个品种并行生成因子。

        Parameters
        ----------
        data_dict : dict[str, DataFrame]
            key 为品种代码，value 为 OHLCV DataFrame
        max_workers : int
            线程池大小

        Returns
        -------
        dict[str, DataFrame]
        """
        results: Dict[str, pd.DataFrame] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as exe:
            futures = {
                sym: exe.submit(self.generate, df, prefix=f"{sym}_")
                for sym, df in data_dict.items()
            }
            for sym, fut in futures.items():
                results[sym] = fut.result()
        return results

    # --- 输出格式转换 ---

    @staticmethod
    def to_long_format(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """将宽格式因子表转为长格式 (symbol, ts, factor_name, value)。"""
        df = df.reset_index().rename(columns={"index": "ts"})
        if "ts" not in df.columns:
            df = df.reset_index().rename(columns={df.index.name or "index": "ts"})
        long = df.melt(id_vars=["ts"], var_name="factor_name", value_name="value")
        long["symbol"] = symbol
        return long[["symbol", "ts", "factor_name", "value"]]

    @staticmethod
    def merge_multi_to_long(multi_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """将多品种结果合并为一张长格式表。"""
        frames = [AlphaGenerator.to_long_format(df, sym) for sym, df in multi_results.items()]
        return pd.concat(frames, ignore_index=True)

    # --- 工具：过滤全 NaN / 零方差因子 ---

    @staticmethod
    def prune_invalid(df: pd.DataFrame, min_obs: int = 30) -> pd.DataFrame:
        """删除观测数不足或方差为 0 的因子列。"""
        valid = df.columns[
            (df.count() >= min_obs) & (df.std() > 1e-12)
        ]
        return df[valid].copy()

    # --- 工具：按族分组提取 ---

    @staticmethod
    def extract_family(df: pd.DataFrame, family_name: str) -> pd.DataFrame:
        from .registry import PrimitiveFamily
        family = PrimitiveFamily(family_name)
        names = [m.name for m in FACTOR_REGISTRY.values() if m.family == family]
        cols = [c for c in df.columns if any(c.startswith(n) for n in names)]
        return df[cols].copy()
