"""
报告生成API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select
import uuid

from app.db import get_session
from app.models import GeneratedReport


class GenerateReportRequest(BaseModel):
    report_type: str
    symbol: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

router = APIRouter(prefix="/api/report-generation", tags=["report-generation"])


@router.get("/reports")
async def list_reports(
    report_type: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """列出报告"""
    with get_session() as session:
        query = select(GeneratedReport)
        
        if report_type:
            query = query.where(GeneratedReport.report_type == report_type)
        
        query = query.order_by(GeneratedReport.created_at.desc()).limit(limit)
        result = session.execute(query)
        reports = result.scalars().all()
        
        return {
            "reports": [
                {
                    "id": r.id,
                    "report_id": r.report_id,
                    "report_type": r.report_type,
                    "title": r.title,
                    "symbol": r.symbol,
                    "file_path": r.file_path,
                    "generated_at": r.created_at.isoformat(),
                    "generated_by": r.generated_by,
                    "status": r.status,
                }
                for r in reports
            ]
        }


@router.post("/reports/performance")
async def generate_performance_report(
    strategy_id: str
) -> Dict[str, Any]:
    """生成绩效报告"""
    with get_session() as session:
        report_id = f"report_{uuid.uuid4().hex[:16]}"
        report = GeneratedReport(
            report_id=report_id,
            report_type="performance",
            title=f"Performance Report - {strategy_id}",
            generated_by="api",
            file_path=f"/reports/{report_id}.pdf",
        )
        session.add(report)
        session.commit()
        
        return {
            "report_id": report_id,
            "strategy_id": strategy_id,
            "generated_at": datetime.utcnow().isoformat()
        }


@router.post("/reports/risk")
async def generate_risk_report() -> Dict[str, Any]:
    """生成风控报告"""
    with get_session() as session:
        report_id = f"report_{uuid.uuid4().hex[:16]}"
        report = GeneratedReport(
            report_id=report_id,
            report_type="risk",
            title="Risk Report",
            generated_by="api",
            file_path=f"/reports/{report_id}.pdf",
        )
        session.add(report)
        session.commit()
        
        return {
            "report_id": report_id,
            "generated_at": datetime.utcnow().isoformat()
        }


@router.post("/generate")
async def generate_report(request: GenerateReportRequest) -> Dict[str, Any]:
    """通用报告生成接口（前端调用）"""
    with get_session() as session:
        report_id = f"report_{uuid.uuid4().hex[:16]}"
        title = f"{request.report_type.title()} Report"
        if request.symbol:
            title += f" - {request.symbol.upper()}"
        
        report = GeneratedReport(
            report_id=report_id,
            report_type=request.report_type,
            title=title,
            symbol=request.symbol.upper() if request.symbol else None,
            generated_by="api",
            file_path=f"/reports/{report_id}.pdf",
            period_start=datetime.fromisoformat(request.start_date) if request.start_date else None,
            period_end=datetime.fromisoformat(request.end_date) if request.end_date else None,
        )
        session.add(report)
        session.commit()
        
        return {
            "success": True,
            "report_id": report_id,
            "generated_at": datetime.utcnow().isoformat()
        }


@router.get("/download/{report_id}")
async def download_report(report_id: str) -> Dict[str, Any]:
    """下载报告（占位）"""
    with get_session() as session:
        query = select(GeneratedReport).where(GeneratedReport.report_id == report_id)
        result = session.execute(query)
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        
        # Return report info (actual file download not implemented yet)
        return {
            "report_id": report.report_id,
            "file_path": report.file_path,
            "status": report.status,
            "message": "Report download placeholder - file generation not yet implemented"
        }


@router.get("/reports/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    """获取报告"""
    with get_session() as session:
        query = select(GeneratedReport).where(GeneratedReport.report_id == report_id)
        result = session.execute(query)
        report = result.scalar_one_or_none()
        
        if report:
            return {
                "report_id": report.report_id,
                "report_type": report.report_type,
                "title": report.title,
                "symbol": report.symbol,
                "file_path": report.file_path,
                "generated_at": report.created_at.isoformat(),
                "generated_by": report.generated_by,
                "status": report.status,
            }
        else:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
