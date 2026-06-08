"""
跨市场交易API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select
import uuid
import numpy as np

from app.db import get_session
from app.models import ArbitrageOpportunity, CrossMarketTrade

router = APIRouter(prefix="/api/cross-market-trading", tags=["cross-market-trading"])


@router.get("/arbitrages")
@router.get("/arbitrage-opportunities")
async def find_arbitrage_opportunities() -> Dict[str, Any]:
    """寻找套利机会"""
    with get_session() as session:
        # Get active arbitrage opportunities
        query = select(ArbitrageOpportunity).where(ArbitrageOpportunity.status == "ACTIVE")
        result = session.execute(query)
        opportunities = result.scalars().all()
        
        return {
            "opportunities": [
                {
                    "id": o.id,
                    "symbol_a": o.symbol_a,
                    "symbol_b": o.symbol_b,
                    "opportunity_type": o.opportunity_type,
                    "expected_return": o.expected_return,
                    "risk_level": o.risk_level,
                    "detected_at": o.detected_at.isoformat(),
                    "expires_at": o.expires_at.isoformat() if o.expires_at else None,
                }
                for o in opportunities
            ]
        }


@router.get("/linkages")
@router.get("/linked-opportunities")
async def find_linked_trading_opportunities() -> Dict[str, Any]:
    """寻找联动交易机会"""
    with get_session() as session:
        # Get recent cross-market trades to find patterns
        query = select(CrossMarketTrade).order_by(
            CrossMarketTrade.trade_date.desc()
        ).limit(100)
        result = session.execute(query)
        trades = result.scalars().all()
        
        if not trades:
            return {
                "opportunities": []
            }
        
        # Analyze trades for correlation patterns
        symbol_pairs = {}
        for trade in trades:
            pair_key = f"{trade.symbol_a}_{trade.symbol_b}"
            if pair_key not in symbol_pairs:
                symbol_pairs[pair_key] = {
                    "symbol_a": trade.symbol_a,
                    "symbol_b": trade.symbol_b,
                    "trade_count": 0,
                    "avg_return": 0.0,
                    "correlation": 0.0
                }
            symbol_pairs[pair_key]["trade_count"] += 1
            symbol_pairs[pair_key]["avg_return"] += trade.profit if trade.profit else 0.0
        
        # Calculate averages and identify opportunities
        opportunities = []
        for pair_key, data in symbol_pairs.items():
            if data["trade_count"] > 0:
                data["avg_return"] /= data["trade_count"]
            
            # If there are enough trades and positive average return, it's an opportunity
            if data["trade_count"] >= 3 and data["avg_return"] > 0:
                opportunities.append({
                    "id": f"linked_{uuid.uuid4().hex[:16]}",
                    "symbol_a": data["symbol_a"],
                    "symbol_b": data["symbol_b"],
                    "opportunity_type": "LINKED_TRADING",
                    "expected_return": data["avg_return"],
                    "trade_count": data["trade_count"],
                    "correlation": data["correlation"],
                    "risk_level": "MEDIUM" if data["avg_return"] > 100 else "LOW"
                })
        
        return {
            "opportunities": opportunities
        }


@router.post("/execute")
@router.post("/execute-trade")
async def execute_cross_market_trade(
    opportunity_id: str
) -> Dict[str, Any]:
    """执行跨市场交易"""
    with get_session() as session:
        query = select(ArbitrageOpportunity).where(ArbitrageOpportunity.id == opportunity_id)
        result = session.execute(query)
        opportunity = result.scalar_one_or_none()
        
        if not opportunity:
            raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found")
        
        opportunity.status = "EXECUTED"
        session.commit()
        
        return {
            "success": True,
            "executed_at": datetime.utcnow().isoformat()
        }
