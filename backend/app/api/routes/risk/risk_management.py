"""
风控管理API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import LiveRiskEvent, RiskConfig

router = APIRouter(prefix="/api/risk-management", tags=["risk-management"])


class RiskConfigUpdate(BaseModel):
    max_total_margin_ratio: Optional[float] = None
    daily_max_loss: Optional[float] = None
    single_symbol_max_dd: Optional[float] = None


@router.get("/events")
async def get_risk_events(
    symbol: Optional[str] = None,
    level: Optional[str] = None,
    resolved: Optional[bool] = None
) -> Dict[str, Any]:
    """获取风控事件"""
    with get_session() as session:
        query = select(LiveRiskEvent)
        
        if symbol:
            query = query.where(LiveRiskEvent.symbol == symbol.upper())
        if level:
            query = query.where(LiveRiskEvent.level == level)
        if resolved is not None:
            query = query.where(LiveRiskEvent.is_resolved == resolved)
        
        query = query.order_by(LiveRiskEvent.created_at.desc())
        result = session.execute(query)
        events = result.scalars().all()
        
        return {
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "level": e.level.value if hasattr(e.level, 'value') else e.level,
                    "symbol": e.symbol,
                    "trigger_value": e.metric_value,
                    "threshold_value": e.metric_threshold,
                    "action_taken": e.action_taken,
                    "handled": e.is_resolved,
                    "handled_at": e.resolved_at.isoformat() if e.resolved_at else None,
                    "handler": e.operator,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ]
        }


@router.get("/summary")
async def get_risk_summary() -> Dict[str, Any]:
    """获取风控摘要"""
    with get_session() as session:
        # Count total events
        total_query = select(LiveRiskEvent)
        total_result = session.execute(total_query)
        total_events = len(total_result.scalars().all())
        
        # Count unresolved events
        unresolved_query = select(LiveRiskEvent).where(LiveRiskEvent.is_resolved == False)
        unresolved_result = session.execute(unresolved_query)
        unresolved_events = len(unresolved_result.scalars().all())
        
        # Count critical events
        from app.models.base import RiskLevel
        critical_query = select(LiveRiskEvent).where(LiveRiskEvent.level == RiskLevel.CRITICAL)
        critical_result = session.execute(critical_query)
        critical_events = len(critical_result.scalars().all())
        
        return {
            "total_events": total_events,
            "unresolved_events": unresolved_events,
            "critical_events": critical_events
        }


@router.put("/config")
async def update_risk_config(config: RiskConfigUpdate) -> Dict[str, Any]:
    """更新风控配置"""
    with get_session() as session:
        # Get or create global risk config
        query = select(RiskConfig).where(RiskConfig.config_name == "global")
        result = session.execute(query)
        risk_config = result.scalar_one_or_none()
        
        if not risk_config:
            risk_config = RiskConfig(
                config_name="global",
                max_total_margin_ratio=0.8,
                daily_max_loss=0.05,
                single_symbol_max_dd=0.15,
            )
            session.add(risk_config)
        
        # Update fields if provided
        if config.max_total_margin_ratio is not None:
            risk_config.max_total_margin_ratio = config.max_total_margin_ratio
        if config.daily_max_loss is not None:
            risk_config.daily_max_loss = config.daily_max_loss
        if config.single_symbol_max_dd is not None:
            risk_config.single_symbol_max_dd = config.single_symbol_max_dd
        
        session.commit()
        
        return {
            "success": True,
            "updated_at": datetime.utcnow()
        }


@router.post("/events/{event_id}/resolve")
async def resolve_risk_event(
    event_id: int,
    handler: str,
    action: str
) -> Dict[str, Any]:
    """解决风控事件"""
    with get_session() as session:
        query = select(LiveRiskEvent).where(LiveRiskEvent.id == event_id)
        result = session.execute(query)
        event = result.scalar_one_or_none()
        
        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        
        event.is_resolved = True
        event.resolved_at = datetime.utcnow()
        event.operator = handler
        event.action_taken = action
        session.commit()
        
        return {
            "success": True,
            "resolved_at": datetime.utcnow()
        }
