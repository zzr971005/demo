"""
Trading related models
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SymbolMode, TradeSide, TradeStatus


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    candidate_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("candidates.id"), nullable=True, index=True
    )
    side: Mapped[TradeSide] = mapped_column(
        Enum(TradeSide, name="trade_side_enum")
    )
    quantity: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exit_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[TradeStatus] = mapped_column(
        Enum(TradeStatus, name="trade_status_enum"),
        default=TradeStatus.PENDING,
    )
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    commission: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    slippage: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))
    order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    candidate: Mapped[Optional["Candidate"]] = relationship("Candidate")


class OrderCost(Base):
    """交易成本记录表"""
    __tablename__ = "order_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entry_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    
    # 成本明细
    commission: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True, default=0)
    slippage: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True, default=0)
    impact_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True, default=0)
    total_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True, default=0)
    
    # 成本百分比
    commission_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slippage_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impact_cost_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_cost_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LiveTransitionCandidate(Base):
    """实盘过渡候选表"""
    __tablename__ = "live_transition_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 过渡状态
    transition_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, approved, rejected, completed
    transition_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 验证指标
    paper_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paper_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paper_max_dd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 实盘指标 (过渡后)
    live_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    live_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    live_max_dd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 时间信息
    paper_test_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paper_test_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    live_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OrderTypeConfig(Base):
    """订单类型配置表"""
    __tablename__ = "order_type_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    
    # 订单类型配置
    order_type: Mapped[str] = mapped_column(String(32))  # market, limit, stop, stop_limit
    time_in_force: Mapped[str] = mapped_column(String(16))  # GTC, IOC, FOK, DAY
    
    # 执行参数
    slippage_tolerance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    execution_timeout: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReplaySession(Base):
    """回放会话表"""
    __tablename__ = "replay_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 回放配置
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_source: Mapped[str] = mapped_column(String(32))  # local, database, api
    
    # 回放状态
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, running, completed, failed
    progress: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 回放结果
    total_trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间信息
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GeneratedReport(Base):
    """生成的报告表"""
    __tablename__ = "generated_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    report_type: Mapped[str] = mapped_column(String(32), index=True)  # daily, weekly, monthly, custom
    symbol: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    
    # 报告内容
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON格式
    
    # 报告期间
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="generated")  # generated, sent, archived
    
    # 元数据
    generated_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SimulationSession(Base):
    """模拟交易会话表"""
    __tablename__ = "simulation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 模拟配置
    initial_capital: Mapped[float] = mapped_column(Float)
    commission_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slippage_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 模拟状态
    status: Mapped[str] = mapped_column(String(32), default="running")  # running, paused, completed, error
    
    # 模拟结果
    final_capital: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 时间信息
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SimulationOrder(Base):
    """模拟订单表"""
    __tablename__ = "simulation_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 订单信息
    side: Mapped[str] = mapped_column(String(8))  # buy, sell
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    order_type: Mapped[str] = mapped_column(String(16))  # market, limit
    
    # 执行信息
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, filled, cancelled, rejected
    filled_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    filled_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SimulationPosition(Base):
    """模拟持仓表"""
    __tablename__ = "simulation_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 持仓信息
    side: Mapped[str] = mapped_column(String(8))  # long, short
    quantity: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    
    # PnL信息
    unrealized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 时间信息
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
