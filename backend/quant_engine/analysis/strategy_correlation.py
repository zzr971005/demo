"""
策略×策略 相关度服务（基于真实行情重建每个多因子策略的收益序列）。

与 ``analysis/correlation_analysis.py``（品种×品种）不同：本模块面向
"按最新部署/候选多因子策略实时构建" 的策略相关度二维矩阵。

做法（全程真实数据、无 mock）：
  1. 用 DataHub 拉取该策略品种的真实 OHLCV；
  2. 用 formula_dsl 编译策略公式，算出因子序列；
  3. 仅用训练集前 train_ratio 段拟合分位归一化（与 gp_fitness 同口径，防泄漏）；
  4. 用向量化回测引擎（内部已 T-1 截断）得到权益曲线 → 逐期收益序列；
  5. 跨品种按时间戳对齐后计算皮尔逊相关矩阵。

收益序列按时间戳索引，跨品种用 inner join 对齐重叠区间，避免错位相关。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_engine.analysis.correlation_analysis import CorrelationAnalyzer
from quant_engine.data.unified_hub import DataHub
from quant_engine.factors.formula_dsl import expr_to_func
from quant_engine.validation.engine import VectorizedBacktestEngine

logger = logging.getLogger(__name__)

# 回测默认参数（相关度对收益尺度不敏感，故合约级参数用通用默认即可）
_DEFAULT_BACKTEST_PARAMS: Dict[str, Any] = {
    "upper_threshold": 0.5,
    "lower_threshold": -0.5,
    "direction_mode": 0,
    "max_holding_bars": 0,
    "position_size_pct": 0.95,
    "contract_value_per_lot": 50000,
    "tick_size": 1.0,
    "slippage_ticks": 1,
    "use_margin": True,
    "margin_rate": 0.12,
}


class StrategyCorrelationService:
    """从策略公式重建收益序列并计算策略×策略相关度矩阵。"""

    def __init__(
        self,
        data_hub: Optional[DataHub] = None,
        frequency: str = "1H",
        train_ratio: float = 0.7,
        correlation_threshold: float = 0.5,
    ) -> None:
        self.hub = data_hub or DataHub()
        self.frequency = frequency
        self.train_ratio = train_ratio
        self.engine = VectorizedBacktestEngine()
        self.analyzer = CorrelationAnalyzer(
            {"correlation_threshold": correlation_threshold}
        )
        self._ohlcv_cache: Dict[str, Optional[pd.DataFrame]] = {}

    # ------------------------------------------------------------------
    def _load_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        if symbol not in self._ohlcv_cache:
            try:
                df = self.hub.get_ohlcv(symbol, frequency=self.frequency)
            except Exception as e:  # noqa: BLE001
                logger.warning("加载 %s 行情失败: %s", symbol, e)
                df = None
            self._ohlcv_cache[symbol] = df
        return self._ohlcv_cache[symbol]

    @staticmethod
    def _train_quantile_normalize(fv: np.ndarray, train_ratio: float) -> np.ndarray:
        """仅用训练集前 train_ratio 段拟合中位数/IQR 归一化（防泄漏）。"""
        n = len(fv)
        train_end = max(10, int(n * train_ratio))
        train_end = min(train_end, n)
        fit = fv[:train_end]
        clean = fit[np.isfinite(fit)]
        if clean.size == 0:
            return fv
        median = float(np.median(clean))
        iqr = float(np.percentile(clean, 75) - np.percentile(clean, 25))
        if iqr <= 0:
            mn, mx = float(np.min(clean)), float(np.max(clean))
            if mx > mn:
                return 2 * (fv - mn) / (mx - mn) - 1
            return fv - median
        return (fv - median) / iqr

    # ------------------------------------------------------------------
    def compute_return_series(
        self, formula: str, symbol: str
    ) -> Optional[pd.Series]:
        """重建单个策略的逐期收益序列（按时间戳索引）。"""
        df = self._load_ohlcv(symbol)
        if df is None or len(df) < 50:
            logger.warning("策略 %s/%s 行情不足，跳过", symbol, formula)
            return None
        try:
            fn, _ = expr_to_func(formula)
        except Exception as e:  # noqa: BLE001
            logger.warning("策略公式编译失败 [%s]: %s", formula, e)
            return None

        def col(name: str) -> np.ndarray:
            if name in df.columns:
                return np.asarray(df[name].values, dtype=np.float64)
            return np.full(len(df), np.nan, dtype=np.float64)

        try:
            fv = np.asarray(
                fn(
                    col("open"),
                    col("high"),
                    col("low"),
                    col("close"),
                    col("volume"),
                    col("open_interest"),
                ),
                dtype=np.float64,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("策略因子计算失败 [%s]: %s", formula, e)
            return None

        if fv.size != len(df) or not np.isfinite(fv).any():
            return None

        fvn = self._train_quantile_normalize(fv, self.train_ratio)
        try:
            result = self.engine.run(
                factor=fvn,
                open_px=col("open"),
                high_px=col("high"),
                low_px=col("low"),
                close_px=col("close"),
                params=_DEFAULT_BACKTEST_PARAMS,
                symbol=symbol,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("策略回测失败 [%s/%s]: %s", symbol, formula, e)
            return None

        equity = np.asarray(result.equity_curve, dtype=np.float64)
        if equity.size < 3:
            return None
        with np.errstate(divide="ignore", invalid="ignore"):
            rets = np.diff(equity) / equity[:-1]
        rets = np.where(np.isfinite(rets), rets, 0.0)
        return pd.Series(rets, index=df.index[1 : len(equity)])

    # ------------------------------------------------------------------
    def build_matrix(
        self,
        strategies: List[Dict[str, Any]],
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """构建策略×策略相关度矩阵。

        Parameters
        ----------
        strategies : list of dict
            每项需含 ``id``、``symbol``、``formula``；可选 ``label``。
        threshold : float, optional
            高相关阈值（默认用初始化时的 correlation_threshold）。
        """
        series_map: Dict[str, pd.Series] = {}
        labels: Dict[str, str] = {}
        skipped: List[Dict[str, str]] = []

        for s in strategies:
            sid = str(s.get("id"))
            symbol = s.get("symbol")
            formula = s.get("formula")
            if not sid or not symbol or not formula:
                skipped.append({"id": sid, "reason": "缺少 id/symbol/formula"})
                continue
            ser = self.compute_return_series(formula, symbol)
            if ser is None or ser.dropna().shape[0] < 30:
                skipped.append({"id": sid, "reason": "收益序列不足或计算失败"})
                continue
            series_map[sid] = ser
            labels[sid] = s.get("label") or f"{symbol}:{formula[:24]}"

        ids = list(series_map.keys())
        if len(ids) < 2:
            return {
                "strategy_ids": ids,
                "labels": [labels.get(i, i) for i in ids],
                "matrix": [[1.0] * len(ids) for _ in ids],
                "avg_abs_corr": 0.0,
                "high_corr_pairs": [],
                "identical_pairs": [],
                "overlap_points": 0,
                "skipped": skipped,
                "message": "可用策略不足 2 个，无法构建相关度矩阵",
            }

        # 按时间戳对齐重叠区间
        aligned = pd.DataFrame(series_map).dropna()
        overlap = int(aligned.shape[0])
        returns_dict = {sid: aligned[sid].to_numpy() for sid in ids}

        corr = self.analyzer.calculate_correlation_matrix(returns_dict)
        matrix = [[float(corr[a][b]) for b in ids] for a in ids]

        pairs = self.analyzer.find_highly_correlated_pairs(corr, threshold)
        high_corr_pairs = [
            {"a": a, "b": b, "label_a": labels[a], "label_b": labels[b],
             "correlation": float(c)}
            for (a, b, c) in pairs
        ]

        # 健全性检查：不同策略收益序列若完全相同（|corr|≈1 且数值一致）→ 告警
        identical_pairs: List[Dict[str, Any]] = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if np.allclose(returns_dict[a], returns_dict[b], atol=1e-12):
                    identical_pairs.append(
                        {"a": a, "b": b, "label_a": labels[a],
                         "label_b": labels[b]}
                    )

        off_diag = [matrix[i][j] for i in range(len(ids))
                    for j in range(len(ids)) if i != j]
        avg_abs = float(np.mean(np.abs(off_diag))) if off_diag else 0.0

        return {
            "strategy_ids": ids,
            "labels": [labels[i] for i in ids],
            "matrix": matrix,
            "avg_abs_corr": avg_abs,
            "high_corr_pairs": high_corr_pairs,
            "identical_pairs": identical_pairs,
            "overlap_points": overlap,
            "skipped": skipped,
        }
