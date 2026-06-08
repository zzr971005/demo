from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc

from app.api.deps import get_config
from app.config import Settings
from app.db import get_session
from app.models import RiskEvent, LiveRiskEvent, RiskLevel
from quant_engine.ops.tqsdk_trading import get_trading_engine, TradingMode, OrderDirection
from app.config import get_settings

router = APIRouter(tags=["risk"])


class RiskAlert(BaseModel):
    id: str
    level: str
    symbol: Optional[str] = None
    message: str
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: datetime
    acknowledged: bool = False


class RiskSummaryResponse(BaseModel):
    total_margin_usage: float = 0.0
    max_total_margin: float
    single_symbol_max_margin: float
    daily_max_loss: float
    current_daily_pnl: float = 0.0
    current_drawdown: float = 0.0
    active_alerts_count: int = 0
    circuit_breaker_triggered: bool = False


class PositionRiskItem(BaseModel):
    symbol: str
    position_direction: str
    position_volume: int
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    margin_used: float = 0.0
    max_drawdown: float = 0.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None


@router.get(
    "/risk/summary",
    response_model=RiskSummaryResponse,
    summary="Get risk management summary",
)
async def get_risk_summary(
    settings: Settings = Depends(get_config),
) -> RiskSummaryResponse:
    return RiskSummaryResponse(
        max_total_margin=settings.system.risk.max_total_margin_ratio,
        single_symbol_max_margin=settings.system.risk.max_margin_per_symbol,
        daily_max_loss=settings.system.risk.daily_max_loss,
    )


@router.get(
    "/risk/alerts",
    response_model=List[RiskAlert],
    summary="Get risk alerts",
)
async def get_risk_alerts(
    level: Optional[str] = Query(default=None),
    acknowledged: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_config),
) -> List[RiskAlert]:
    with get_session() as session:
        # Query from both RiskEvent and LiveRiskEvent tables
        alerts = []
        
        # From RiskEvent table
        query = select(RiskEvent)
        if level:
            query = query.where(RiskEvent.level == RiskLevel(level.upper()))
        if acknowledged is not None:
            query = query.where(RiskEvent.is_resolved == (not acknowledged))
        
        query = query.order_by(RiskEvent.triggered_at.desc()).limit(limit)
        result = session.execute(query)
        events = result.scalars().all()
        
        for e in events:
            alerts.append(
                RiskAlert(
                    id=str(e.id),
                    level=e.level.value,
                    symbol=e.symbol,
                    message=e.message,
                    metric_name=e.event_type,
                    current_value=e.metric_value,
                    threshold=e.metric_threshold,
                    created_at=e.triggered_at,
                    acknowledged=e.is_resolved,
                )
            )
        
        # From LiveRiskEvent table (if needed for more alerts)
        if len(alerts) < limit:
            query = select(LiveRiskEvent)
            if level:
                query = query.where(LiveRiskEvent.level == level.upper())
            if acknowledged is not None:
                query = query.where(LiveRiskEvent.handled == (not acknowledged))
            
            query = query.order_by(LiveRiskEvent.created_at.desc()).limit(limit - len(alerts))
            result = session.execute(query)
            live_events = result.scalars().all()
            
            for e in live_events:
                alerts.append(
                    RiskAlert(
                        id=str(e.id),
                        level=e.level,
                        symbol=e.symbol,
                        message=e.action_taken or e.event_type,
                        metric_name=e.event_type,
                        current_value=e.trigger_value,
                        threshold=e.threshold_value,
                        created_at=e.created_at,
                        acknowledged=e.handled,
                    )
                )
        
        return alerts


@router.get(
    "/risk/positions",
    response_model=List[PositionRiskItem],
    summary="Get all positions with risk metrics",
)
async def get_position_risks(
    symbol: Optional[str] = Query(default=None),
    settings: Settings = Depends(get_config),
) -> List[PositionRiskItem]:
    from app.models import Trade, TradeSide
    
    config = get_settings()
    
    with get_session() as session:
        # Get all open trades (not closed)
        query = select(Trade).where(Trade.exit_at.is_(None))
        
        if symbol:
            query = query.where(Trade.symbol == symbol.upper())
        
        result = session.execute(query)
        open_trades = result.scalars().all()
        
        # Get trading engine for current prices
        engine = get_trading_engine()
        
        # Connect to TQSDK if not connected
        if not engine.connected:
            engine.connect(
                mode=TradingMode.PAPER,
                account_id=config.tqsdk_account,
                password=config.tqsdk_password
            )
        
        # Group by symbol to calculate position risk
        position_risks = {}
        for trade in open_trades:
            sym = trade.symbol
            if sym not in position_risks:
                # Get current price from TQSDK
                quote = engine.get_quote(sym)
                current_price = float(quote["last_price"]) if quote else float(trade.entry_price)
                
                # Calculate unrealized PnL
                if trade.side == TradeSide.BUY:
                    unrealized_pnl = (current_price - float(trade.entry_price)) * trade.quantity
                else:
                    unrealized_pnl = (float(trade.entry_price) - current_price) * trade.quantity
                
                # Calculate margin used
                margin = engine.calculate_margin(sym, trade.quantity, 
                    OrderDirection.BUY if trade.side == TradeSide.BUY else OrderDirection.SELL)
                margin_used = float(margin) if margin else 0.0
                
                position_risks[sym] = {
                    "symbol": sym,
                    "position_direction": "LONG" if trade.side == TradeSide.BUY else "SHORT",
                    "position_volume": 0,
                    "entry_price": float(trade.entry_price),
                    "current_price": current_price,
                    "unrealized_pnl": unrealized_pnl,
                    "margin_used": margin_used,
                    "max_drawdown": 0.0,
                }
            
            position_risks[sym]["position_volume"] += trade.quantity
        
        return [
            PositionRiskItem(**risk_data)
            for risk_data in position_risks.values()
        ]


@router.post(
    "/risk/alerts/{alert_id}/acknowledge",
    summary="Acknowledge a risk alert",
)
async def acknowledge_alert(
    alert_id: str,
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    with get_session() as session:
        # Try to find in RiskEvent table
        query = select(RiskEvent).where(RiskEvent.id == int(alert_id))
        result = session.execute(query)
        event = result.scalar_one_or_none()
        
        if event:
            event.is_resolved = True
            event.resolved_at = datetime.utcnow()
            session.commit()
            return {"alert_id": alert_id, "status": "acknowledged"}
        
        # Try to find in LiveRiskEvent table
        query = select(LiveRiskEvent).where(LiveRiskEvent.id == int(alert_id))
        result = session.execute(query)
        live_event = result.scalar_one_or_none()
        
        if live_event:
            live_event.handled = True
            live_event.handled_at = datetime.utcnow()
            session.commit()
            return {"alert_id": alert_id, "status": "acknowledged"}
        
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@router.post(
    "/risk/circuit-breaker/reset",
    summary="Reset circuit breaker",
)
async def reset_circuit_breaker(
    settings: Settings = Depends(get_config),
) -> Dict[str, str]:
    with get_session() as session:
        # Reset all unresolved risk events
        query = select(RiskEvent).where(RiskEvent.is_resolved == False)
        result = session.execute(query)
        unresolved_events = result.scalars().all()
        
        for event in unresolved_events:
            event.is_resolved = True
            event.resolved_at = datetime.utcnow()
        
        # Reset all unhandled live risk events
        query = select(LiveRiskEvent).where(LiveRiskEvent.handled == False)
        result = session.execute(query)
        unhandled_events = result.scalars().all()
        
        for event in unhandled_events:
            event.handled = True
            event.handled_at = datetime.utcnow()
        
        session.commit()
        
        return {
            "status": "reset",
            "reset_count": len(unresolved_events) + len(unhandled_events)
        }
