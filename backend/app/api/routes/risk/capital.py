"""
资金管理API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import CapitalAllocation, PortfolioMetrics

router = APIRouter(prefix="/api/capital-management", tags=["capital-management"])


class CapitalAllocationRequest(BaseModel):
    strategies: List[Dict[str, float]]
    allocation_method: str = "risk_parity"


@router.get("/allocation")
async def get_capital_allocation() -> Dict[str, Any]:
    """获取资金配置"""
    with get_session() as session:
        query = select(CapitalAllocation)
        result = session.execute(query)
        allocations = result.scalars().all()
        
        allocation_dict = {a.strategy_id: a.allocation_ratio for a in allocations}
        
        return {
            "allocation": allocation_dict
        }


@router.post("/allocation")
async def update_capital_allocation(request: CapitalAllocationRequest) -> Dict[str, Any]:
    """更新资金配置"""
    with get_session() as session:
        for strategy in request.strategies:
            strategy_id = strategy.get("strategy_id")
            allocation_ratio = strategy.get("allocation_ratio", 0.0)
            
            query = select(CapitalAllocation).where(CapitalAllocation.strategy_id == strategy_id)
            result = session.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.allocation_ratio = allocation_ratio
                existing.allocation_method = request.allocation_method
                existing.updated_by = "api"
            else:
                new_allocation = CapitalAllocation(
                    strategy_id=strategy_id,
                    allocation_ratio=allocation_ratio,
                    allocation_method=request.allocation_method,
                    updated_by="api"
                )
                session.add(new_allocation)
        
        session.commit()
        
        return {
            "success": True,
            "updated_at": datetime.utcnow()
        }


@router.get("/portfolio-metrics")
async def get_portfolio_metrics() -> Dict[str, Any]:
    """获取组合指标"""
    with get_session() as session:
        # Get the most recent portfolio metrics
        query = select(PortfolioMetrics).order_by(PortfolioMetrics.evaluation_date.desc()).limit(1)
        result = session.execute(query)
        metrics = result.scalar_one_or_none()
        
        if metrics:
            return {
                "annual_return": metrics.annual_return,
                "annual_volatility": metrics.annual_volatility,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "total_capital": float(metrics.total_capital),
                "evaluation_date": metrics.evaluation_date.isoformat(),
            }
        else:
            return {
                "annual_return": 0.0,
                "annual_volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }
