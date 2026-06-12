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
from quant_engine.analysis.strategy_correlation import StrategyCorrelationService

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
