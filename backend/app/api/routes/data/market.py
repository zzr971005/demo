"""
行情数据API

提供实时行情数据查询和WebSocket推送
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from datetime import datetime

from quant_engine.infra.market_data_service import (
    get_market_data_service,
    MarketDataService,
    MarketData,
    KlineData,
)

logger = logging.getLogger("quant_engine.api.market_data")

router = APIRouter(prefix="/market", tags=["market_data"])


# ============ 数据模型 ============

class MarketDataResponse(BaseModel):
    """行情数据响应"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    bid_price: float
    bid_volume: int
    ask_price: float
    ask_volume: int
    
    class Config:
        from_attributes = True


class KlineResponse(BaseModel):
    """K线数据响应"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    
    class Config:
        from_attributes = True


class SubscribeRequest(BaseModel):
    """订阅请求"""
    symbols: List[str]
    kline_period: int = 60  # 默认1分钟K线


class SubscribeResponse(BaseModel):
    """订阅响应"""
    success: bool
    message: str
    subscribed_symbols: List[str]


# ============ 依赖注入 ============

def get_market_service() -> MarketDataService:
    """获取行情服务实例"""
    return get_market_data_service(mock=False)  # 使用真实数据


# ============ API端点 ============

@router.post(
    "/subscribe",
    response_model=SubscribeResponse,
    summary="订阅行情",
    description="订阅指定品种的实时行情数据",
)
async def subscribe_market_data(
    request: SubscribeRequest,
    service: MarketDataService = Depends(get_market_service),
) -> SubscribeResponse:
    """订阅行情数据"""
    try:
        # 确保服务已启动
        if not service._running:
            if not service.connect():
                raise HTTPException(
                    status_code=500,
                    detail="Failed to connect to market data service"
                )
            service.start()
        
        # 订阅品种
        success = service.subscribe(request.symbols, request.kline_period)
        
        if success:
            return SubscribeResponse(
                success=True,
                message=f"Successfully subscribed to {len(request.symbols)} symbols",
                subscribed_symbols=list(service._subscribed_symbols),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to subscribe to some symbols"
            )
            
    except Exception as e:
        logger.error(f"Error subscribing to market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/unsubscribe",
    response_model=SubscribeResponse,
    summary="取消订阅",
    description="取消指定品种的行情订阅",
)
async def unsubscribe_market_data(
    symbols: List[str],
    service: MarketDataService = Depends(get_market_service),
) -> SubscribeResponse:
    """取消订阅行情数据"""
    try:
        service.unsubscribe(symbols)
        
        return SubscribeResponse(
            success=True,
            message=f"Successfully unsubscribed from {len(symbols)} symbols",
            subscribed_symbols=list(service._subscribed_symbols),
        )
        
    except Exception as e:
        logger.error(f"Error unsubscribing from market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tick/{symbol}",
    response_model=Optional[MarketDataResponse],
    summary="获取最新Tick",
    description="获取指定品种的最新行情数据",
)
async def get_latest_tick(
    symbol: str,
    service: MarketDataService = Depends(get_market_service),
) -> Optional[MarketDataResponse]:
    """获取最新Tick数据"""
    try:
        data = service.get_tick(symbol)
        
        if data is None:
            return None
        
        return MarketDataResponse(
            symbol=data.symbol,
            timestamp=data.timestamp,
            open=data.open,
            high=data.high,
            low=data.low,
            close=data.close,
            volume=data.volume,
            amount=data.amount,
            bid_price=data.bid_price,
            bid_volume=data.bid_volume,
            ask_price=data.ask_price,
            ask_volume=data.ask_volume,
        )
        
    except Exception as e:
        logger.error(f"Error getting tick data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ticks",
    response_model=List[MarketDataResponse],
    summary="获取所有Tick",
    description="获取所有已订阅品种的最新行情数据",
)
async def get_all_ticks(
    service: MarketDataService = Depends(get_market_service),
) -> List[MarketDataResponse]:
    """获取所有最新Tick数据"""
    try:
        ticks = service.get_all_ticks()
        
        return [
            MarketDataResponse(
                symbol=data.symbol,
                timestamp=data.timestamp,
                open=data.open,
                high=data.high,
                low=data.low,
                close=data.close,
                volume=data.volume,
                amount=data.amount,
                bid_price=data.bid_price,
                bid_volume=data.bid_volume,
                ask_price=data.ask_price,
                ask_volume=data.ask_volume,
            )
            for data in ticks.values()
        ]
        
    except Exception as e:
        logger.error(f"Error getting all tick data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/klines/{symbol}",
    response_model=List[KlineResponse],
    summary="获取K线数据",
    description="获取指定品种的历史K线数据",
)
async def get_klines(
    symbol: str,
    n: int = Query(100, ge=1, le=1000, description="K线数量"),
    service: MarketDataService = Depends(get_market_service),
) -> List[KlineResponse]:
    """获取K线数据"""
    try:
        klines = service.get_klines(symbol, n)
        
        return [
            KlineResponse(
                symbol=data.symbol,
                timestamp=data.timestamp,
                open=data.open,
                high=data.high,
                low=data.low,
                close=data.close,
                volume=data.volume,
                amount=data.amount,
            )
            for data in klines
        ]
        
    except Exception as e:
        logger.error(f"Error getting kline data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/subscribed",
    response_model=List[str],
    summary="获取已订阅品种",
    description="获取当前已订阅的所有品种列表",
)
async def get_subscribed_symbols(
    service: MarketDataService = Depends(get_market_service),
) -> List[str]:
    """获取已订阅的品种列表"""
    return list(service._subscribed_symbols)


# ============ WebSocket ============

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


@router.websocket("/ws")
async def market_data_websocket(
    websocket: WebSocket,
    service: MarketDataService = Depends(get_market_service),
):
    """WebSocket实时行情推送"""
    await manager.connect(websocket)
    
    try:
        # 启动行情服务
        if not service._running:
            if not service.connect():
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to connect to market data service"
                })
                return
            service.start()
        
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to market data stream"
        })
        
        # 设置回调函数
        async def on_tick(data: MarketData):
            await manager.broadcast({
                "type": "tick",
                "data": {
                    "symbol": data.symbol,
                    "timestamp": data.timestamp.isoformat(),
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "close": data.close,
                    "volume": data.volume,
                    "amount": data.amount,
                    "bid_price": data.bid_price,
                    "bid_volume": data.bid_volume,
                    "ask_price": data.ask_price,
                    "ask_volume": data.ask_volume,
                }
            })
        
        async def on_kline(data: KlineData):
            await manager.broadcast({
                "type": "kline",
                "data": {
                    "symbol": data.symbol,
                    "timestamp": data.timestamp.isoformat(),
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "close": data.close,
                    "volume": data.volume,
                    "amount": data.amount,
                }
            })
        
        # 添加回调
        # Note: 这里需要将同步回调转换为异步，实际实现可能需要调整
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            if data.get("action") == "subscribe":
                symbols = data.get("symbols", [])
                service.subscribe(symbols)
                await websocket.send_json({
                    "type": "subscribed",
                    "symbols": symbols
                })
                
            elif data.get("action") == "unsubscribe":
                symbols = data.get("symbols", [])
                service.unsubscribe(symbols)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "symbols": symbols
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
