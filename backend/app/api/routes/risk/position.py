"""
仓位限制配置API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import PositionLimitConfig as PositionLimitConfigModel

router = APIRouter(prefix="/api/position-limit", tags=["position-limit"])


class PositionLimitRequest(BaseModel):
    symbol: str
    max_position_ratio: float
    max_positions: int = 10


@router.get("/config")
async def get_position_limit_config() -> Dict[str, Any]:
    """获取仓位限制配置"""
    with get_session() as session:
        query = select(PositionLimitConfigModel)
        result = session.execute(query)
        configs = result.scalars().all()
        
        return {
            "config": [
                {
                    "id": c.id,
                    "symbol": c.symbol,
                    "max_positions": c.max_positions,
                    "max_position_ratio": c.max_position_ratio,
                    "max_position_value": c.max_position_value,
                    "is_active": c.is_active,
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in configs
            ]
        }


@router.post("/config")
async def create_position_limit_config(config: PositionLimitRequest) -> Dict[str, Any]:
    """创建仓位限制配置"""
    with get_session() as session:
        new_config = PositionLimitConfigModel(
            symbol=config.symbol.upper(),
            max_position_ratio=config.max_position_ratio,
            max_positions=config.max_positions,
        )
        session.add(new_config)
        session.commit()
        
        return {
            "success": True,
            "created_at": datetime.utcnow()
        }


@router.put("/config/{symbol}")
async def update_position_limit_config(
    symbol: str,
    config: PositionLimitRequest
) -> Dict[str, Any]:
    """更新仓位限制配置"""
    with get_session() as session:
        query = select(PositionLimitConfigModel).where(
            PositionLimitConfigModel.symbol == symbol.upper()
        )
        result = session.execute(query)
        existing_config = result.scalar_one_or_none()
        
        if not existing_config:
            raise HTTPException(status_code=404, detail=f"Config for {symbol} not found")
        
        existing_config.max_position_ratio = config.max_position_ratio
        existing_config.max_positions = config.max_positions
        session.commit()
        
        return {
            "success": True,
            "updated_at": datetime.utcnow()
        }


@router.delete("/config/{symbol}")
async def delete_position_limit_config(symbol: str) -> Dict[str, Any]:
    """删除仓位限制配置"""
    with get_session() as session:
        query = select(PositionLimitConfigModel).where(
            PositionLimitConfigModel.symbol == symbol.upper()
        )
        result = session.execute(query)
        existing_config = result.scalar_one_or_none()
        
        if not existing_config:
            raise HTTPException(status_code=404, detail=f"Config for {symbol} not found")
        
        session.delete(existing_config)
        session.commit()
        
        return {
            "success": True,
            "deleted_at": datetime.utcnow()
        }
