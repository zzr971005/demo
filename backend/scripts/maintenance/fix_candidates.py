"""修复 candidates.py 编码问题"""
import sys
from pathlib import Path

# 读取并重新写
content = '''from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_config, get_sqlite
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
    summary="Get candidate strategies list",
)
async def list_candidates(
    symbol: Optional[str] = Query(default=None),
    status: Optional[CandidateStatus] = Query(default=None),
    regime: Optional[CandidateRegime] = Query(default=None),
    generation: Optional[int] = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_config),
) -> CandidateListResponse:
    if symbol and symbol not in settings.system.symbols.all_symbols:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {symbol} not found",
        )

    return CandidateListResponse(total=0, items=[])


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateDetailResponse,
    summary="Get candidate strategy detail",
)
async def get_candidate(
    candidate_id: str,
    settings: Settings = Depends(get_config),
) -> CandidateDetailResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )


@router.put(
    "/candidates/{candidate_id}",
    summary="Update candidate strategy",
)
async def update_candidate(
    candidate_id: str,
    request: CandidateUpdateRequest,
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )


@router.post(
    "/candidates/{candidate_id}/activate",
    summary="Activate candidate strategy",
)
async def activate_candidate(
    candidate_id: str,
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )


@router.post(
    "/candidates/{candidate_id}/retire",
    summary="Retire candidate strategy",
)
async def retire_candidate(
    candidate_id: str,
    request: CandidateUpdateRequest,
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented",
    )
'''

with open("app/api/routes/candidates.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed candidates.py")
