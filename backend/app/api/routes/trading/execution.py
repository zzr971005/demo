"""
交易执行网关API

提供统一的交易接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional

from quant_engine.runtime.execution_gateway import (
    get_execution_gateway,
    ExecutionGateway,
    TradingMode,
    TradingConfig,
)

router = APIRouter(prefix="/execution", tags=["交易网关"])


def get_gateway() -> ExecutionGateway:
    """获取交易网关"""
    return get_execution_gateway()


@router.post("/start")
async def start_gateway(
    mode: str = "mock",
    account_id: Optional[str] = None,
    password: Optional[str] = None,
):
    """启动交易网关"""
    gateway = get_execution_gateway()
    
    # 配置
    config = TradingConfig(
        mode=TradingMode(mode.lower()),
        account_id=account_id,
        password=password,
    )
    gateway.config = config
    
    if gateway.start():
        return {
            "success": True,
            "message": f"Gateway started in {mode} mode",
            "status": gateway.get_trading_status(),
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start gateway")


@router.post("/stop")
async def stop_gateway():
    """停止交易网关"""
    gateway = get_execution_gateway()
    gateway.stop()
    
    return {
        "success": True,
        "message": "Gateway stopped",
    }


@router.get("/status")
async def get_status(
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """获取交易状态"""
    return gateway.get_trading_status()


@router.post("/order")
async def place_order(
    symbol: str,
    direction: str,  # buy/sell
    offset: str,     # open/close
    volume: int,
    price: Optional[float] = None,
    order_type: str = "limit",
    strategy_id: Optional[str] = None,
    factor_id: Optional[str] = None,
    comment: Optional[str] = None,
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """下单"""
    result = gateway.place_order(
        symbol=symbol,
        direction=direction,
        offset=offset,
        volume=volume,
        price=price,
        order_type=order_type,
        strategy_id=strategy_id,
        factor_id=factor_id,
        comment=comment,
    )
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))


@router.post("/order/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """撤单"""
    result = gateway.cancel_order(order_id)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))


@router.post("/position/{symbol}/close")
async def close_position(
    symbol: str,
    price: Optional[float] = None,
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """平仓"""
    result = gateway.close_position(symbol, price)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))


@router.post("/positions/close-all")
async def close_all_positions(
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """平掉所有仓位"""
    return gateway.close_all_positions()


@router.post("/emergency-close")
async def emergency_close(
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """紧急平仓"""
    return gateway.emergency_close_all()


@router.get("/account")
async def get_account(
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """获取账户信息"""
    return gateway.get_account_info()


@router.get("/health")
async def health_check(
    gateway: ExecutionGateway = Depends(get_gateway),
):
    """健康检查"""
    status = gateway.get_trading_status()
    
    return {
        "status": "healthy" if status["running"] else "unhealthy",
        "connected": status["connected"],
        "mode": status["mode"],
        "can_trade": status["can_trade"],
        "risk_status": status["risk_status"],
    }
