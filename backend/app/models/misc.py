"""
Miscellaneous models - other models not yet categorized
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
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

from app.models.base import Base


class ValidationPipelineData(Base):
    """验证流程数据持久化表（记录各阶段的输入输出统计）"""
    __tablename__ = "validation_pipeline_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    generation: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'), index=True)
    
    # Search 阶段
    search_input: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代生成的表达式数
    search_output: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代去重后的表达式数
    search_drop: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代重复被淘汰数
    
    # Replay 阶段
    replay_input: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代Search的输出
    replay_output: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代通过风险筛选的因子数
    replay_drop: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代未通过风险筛选的因子数
    
    # Validation 阶段
    validation_input: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代Replay的输出
    validation_output: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代通过过拟合检验的因子数
    validation_drop: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代未通过过拟合检验的因子数
    
    # Demo 阶段
    demo_input: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代Validation的输出
    demo_output: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代最终保留的因子数（最多20个）
    demo_drop: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 当前代未进入Demo的因子数

    # IC计算阶段
    ic_input: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # Demo阶段的输出
    ic_output: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 通过IC筛选的因子数（前50个）
    ic_drop: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))  # 未通过IC筛选的因子数

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    __table_args__ = (
        UniqueConstraint("symbol", "generation", name="uq_validation_pipeline_symbol_gen"),
    )


class FactorValueHistory(Base):
    """因子值序列历史表 - 存储因子的值序列供IC计算使用"""
    __tablename__ = "factor_value_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factor_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    factor_value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_factor_value_history_factor_timestamp", "factor_id", "timestamp"),
    )


class BaselineComparisonResult(Base):
    """预计算的基线对比结果（用于快速展示和横向对比）"""
    __tablename__ = "baseline_comparison_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    baseline_type: Mapped[str] = mapped_column(String(32), index=True)
    strategy_candidate_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("candidates.id"), nullable=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    strategy_return: Mapped[float] = mapped_column(Float)
    strategy_sharpe: Mapped[float] = mapped_column(Float)
    strategy_max_drawdown: Mapped[float] = mapped_column(Float)
    strategy_calmar: Mapped[float] = mapped_column(Float)
    strategy_win_rate: Mapped[float] = mapped_column(Float)
    strategy_total_trades: Mapped[int] = mapped_column(Integer)
    baseline_return: Mapped[float] = mapped_column(Float)
    baseline_sharpe: Mapped[float] = mapped_column(Float)
    baseline_max_drawdown: Mapped[float] = mapped_column(Float)
    equity_curve_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    monthly_returns_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    drawdown_curve_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    candidate: Mapped[Optional["Candidate"]] = relationship(
        "Candidate", foreign_keys=[strategy_candidate_id]
    )


class BacktestLiveComparison(Base):
    """回测实盘对比结果表"""
    __tablename__ = "backtest_live_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 回测指标
    backtest_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    backtest_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    backtest_max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 实盘指标
    live_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    live_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    live_max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 对比结果
    overfitting_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    overall_health: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 元数据
    comparison_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    period: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    __table_args__ = (
        Index("ix_backtest_live_comparison_strategy_date", "strategy_id", "comparison_date"),
    )


class ABTestResult(Base):
    """A/B测试结果表"""
    __tablename__ = "ab_test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 测试配置
    control_strategy_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    treatment_strategy_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 测试结果
    control_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    treatment_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    control_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    treatment_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    control_max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    treatment_max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 统计显著性
    is_significant: Mapped[bool] = mapped_column(Boolean, default=False)
    p_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="running")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SystemAnomaly(Base):
    """系统异常检测表"""
    __tablename__ = "system_anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anomaly_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 异常类型
    anomaly_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # low, medium, high, critical
    
    # 异常描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metric_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_range: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # 时间信息
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, resolved, ignored
    
    # 处理信息
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CorrelationMatrix(Base):
    """相关性矩阵表"""
    __tablename__ = "correlation_matrices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol1: Mapped[str] = mapped_column(String(16), index=True)
    symbol2: Mapped[str] = mapped_column(String(16), index=True)
    correlation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("symbol1", "symbol2", "period", name="uq_correlation_symbol_period"),
    )


class PortfolioOptimization(Base):
    """投资组合优化结果表"""
    __tablename__ = "portfolio_optimizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optimization_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    
    # 优化配置
    method: Mapped[str] = mapped_column(String(32))  # mean_variance, risk_parity, equal_weight
    risk_free_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 优化结果
    expected_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_volatility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 权重配置 (JSON格式)
    weights_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MicrostructureData(Base):
    """微观结构数据表"""
    __tablename__ = "microstructure_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    
    # 订单流指标
    order_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bid_ask_spread: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    depth_imbalance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 成交指标
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vwap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ArbitrageOpportunity(Base):
    """跨市场套利机会表"""
    __tablename__ = "arbitrage_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 套利配置
    market1: Mapped[str] = mapped_column(String(32))
    market2: Mapped[str] = mapped_column(String(32))
    price1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="active")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CrossMarketTrade(Base):
    """跨市场交易表"""
    __tablename__ = "cross_market_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    opportunity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 交易配置
    market1: Mapped[str] = mapped_column(String(32))
    market2: Mapped[str] = mapped_column(String(32))
    side1: Mapped[str] = mapped_column(String(8))
    side2: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 交易结果
    entry_price1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_price2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_price1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_price2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyMonitorStatus(Base):
    """策略监控状态表"""
    __tablename__ = "strategy_monitor_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 监控状态
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, paused, stopped, error
    last_signal: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # long, short, neutral
    last_signal_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 性能指标
    current_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_pnl_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 持仓信息
    current_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 错误信息
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 时间信息
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StrategyWeight(Base):
    """策略权重表"""
    __tablename__ = "strategy_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 权重配置
    weight: Mapped[float] = mapped_column(Float)
    max_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StrategySwitchHistory(Base):
    """策略切换历史表"""
    __tablename__ = "strategy_switch_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    
    # 切换信息
    old_strategy_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_strategy_id: Mapped[str] = mapped_column(String(64))
    
    # 切换原因
    switch_reason: Mapped[str] = mapped_column(String(64))  # degradation, better_candidate, manual
    old_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="completed")
    
    # 时间信息
    switched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
