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
            "candidates": [
                {
                    "strategy_id": c.strategy_id,
                    "evaluation_period_days": c.evaluation_period_days,
                    "min_sharpe": c.min_sharpe,
                    "max_drawdown": c.max_drawdown,
                    "current_sharpe": c.current_sharpe,
                    "current_drawdown": c.current_drawdown,
                    "is_ready": c.is_ready,
                    "promoted_at": c.promoted_at.isoformat() if c.promoted_at else None,
                }
                for c in candidates
            ]
        }


@router.post("/strategies/{strategy_id}/promote")
async def promote_to_live(
    strategy_id: str,
    request: TransitionRequest
) -> Dict[str, Any]:
    """将策略提升到实盘"""
    with get_session() as session:
        query = select(LiveTransitionCandidate).where(LiveTransitionCandidate.strategy_id == strategy_id)
        result = session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found in candidates")
        
        candidate.is_ready = True
        candidate.promoted_at = datetime.utcnow()
        session.commit()
        
        return {
            "strategy_id": strategy_id,
            "status": "PROMOTED",
            "promoted_at": datetime.utcnow().isoformat()
        }


@router.get("/strategies/{strategy_id}/evaluation")
async def get_transition_evaluation(strategy_id: str) -> Dict[str, Any]:
    """获取过渡评估"""
    with get_session() as session:
        query = select(LiveTransitionCandidate).where(LiveTransitionCandidate.strategy_id == strategy_id)
        result = session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if candidate:
            return {
                "strategy_id": strategy_id,
                "evaluation_period_days": candidate.evaluation_period_days,
                "min_sharpe": candidate.min_sharpe,
                "max_drawdown": candidate.max_drawdown,
                "current_metrics": {
                    "sharpe": candidate.current_sharpe,
                    "drawdown": candidate.current_drawdown,
                },
                "is_ready": candidate.is_ready
            }
        else:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found in candidates")
