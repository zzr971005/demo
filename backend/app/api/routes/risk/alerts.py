"""
告警系统API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import AlertHistory

router = APIRouter(prefix="/api/alert-system", tags=["alert-system"])


class AlertRequest(BaseModel):
    alert_type: str
    level: str
    message: str
    channels: Optional[List[str]] = None


@router.post("/send")
async def send_alert(request: AlertRequest) -> Dict[str, Any]:
    """发送告警"""
    with get_session() as session:
        # Record the alert in history
        for channel in request.channels or ["email"]:
            alert = AlertHistory(
                alert_type=request.alert_type,
                level=request.level,
                message=request.message,
                channel=channel,
                sent_at=datetime.utcnow()
            )
            session.add(alert)
        
        session.commit()
        
        return {
            "success": True,
            "sent_at": datetime.utcnow()
        }


@router.get("/history")
async def get_alert_history(
    level: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """获取告警历史"""
    with get_session() as session:
        query = select(AlertHistory)
        
        if level:
            query = query.where(AlertHistory.severity == level.upper())
        if acknowledged is not None:
            query = query.where(AlertHistory.acknowledged_at.isnot(None) if acknowledged else AlertHistory.acknowledged_at.is_(None))
        
        query = query.order_by(AlertHistory.triggered_at.desc()).limit(limit)
        result = session.execute(query)
        alerts = result.scalars().all()
        
        return {
            "alerts": [
                {
                    "id": a.id,
                    "alert_type": a.alert_type,
                    "level": a.severity,
                    "message": a.message,
                    "channel": a.alert_type,
                    "sent_at": a.triggered_at.isoformat() if a.triggered_at else None,
                    "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                    "acknowledged_by": a.acknowledged_by,
                }
                for a in alerts
            ]
        }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str
) -> Dict[str, Any]:
    """确认告警"""
    with get_session() as session:
        query = select(AlertHistory).where(AlertHistory.id == alert_id)
        result = session.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        session.commit()
        
        return {
            "success": True,
            "acknowledged_at": datetime.utcnow()
        }


@router.get("/summary")
async def get_alert_summary() -> Dict[str, Any]:
    """获取告警摘要"""
    with get_session() as session:
        # Count total alerts
        total_query = select(AlertHistory)
        total_result = session.execute(total_query)
        total_alerts = len(total_result.scalars().all())
        
        # Count unacknowledged alerts
        unack_query = select(AlertHistory).where(AlertHistory.acknowledged_at.is_(None))
        unack_result = session.execute(unack_query)
        unacknowledged = len(unack_result.scalars().all())
        
        # Count critical alerts
        critical_query = select(AlertHistory).where(AlertHistory.level == "CRITICAL")
        critical_result = session.execute(critical_query)
        critical = len(critical_result.scalars().all())
        
        return {
            "total_alerts": total_alerts,
            "unacknowledged": unacknowledged,
            "critical": critical
        }


# 告警配置（内存存储，可扩展为数据库）
_alert_config: Dict[str, Any] = {
    "channels": ["email", "system"],
    "thresholds": {
        "max_drawdown": 0.1,
        "position_limit": 0.8,
        "daily_loss_limit": 5000,
    },
    "notification_enabled": True,
    "escalation_delay_minutes": 5,
}


@router.get("/config")
async def get_alert_config() -> Dict[str, Any]:
    """获取告警配置"""
    return _alert_config


@router.post("/config")
async def update_alert_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """更新告警配置"""
    global _alert_config
    _alert_config.update(config)
    return {"success": True, "config": _alert_config}
