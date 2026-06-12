"""
异常检测API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select

from app.db import get_session
from app.models import SystemAnomaly

router = APIRouter(prefix="/api/anomaly-detection", tags=["anomaly-detection"])


@router.get("/anomalies")
async def get_anomalies(
    hours: int = 24,
    severity: Optional[str] = None
) -> Dict[str, Any]:
    """获取异常"""
    with get_session() as session:
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(SystemAnomaly).where(SystemAnomaly.detected_at >= cutoff_time)
        
        if severity:
            query = query.where(SystemAnomaly.severity == severity.upper())
        
        query = query.order_by(SystemAnomaly.detected_at.desc())
        result = session.execute(query)
        anomalies = result.scalars().all()
        
        return {
            "anomalies": [
                {
                    "id": a.id,
                    "anomaly_type": a.anomaly_type,
                    "severity": a.severity,
                    "description": a.description,
                    "detected_at": a.detected_at.isoformat(),
                    "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                    "action_taken": a.action_taken,
                    "auto_resolved": a.auto_resolved,
                }
                for a in anomalies
            ]
        }


@router.get("/summary")
async def get_anomaly_summary() -> Dict[str, Any]:
    """获取异常摘要"""
    with get_session() as session:
        # Count total anomalies
        total_query = select(SystemAnomaly)
        total_result = session.execute(total_query)
        total_anomalies = len(total_result.scalars().all())
        
        # Count unresolved anomalies
        unresolved_query = select(SystemAnomaly).where(SystemAnomaly.resolved_at.is_(None))
        unresolved_result = session.execute(unresolved_query)
        unresolved = len(unresolved_result.scalars().all())
        
        # Count critical anomalies
        critical_query = select(SystemAnomaly).where(SystemAnomaly.severity == "CRITICAL")
        critical_result = session.execute(critical_query)
        critical = len(critical_result.scalars().all())
        
        return {
            "total_anomalies": total_anomalies,
            "unresolved": unresolved,
            "critical": critical
        }


@router.post("/anomalies/{anomaly_id}/recover")
async def attempt_recovery(anomaly_id: int) -> Dict[str, Any]:
    """尝试恢复"""
    with get_session() as session:
        query = select(SystemAnomaly).where(SystemAnomaly.id == anomaly_id)
        result = session.execute(query)
        anomaly = result.scalar_one_or_none()
        
        if not anomaly:
            raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")
        
        anomaly.resolved_at = datetime.utcnow()
        anomaly.action_taken = "Manual recovery attempted"
        session.commit()
        
        return {
            "success": True,
            "recovered_at": datetime.utcnow().isoformat()
        }


# 异常检测配置（内存存储，可扩展为数据库）
_anomaly_config: Dict[str, Any] = {
    "detection_interval_seconds": 60,
    "severity_thresholds": {
        "critical": 0.95,
        "high": 0.8,
        "medium": 0.6,
    },
    "auto_resolve_enabled": True,
    "notification_channels": ["system"],
}


@router.get("/config")
async def get_anomaly_config() -> Dict[str, Any]:
    """获取异常检测配置"""
    return _anomaly_config


@router.put("/config")
async def update_anomaly_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """更新异常检测配置"""
    global _anomaly_config
    _anomaly_config.update(config)
    return {"success": True, "config": _anomaly_config}
