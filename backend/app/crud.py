"""
数据库访问层 - CRUD 操作封装

提供统一的数据访问接口，支持：
- 品种状态查询与更新
- 候选策略管理
- 风险事件查询
- 交易记录查询
- 进化进度查询
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    Candidate,
    CandidateStatus,
    EvolutionGeneration,
    RiskEvent,
    RiskLevel,
    SymbolMode,
    SymbolSwitch,
    Trade,
    TradeStatus,
)


# ---------------------------------------------------------------------------
# 品种相关操作
# ---------------------------------------------------------------------------

def get_symbol_switch(db: Session, symbol: str) -> Optional[SymbolSwitch]:
    """获取品种开关状态"""
    result = db.execute(
        select(SymbolSwitch).filter(SymbolSwitch.symbol == symbol)
    )
    return result.scalar_one_or_none()


def get_all_symbol_switches(db: Session) -> List[SymbolSwitch]:
    """获取所有品种开关状态"""
    result = db.execute(select(SymbolSwitch))
    return result.scalars().all()


def create_or_update_symbol_switch(
    db: Session,
    symbol: str,
    mode: SymbolMode,
    group_name: str = "A",
    max_lots: int = 1,
    operator: Optional[str] = None,
    switch_reason: Optional[str] = None,
) -> SymbolSwitch:
    """创建或更新品种开关"""
    existing = get_symbol_switch(db, symbol)
    
    if existing:
        existing.mode = mode
        existing.last_switch_at = datetime.utcnow()
        existing.switch_reason = switch_reason
        existing.operator = operator
        existing.max_lots = max_lots
        existing.group_name = group_name
    else:
        existing = SymbolSwitch(
            symbol=symbol,
            mode=mode,
            group_name=group_name,
            max_lots=max_lots,
            operator=operator,
            switch_reason=switch_reason,
        )
        db.add(existing)
    
    db.commit()
    db.refresh(existing)
    return existing


def update_symbol_mode(
    db: Session,
    symbol: str,
    new_mode: SymbolMode,
    operator: Optional[str] = None,
    reason: Optional[str] = None,
) -> SymbolSwitch:
    """更新品种交易模式"""
    switch = get_symbol_switch(db, symbol)
    if not switch:
        switch = SymbolSwitch(
            symbol=symbol,
            mode=new_mode,
            operator=operator,
            switch_reason=reason,
        )
        db.add(switch)
    else:
        switch.mode = new_mode
        switch.last_switch_at = datetime.utcnow()
        switch.switch_reason = reason
        switch.operator = operator
        
        if new_mode == SymbolMode.LIVE:
            switch.live_enabled_at = datetime.utcnow()
    
    db.commit()
    db.refresh(switch)
    return switch


# ---------------------------------------------------------------------------
# 候选策略相关操作
# ---------------------------------------------------------------------------

def get_running_candidates(db: Session) -> List[Candidate]:
    """获取所有运行中的策略"""
    result = db.execute(
        select(Candidate).filter(Candidate.status == CandidateStatus.RUNNING)
    )
    return result.scalars().all()


def get_running_candidate_by_symbol(
    db: Session, symbol: str
) -> Optional[Candidate]:
    """获取指定品种正在运行的策略"""
    result = db.execute(
        select(Candidate).filter(
            Candidate.symbol == symbol,
            Candidate.status == CandidateStatus.RUNNING,
        )
    )
    return result.scalar_one_or_none()


def get_candidate_count_by_status(
    db: Session, status: CandidateStatus
) -> int:
    """统计指定状态的候选策略数量"""
    result = db.execute(
        select(func.count(Candidate.id)).filter(Candidate.status == status)
    )
    return result.scalar_one()


def get_candidate_count_by_symbol(db: Session, symbol: str) -> Dict[str, int]:
    """按状态统计指定品种的候选策略数量"""
    result = db.execute(
        select(Candidate.status, func.count(Candidate.id)).filter(
            Candidate.symbol == symbol
        ).group_by(Candidate.status)
    )
    rows = result.all()
    return {str(row[0]): row[1] for row in rows}


# ---------------------------------------------------------------------------
# 风险事件相关操作
# ---------------------------------------------------------------------------

def get_unresolved_risk_events(
    db: Session, limit: int = 20
) -> List[RiskEvent]:
    """获取未解决的风险事件"""
    result = db.execute(
        select(RiskEvent)
        .filter(RiskEvent.is_resolved == False)
        .order_by(RiskEvent.level.desc(), RiskEvent.triggered_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


def get_risk_event_count_by_level(db: Session) -> Dict[str, int]:
    """按风险等级统计未解决事件数量"""
    result = db.execute(
        select(RiskEvent.level, func.count(RiskEvent.id)).filter(
            RiskEvent.is_resolved == False
        ).group_by(RiskEvent.level)
    )
    rows = result.all()
    return {str(row[0]): row[1] for row in rows}


def create_risk_event(
    db: Session,
    event_type: str,
    symbol: Optional[str],
    level: RiskLevel,
    message: str,
    metric_value: Optional[float] = None,
    metric_threshold: Optional[float] = None,
) -> RiskEvent:
    """创建风险事件"""
    event = RiskEvent(
        event_type=event_type,
        symbol=symbol,
        level=level,
        message=message,
        metric_value=metric_value,
        metric_threshold=metric_threshold,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ---------------------------------------------------------------------------
# 交易记录相关操作
# ---------------------------------------------------------------------------

def get_trades_by_date_range(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    symbol: Optional[str] = None,
) -> List[Trade]:
    """获取指定日期范围的交易记录"""
    query = select(Trade).filter(
        Trade.entry_at >= start_date,
        Trade.entry_at <= end_date,
    )
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    
    result = db.execute(query)
    return result.scalars().all()


def get_today_trades(db: Session) -> List[Trade]:
    """获取今日交易记录"""
    today = datetime.utcnow().date()
    start_date = datetime(today.year, today.month, today.day)
    end_date = start_date + timedelta(days=1)
    return get_trades_by_date_range(db, start_date, end_date)


def get_today_pnl_by_symbol(db: Session) -> Dict[str, float]:
    """获取各品种今日盈亏"""
    today_trades = get_today_trades(db)
    pnl_by_symbol: Dict[str, float] = {}
    
    for trade in today_trades:
        if trade.status == TradeStatus.FILLED and trade.pnl:
            pnl_by_symbol[trade.symbol] = pnl_by_symbol.get(trade.symbol, 0) + float(trade.pnl)
    
    return pnl_by_symbol


# ---------------------------------------------------------------------------
# 进化进度相关操作
# ---------------------------------------------------------------------------

def get_latest_evolution_generation(
    db: Session, symbol: Optional[str] = None
) -> Optional[EvolutionGeneration]:
    """获取最新进化代次"""
    query = select(EvolutionGeneration).order_by(
        EvolutionGeneration.generation.desc()
    )
    if symbol:
        query = query.filter(EvolutionGeneration.symbol == symbol)
    
    result = db.execute(query.limit(1))
    return result.scalar_one_or_none()


def get_evolution_status(db: Session) -> Dict[str, int]:
    """获取进化状态统计"""
    latest_gen = get_latest_evolution_generation(db)
    
    if latest_gen:
        return {
            "total_generations": latest_gen.generation,
            "current_generation": latest_gen.generation,
            "population_size": latest_gen.population_size,
            "elite_count": latest_gen.elite_count,
        }
    return {
        "total_generations": 0,
        "current_generation": 0,
        "population_size": 0,
        "elite_count": 0,
    }


# ---------------------------------------------------------------------------
# Dashboard 数据聚合
# ---------------------------------------------------------------------------

def get_dashboard_summary_data(db: Session) -> Dict[str, any]:
    """获取仪表盘汇总数据"""
    # 获取品种状态
    switches = get_all_symbol_switches(db)
    symbol_data = []
    
    # 获取今日盈亏
    today_pnl = get_today_pnl_by_symbol(db)
    
    # 获取运行中策略
    running_candidates = get_running_candidates(db)
    running_by_symbol = {c.symbol: c for c in running_candidates}
    
    for switch in switches:
        symbol_data.append({
            "symbol": switch.symbol,
            "mode": switch.mode.value,
            "current_candidate_id": switch.current_candidate_id,
            "today_pnl": today_pnl.get(switch.symbol, 0.0),
            "running_strategy": running_by_symbol.get(switch.symbol) is not None,
        })
    
    # 获取进化状态
    evolution_status = get_evolution_status(db)
    
    # 获取风险事件统计
    risk_counts = get_risk_event_count_by_level(db)
    
    return {
        "symbols": symbol_data,
        "evolution": evolution_status,
        "risk": risk_counts,
    }


def get_equity_curve_data(
    db: Session, days: int = 30
) -> List[Dict[str, any]]:
    """获取权益曲线数据"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    trades = get_trades_by_date_range(db, start_date, end_date)
    
    # 按日期聚合
    daily_pnl: Dict[str, float] = {}
    for trade in trades:
        if trade.status == TradeStatus.FILLED and trade.pnl:
            date_key = trade.entry_at.strftime("%Y-%m-%d")
            daily_pnl[date_key] = daily_pnl.get(date_key, 0) + float(trade.pnl)
    
    # 生成连续日期的权益曲线
    result = []
    current_equity = 0.0
    
    for i in range(days, -1, -1):
        date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
        current_equity += daily_pnl.get(date, 0)
        result.append({
            "date": date,
            "equity": current_equity,
            "daily_pnl": daily_pnl.get(date, 0),
        })
    
    return result
