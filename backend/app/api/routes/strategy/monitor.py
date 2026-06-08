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
            query = query.where(StrategyMonitorStatus.status == status)
        
        query = query.order_by(StrategyMonitorStatus.updated_at.desc()).limit(limit)
        result = session.execute(query)
        strategies = result.scalars().all()
        
        return {
            "strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "symbol": s.symbol,
                    "status": s.status,
                    "last_check_at": s.updated_at.isoformat() if s.updated_at else None,
                    "last_signal": s.last_signal,
                    "current_pnl": s.current_pnl,
                    "current_pnl_pct": s.current_pnl_pct,
                    "max_drawdown": s.max_drawdown,
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
                "symbol": strategy.symbol,
                "status": strategy.status,
                "last_check_at": strategy.updated_at.isoformat() if strategy.updated_at else None,
                "last_signal": strategy.last_signal,
                "current_pnl": strategy.current_pnl,
                "current_pnl_pct": strategy.current_pnl_pct,
                "max_drawdown": strategy.max_drawdown,
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
