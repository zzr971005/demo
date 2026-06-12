"""
交易成本API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select

from app.db import get_session
from app.models import OrderCost

router = APIRouter(prefix="/api/transaction-cost", tags=["transaction-cost"])


@router.get("/analysis")
async def get_transaction_cost_analysis(
    symbol: Optional[str] = None,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """获取交易成本分析"""
    with get_session() as session:
        query = select(OrderCost)
        
        if symbol:
            query = query.where(OrderCost.symbol == symbol.upper())
        
        result = session.execute(query)
        costs = result.scalars().all()
        
        if costs:
            total_cost = sum(float(c.total_cost) for c in costs)
            return {
                "total_cost": total_cost,
                "cost_breakdown": {
                    "commission": sum(float(c.commission) for c in costs),
                    "slippage": sum(float(c.slippage) for c in costs),
                    "impact_cost": sum(float(c.impact_cost) for c in costs),
                },
                "order_count": len(costs)
            }
        else:
            return {
                "total_cost": 0.0,
                "cost_breakdown": {},
                "order_count": 0
            }


@router.get("/analysis/{symbol}")
async def get_analysis_by_symbol(symbol: str) -> Dict[str, Any]:
    """获取品种交易成本分析（前端路径兼容）"""
    with get_session() as session:
        query = select(OrderCost).where(OrderCost.symbol == symbol.upper())
        result = session.execute(query)
        costs = result.scalars().all()
        
        if costs:
            total_commission = sum(float(c.commission) for c in costs)
            total_slippage = sum(float(c.slippage) for c in costs)
            total_impact = sum(float(c.impact_cost) for c in costs)
            total_cost = sum(float(c.total_cost) for c in costs)
            cost_per_trade = total_cost / len(costs) if costs else 0.0
            return {
                "symbol": symbol.upper(),
                "commission": total_commission,
                "slippage": total_slippage,
                "market_impact": total_impact,
                "total_cost": total_cost,
                "cost_per_trade": cost_per_trade,
            }
        else:
            return {
                "symbol": symbol.upper(),
                "commission": 0.0,
                "slippage": 0.0,
                "market_impact": 0.0,
                "total_cost": 0.0,
                "cost_per_trade": 0.0,
            }


@router.get("/by-symbol/{symbol}")
async def get_cost_by_symbol(symbol: str) -> Dict[str, Any]:
    """获取品种交易成本"""
    with get_session() as session:
        query = select(OrderCost).where(OrderCost.symbol == symbol.upper())
        result = session.execute(query)
        costs = result.scalars().all()
        
        if costs:
            total_cost = sum(float(c.total_cost) for c in costs)
            avg_cost = total_cost / len(costs) if costs else 0.0
            return {
                "symbol": symbol,
                "total_cost": total_cost,
                "avg_cost": avg_cost
            }
        else:
            return {
                "symbol": symbol,
                "total_cost": 0.0,
                "avg_cost": 0.0
            }


@router.get("/breakdown/{symbol}")
async def get_cost_breakdown(symbol: str) -> Dict[str, Any]:
    """获取品种交易成本明细"""
    with get_session() as session:
        query = select(OrderCost).where(OrderCost.symbol == symbol.upper())
        result = session.execute(query)
        costs = result.scalars().all()
        
        if costs:
            breakdown = {
                "symbol": symbol,
                "commission": sum(float(c.commission) for c in costs),
                "slippage": sum(float(c.slippage) for c in costs),
                "impact_cost": sum(float(c.impact_cost) for c in costs),
                "total_cost": sum(float(c.total_cost) for c in costs),
                "order_count": len(costs),
                "avg_commission": sum(float(c.commission) for c in costs) / len(costs) if costs else 0.0,
                "avg_slippage": sum(float(c.slippage) for c in costs) / len(costs) if costs else 0.0,
                "avg_impact_cost": sum(float(c.impact_cost) for c in costs) / len(costs) if costs else 0.0,
            }
            return breakdown
        else:
            return {
                "symbol": symbol,
                "commission": 0.0,
                "slippage": 0.0,
                "impact_cost": 0.0,
                "total_cost": 0.0,
                "order_count": 0,
                "avg_commission": 0.0,
                "avg_slippage": 0.0,
                "avg_impact_cost": 0.0,
            }
