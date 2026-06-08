from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_config
from app.config import Settings

router = APIRouter(tags=["candidates"])

CandidateStatus = Literal[
    "SEED", "BACKTEST", "PAPER", "DEPLOYABLE", "RUNNING", "DEGRADED", "RETIRED"
]
CandidateRegime = Literal["TREND", "BAND", "REVERSAL", "ALL"]


class CandidateListItem(BaseModel):
    id: str
    symbol: str
    template: str
    formula: str
    status: CandidateStatus
    regime: CandidateRegime
    sharpe_train: Optional[float] = None
    sharpe_val: Optional[float] = None
    sharpe_test: Optional[float] = None
    sharpe_paper_5d: Optional[float] = None
    max_dd: Optional[float] = None
    calmar: Optional[float] = None
    generation: int
    parent_ids: Optional[str] = None
    created_at: datetime
    activated_at: Optional[datetime] = None


class CandidateListResponse(BaseModel):
    total: int
    items: List[CandidateListItem]


class CandidateDetailResponse(BaseModel):
    id: str
    symbol: str
    template: str
    formula: str
    formula_tree: Optional[Dict[str, Any]] = None
    status: CandidateStatus
    regime: CandidateRegime
    sharpe_train: Optional[float] = None
    sharpe_val: Optional[float] = None
    sharpe_test: Optional[float] = None
    sharpe_paper_5d: Optional[float] = None
    max_dd: Optional[float] = None
    calmar: Optional[float] = None
    generation: int
    parent_ids: Optional[str] = None
    children_ids: Optional[List[str]] = None
    backtest_summary: Optional[Dict[str, Any]] = None
    created_at: datetime
    activated_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    retire_reason: Optional[str] = None


class CandidateUpdateRequest(BaseModel):
    status: Optional[CandidateStatus] = None
    retire_reason: Optional[str] = None


@router.get(
    "/candidates",
    response_model=CandidateListResponse,
    summary="获取候选策略列表",
)
async def list_candidates(
    symbol: Optional[str] = Query(default=None, description="按品种过滤"),
    status_filter: Optional[CandidateStatus] = Query(default=None, alias="status", description="按状态过滤"),
    regime: Optional[CandidateRegime] = Query(default=None, description="按Regime过滤"),
    generation: Optional[int] = Query(default=None, ge=0, description="按代数过滤"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_config),
) -> CandidateListResponse:
    try:
        from sqlalchemy import select, func
        from app.models import Candidate
        from app.db import get_session

        if symbol and symbol not in settings.system.symbols.all_symbols:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"品种 {symbol} 不存在",
            )

        with get_session() as session:
            query = select(Candidate)

            if symbol:
                query = query.where(Candidate.symbol == symbol.upper())
            if status_filter:
                query = query.where(Candidate.status == status_filter)
            if regime:
                query = query.where(Candidate.regime == regime.upper())
            if generation is not None:
                query = query.where(Candidate.generation == generation)

            count_query = select(func.count()).select_from(query.subquery())
            total = session.execute(count_query).scalar() or 0

            query = query.order_by(Candidate.created_at.desc())
            query = query.offset(offset).limit(limit)

            candidates = session.execute(query).scalars().all()

            items = []
            for c in candidates:
                items.append(
                    CandidateListItem(
                        id=c.id,
                        symbol=c.symbol,
                        template=c.template or "",
                        formula=c.formula,
                        status=c.status.value if hasattr(c.status, 'value') else c.status,
                        regime=c.regime.value if hasattr(c.regime, 'value') else (c.regime or "TREND"),
                        sharpe_train=c.sharpe_train,
                        sharpe_val=c.sharpe_val,
                        sharpe_test=c.sharpe_test,
                        sharpe_paper_5d=c.sharpe_paper_5d,
                        max_dd=c.max_drawdown,
                        calmar=c.calmar,
                        generation=c.generation or 0,
                        parent_ids=c.parent_id,
                        created_at=c.created_at,
                        activated_at=c.activated_at,
                    )
                )

            return CandidateListResponse(total=total, items=items)

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取候选策略失败: {e}")
        return CandidateListResponse(total=0, items=[])


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateDetailResponse,
    summary="获取候选策略详情",
)
async def get_candidate(
    candidate_id: str,
    settings: Settings = Depends(get_config),
) -> CandidateDetailResponse:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"候选策略 {candidate_id} 不存在",
    )


@router.patch(
    "/candidates/{candidate_id}",
    response_model=CandidateDetailResponse,
    summary="更新候选策略",
)
async def update_candidate(
    candidate_id: str,
    req: CandidateUpdateRequest,
    settings: Settings = Depends(get_config),
) -> CandidateDetailResponse:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"候选策略 {candidate_id} 不存在",
    )
