"""
策略×策略 相关度 API（按最新部署/候选多因子策略实时构建）。

与 ``/api/correlation-analysis``（品种×品种、读预存表）不同：本端点基于
每个策略公式在真实行情上重建的收益序列，实时计算策略间相关度二维矩阵。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Candidate, CandidateStatus
import numpy as np
import pandas as pd

from quant_engine.analysis.portfolio_optimizer import PortfolioOptimizer, ic_ir_weights
from quant_engine.analysis.strategy_correlation import StrategyCorrelationService
from quant_engine.ops.strategy_selector import select_top2_low_correlation
from quant_engine.validation.pbo_dsr import dsr as deflated_sharpe

router = APIRouter(
    prefix="/api/strategy-correlation", tags=["strategy-correlation"]
)

# 视为"已部署/在跑"的候选状态
_DEPLOYED_STATUSES = [
    CandidateStatus.DEPLOYABLE,
    CandidateStatus.RUNNING,
    CandidateStatus.PAPER,
    CandidateStatus.VALIDATED,
]


class StrategyCorrelationRequest(BaseModel):
    # 显式传入策略（每项含 id/symbol/formula），优先级最高
    strategies: Optional[List[Dict[str, Any]]] = None
    # 不传 strategies 时按以下条件从候选库取
    symbols: Optional[List[str]] = None
    scope: str = "selected"  # selected=已选策略, deployed=已部署候选
    frequency: str = "1H"
    threshold: float = 0.5
    limit: int = 50


def _collect_strategies(
    session: Session, req: StrategyCorrelationRequest
) -> List[Dict[str, Any]]:
    if req.strategies:
        return req.strategies

    query = session.query(Candidate).filter(Candidate.formula.isnot(None))
    if req.scope == "selected":
        query = query.filter(Candidate.is_selected_strategy.is_(True))
    elif req.scope == "deployed":
        query = query.filter(Candidate.status.in_(_DEPLOYED_STATUSES))
    # scope == "all"/"candidates": 不按状态过滤，取候选池（选择流水线落地前可用）
    if req.symbols:
        query = query.filter(Candidate.symbol.in_(req.symbols))

    order_col = getattr(Candidate, "sharpe_test", None)
    if order_col is not None:
        query = query.order_by(order_col.desc().nullslast())
    rows = query.limit(req.limit).all()
    return [
        {
            "id": str(r.id),
            "symbol": r.symbol,
            "formula": r.formula,
            "label": f"{r.symbol}:{(r.formula or '')[:24]}",
            "ic_ir": r.ic_ir,
        }
        for r in rows
    ]


@router.post("/matrix")
async def get_strategy_correlation_matrix(
    request: StrategyCorrelationRequest,
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """构建策略×策略实时相关度矩阵。"""
    strategies = _collect_strategies(session, request)
    service = StrategyCorrelationService(
        frequency=request.frequency,
        correlation_threshold=request.threshold,
    )
    return service.build_matrix(strategies, threshold=request.threshold)


class SelectTop2Request(BaseModel):
    symbols: Optional[List[str]] = None  # 不传则覆盖全部有候选的品种
    frequency: str = "1H"
    tau_corr: float = 0.5  # 低相关阈值
    dsr_floor: float = 0.0  # DSR 硬门槛
    min_trades: int = 10
    pool_per_symbol: int = 5  # 每品种参与评估的候选数（按 sharpe_train 取前 N）
    persist: bool = False  # 是否落库标记 is_selected_strategy / strategy_rank


def _symbols_with_candidates(
    session: Session, requested: Optional[List[str]]
) -> List[str]:
    if requested:
        return requested
    rows = (
        session.query(Candidate.symbol)
        .filter(Candidate.formula.isnot(None))
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


@router.post("/select-top2")
async def select_top2_per_symbol(
    request: SelectTop2Request,
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """为每个品种选出 top2 低相关多因子策略（质量分 + DSR 硬门槛 + 低相关）。

    指标全部基于真实行情重建的收益序列实时计算（DSR 用本品种候选数作多检次数），
    不依赖候选库中可能为空的 sharpe_test/dsr 列。persist=True 时落库标记。
    """
    service = StrategyCorrelationService(frequency=request.frequency)
    symbols = _symbols_with_candidates(session, request.symbols)
    results: List[Dict[str, Any]] = []

    for symbol in symbols:
        rows = (
            session.query(Candidate)
            .filter(Candidate.formula.isnot(None), Candidate.symbol == symbol)
            .order_by(Candidate.sharpe_train.desc().nullslast())
            .limit(request.pool_per_symbol)
            .all()
        )
        cand_meta: List[Dict[str, Any]] = []
        returns_map: Dict[str, Any] = {}
        n_trials = len(rows)
        for r in rows:
            stats = service.compute_stats(r.formula, symbol)
            if stats is None:
                continue
            ret = stats["returns"]
            if ret is None or ret.dropna().shape[0] < 30:
                continue
            cid = str(r.id)
            dsr_val = deflated_sharpe(
                sharpe=stats["sharpe"],
                n_trials=max(n_trials, 2),
                skewness=stats["skew"],
                kurtosis=stats["kurtosis"],
            )
            cand_meta.append(
                {
                    "id": cid,
                    "formula": r.formula,
                    "symbol": symbol,
                    "sharpe": stats["sharpe"],
                    "calmar": stats["calmar"],
                    "max_drawdown": stats["max_drawdown"],
                    "total_trades": stats["total_trades"],
                    "total_return": stats["total_return"],
                    "ic_ir": r.ic_ir,
                    "dsr": dsr_val,
                }
            )
            returns_map[cid] = ret.to_numpy()

        sel = select_top2_low_correlation(
            cand_meta,
            returns_map,
            tau_corr=request.tau_corr,
            dsr_floor=request.dsr_floor,
            min_trades=request.min_trades,
        )

        if request.persist:
            # 先清空该品种旧的选中标记，再写入新 top2
            session.query(Candidate).filter(
                Candidate.symbol == symbol,
                Candidate.is_selected_strategy.is_(True),
            ).update(
                {"is_selected_strategy": False, "strategy_rank": None},
                synchronize_session=False,
            )
            for c in sel["selected"]:
                session.query(Candidate).filter(Candidate.id == c["id"]).update(
                    {
                        "is_selected_strategy": True,
                        "strategy_rank": c["strategy_rank"],
                    },
                    synchronize_session=False,
                )

        results.append(
            {
                "symbol": symbol,
                "n_candidates": len(cand_meta),
                "selected": [
                    {
                        "id": c["id"],
                        "formula": c["formula"],
                        "strategy_rank": c["strategy_rank"],
                        "quality_score": round(c["quality_score"], 4),
                        "sharpe": round(c["sharpe"], 4),
                        "calmar": round(c["calmar"], 4),
                        "dsr": round(c["dsr"], 4),
                        "total_trades": c["total_trades"],
                    }
                    for c in sel["selected"]
                ],
                "top2_correlation": sel.get("top2_correlation"),
                "warnings": sel.get("warnings", []),
            }
        )

    if request.persist:
        session.commit()

    return {"persisted": request.persist, "results": results}


class PortfolioRequest(BaseModel):
    strategies: Optional[List[Dict[str, Any]]] = None
    symbols: Optional[List[str]] = None
    scope: str = "selected"
    method: str = "hrp"  # hrp | risk_parity | sharpe | markowitz | ic_ir | equal
    frequency: str = "1H"
    limit: int = 50


@router.post("/portfolio")
async def optimize_strategy_portfolio(
    request: PortfolioRequest,
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """对已选/部署的多因子策略做组合权重分配（HRP / IC_IR / 风险平价 等）。

    全部基于真实行情重建的收益序列，按时间戳对齐后计算。
    """
    strategies = _collect_strategies(
        session,
        StrategyCorrelationRequest(
            strategies=request.strategies,
            symbols=request.symbols,
            scope=request.scope,
            limit=request.limit,
        ),
    )
    service = StrategyCorrelationService(frequency=request.frequency)

    series_map: Dict[str, pd.Series] = {}
    meta: Dict[str, Dict[str, Any]] = {}
    for s in strategies:
        sid = str(s.get("id"))
        ser = service.compute_return_series(s.get("formula"), s.get("symbol"))
        if ser is None or ser.dropna().shape[0] < 30:
            continue
        series_map[sid] = ser
        meta[sid] = s

    ids = list(series_map.keys())
    if len(ids) < 2:
        return {
            "method": request.method,
            "weights": {i: 1.0 for i in ids},
            "labels": {i: meta[i].get("label", i) for i in ids},
            "metrics": {},
            "message": "可用策略不足 2 个，无法做组合优化",
        }

    aligned = pd.DataFrame(series_map).dropna()
    returns_matrix = aligned[ids].to_numpy()

    if request.method == "ic_ir":
        factors = [{"id": i, "ic_ir": meta[i].get("ic_ir")} for i in ids]
        weights = ic_ir_weights(factors)
    elif request.method == "equal":
        weights = {i: 1.0 / len(ids) for i in ids}
    else:
        optimizer = PortfolioOptimizer({"optimization_method": request.method})
        weights = optimizer.optimize_portfolio(
            [{"id": i} for i in ids], returns_matrix=returns_matrix
        )

    # 组合绩效（与权重同序）
    w_vec = np.array([weights[i] for i in ids])
    port_ret = returns_matrix @ w_vec
    ann_ret = float(np.mean(port_ret) * 252)
    ann_vol = float(np.std(port_ret) * np.sqrt(252))
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    cum = np.cumprod(1 + port_ret)
    running_max = np.maximum.accumulate(cum)
    max_dd = float(np.min((cum - running_max) / running_max)) if cum.size else 0.0

    return {
        "method": request.method,
        "strategy_ids": ids,
        "labels": {i: meta[i].get("label", i) for i in ids},
        "weights": {i: float(weights[i]) for i in ids},
        "overlap_points": int(aligned.shape[0]),
        "metrics": {
            "annual_return": ann_ret,
            "annual_volatility": ann_vol,
            "sharpe_ratio": float(sharpe),
            "max_drawdown": max_dd,
        },
    }
