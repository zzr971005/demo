"""
交易执行API

提供订单管理、仓位查询、风险控制等接口
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from quant_engine.runtime.order_manager import (
    get_order_manager,
    OrderManager,
    Order,
    OrderDirection,
    OrderOffset,
    OrderType,
    OrderStatus,
)
from quant_engine.runtime.position_tracker import (
    get_position_tracker,
    PositionTracker,
    Position,
)
from quant_engine.runtime.risk_manager import (
    get_risk_manager,
    RiskManager,
    RiskEvent,
    RiskLevel,
    RiskEventType,
)
from quant_engine.ops.tqsdk_trading import (
    get_trading_engine,
    init_trading_engine,
    shutdown_trading_engine,
    TradingMode,
    OrderDirection as TqOrderDirection,
    OrderOffset as TqOrderOffset,
)

router = APIRouter(prefix="/trading", tags=["交易执行"])


def get_order_mgr() -> OrderManager:
    """获取订单管理器"""
    return get_order_manager()


def get_position_trk() -> PositionTracker:
    """获取仓位跟踪器"""
    return get_position_tracker()


def get_risk_mgr() -> RiskManager:
    """获取风险管理器"""
    return get_risk_manager()


# ============== 订单接口 ==============

@router.post("/orders", response_model=Dict[str, Any])
async def create_order(
    symbol: str,
    direction: str,  # buy/sell
    offset: str,     # open/close/close_today
    volume: int,
    price: Optional[float] = None,
    order_type: str = "limit",
    strategy_id: Optional[str] = None,
    factor_id: Optional[str] = None,
    comment: Optional[str] = None,
    order_mgr: OrderManager = Depends(get_order_mgr),
):
    """创建订单"""
    try:
        # 转换枚举
        dir_enum = OrderDirection(direction.lower())
        offset_enum = OrderOffset(offset.lower())
        type_enum = OrderType(order_type.lower())
        
        order = order_mgr.create_order(
            symbol=symbol,
            direction=dir_enum,
            offset=offset_enum,
            volume=volume,
            price=price,
            order_type=type_enum,
            strategy_id=strategy_id,
            factor_id=factor_id,
            comment=comment,
        )
        
        return {
            "success": True,
            "order_id": order.order_id,
            "status": order.status.value,
            "message": "Order created successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建订单失败: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/{order_id}/submit")
async def submit_order(
    order_id: str,
    order_mgr: OrderManager = Depends(get_order_mgr),
):
    """提交订单"""
    if order_mgr.submit_order(order_id):
        return {"success": True, "message": "Order submitted"}
    raise HTTPException(status_code=400, detail="Failed to submit order")


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    reason: Optional[str] = None,
    order_mgr: OrderManager = Depends(get_order_mgr),
):
    """取消订单"""
    if order_mgr.cancel_order(order_id, reason):
        return {"success": True, "message": "Order cancelled"}
    raise HTTPException(status_code=400, detail="Failed to cancel order")


@router.get("/orders", response_model=List[Dict[str, Any]])
async def get_orders(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    strategy_id: Optional[str] = None,
    order_mgr: OrderManager = Depends(get_order_mgr),
):
    """获取订单列表"""
    status_enum = OrderStatus(status) if status else None
    orders = order_mgr.get_orders(symbol, status_enum, strategy_id)
    
    return [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "direction": o.direction.value,
            "offset": o.offset.value,
            "volume": o.volume,
            "price": o.price,
            "order_type": o.order_type.value,
            "status": o.status.value,
            "filled_volume": o.filled_volume,
            "filled_price": o.filled_price,
            "remaining_volume": o.remaining_volume,
            "created_at": o.created_at.isoformat(),
            "strategy_id": o.strategy_id,
            "factor_id": o.factor_id,
        }
        for o in orders
    ]


@router.get("/orders/active", response_model=List[Dict[str, Any]])
async def get_active_orders(
    symbol: Optional[str] = None,
    strategy_id: Optional[str] = None,
    order_mgr: OrderManager = Depends(get_order_mgr),
):
    """获取活跃订单"""
    orders = order_mgr.get_active_orders(symbol, strategy_id)
    
    return [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "direction": o.direction.value,
            "offset": o.offset.value,
            "volume": o.volume,
            "price": o.price,
            "filled_volume": o.filled_volume,
            "remaining_volume": o.remaining_volume,
            "status": o.status.value,
        }
        for o in orders
    ]


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    order_mgr: OrderManager = Depends(get_order_mgr),
):
    """获取订单详情"""
    order = order_mgr.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": order.order_id,
        "symbol": order.symbol,
        "direction": order.direction.value,
        "offset": order.offset.value,
        "volume": order.volume,
        "price": order.price,
        "order_type": order.order_type.value,
        "status": order.status.value,
        "filled_volume": order.filled_volume,
        "filled_price": order.filled_price,
        "filled_amount": order.filled_amount,
        "remaining_volume": order.remaining_volume,
        "created_at": order.created_at.isoformat(),
        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        "filled_at": order.filled_at.isoformat() if order.filled_at else None,
        "strategy_id": order.strategy_id,
        "factor_id": order.factor_id,
        "comment": order.comment,
        "error_message": order.error_message,
    }


@router.get("/orders/statistics")
async def get_order_statistics(
    order_mgr: OrderManager = Depends(get_order_mgr),
):
    """获取订单统计"""
    return order_mgr.get_statistics()


# ============== 仓位接口 ==============

@router.get("/positions", response_model=List[Dict[str, Any]])
async def get_positions(
    position_trk: PositionTracker = Depends(get_position_trk),
):
    """获取所有仓位"""
    positions = position_trk.get_all_positions()
    
    return [
        {
            "symbol": p.symbol,
            "direction": p.direction.value,
            "volume": p.volume,
            "avg_price": p.avg_price,
            "market_value": p.market_value,
            "realized_pnl": p.realized_pnl,
            "unrealized_pnl": p.unrealized_pnl,
            "total_pnl": p.total_pnl,
            "margin": p.margin,
            "is_long": p.is_long,
            "is_short": p.is_short,
            "is_flat": p.is_flat,
            "opened_at": p.opened_at.isoformat() if p.opened_at else None,
            "last_trade_at": p.last_trade_at.isoformat() if p.last_trade_at else None,
        }
        for p in positions
    ]


@router.get("/positions/non-flat", response_model=List[Dict[str, Any]])
async def get_non_flat_positions(
    position_trk: PositionTracker = Depends(get_position_trk),
):
    """获取非空仓位"""
    positions = position_trk.get_non_flat_positions()
    
    return [
        {
            "symbol": p.symbol,
            "direction": p.direction.value,
            "volume": p.volume,
            "avg_price": p.avg_price,
            "market_value": p.market_value,
            "realized_pnl": p.realized_pnl,
            "unrealized_pnl": p.unrealized_pnl,
            "total_pnl": p.total_pnl,
            "margin": p.margin,
        }
        for p in positions
    ]


@router.get("/positions/{symbol}")
async def get_position(
    symbol: str,
    position_trk: PositionTracker = Depends(get_position_trk),
):
    """获取指定品种仓位"""
    position = position_trk.get_position(symbol)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return {
        "symbol": position.symbol,
        "direction": position.direction.value,
        "volume": position.volume,
        "avg_price": position.avg_price,
        "market_value": position.market_value,
        "realized_pnl": position.realized_pnl,
        "unrealized_pnl": position.unrealized_pnl,
        "total_pnl": position.total_pnl,
        "margin": position.margin,
        "total_commission": position.total_commission,
        "opened_at": position.opened_at.isoformat() if position.opened_at else None,
        "last_trade_at": position.last_trade_at.isoformat() if position.last_trade_at else None,
    }


@router.get("/positions/summary")
async def get_position_summary(
    position_trk: PositionTracker = Depends(get_position_trk),
):
    """获取仓位汇总"""
    return position_trk.get_position_summary()


@router.post("/positions/{symbol}/close")
async def close_position(
    symbol: str,
    price: float,
    position_trk: PositionTracker = Depends(get_position_trk),
):
    """平仓"""
    position = position_trk.close_position(symbol, price)
    if not position:
        raise HTTPException(status_code=400, detail="Failed to close position")
    
    return {
        "success": True,
        "symbol": symbol,
        "closed_volume": position.volume,
        "realized_pnl": position.realized_pnl,
    }


# ============== 风险控制接口 ==============

@router.get("/risk/events", response_model=List[Dict[str, Any]])
async def get_risk_events(
    event_type: Optional[str] = None,
    level: Optional[str] = None,
    symbol: Optional[str] = None,
    unhandled_only: bool = False,
    limit: int = Query(default=100, le=500),
    risk_mgr: RiskManager = Depends(get_risk_mgr),
):
    """获取风险事件"""
    event_type_enum = RiskEventType(event_type) if event_type else None
    level_enum = RiskLevel(level) if level else None
    
    events = risk_mgr.get_risk_events(
        event_type=event_type_enum,
        level=level_enum,
        symbol=symbol,
        unhandled_only=unhandled_only,
        limit=limit,
    )
    
    return [
        {
            "event_id": e.event_id,
            "event_type": e.event_type.value,
            "level": e.level.value,
            "symbol": e.symbol,
            "message": e.message,
            "timestamp": e.timestamp.isoformat(),
            "trigger_value": e.trigger_value,
            "threshold_value": e.threshold_value,
            "suggested_action": e.suggested_action,
            "is_handled": e.is_handled,
        }
        for e in events
    ]


@router.post("/risk/events/{event_id}/handle")
async def handle_risk_event(
    event_id: str,
    handled_by: str,
    risk_mgr: RiskManager = Depends(get_risk_mgr),
):
    """处理风险事件"""
    if risk_mgr.handle_risk_event(event_id, handled_by):
        return {"success": True, "message": "Risk event handled"}
    raise HTTPException(status_code=404, detail="Risk event not found")


@router.get("/risk/summary")
async def get_risk_summary(
    risk_mgr: RiskManager = Depends(get_risk_mgr),
):
    """获取风险汇总"""
    return risk_mgr.get_risk_summary()


@router.post("/risk/circuit-breaker/reset")
async def reset_circuit_breaker(
    risk_mgr: RiskManager = Depends(get_risk_mgr),
):
    """重置熔断"""
    risk_mgr.reset_circuit_breaker()
    return {"success": True, "message": "Circuit breaker reset"}


@router.get("/risk/status")
async def get_risk_status(
    risk_mgr: RiskManager = Depends(get_risk_mgr),
):
    """获取风险状态"""
    summary = risk_mgr.get_risk_summary()
    
    return {
        "status": "critical" if summary["circuit_breaker_level"] >= 3 else (
            "warning" if summary["circuit_breaker_level"] >= 1 else "normal"
        ),
        "circuit_breaker_level": summary["circuit_breaker_level"],
        "unhandled_events": summary["unhandled_events"],
        "critical_events": summary["critical_events"],
    }


# ============== TQSDK连接接口 ==============

class ConnectRequest(BaseModel):
    mode: str = "paper"
    account_id: Optional[str] = None
    password: Optional[str] = None

@router.post("/connect")
async def connect_tqsdk(request: ConnectRequest = Body(...)):
    """
    连接TQSDK交易引擎
    
    Args:
        request: 连接参数
            mode: 交易模式（paper=模拟盘, live=实盘）
            account_id: 账户ID（默认从环境变量读取）
            password: 密码（默认从环境变量读取）
    
    Returns:
        连接结果
    """
    try:
        # 从环境变量获取默认账户信息
        default_account = os.environ.get("TQSDK_ACCOUNT")
        default_password = os.environ.get("TQSDK_PASSWORD")
        
        # 使用传入参数或环境变量
        use_account = request.account_id or default_account
        use_password = request.password or default_password
        
        if not use_account or not use_password:
            raise HTTPException(status_code=400, detail="账户ID和密码不能为空")
        
        tq_mode = TradingMode[request.mode.upper()]
        
        success = init_trading_engine(
            mode=tq_mode,
            account_id=use_account,
            password=use_password
        )
        
        if success:
            engine = get_trading_engine()
            return {
                "success": True,
                "message": f"成功连接{request.mode}账户",
                "mode": request.mode,
                "status": engine.get_status()
            }
        else:
            raise HTTPException(status_code=500, detail="连接失败")
    
    except KeyError:
        raise HTTPException(status_code=400, detail="无效的交易模式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接失败: {str(e)}")


@router.post("/disconnect")
async def disconnect_tqsdk():
    """
    断开TQSDK连接
    
    Returns:
        断开结果
    """
    try:
        shutdown_trading_engine()
        return {
            "success": True,
            "message": "已断开连接"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"断开失败: {str(e)}")


@router.get("/tqsdk/status")
async def get_tqsdk_status():
    """
    获取TQSDK连接状态
    
    Returns:
        TQSDK状态
    """
    engine = get_trading_engine()
    return engine.get_status()


@router.get("/tqsdk/account")
async def get_tqsdk_account():
    """
    获取TQSDK账户信息
    
    Returns:
        账户信息
    """
    engine = get_trading_engine()
    
    if not engine.connected:
        raise HTTPException(status_code=400, detail="TQSDK未连接")
    
    return engine.get_account_info()


@router.get("/tqsdk/quote/{symbol}")
async def get_tqsdk_quote(symbol: str):
    """
    获取TQSDK行情报价
    
    Args:
        symbol: 合约代码
    
    Returns:
        报价信息
    """
    engine = get_trading_engine()
    
    if not engine.connected:
        raise HTTPException(status_code=400, detail="TQSDK未连接")
    
    quote = engine.get_quote(symbol)
    if quote is None:
        raise HTTPException(status_code=500, detail=f"获取报价失败: {symbol}")
    
    return quote


@router.post("/tqsdk/order")
async def place_tqsdk_order(
    symbol: str,
    direction: str,
    offset: str,
    volume: int,
    limit_price: Optional[float] = None,
):
    """
    通过TQSDK下单
    
    Args:
        symbol: 合约代码
        direction: BUY/SELL
        offset: OPEN/CLOSE/CLOSE_TODAY
        volume: 数量
        limit_price: 限价
    
    Returns:
        订单信息
    """
    engine = get_trading_engine()
    
    if not engine.connected:
        raise HTTPException(status_code=400, detail="TQSDK未连接")
    
    try:
        dir_enum = TqOrderDirection[direction.upper()]
        offset_enum = TqOrderOffset[offset.upper()]
        
        order_id = engine.insert_order(
            symbol=symbol,
            direction=dir_enum,
            offset=offset_enum,
            volume=volume,
            limit_price=limit_price
        )
        
        if order_id is None:
            raise HTTPException(status_code=500, detail="下单失败")
        
        return {
            "success": True,
            "order_id": order_id,
            "message": "下单成功"
        }
    
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"无效参数: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下单失败: {str(e)}")


@router.get("/tqsdk/margin/{symbol}/{volume}/{direction}")
async def calculate_tqsdk_margin(
    symbol: str,
    volume: int,
    direction: str,
):
    """
    计算TQSDK保证金
    
    Args:
        symbol: 合约代码
        volume: 数量
        direction: BUY/SELL
    
    Returns:
        保证金金额
    """
    engine = get_trading_engine()
    
    if not engine.connected:
        raise HTTPException(status_code=400, detail="TQSDK未连接")
    
    try:
        dir_enum = TqOrderDirection[direction.upper()]
        margin = engine.calculate_margin(symbol, volume, dir_enum)
        
        if margin is None:
            raise HTTPException(status_code=500, detail="计算保证金失败")
        
        return {
            "symbol": symbol,
            "volume": volume,
            "direction": direction,
            "margin": margin
        }
    
    except KeyError:
        raise HTTPException(status_code=400, detail="无效的方向参数")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")
