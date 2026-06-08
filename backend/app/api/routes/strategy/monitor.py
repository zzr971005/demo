"""
策略监控API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import StrategyMonitorStatus

router = APIRouter(prefix="/api/strategy-monitor", tags=["strategy-monitor"])


class StrategyEvaluationRequest(BaseModel):
    strategy_id: str
    evaluation_type: str  # simulation/backtest/live


@router.get("/strategies")
async def list_strategies(
    status: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """列出策略"""
    with get_session() as session:
        query = select(StrategyMonitorStatus)
        
        if status:
            query = query.where(StrategyMonitorStatus.status == status.upper())
        
        query = query.order_by(StrategyMonitorStatus.last_check_at.desc()).limit(limit)
        result = session.execute(query)
        strategies = result.scalars().all()
        
        return {
            "strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "status": s.status,
                    "last_check_at": s.last_check_at.isoformat(),
                    "health_score": s.health_score,
                    "performance_metrics": eval(s.performance_metrics_json) if s.performance_metrics_json else {},
                }
                for s in strategies
            ]
        }


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str) -> Dict[str, Any]:
    """获取策略详情"""
    with get_session() as session:
        query = select(StrategyMonitorStatus).where(StrategyMonitorStatus.strategy_id == strategy_id)
        result = session.execute(query)
        strategy = result.scalar_one_or_none()
        
        if strategy:
            return {
                "strategy_id": strategy_id,
                "status": strategy.status,
                "last_check_at": strategy.last_check_at.isoformat(),
                "health_score": strategy.health_score,
                "performance": eval(strategy.performance_metrics_json) if strategy.performance_metrics_json else {},
            }
        else:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")


@router.post("/strategies/{strategy_id}/evaluate")
async def evaluate_strategy(
    strategy_id: str,
    request: StrategyEvaluationRequest
) -> Dict[str, Any]:
    """评估策略"""
    return {
        "strategy_id": strategy_id,
        "evaluation_type": request.evaluation_type,
        "score": 0.0,
        "recommendation": "HOLD"
    }


@router.get("/strategies/{strategy_id}/performance")
async def get_strategy_performance(strategy_id: str) -> Dict[str, Any]:
    """获取策略绩效"""
    return {
        "strategy_id": strategy_id,
        "metrics": {}
    }
