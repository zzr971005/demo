"""
订单类型API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select
import uuid

from app.db import get_session
from app.models import OrderTypeConfig
from quant_engine.ops.tqsdk_trading import (
    get_trading_engine,
    TradingMode,
    OrderDirection,
    OrderOffset,
)
from app.config import get_settings

router = APIRouter(prefix="/api/order-types", tags=["order-types"])


class OrderRequest(BaseModel):
    symbol: str
    direction: str
    volume: int
    order_type: str
    price: Optional[float] = None
    stop_price: Optional[float] = None
    take_profit_price: Optional[float] = None


@router.get("/types")
async def get_order_types() -> Dict[str, Any]:
    """获取所有订单类型配置"""
    with get_session() as session:
        query = select(OrderTypeConfig)
        result = session.execute(query)
        configs = result.scalars().all()

        if not configs:
            # Return default types if none configured
            return {
                "types": [
                    {"id": "MARKET", "name": "市价单", "enabled": True, "description": "按当前市场价格立即成交"},
                    {"id": "LIMIT", "name": "限价单", "enabled": True, "description": "指定价格挂单等待成交"},
                    {"id": "STOP", "name": "止损单", "enabled": True, "description": "达到止损价时触发市价单"},
                    {"id": "STOP_LIMIT", "name": "止损限价单", "enabled": False, "description": "达到止损价时触发限价单"},
                    {"id": "TRAILING_STOP", "name": "追踪止损", "enabled": False, "description": "跟随价格移动的动态止损"},
                ]
            }

        return {
            "types": [
                {
                    "id": c.order_type,
                    "name": c.display_name if hasattr(c, 'display_name') else c.order_type,
                    "enabled": c.is_enabled,
                    "description": c.description if hasattr(c, 'description') else "",
                }
                for c in configs
            ]
        }


@router.put("/types/{type_id}")
async def update_order_type(type_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """更新订单类型配置（启用/禁用）"""
    with get_session() as session:
        query = select(OrderTypeConfig).where(OrderTypeConfig.order_type == type_id.upper())
        result = session.execute(query)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Order type {type_id} not found")

        if "enabled" in body:
            config.is_enabled = body["enabled"]
        session.commit()

        return {"success": True, "type_id": type_id, "enabled": config.is_enabled}


@router.post("/order")
async def create_order(request: OrderRequest) -> Dict[str, Any]:
    """创建订单"""
    config = get_settings()
    
    with get_session() as session:
        # Check if order type is enabled
        query = select(OrderTypeConfig).where(OrderTypeConfig.order_type == request.order_type.upper())
        result = session.execute(query)
        order_type_config = result.scalar_one_or_none()
        
        if not order_type_config or not order_type_config.is_enabled:
            raise HTTPException(status_code=400, detail=f"Order type {request.order_type} is not enabled")
        
        # Get trading engine
        engine = get_trading_engine()
        
        # Connect to TQSDK if not connected
        if not engine.connected:
            success = engine.connect(
                mode=TradingMode.PAPER,
                account_id=config.tqsdk_account,
                password=config.tqsdk_password
            )
            if not success:
                raise HTTPException(
                    status_code=503,
                    detail="Failed to connect to trading system"
                )
        
        # Determine order direction and offset
        direction = OrderDirection.BUY if request.direction.upper() == "BUY" else OrderDirection.SELL
        offset = OrderOffset.OPEN  # Default to OPEN for new orders
        
        # Submit order to TQSDK
        limit_price = request.price if request.order_type.upper() == "LIMIT" else None
        tq_order_id = engine.insert_order(
            symbol=request.symbol.upper(),
            direction=direction,
            offset=offset,
            volume=request.volume,
            limit_price=limit_price
        )
        
        if not tq_order_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to submit order to trading system"
            )
        
        order_id = f"order_{uuid.uuid4().hex[:16]}"
        
        return {
            "success": True,
            "order_id": order_id,
            "tq_order_id": tq_order_id,
            "status": "PENDING",
            "created_at": datetime.utcnow()
        }


@router.delete("/order/{order_id}")
async def cancel_order(order_id: str) -> Dict[str, Any]:
    """取消订单"""
    config = get_settings()
    
    # Get trading engine
    engine = get_trading_engine()
    
    # Connect to TQSDK if not connected
    if not engine.connected:
        success = engine.connect(
            mode=TradingMode.PAPER,
            account_id=config.tqsdk_account,
            password=config.tqsdk_password
        )
        if not success:
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to trading system"
            )
    
    # Cancel order in TQSDK
    cancel_success = engine.cancel_order(order_id)
    
    if not cancel_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel order in trading system"
        )
    
    return {
        "success": True,
        "order_id": order_id,
        "cancelled_at": datetime.utcnow()
    }


@router.get("/order/{order_id}")
async def get_order(order_id: str) -> Dict[str, Any]:
    """获取订单"""
    config = get_settings()
    
    # Get trading engine
    engine = get_trading_engine()
    
    # Connect to TQSDK if not connected
    if not engine.connected:
        success = engine.connect(
            mode=TradingMode.PAPER,
            account_id=config.tqsdk_account,
            password=config.tqsdk_password
        )
        if not success:
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to trading system"
            )
    
    # Get order status from TQSDK
    order_status = engine.get_order_status(order_id)
    
    if not order_status:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found"
        )
    
    return {
        "order_id": order_id,
        "symbol": order_status.get("symbol"),
        "direction": order_status.get("direction"),
        "offset": order_status.get("offset"),
        "volume": order_status.get("volume"),
        "price": order_status.get("price"),
        "status": order_status.get("status"),
        "filled_volume": order_status.get("filled_volume"),
        "create_time": order_status.get("create_time"),
        "update_time": order_status.get("update_time")
    }


@router.get("/orders")
async def get_orders(
    symbol: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """获取订单列表"""
    config = get_settings()
    
    # Get trading engine
    engine = get_trading_engine()
    
    # Connect to TQSDK if not connected
    if not engine.connected:
        success = engine.connect(
            mode=TradingMode.PAPER,
            account_id=config.tqsdk_account,
            password=config.tqsdk_password
        )
        if not success:
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to trading system"
            )
    
    # Get account info which includes positions
    account_info = engine.get_account_info()
    positions = engine.get_positions()
    
    # Convert positions to order-like format
    orders = []
    for symbol_key, pos_data in positions.items():
        if symbol and symbol.upper() != symbol_key.upper():
            continue
        
        # Create order entries from positions
        if pos_data.get("volume_long", 0) > 0:
            orders.append({
                "order_id": f"pos_long_{symbol_key}",
                "symbol": symbol_key,
                "direction": "BUY",
                "offset": "OPEN",
                "volume": pos_data.get("volume_long", 0),
                "price": pos_data.get("open_price_long", 0),
                "status": "FILLED",
                "filled_volume": pos_data.get("volume_long", 0)
            })
        
        if pos_data.get("volume_short", 0) > 0:
            orders.append({
                "order_id": f"pos_short_{symbol_key}",
                "symbol": symbol_key,
                "direction": "SELL",
                "offset": "OPEN",
                "volume": pos_data.get("volume_short", 0),
                "price": pos_data.get("open_price_short", 0),
                "status": "FILLED",
                "filled_volume": pos_data.get("volume_short", 0)
            })
    
    return {
        "orders": orders,
        "account_balance": account_info.get("balance", 0),
        "available": account_info.get("available", 0)
    }
