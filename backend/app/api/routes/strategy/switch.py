"""
策略切换API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import StrategyWeight, StrategySwitchHistory

router = APIRouter(prefix="/api/strategy-switch", tags=["strategy-switch"])


class SwitchRequest(BaseModel):
    symbol: str
    old_strategy_id: Optional[str] = None
    new_strategy_id: str
    reason: str


@router.post("/switch")
async def switch_strategy(request: SwitchRequest) -> Dict[str, Any]:
    """切换策略"""
    with get_session() as session:
        # Record the switch in history
        switch_history = StrategySwitchHistory(
            symbol=request.symbol.upper(),
            old_strategy_id=request.old_strategy_id,
            new_strategy_id=request.new_strategy_id,
            switch_reason=request.reason,
            switched_at=datetime.utcnow(),
        )
        session.add(switch_history)
        
        # Update strategy weights
        if request.old_strategy_id:
            # Set old strategy weight to 0
            query = select(StrategyWeight).where(
                StrategyWeight.symbol == request.symbol.upper(),
                StrategyWeight.strategy_id == request.old_strategy_id
            )
            result = session.execute(query)
            old_weight = result.scalar_one_or_none()
            if old_weight:
                old_weight.weight = 0.0
        
        # Set new strategy weight to 1.0
        query = select(StrategyWeight).where(
            StrategyWeight.symbol == request.symbol.upper(),
            StrategyWeight.strategy_id == request.new_strategy_id
        )
        result = session.execute(query)
        new_weight = result.scalar_one_or_none()
        if new_weight:
            new_weight.weight = 1.0
        else:
            # Create new weight entry
            new_weight = StrategyWeight(
                symbol=request.symbol.upper(),
                strategy_id=request.new_strategy_id,
                weight=1.0,
            )
            session.add(new_weight)
        
        session.commit()
        
        return {
            "success": True,
            "symbol": request.symbol,
            "old_strategy_id": request.old_strategy_id,
            "new_strategy_id": request.new_strategy_id,
            "switched_at": datetime.utcnow()
        }


@router.get("/history")
async def get_switch_history(
    symbol: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """获取切换历史"""
    with get_session() as session:
        query = select(StrategySwitchHistory)
        
        if symbol:
            query = query.where(StrategySwitchHistory.symbol == symbol.upper())
        
        query = query.order_by(StrategySwitchHistory.switched_at.desc()).limit(limit)
        result = session.execute(query)
        history = result.scalars().all()
        
        return {
            "history": [
                {
                    "id": h.id,
                    "symbol": h.symbol,
                    "old_strategy_id": h.old_strategy_id,
                    "new_strategy_id": h.new_strategy_id,
                    "switch_reason": h.switch_reason,
                    "old_sharpe": h.old_sharpe,
                    "new_sharpe": h.new_sharpe,
                    "switched_at": h.switched_at.isoformat(),
                    "status": h.status,
                }
                for h in history
            ]
        }


@router.get("/weights")
async def get_all_strategy_weights() -> Dict[str, Any]:
    """获取所有策略权重"""
    with get_session() as session:
        query = select(StrategyWeight)
        result = session.execute(query)
        weights = result.scalars().all()
        
        return {
            "weights": [
                {
                    "factor_id": w.strategy_id,
                    "symbol": w.symbol,
                    "weight": w.weight,
                }
                for w in weights
            ]
        }


@router.get("/weights/{symbol}")
async def get_strategy_weights(symbol: str) -> Dict[str, Any]:
    """获取策略权重"""
    with get_session() as session:
        query = select(StrategyWeight).where(StrategyWeight.symbol == symbol.upper())
        result = session.execute(query)
        weights = result.scalars().all()
        
        weights_dict = {w.strategy_id: w.weight for w in weights}
        
        return {
            "symbol": symbol,
            "weights": weights_dict
        }


@router.post("/weights/{symbol}/update")
async def update_strategy_weights(
    symbol: str,
    strategies: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """更新策略权重"""
    with get_session() as session:
        for strategy in strategies:
            strategy_id = strategy.get("strategy_id")
            weight = strategy.get("weight", 0.0)
            
            query = select(StrategyWeight).where(
                StrategyWeight.symbol == symbol.upper(),
                StrategyWeight.strategy_id == strategy_id
            )
            result = session.execute(query)
            existing_weight = result.scalar_one_or_none()
            
            if existing_weight:
                existing_weight.weight = weight
            else:
                new_weight = StrategyWeight(
                    symbol=symbol.upper(),
                    strategy_id=strategy_id,
                    weight=weight,
                )
                session.add(new_weight)
        
        session.commit()
        
        return {
            "success": True,
            "updated_at": datetime.utcnow()
        }
