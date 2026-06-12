"""
Evolution related models
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
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CandidateStatus, EvolutionTaskStatus


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus, name="candidate_status_enum"),
        default=CandidateStatus.SEED,
        index=True,
    )
    strategy_type: Mapped[str] = mapped_column(String(16), default="trend", server_default=text("'trend'"))
    formula: Mapped[str] = mapped_column(Text)
    params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("candidates.id"), nullable=True
    )
    generation: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    sharpe_train: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sharpe_val: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sharpe_test: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sharpe_paper_5d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_drawdown_train: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calmar: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    win_rate_train: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    node_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tree_depth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pbo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dsr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wfe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_holding_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_trade_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    seed_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    degraded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retire_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # IC相关指标
    ic_mean_4h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ic_mean_24h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ic_mean_168h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ic_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ic_ir: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ic_half_life: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 因子分类
    factor_category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # 泛化测试相关字段
    is_universal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'), index=True)
    generalization_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    applicable_symbols: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    generalization_tested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # 策略选择标记
    is_selected_strategy: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'), index=True)
    strategy_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    parent: Mapped[Optional["Candidate"]] = relationship(
        "Candidate", remote_side="Candidate.id", back_populates="children"
    )
    children: Mapped[list["Candidate"]] = relationship(
        "Candidate", back_populates="parent"
    )


class EvolutionGeneration(Base):
    __tablename__ = "evolution_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    generation: Mapped[int] = mapped_column(Integer, index=True)
    stage: Mapped[int] = mapped_column(Integer, default=1, server_default=text('1'))
    population_size: Mapped[int] = mapped_column(Integer, default=300, server_default=text('300'))
    elite_count: Mapped[int] = mapped_column(Integer, default=30, server_default=text('30'))
    mutation_rate: Mapped[float] = mapped_column(Float, default=0.2, server_default=text('0.2'))
    crossover_rate: Mapped[float] = mapped_column(Float, default=0.7, server_default=text('0.7'))
    best_fitness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_fitness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diversity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_candidates: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    pruned_candidates: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    runtime_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    log_path: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "symbol", "generation", "stage",
            name="uq_evolution_generations_symbol_gen_stage"
        ),
    )


class EvolutionTask(Base):
    """进化任务（多进程任务追踪表，FastAPI 与 Worker 进程间共享状态）"""
    __tablename__ = "evolution_tasks"

    task_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[EvolutionTaskStatus] = mapped_column(
        Enum(EvolutionTaskStatus, name="evolution_task_status_enum"),
        default=EvolutionTaskStatus.PENDING,
        index=True,
    )
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    population_size: Mapped[int] = mapped_column(Integer, default=100, server_default=text('100'))
    max_generations: Mapped[int] = mapped_column(Integer, default=99999999, server_default=text('99999999'))
    current_generation: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    best_fitness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diversity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unique_expressions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_factors: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    passed_factors: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    use_gpu: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class GenerationStats(Base):
    """世代统计表 - 存储每代的统计指标"""
    __tablename__ = "generation_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    generation: Mapped[int] = mapped_column(Integer, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # 搜索阶段统计
    search_generated: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    search_unique: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    
    # 回测阶段统计
    backtest_passed: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    backtest_failed: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    
    # 验证阶段统计
    validation_passed: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    validation_failed: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    
    # 性能指标
    best_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # IC指标
    best_ic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_ic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 夏普分布（写入端 _save_generation_stats / 读取端 /evolution/generations 依赖）
    max_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_10_avg_sharpe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 适应度
    avg_fitness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_fitness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 种群结构
    unique_expressions: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    population_size: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    elite_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))

    # 过拟合检验指标
    pbo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dsr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wfe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 多样性指标
    diversity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    __table_args__ = (
        UniqueConstraint("symbol", "generation", "task_id", name="uq_generation_stats"),
    )
