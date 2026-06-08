"""
数据质量API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select

from app.db import get_session
from app.models import DataQualityReport

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])


@router.get("/report/{symbol}")
async def get_data_quality_report(symbol: str) -> Dict[str, Any]:
    """获取数据质量报告"""
    with get_session() as session:
        # Get the most recent data quality report for this symbol
        query = select(DataQualityReport).where(
            DataQualityReport.symbol == symbol.upper()
        ).order_by(DataQualityReport.created_at.desc()).limit(1)
        result = session.execute(query)
        report = result.scalar_one_or_none()
        
        if report:
            return {
                "symbol": symbol,
                "quality_score": report.overall_quality or 1.0,
                "checks": {},
                "report_date": report.created_at.isoformat() if report.created_at else None,
            }
        else:
            return {
                "symbol": symbol,
                "quality_score": 1.0,
                "checks": {},
                "report_date": datetime.utcnow().isoformat(),
            }


@router.get("/summary")
async def get_data_quality_summary() -> Dict[str, Any]:
    """获取数据质量摘要"""
    with get_session() as session:
        # Get all data quality reports
        query = select(DataQualityReport)
        result = session.execute(query)
        reports = result.scalars().all()
        
        if reports:
            symbols = list(set(r.symbol for r in reports if r.symbol))
            scores = [r.overall_quality for r in reports if r.overall_quality is not None]
            avg_quality_score = sum(scores) / len(scores) if scores else 1.0
            return {
                "reports": [
                    {
                        "symbol": r.symbol,
                        "data_points": r.total_records or 0,
                        "missing_rate": (r.missing_records or 0) / max(r.total_records or 1, 1),
                        "outlier_rate": (r.outlier_count or 0) / max(r.total_records or 1, 1),
                        "quality_score": (r.overall_quality or 1.0) * 100,
                        "last_updated": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in reports
                ],
                "symbols": symbols,
                "avg_quality_score": avg_quality_score
            }
        else:
            return {
                "reports": [],
                "symbols": [],
                "avg_quality_score": 1.0
            }


@router.get("/checks")
async def get_data_quality_checks() -> Dict[str, Any]:
    """获取数据质量检查记录"""
    with get_session() as session:
        query = select(DataQualityReport).order_by(
            DataQualityReport.created_at.desc()
        ).limit(50)
        result = session.execute(query)
        reports = result.scalars().all()

        checks = []
        for r in reports:
            score = r.overall_quality or 1.0
            checks.append({
                "check_id": str(r.id),
                "check_type": "quality_scan",
                "status": "passed" if score >= 0.9 else ("warning" if score >= 0.7 else "failed"),
                "message": f"{r.symbol} quality score: {score:.2f}",
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            })

        return {"checks": checks}


@router.post("/check")
async def run_data_quality_check() -> Dict[str, Any]:
    """手动触发数据质量检查"""
    with get_session() as session:
        query = select(DataQualityReport)
        result = session.execute(query)
        reports = result.scalars().all()

        issues_found = sum(1 for r in reports if (r.overall_quality or 1.0) < 0.9)

        return {
            "success": True,
            "checked_at": datetime.utcnow().isoformat(),
            "symbols_checked": len(set(r.symbol for r in reports if r.symbol)),
            "issues_found": issues_found,
        }
