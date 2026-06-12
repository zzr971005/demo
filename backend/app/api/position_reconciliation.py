"""
仓位对账API
持仓核对和风险控制
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

router = APIRouter(prefix="/position", tags=["position"])


class PositionStatus(Enum):
    """持仓状态"""
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    PENDING = "pending"
    ERROR = "error"


class PositionData(BaseModel):
    """持仓数据"""
    symbol: str
    direction: str
    volume: float
    open_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin_used: float
    leverage: float
    update_time: datetime


class ReconciliationItem(BaseModel):
    """对账条目"""
    symbol: str
    direction: str
    expected_volume: float
    actual_volume: float
    volume_diff: float
    expected_margin: float
    actual_margin: float
    margin_diff: float
    status: str
    discrepancy: str
    severity: str


class ReconciliationResult(BaseModel):
    """对账结果"""
    reconciliation_id: str
    start_time: datetime
    end_time: datetime
    total_positions: int
    matched_count: int
    mismatched_count: int
    pending_count: int
    items: List[ReconciliationItem]
    summary: Dict[str, float]
    status: str


class PositionAlert(BaseModel):
    """持仓告警"""
    alert_id: str
    symbol: str
    alert_type: str
    severity: str
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False


class RiskReport(BaseModel):
    """风险报告"""
    report_id: str
    generated_at: datetime
    total_exposure: float
    total_margin_used: float
    margin_utilization: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    risk_level: str
    alerts: List[PositionAlert]
    recommendations: List[str]


# 模拟数据存储
reconciliation_history: List[ReconciliationResult] = []
alerts_history: List[PositionAlert] = []


def generate_mock_positions() -> List[PositionData]:
    """生成模拟持仓数据"""
    symbols = ["KQ.m@SHFE.rb", "KQ.m@DCE.i", "KQ.m@SHFE.ag", "KQ.m@CZCE.MA"]
    positions = []
    
    for i, symbol in enumerate(symbols):
        direction = "long" if i % 2 == 0 else "short"
        volume = 10 * (i + 1)
        open_price = 3000 + i * 500
        current_price = open_price + (i - 1.5) * 50
        
        positions.append(PositionData(
            symbol=symbol,
            direction=direction,
            volume=volume,
            open_price=open_price,
            current_price=current_price,
            unrealized_pnl=(current_price - open_price) * volume * (1 if direction == "long" else -1),
            realized_pnl=i * 1000 - 500,
            margin_used=volume * open_price * 0.12,
            leverage=8.33,
            update_time=datetime.now()
        ))
    
    return positions


@router.get("/current", response_model=List[PositionData])
async def get_current_positions(symbol: Optional[str] = None):
    """
    获取当前持仓
    
    Args:
        symbol: 可选品种过滤
    
    Returns:
        持仓数据列表
    """
    positions = generate_mock_positions()
    
    if symbol:
        return [p for p in positions if p.symbol == symbol]
    return positions


@router.post("/reconcile", response_model=ReconciliationResult)
async def run_reconciliation():
    """执行仓位对账"""
    start_time = datetime.now()
    positions = generate_mock_positions()
    
    items = []
    matched_count = 0
    mismatched_count = 0
    
    for pos in positions:
        # 模拟预期值与实际值的差异
        expected_volume = pos.volume + (pos.volume * 0.05 if pos.symbol.endswith("rb") else 0)
        expected_margin = pos.margin_used + (pos.margin_used * 0.02 if pos.symbol.endswith("i") else 0)
        
        volume_diff = expected_volume - pos.volume
        margin_diff = expected_margin - pos.margin_used
        
        has_discrepancy = abs(volume_diff) > 0.1 or abs(margin_diff) > 0.1
        
        if has_discrepancy:
            status = "mismatched"
            mismatched_count += 1
            discrepancy = f"Volume: {volume_diff:.2f}, Margin: {margin_diff:.2f}"
            severity = "high" if abs(volume_diff) > pos.volume * 0.1 else "medium"
        else:
            status = "matched"
            matched_count += 1
            discrepancy = ""
            severity = "low"
        
        items.append(ReconciliationItem(
            symbol=pos.symbol,
            direction=pos.direction,
            expected_volume=expected_volume,
            actual_volume=pos.volume,
            volume_diff=volume_diff,
            expected_margin=expected_margin,
            actual_margin=pos.margin_used,
            margin_diff=margin_diff,
            status=status,
            discrepancy=discrepancy,
            severity=severity
        ))
    
    end_time = datetime.now()
    
    result = ReconciliationResult(
        reconciliation_id=f"rec_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        start_time=start_time,
        end_time=end_time,
        total_positions=len(positions),
        matched_count=matched_count,
        mismatched_count=mismatched_count,
        pending_count=0,
        items=items,
        summary={
            "total_expected_volume": sum(i.expected_volume for i in items),
            "total_actual_volume": sum(i.actual_volume for i in items),
            "total_expected_margin": sum(i.expected_margin for i in items),
            "total_actual_margin": sum(i.actual_margin for i in items),
            "match_rate": matched_count / len(items) if items else 0
        },
        status="completed"
    )
    
    reconciliation_history.append(result)
    
    # 生成告警
    for item in items:
        if item.status == "mismatched":
            alert = PositionAlert(
                alert_id=f"alert_{item.symbol.replace('.', '_')}_{datetime.now().strftime('%H%M%S')}",
                symbol=item.symbol,
                alert_type="position_mismatch",
                severity=item.severity,
                message=f"Position mismatch detected: {item.discrepancy}",
                current_value=item.actual_volume,
                threshold=item.expected_volume,
                timestamp=datetime.now()
            )
            alerts_history.append(alert)
    
    return result


@router.get("/reconciliation/history", response_model=List[ReconciliationResult])
async def get_reconciliation_history(limit: int = 10):
    """获取对账历史"""
    return reconciliation_history[-limit:]


@router.get("/reconciliation/{reconciliation_id}", response_model=ReconciliationResult)
async def get_reconciliation_detail(reconciliation_id: str):
    """获取对账详情"""
    for rec in reconciliation_history:
        if rec.reconciliation_id == reconciliation_id:
            return rec
    raise HTTPException(status_code=404, detail="Reconciliation record not found")


@router.get("/alerts", response_model=List[PositionAlert])
async def get_alerts(severity: Optional[str] = None, acknowledged: Optional[bool] = None):
    """获取持仓告警"""
    alerts = alerts_history
    
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    if acknowledged is not None:
        alerts = [a for a in alerts if a.acknowledged == acknowledged]
    
    return alerts


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """确认告警"""
    for alert in alerts_history:
        if alert.alert_id == alert_id:
            alert.acknowledged = True
            return {"success": True, "alert_id": alert_id, "acknowledged": True}
    
    raise HTTPException(status_code=404, detail="Alert not found")


@router.get("/risk-report", response_model=RiskReport)
async def get_risk_report():
    """获取风险报告"""
    positions = generate_mock_positions()
    
    total_margin_used = sum(p.margin_used for p in positions)
    total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
    total_realized_pnl = sum(p.realized_pnl for p in positions)
    total_exposure = total_margin_used * 8.33
    margin_utilization = min(total_margin_used / 500000, 1.0) if total_margin_used > 0 else 0
    
    # 确定风险等级
    if margin_utilization < 0.5 and total_unrealized_pnl > 0:
        risk_level = "low"
    elif margin_utilization < 0.8:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    # 生成建议
    recommendations = []
    if margin_utilization > 0.7:
        recommendations.append("建议减少仓位以降低保证金使用率")
    if risk_level == "high":
        recommendations.append("风险等级较高，建议采取风险控制措施")
    if total_unrealized_pnl < 0:
        recommendations.append("当前浮动亏损，建议关注市场动向")
    
    return RiskReport(
        report_id=f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        generated_at=datetime.now(),
        total_exposure=total_exposure,
        total_margin_used=total_margin_used,
        margin_utilization=margin_utilization,
        total_unrealized_pnl=total_unrealized_pnl,
        total_realized_pnl=total_realized_pnl,
        risk_level=risk_level,
        alerts=[a for a in alerts_history if not a.acknowledged],
        recommendations=recommendations
    )


@router.post("/confirm/{symbol}")
async def confirm_position(symbol: str, notes: Optional[str] = None):
    """确认持仓"""
    # 模拟确认操作
    return {
        "success": True,
        "symbol": symbol,
        "confirmed_at": datetime.now(),
        "notes": notes,
        "message": f"Position for {symbol} confirmed successfully"
    }


@router.post("/auto-confirm")
async def auto_confirm_positions(threshold: float = 0.01):
    """自动确认差异在阈值内的持仓"""
    positions = generate_mock_positions()
    confirmed_count = 0
    
    for pos in positions:
        # 模拟差异检查
        expected_volume = pos.volume * (1 + threshold / 2)
        if abs(expected_volume - pos.volume) < threshold:
            confirmed_count += 1
    
    return {
        "success": True,
        "confirmed_count": confirmed_count,
        "total_count": len(positions),
        "threshold": threshold,
        "timestamp": datetime.now()
    }
