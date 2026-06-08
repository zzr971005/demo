from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc

from app.api.deps import get_config
from app.config import Settings
from app.db import get_session
from app.models import Trade, Candidate
from quant_engine.ops.tqsdk_trading import (
    get_trading_engine,
    TradingMode,
    OrderDirection,
    OrderOffset,
)

router = APIRouter(tags=["trades"])


class Trade(BaseModel):
    id: str
    symbol: str
    direction: str
    offset: str
    volume: int
    price: float
    realized_pnl: Optional[float] = None
    commission: float = 0.0
    strategy_id: Optional[str] = None
    signal_time: Optional[datetime] = None
    fill_time: Optional[datetime] = None
    status: str = "FILLED"


class TradeListResponse(BaseModel):
    total: int
    items: List[Trade]


class Position(BaseModel):
    symbol: str
    direction: str
    volume: int
    avg_price: float
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    margin_used: float = 0.0
    realized_pnl: float = 0.0
    commission: float = 0.0
    open_time: Optional[datetime] = None


class PositionListResponse(BaseModel):
    total: int
    items: List[Position]


class Order(BaseModel):
    id: str
    symbol: str
    direction: str
    offset: str
    volume: int
    price: Optional[float] = None
    order_type: str = "LIMIT"
    status: str = "PENDING"
    filled_volume: int = 0
    strategy_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class OrderListResponse(BaseModel):
    total: int
    items: List[Order]


class ManualOrderRequest(BaseModel):
    symbol: str
    direction: str
    offset: str
    volume: int
    price: Optional[float] = None
    order_type: str = "MARKET"


@router.get(
    "/trades",
    response_model=TradeListResponse,
    summary="Get trade history",
)
async def get_trades(
    symbol: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_config),
) -> TradeListResponse:
    with get_session() as session:
        query = select(Trade)
        
        if symbol:
            query = query.where(Trade.symbol == symbol.upper())
        if start_date:
            query = query.where(Trade.entry_at >= start_date)
        if end_date:
            query = query.where(Trade.entry_at <= end_date)
        
        # Get total count
        count_query = select(Trade)
        if symbol:
            count_query = count_query.where(Trade.symbol == symbol.upper())
        if start_date:
            count_query = count_query.where(Trade.entry_at >= start_date)
        if end_date:
            count_query = count_query.where(Trade.entry_at <= end_date)
        
        total_result = session.execute(count_query)
        total = len(total_result.scalars().all())
        
        # Get paginated results
        query = query.order_by(Trade.entry_at.desc()).limit(limit).offset(offset)
        result = session.execute(query)
        trades = result.scalars().all()
        
        return TradeListResponse(
            total=total,
            items=[
                Trade(
                    id=t.id,
                    symbol=t.symbol,
                    direction=t.side.value,
                    offset="OPEN" if t.exit_at is None else "CLOSE",
                    volume=t.quantity,
                    price=float(t.entry_price),
                    realized_pnl=float(t.pnl) if t.pnl else None,
                    commission=float(t.commission) if t.commission else 0.0,
                    strategy_id=t.candidate_id,
                    signal_time=t.entry_at,
                    fill_time=t.exit_at,
                    status=t.status.value,
                )
                for t in trades
            ]
        )


@router.get(
    "/trades/{trade_id}",
    response_model=Trade,
    summary="Get trade detail",
)
async def get_trade(
    trade_id: str,
    settings: Settings = Depends(get_config),
) -> Trade:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Trade {trade_id} not found",
    )


@router.get(
    "/positions",
    response_model=PositionListResponse,
    summary="Get current positions",
)
async def get_positions(
    symbol: Optional[str] = Query(default=None),
    settings: Settings = Depends(get_config),
) -> PositionListResponse:
    with get_session() as session:
        # Get all trades that are not closed (exit_at is None)
        query = select(Trade).where(Trade.exit_at.is_(None))
        
        if symbol:
            query = query.where(Trade.symbol == symbol.upper())
        
        result = session.execute(query)
        open_trades = result.scalars().all()
        
        # Group by symbol to calculate positions
        positions = {}
        for trade in open_trades:
            sym = trade.symbol
            if sym not in positions:
                positions[sym] = {
                    "symbol": sym,
                    "direction": "LONG" if trade.side.value == "BUY" else "SHORT",
                    "volume": 0,
                    "avg_price": 0,
                    "total_value": 0,
                }
            
            positions[sym]["volume"] += trade.quantity
            positions[sym]["total_value"] += float(trade.entry_price) * trade.quantity
        
        # Calculate average price
        position_items = []
        for pos_data in positions.values():
            if pos_data["volume"] > 0:
                avg_price = pos_data["total_value"] / pos_data["volume"]
            else:
                avg_price = 0
            
            position_items.append(
                Position(
                    symbol=pos_data["symbol"],
                    direction=pos_data["direction"],
                    volume=pos_data["volume"],
                    avg_price=avg_price,
                    current_price=None,
                    unrealized_pnl=0.0,
                    margin_used=0.0,
                    realized_pnl=0.0,
                    commission=0.0,
                    open_time=None,
                )
            )
        
        return PositionListResponse(total=len(position_items), items=position_items)


@router.get(
    "/orders",
    response_model=OrderListResponse,
    summary="Get active orders",
)
async def get_orders(
    symbol: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_config),
) -> OrderListResponse:
    with get_session() as session:
        # Get trades with PENDING status
        query = select(Trade).where(Trade.status == "PENDING")
        
        if symbol:
            query = query.where(Trade.symbol == symbol.upper())
        if status:
            query = query.where(Trade.status == status.upper())
        
        query = query.order_by(Trade.entry_at.desc()).limit(limit)
        result = session.execute(query)
        pending_trades = result.scalars().all()
        
        return OrderListResponse(
            total=len(pending_trades),
            items=[
                Order(
                    id=t.id,
                    symbol=t.symbol,
                    direction=t.side.value,
                    offset="OPEN" if t.exit_at is None else "CLOSE",
                    volume=t.quantity,
                    price=float(t.entry_price) if t.entry_price else None,
                    order_type="LIMIT",
                    status=t.status.value,
                    filled_volume=0,
                    strategy_id=t.candidate_id,
                    created_at=t.entry_at,
                    updated_at=t.entry_at,
                )
                for t in pending_trades
            ]
        )


@router.post(
    "/orders",
    summary="Create manual order",
)
async def create_order(
    request: ManualOrderRequest,
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    import uuid
    from app.models import Trade, TradeSide, TradeStatus
    from app.config import get_settings
    
    config = get_settings()
    
    with get_session() as session:
        order_id = f"order_{uuid.uuid4().hex[:16]}"
        
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
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to connect to trading system"
                )
        
        # Determine order direction and offset
        direction = OrderDirection.BUY if request.direction.upper() == "BUY" else OrderDirection.SELL
        offset = OrderOffset.OPEN if request.offset.upper() == "OPEN" else OrderOffset.CLOSE
        
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit order to trading system"
            )
        
        # Create a new trade record
        new_trade = Trade(
            id=order_id,
            symbol=request.symbol.upper(),
            side=TradeSide.BUY if request.direction.upper() == "BUY" else TradeSide.SELL,
            quantity=request.volume,
            entry_price=request.price if request.price else 0,
            entry_at=datetime.utcnow(),
            status=TradeStatus.PENDING,
            is_paper=True,  # Manual orders are paper trading by default
        )
        
        session.add(new_trade)
        session.commit()
        
        return {"order_id": order_id, "tq_order_id": tq_order_id, "status": "created"}


@router.delete(
    "/orders/{order_id}",
    summary="Cancel order",
)
async def cancel_order(
    order_id: str,
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    from app.models import Trade, TradeStatus
    from app.config import get_settings
    
    config = get_settings()
    
    with get_session() as session:
        # Find the trade/order
        query = select(Trade).where(Trade.id == order_id)
        result = session.execute(query)
        trade = result.scalar_one_or_none()
        
        if not trade:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
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
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to connect to trading system"
                )
        
        # Cancel order in TQSDK
        cancel_success = engine.cancel_order(order_id)
        
        if not cancel_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel order in trading system"
            )
        
        # Update status to cancelled
        trade.status = TradeStatus.CANCELLED
        session.commit()
        
        return {"order_id": order_id, "status": "cancelled"}


@router.post(
    "/positions/{symbol}/close",
    summary="Close position",
)
async def close_position(
    symbol: str,
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    from app.models import Trade, TradeStatus, TradeSide
    from app.config import get_settings
    
    config = get_settings()
    
    with get_session() as session:
        # Find all open trades for this symbol
        query = select(Trade).where(
            Trade.symbol == symbol.upper(),
            Trade.exit_at.is_(None),
            Trade.status == TradeStatus.PENDING
        )
        result = session.execute(query)
        open_trades = result.scalars().all()
        
        if not open_trades:
            raise HTTPException(status_code=404, detail=f"No open position for {symbol}")
        
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
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to connect to trading system"
                )
        
        # Close each position by submitting opposite orders
        closed_count = 0
        for trade in open_trades:
            # Determine opposite direction
            opposite_direction = OrderDirection.SELL if trade.side == TradeSide.BUY else OrderDirection.BUY
            
            # Submit closing order
            tq_order_id = engine.insert_order(
                symbol=trade.symbol,
                direction=opposite_direction,
                offset=OrderOffset.CLOSE,
                volume=trade.quantity,
                limit_price=None  # Market order
            )
            
            if tq_order_id:
                # Mark as closed in database
                trade.exit_at = datetime.utcnow()
                trade.status = TradeStatus.FILLED
                closed_count += 1
        
        session.commit()
        
        return {"symbol": symbol, "status": "closed", "closed_count": closed_count}
