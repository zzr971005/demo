"""
信息系数(IC)分析

提供：
- 因子值与未来收益率的 Rank IC / Pearson IC
- IC 序列的均值、标准差、IR、胜率、t检验
- 按品种/分组聚合 IC 统计
- 支持1H和1D数据，自动对齐未来收益标签
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# 工具：计算未来收益率标签
# ---------------------------------------------------------------------------

def forward_returns(
    close: Union[pd.Series, np.ndarray],
    periods: int = 1,
    index: Optional[pd.Index] = None,
) -> pd.Series:
    """
    计算未来 periods 期的对数收益率，作为因子预测目标。

    Parameters
    ----------
    close : Series or ndarray
        收盘价序列
    periods : int
        向前展望期数（1H数据下 periods=5 代表5小时后）
    index : Index, optional
        若 close 为 ndarray，需提供 index

    Returns
    -------
    pd.Series — 与 close 同长度，末尾 periods 个为 NaN
    """
    if isinstance(close, pd.Series):
        idx = close.index
        arr = close.to_numpy(dtype=np.float64)
    else:
        arr = np.asarray(close, dtype=np.float64)
        idx = index if index is not None else pd.RangeIndex(len(arr))

    fwd = np.empty_like(arr)
    fwd[:] = np.nan
    valid = arr[:-periods] > 0
    fwd[:-periods][valid] = np.log(arr[periods:][valid] / arr[:-periods][valid])
    return pd.Series(fwd, index=idx)


# ---------------------------------------------------------------------------
# IC 计算核心
# ---------------------------------------------------------------------------

def rank_ic(
    factor: Union[pd.Series, np.ndarray],
    forward_ret: Union[pd.Series, np.ndarray],
) -> float:
    """计算单期 Rank IC（Spearman 相关系数）。"""
    if isinstance(factor, pd.Series) and isinstance(forward_ret, pd.Series):
        aligned = pd.concat([factor, forward_ret], axis=1).dropna()
        if len(aligned) < 3:
            return np.nan
        f = aligned.iloc[:, 0].to_numpy(dtype=np.float64)
        r = aligned.iloc[:, 1].to_numpy(dtype=np.float64)
    else:
        f = np.asarray(factor, dtype=np.float64)
        r = np.asarray(forward_ret, dtype=np.float64)
        min_len = min(len(f), len(r))
        f = f[:min_len]
        r = r[:min_len]
        mask = np.isfinite(f) & np.isfinite(r)
        f = f[mask]
        r = r[mask]
        if len(f) < 3:
            return np.nan
    return stats.spearmanr(f, r)[0]


def pearson_ic(
    factor: Union[pd.Series, np.ndarray],
    forward_ret: Union[pd.Series, np.ndarray],
) -> float:
    """计算单期 Pearson IC。"""
    if isinstance(factor, pd.Series) and isinstance(forward_ret, pd.Series):
        aligned = pd.concat([factor, forward_ret], axis=1).dropna()
        if len(aligned) < 3:
            return np.nan
        f = aligned.iloc[:, 0].to_numpy(dtype=np.float64)
        r = aligned.iloc[:, 1].to_numpy(dtype=np.float64)
    else:
        f = np.asarray(factor, dtype=np.float64)
        r = np.asarray(forward_ret, dtype=np.float64)
        min_len = min(len(f), len(r))
        f = f[:min_len]
        r = r[:min_len]
        mask = np.isfinite(f) & np.isfinite(r)
        f = f[mask]
        r = r[mask]
        if len(f) < 3:
            return np.nan
    return np.corrcoef(f, r)[0, 1]


# ---------------------------------------------------------------------------
# 滚动 IC 序列
# ---------------------------------------------------------------------------

def rolling_ic(
    factor: pd.Series,
    forward_ret: pd.Series,
    window: int = 60,
    method: str = "rank",
) -> pd.Series:
    """
    计算滚动窗口 IC 序列。

    Parameters
    ----------
    factor : pd.Series
    forward_ret : pd.Series
    window : int
        滚动窗口长度
    method : str
        'rank' 或 'pearson'

    Returns
    -------
    pd.Series
    """
    df = pd.DataFrame({"f": factor, "r": forward_ret}).dropna()
    if method == "rank":
        return df["f"].rolling(window).corr(df["r"], method="spearman")
    return df["f"].rolling(window).corr(df["r"], method="pearson")


# ---------------------------------------------------------------------------
# IC 统计摘要
# ---------------------------------------------------------------------------

@dataclass
class ICStats:
    mean_ic: float
    std_ic: float
    ir: float
    win_rate: float
    pos_ratio: float
    t_stat: float
    p_value: float
    skew: float
    kurt: float
    max_drawdown: float
    ic_series: pd.Series

    def to_dict(self) -> dict:
        return {
            "mean_ic": self.mean_ic,
            "std_ic": self.std_ic,
            "ir": self.ir,
            "win_rate": self.win_rate,
            "pos_ratio": self.pos_ratio,
            "t_stat": self.t_stat,
            "p_value": self.p_value,
            "skew": self.skew,
            "kurt": self.kurt,
            "max_drawdown": self.max_drawdown,
        }


def ic_stats(
    ic_series: pd.Series,
) -> ICStats:
    """
    对 IC 时间序列做统计摘要。

    Parameters
    ----------
    ic_series : pd.Series
        单期 IC 值序列（index 为时间）

    Returns
    -------
    ICStats
    """
    s = ic_series.dropna()
    if len(s) == 0:
        nan = float("nan")
        return ICStats(nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, s)

    mean_ic = s.mean()
    std_ic = s.std()
    ir = mean_ic / (std_ic + 1e-12)
    win_rate = (s > 0).sum() / len(s)
    pos_ratio = (s > 0).sum() / len(s)
    t_stat, p_value = stats.ttest_1samp(s, 0)
    skew = s.skew()
    kurt = s.kurt()

    cum = s.cumsum()
    running_max = cum.cummax()
    drawdown = cum - running_max
    max_dd = drawdown.min()

    return ICStats(
        mean_ic=mean_ic,
        std_ic=std_ic,
        ir=ir,
        win_rate=win_rate,
        pos_ratio=pos_ratio,
        t_stat=t_stat,
        p_value=p_value,
        skew=skew,
        kurt=kurt,
        max_drawdown=max_dd,
        ic_series=s,
    )


# ---------------------------------------------------------------------------
# 批量因子 IC 分析
# ---------------------------------------------------------------------------

class ICAnalyzer:
    """对多因子批量做 IC 分析。"""

    def __init__(
        self,
        factor_df: pd.DataFrame,
        close: pd.Series,
        forward_periods: int = 5,
        method: str = "rank",
    ):
        """
        Parameters
        ----------
        factor_df : pd.DataFrame
            宽格式因子值表，index 为时间
        close : pd.Series
            收盘价序列，与 factor_df 同 index
        forward_periods : int
            未来收益展望期数
        method : str
            'rank' 或 'pearson'
        """
        self.factor_df = factor_df
        self.close = close.reindex(factor_df.index)
        self.forward_periods = forward_periods
        self.method = method
        self._fwd_ret = forward_returns(self.close, periods=forward_periods)
        self._results: Optional[pd.DataFrame] = None

    def analyze(self) -> pd.DataFrame:
        """
        逐因子计算 IC 统计，返回汇总表。

        Returns
        -------
        pd.DataFrame — 每行一个因子，列包含 mean_ic, std_ic, ir, win_rate, t_stat, p_value
        """
        records = []
        for col in self.factor_df.columns:
            ic_val = rank_ic(self.factor_df[col], self._fwd_ret) if self.method == "rank" else pearson_ic(self.factor_df[col], self._fwd_ret)
            records.append({
                "factor": col,
                "ic": ic_val,
            })

        ic_df = pd.DataFrame(records)
        ic_df = ic_df.dropna(subset=["ic"])
        if ic_df.empty:
            self._results = ic_df
            return ic_df

        stats_list = []
        for col in self.factor_df.columns:
            if self.method == "rank":
                ic_s = self.factor_df[col].rolling(60).corr(self._fwd_ret, method="spearman")
            else:
                ic_s = self.factor_df[col].rolling(60).corr(self._fwd_ret, method="pearson")
            st = ic_stats(ic_s)
            d = st.to_dict()
            d["factor"] = col
            stats_list.append(d)

        self._results = pd.DataFrame(stats_list)
        return self._results

    def top_factors(self, n: int = 10, by: str = "ir") -> pd.DataFrame:
        """按指定指标取 Top N 因子。"""
        if self._results is None:
            self.analyze()
        df = self._results.sort_values(by=by, ascending=False).head(n)
        return df

    def filter_significant(self, min_ir: float = 0.3, max_pvalue: float = 0.05) -> pd.DataFrame:
        """筛选显著因子。"""
        if self._results is None:
            self.analyze()
        df = self._results
        mask = (df["ir"].abs() >= min_ir) & (df["p_value"] <= max_pvalue)
        return df[mask].copy()


# ---------------------------------------------------------------------------
# 跨品种/分组聚合 IC
# ---------------------------------------------------------------------------

def cross_symbol_ic(
    factor_dict: Dict[str, pd.Series],
    close_dict: Dict[str, pd.Series],
    forward_periods: int = 5,
    method: str = "rank",
) -> pd.DataFrame:
    """
    计算多个品种同一因子的 IC，并汇总统计。

    Parameters
    ----------
    factor_dict : dict[str, Series]
        各品种因子值
    close_dict : dict[str, Series]
        各品种收盘价
    forward_periods : int
    method : str

    Returns
    -------
    pd.DataFrame — 每行一个品种，列包含 ic, mean_ic, std_ic, ir
    """
    records = []
    for sym, fac in factor_dict.items():
        close = close_dict.get(sym)
        if close is None:
            continue
        fwd = forward_returns(close, periods=forward_periods)
        ic_val = rank_ic(fac, fwd) if method == "rank" else pearson_ic(fac, fwd)
        records.append({"symbol": sym, "ic": ic_val})
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["mean_ic"] = df["ic"].mean()
    df["std_ic"] = df["ic"].std()
    df["ir"] = df["mean_ic"] / (df["std_ic"] + 1e-12)
    return df


def group_ic_summary(
    factor_dict: Dict[str, pd.Series],
    close_dict: Dict[str, pd.Series],
    group_map: Dict[str, str],
    forward_periods: int = 5,
    method: str = "rank",
) -> pd.DataFrame:
    """
    按品种分组聚合 IC。

    Parameters
    ----------
    group_map : dict[str, str]
        symbol -> group_name
    """
    records = []
    for sym, fac in factor_dict.items():
        close = close_dict.get(sym)
        if close is None:
            continue
        fwd = forward_returns(close, periods=forward_periods)
        ic_val = rank_ic(fac, fwd) if method == "rank" else pearson_ic(fac, fwd)
        records.append({"symbol": sym, "group": group_map.get(sym, "Z其他"), "ic": ic_val})
    df = pd.DataFrame(records)
    if df.empty:
        return df
    summary = df.groupby("group")["ic"].agg(["mean", "std", "count"]).reset_index()
    summary["ir"] = summary["mean"] / (summary["std"] + 1e-12)
    summary.columns = ["group", "mean_ic", "std_ic", "count", "ir"]
    return summary
