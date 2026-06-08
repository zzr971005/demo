from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_db
from app.config import Settings, get_config
from app.crud import (
    get_dashboard_summary_data,
    get_equity_curve_data,
    get_unresolved_risk_events,
)
from app.models import RiskEvent

router = APIRouter(tags=["dashboard"])


class SymbolSummaryItem(BaseModel):
    symbol: str
    name: str
    mode: str = "OFF"
    current_margin: float = 0.0
    max_margin: float
    position_direction: str = "NONE"
    position_volume: int = 0
    unrealized_pnl: float = 0.0
    today_pnl: float = 0.0
    running_strategies_count: int = 0
    regime: Optional[str] = None
    last_signal_at: Optional[datetime] = None


class EvolutionSummary(BaseModel):
    total_generations: int = 0
    current_generation: int = 0
    population_size: int = 0
    elite_count: int = 0
    last_evolution_time: Optional[datetime] = None
    status: str = "IDLE"


class RiskSummary(BaseModel):
    total_margin_usage: float = 0.0
    max_total_margin: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    circuit_breaker_triggered: bool = False
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


class DashboardSummaryResponse(BaseModel):
    symbols: List[SymbolSummaryItem]
    evolution: EvolutionSummary
    risk: RiskSummary
    updated_at: datetime


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    summary="Get dashboard summary",
)
async def get_dashboard_summary(
    settings: Settings = Depends(get_config),
    db=Depends(get_db),
) -> DashboardSummaryResponse:
    all_symbols = settings.system.symbols.all_symbols
    db_data = get_dashboard_summary_data(db)
    
    symbol_items = []
    
    for symbol, config in all_symbols.items():
        # 从数据库获取品种状态
        db_symbol_data = next((s for s in db_data["symbols"] if s["symbol"] == symbol), None)
        
        symbol_items.append(SymbolSummaryItem(
            symbol=symbol,
            name=config.name,
            mode=db_symbol_data["mode"] if db_symbol_data else "OFF",
            max_margin=config.max_margin,
            today_pnl=db_symbol_data["today_pnl"] if db_symbol_data else 0.0,
            running_strategies_count=1 if (db_symbol_data and db_symbol_data["running_strategy"]) else 0,
        ))
    
    evolution_data = db_data["evolution"]
    risk_counts = db_data["risk"]
    
    return DashboardSummaryResponse(
        symbols=symbol_items,
        evolution=EvolutionSummary(
            total_generations=evolution_data["total_generations"],
            current_generation=evolution_data["current_generation"],
            population_size=evolution_data["population_size"],
            elite_count=evolution_data["elite_count"],
        ),
        risk=RiskSummary(
            max_total_margin=settings.system.risk.max_total_margin_ratio,
            critical_count=risk_counts.get("CRITICAL", 0),
            high_count=risk_counts.get("HIGH", 0),
            medium_count=risk_counts.get("MEDIUM", 0),
            low_count=risk_counts.get("LOW", 0),
        ),
        updated_at=datetime.utcnow(),
    )


class EquityCurvePoint(BaseModel):
    date: str
    equity: float
    daily_pnl: float


@router.get(
    "/dashboard/equity-curve",
    response_model=List[EquityCurvePoint],
    summary="Get equity curve data",
)
async def get_equity_curve(
    days: int = 30,
    db=Depends(get_db),
) -> List[EquityCurvePoint]:
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be at least 1")
    if days > 365:
        raise HTTPException(status_code=400, detail="days cannot exceed 365")
    
    data = get_equity_curve_data(db, days)
    return [EquityCurvePoint(**item) for item in data]


class AlertItem(BaseModel):
    id: int
    event_type: str
    symbol: Optional[str]
    level: str
    message: str
    metric_value: Optional[float]
    metric_threshold: Optional[float]
    triggered_at: datetime
    is_resolved: bool


@router.get(
    "/dashboard/alerts",
    response_model=List[AlertItem],
    summary="Get recent alerts",
)
async def get_alerts(
    limit: int = 20,
    db=Depends(get_db),
) -> List[AlertItem]:
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be at least 1")
    if limit > 100:
        raise HTTPException(status_code=400, detail="limit cannot exceed 100")
    
    events = get_unresolved_risk_events(db, limit)
    return [AlertItem(
        id=event.id,
        event_type=event.event_type,
        symbol=event.symbol,
        level=event.level.value,
        message=event.message,
        metric_value=event.metric_value,
        metric_threshold=event.metric_threshold,
        triggered_at=event.triggered_at,
        is_resolved=event.is_resolved,
    ) for event in events]
