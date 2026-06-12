"""
Risk management related models
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, RiskLevel


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum")
    )
    message: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metric_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    operator: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AlertHistory(Base):
    """告警历史表"""
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 告警类型
    alert_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # low, medium, high, critical
    
    # 告警内容
    message: Mapped[str] = mapped_column(Text)
    metric_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, acknowledged, resolved
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 时间信息
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CapitalAllocation(Base):
    """资金分配表"""
    __tablename__ = "capital_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    allocation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 分配配置
    total_capital: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    allocated_capital: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    allocation_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 风险限制
    max_position_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_loss_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="active")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioMetrics(Base):
    """投资组合指标表"""
    __tablename__ = "portfolio_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    
    # 性能指标
    total_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 风险指标
    volatility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    var_95: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    beta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 持仓信息
    total_positions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_capital: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    used_capital: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 时间信息
    as_of_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LiquidityRiskAnalysis(Base):
    """流动性风险分析表"""
    __tablename__ = "liquidity_risk_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    analysis_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    
    # 流动性指标
    bid_ask_spread: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_ask_spread_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    turnover_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 风险评估
    liquidity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")  # low, medium, high
    
    # 价格影响
    price_impact_1pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_impact_5pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PositionLimitConfig(Base):
    """持仓限制配置表"""
    __tablename__ = "position_limit_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 持仓限制
    max_positions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_position_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_position_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 风险限制
    max_loss_per_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown_per_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LiveRiskEvent(Base):
    """实盘风险事件表"""
    __tablename__ = "live_risk_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum")
    )
    message: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metric_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    operator: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RiskConfig(Base):
    """风险配置表"""
    __tablename__ = "risk_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    
    # 风险限制
    max_total_margin_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    single_symbol_max_dd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    daily_max_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_positions_per_symbol: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 熔断机制
    circuit_breaker_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    circuit_breaker_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    circuit_breaker_consecutive_errors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
