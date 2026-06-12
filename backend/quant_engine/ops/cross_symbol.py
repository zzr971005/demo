"""
跨品种多因子策略（设计文档 §5.4，PR-E）。

两条子通道：
- A 广播（broadcast）：一套因子/策略应用到多个品种，按品种分散合成一条跨品种收益序列。
- B 组合（combo）：不同品种用不同因子，按权重（HRP/IC_IR/风险平价/等权）合成一条
  跨品种多因子策略收益序列。

全部基于真实行情重建的逐期收益序列，按时间戳对齐计算。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_engine.analysis.portfolio_optimizer import PortfolioOptimizer, ic_ir_weights
from quant_engine.analysis.strategy_correlation import StrategyCorrelationService

logger = logging.getLogger(__name__)

_ANNUAL = 252


def _portfolio_metrics(port_ret: np.ndarray) -> Dict[str, float]:
    if port_ret.size < 2:
        return {
            "annual_return": 0.0,
            "annual_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
        }
    ann_ret = float(np.mean(port_ret) * _ANNUAL)
    ann_vol = float(np.std(port_ret) * np.sqrt(_ANNUAL))
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    cum = np.cumprod(1 + port_ret)
    running_max = np.maximum.accumulate(cum)
    max_dd = float(np.min((cum - running_max) / running_max))
    return {
        "annual_return": ann_ret,
        "annual_volatility": ann_vol,
        "sharpe_ratio": float(sharpe),
        "max_drawdown": max_dd,
    }


def _detect_identical(series_map: Dict[str, pd.Series]) -> List[List[str]]:
    """标记收益序列完全相同的腿（同一因子在不同品种本应不同→相同即可疑）。"""
    keys = list(series_map.keys())
    groups: List[List[str]] = []
    used = set()
    for i, a in enumerate(keys):
        if a in used:
            continue
        grp = [a]
        for b in keys[i + 1 :]:
            if b in used:
                continue
            joined = (
                series_map[a].to_frame("x").join(series_map[b].to_frame("y"), how="inner").dropna()
            )
            if joined.shape[0] >= 30 and float(
                np.max(np.abs(joined["x"].to_numpy() - joined["y"].to_numpy()))
            ) < 1e-12:
                grp.append(b)
                used.add(b)
        if len(grp) > 1:
            used.update(grp)
            groups.append(grp)
    return groups


def broadcast_factor(
    formula: str,
    symbols: List[str],
    frequency: str = "1H",
    combine: str = "equal",  # equal | inv_vol
    service: Optional[StrategyCorrelationService] = None,
) -> Dict[str, Any]:
    """A 广播：一套因子应用到多个品种，分散合成跨品种收益序列。"""
    service = service or StrategyCorrelationService(frequency=frequency)
    per_symbol: List[Dict[str, Any]] = []
    series_map: Dict[str, pd.Series] = {}
    skipped: List[Dict[str, str]] = []

    for sym in symbols:
        stats = service.compute_stats(formula, sym)
        if stats is None or stats["returns"].dropna().shape[0] < 30:
            skipped.append({"symbol": sym, "reason": "数据不足或公式无效"})
            continue
        series_map[sym] = stats["returns"]
        per_symbol.append(
            {
                "symbol": sym,
                "sharpe": round(stats["sharpe"], 4),
                "calmar": round(stats["calmar"], 4),
                "max_drawdown": round(stats["max_drawdown"], 4),
                "total_trades": stats["total_trades"],
                "total_return": round(stats["total_return"], 4),
            }
        )

    if len(series_map) < 1:
        return {"formula": formula, "per_symbol": [], "skipped": skipped,
                "message": "无可用品种"}

    identical = _detect_identical(series_map)
    aligned = pd.DataFrame(series_map).dropna()
    cols = list(aligned.columns)
    mat = aligned[cols].to_numpy()

    if combine == "inv_vol":
        vol = np.std(mat, axis=0)
        inv = np.where(vol > 1e-12, 1.0 / vol, 0.0)
        w = inv / inv.sum() if inv.sum() > 0 else np.ones(len(cols)) / len(cols)
    else:
        w = np.ones(len(cols)) / len(cols)

    port_ret = mat @ w
    result = {
        "mode": "A_broadcast",
        "formula": formula,
        "combine": combine,
        "symbols_used": cols,
        "weights": {c: float(wi) for c, wi in zip(cols, w)},
        "overlap_points": int(aligned.shape[0]),
        "per_symbol": per_symbol,
        "metrics": _portfolio_metrics(port_ret),
        "skipped": skipped,
        "identical_groups": identical,
    }
    if identical:
        result["warning"] = (
            "检测到不同品种收益序列完全相同，可能为数据/编译异常"
        )
    return result


def cross_symbol_combo(
    legs: List[Dict[str, str]],  # [{symbol, formula, id?}]
    frequency: str = "1H",
    method: str = "hrp",  # hrp | ic_ir | risk_parity | sharpe | equal
    ic_ir_map: Optional[Dict[str, float]] = None,
    service: Optional[StrategyCorrelationService] = None,
) -> Dict[str, Any]:
    """B 组合：不同品种不同因子，按权重合成一条跨品种多因子策略。"""
    service = service or StrategyCorrelationService(frequency=frequency)
    series_map: Dict[str, pd.Series] = {}
    labels: Dict[str, str] = {}
    skipped: List[Dict[str, str]] = []

    for i, leg in enumerate(legs):
        sym, formula = leg.get("symbol"), leg.get("formula")
        lid = str(leg.get("id") or f"{sym}#{i}")
        ser = service.compute_return_series(formula, sym)
        if ser is None or ser.dropna().shape[0] < 30:
            skipped.append({"id": lid, "reason": "数据不足或公式无效"})
            continue
        series_map[lid] = ser
        labels[lid] = f"{sym}:{(formula or '')[:24]}"

    ids = list(series_map.keys())
    if len(ids) < 2:
        return {"mode": "B_combo", "legs": ids, "skipped": skipped,
                "message": "可用腿不足 2 条，无法组合"}

    identical = _detect_identical(series_map)
    aligned = pd.DataFrame(series_map).dropna()
    mat = aligned[ids].to_numpy()

    if method == "ic_ir":
        factors = [{"id": i, "ic_ir": (ic_ir_map or {}).get(i)} for i in ids]
        weights = ic_ir_weights(factors)
    elif method == "equal":
        weights = {i: 1.0 / len(ids) for i in ids}
    else:
        opt = PortfolioOptimizer({"optimization_method": method})
        weights = opt.optimize_portfolio([{"id": i} for i in ids], returns_matrix=mat)

    w_vec = np.array([weights[i] for i in ids])
    port_ret = mat @ w_vec
    result = {
        "mode": "B_combo",
        "method": method,
        "legs": ids,
        "labels": labels,
        "weights": {i: float(weights[i]) for i in ids},
        "overlap_points": int(aligned.shape[0]),
        "metrics": _portfolio_metrics(port_ret),
        "skipped": skipped,
        "identical_groups": identical,
    }
    if identical:
        result["warning"] = "检测到不同腿收益序列完全相同，可能为数据/编译异常"
    return result
