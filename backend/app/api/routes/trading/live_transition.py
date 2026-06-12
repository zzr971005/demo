"""
实盘衔接API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import LiveTransitionCandidate

router = APIRouter(prefix="/api/live-transition", tags=["live-transition"])


def _evaluation_period_days(c: LiveTransitionCandidate) -> Optional[int]:
    if c.paper_test_start and c.paper_test_end:
        return (c.paper_test_end - c.paper_test_start).days
    return None


def _candidate_to_dict(c: LiveTransitionCandidate) -> Dict[str, Any]:
    """Serialize a candidate using the real model columns."""
    is_live = c.live_start is not None
    return {
        "strategy_id": c.candidate_id,
        "symbol": c.symbol,
        "transition_status": c.transition_status,
        "transition_score": c.transition_score,
        "evaluation_period_days": _evaluation_period_days(c),
        "current_metrics": {
            "sharpe": c.live_sharpe if is_live else c.paper_sharpe,
            "return": c.live_return if is_live else c.paper_return,
            "drawdown": c.live_max_dd if is_live else c.paper_max_dd,
        },
        "paper_metrics": {
            "sharpe": c.paper_sharpe,
            "return": c.paper_return,
            "drawdown": c.paper_max_dd,
        },
        "is_ready": c.transition_status in ("approved", "completed"),
        "promoted_at": c.live_start.isoformat() if c.live_start else None,
    }


class TransitionRequest(BaseModel):
    strategy_id: str
    target_mode: str  # simulation -> live


@router.get("/candidates")
async def get_transition_candidates() -> Dict[str, Any]:
    """获取可过渡到实盘的策略候选"""
    with get_session() as session:
        query = select(LiveTransitionCandidate)
        result = session.execute(query)
        candidates = result.scalars().all()
        
        return {
            "candidates": [_candidate_to_dict(c) for c in candidates]
        }


@router.post("/strategies/{strategy_id}/promote")
async def promote_to_live(
    strategy_id: str,
    request: TransitionRequest
) -> Dict[str, Any]:
    """将策略提升到实盘"""
    with get_session() as session:
        query = select(LiveTransitionCandidate).where(LiveTransitionCandidate.candidate_id == strategy_id)
        result = session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found in candidates")
        
        candidate.transition_status = "completed"
        candidate.live_start = datetime.utcnow()
        session.commit()
        
        return {
            "strategy_id": strategy_id,
            "status": "PROMOTED",
            "promoted_at": candidate.live_start.isoformat()
        }


@router.get("/strategies/{strategy_id}/evaluation")
async def get_transition_evaluation(strategy_id: str) -> Dict[str, Any]:
    """获取过渡评估"""
    with get_session() as session:
        query = select(LiveTransitionCandidate).where(LiveTransitionCandidate.candidate_id == strategy_id)
        result = session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if candidate:
            return _candidate_to_dict(candidate)
        else:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found in candidates")
