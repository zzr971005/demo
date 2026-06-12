"""
进化相关数据库模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
    func,
)
from sqlalchemy.orm import Session, relationship, DeclarativeBase


# 声明式基类
class Base(DeclarativeBase):
    pass


# 数据库会话上下文管理器
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# SQLite数据库路径
SQLITE_PATH = os.getenv(
    "SQLITE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "runtime.db")
)

# 创建引擎
sqlite_engine = create_engine(
    f"sqlite:///{SQLITE_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SQLiteSession = sessionmaker(
    bind=sqlite_engine,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话"""
    session = SQLiteSession()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def get_sqlite_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a SQLite session for evolution-runtime models.

    Plain generator (not a ``@contextmanager``) so it can be used directly with
    ``Depends(...)``.
    """
    session = SQLiteSession()
    try:
        yield session
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 进化任务
# ---------------------------------------------------------------------------

class EvolutionTask(Base):
    """进化任务"""

    __tablename__ = "evolution_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, index=True, nullable=False)
    symbol = Column(String(16), index=True, nullable=False)
    description = Column(Text, nullable=True)

    # 配置参数
    generations = Column(Integer, default=30)
    population_size = Column(Integer, default=100)
    enable_overfitting_check = Column(Boolean, default=True)
    pbo_threshold = Column(Float, default=0.3)
    dsr_threshold = Column(Float, default=0.6)
    wfe_threshold = Column(Float, default=0.7)

    # 状态
    status = Column(String(16), default="PENDING")  # PENDING | RUNNING | COMPLETED | STOPPED | FAILED
    current_generation = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # 统计
    total_time_seconds = Column(Float, default=0.0)
    best_sharpe_ratio = Column(Float, default=0.0)
    best_fitness = Column(Float, default=0.0)
    total_factors_generated = Column(Integer, default=0)
    factors_passed_overfitting = Column(Integer, default=0)

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    generations_rel = relationship("EvolutionGeneration", back_populates="task", cascade="all, delete-orphan")
    factors_rel = relationship("EvolutionFactor", back_populates="task", cascade="all, delete-orphan")

    @classmethod
    def create(cls, db: Session, task_id: str, symbol: str, description: str = "", **kwargs) -> "EvolutionTask":
        """创建进化任务"""
        task = cls(task_id=task_id, symbol=symbol, description=description, **kwargs)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @classmethod
    def get_by_id(cls, db: Session, task_id: str) -> Optional["EvolutionTask"]:
        """按任务ID获取"""
        return db.query(cls).filter(cls.task_id == task_id).first()

    @classmethod
    def list_by_symbol(cls, db: Session, symbol: str, limit: int = 20) -> List["EvolutionTask"]:
        """按品种列出任务"""
        return (
            db.query(cls)
            .filter(cls.symbol == symbol)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def get_running_tasks(cls, db: Session) -> List["EvolutionTask"]:
        """获取正在运行的任务"""
        return db.query(cls).filter(cls.status == "RUNNING").all()

    def update_progress(self, db: Session, generation: int, best_sharpe: float, best_fitness: float):
        """更新任务进度"""
        self.current_generation = generation
        self.best_sharpe_ratio = max(self.best_sharpe_ratio, best_sharpe)
        self.best_fitness = max(self.best_fitness, best_fitness)
        self.updated_at = datetime.utcnow()
        db.commit()

    def mark_running(self, db: Session):
        """标记为运行中"""
        self.status = "RUNNING"
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.commit()

    def mark_completed(self, db: Session, total_factors: int, passed_count: int):
        """标记为完成"""
        self.status = "COMPLETED"
        self.current_generation = self.generations
        self.total_factors_generated = total_factors
        self.factors_passed_overfitting = passed_count
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.total_time_seconds = (self.completed_at - self.started_at).total_seconds()
        self.updated_at = datetime.utcnow()
        db.commit()

    def mark_stopped(self, db: Session):
        """标记为停止"""
        self.status = "STOPPED"
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.total_time_seconds = (self.completed_at - self.started_at).total_seconds()
        self.updated_at = datetime.utcnow()
        db.commit()

    def mark_failed(self, db: Session, error_message: str):
        """标记为失败"""
        self.status = "FAILED"
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.total_time_seconds = (self.completed_at - self.started_at).total_seconds()
        self.updated_at = datetime.utcnow()
        db.commit()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "symbol": self.symbol,
            "description": self.description,
            "status": self.status,
            "current_generation": self.current_generation,
            "total_generations": self.generations,
            "population_size": self.population_size,
            "best_sharpe_ratio": self.best_sharpe_ratio,
            "best_fitness": self.best_fitness,
            "total_factors_generated": self.total_factors_generated,
            "factors_passed_overfitting": self.factors_passed_overfitting,
            "total_time_seconds": self.total_time_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# 进化世代记录
# ---------------------------------------------------------------------------

class EvolutionGeneration(Base):
    """进化世代记录"""

    __tablename__ = "evolution_generations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("evolution_tasks.task_id"), index=True, nullable=False)
    generation = Column(Integer, index=True, nullable=False)

    # 性能指标
    avg_sharpe = Column(Float, default=0.0)
    max_sharpe = Column(Float, default=0.0)
    min_sharpe = Column(Float, default=0.0)
    top_10_sharpe = Column(Float, default=0.0)
    avg_fitness = Column(Float, default=0.0)
    best_fitness = Column(Float, default=0.0)

    # 多样性指标
    diversity_score = Column(Float, default=0.0)
    unique_expressions = Column(Integer, default=0)

    # 过拟合检验
    pbo_value = Column(Float, nullable=True)
    dsr_value = Column(Float, nullable=True)
    wfe_value = Column(Float, nullable=True)

    # 时间
    generation_time_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    task = relationship("EvolutionTask", back_populates="generations_rel")

    __table_args__ = (
        UniqueConstraint("task_id", "generation", name="unique_task_generation"),
    )

    @classmethod
    def add_generation(cls, db: Session, task_id: str, generation: int, **kwargs) -> "EvolutionGeneration":
        """添加世代记录"""
        gen = cls(task_id=task_id, generation=generation, **kwargs)
        db.add(gen)
        db.commit()
        db.refresh(gen)
        return gen

    @classmethod
    def get_by_task(cls, db: Session, task_id: str) -> List["EvolutionGeneration"]:
        """获取任务的所有世代记录"""
        return (
            db.query(cls)
            .filter(cls.task_id == task_id)
            .order_by(cls.generation)
            .all()
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "generation": self.generation,
            "avg_sharpe": self.avg_sharpe,
            "max_sharpe": self.max_sharpe,
            "min_sharpe": self.min_sharpe,
            "top_10_sharpe": self.top_10_sharpe,
            "avg_fitness": self.avg_fitness,
            "best_fitness": self.best_fitness,
            "diversity_score": self.diversity_score,
            "unique_expressions": self.unique_expressions,
            "pbo": self.pbo_value,
            "dsr": self.dsr_value,
            "wfe": self.wfe_value,
            "generation_time_seconds": self.generation_time_seconds,
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# 进化因子记录
# ---------------------------------------------------------------------------

class EvolutionFactor(Base):
    """进化产生的因子记录"""

    __tablename__ = "evolution_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(String(64), unique=True, index=True, nullable=False)
    task_id = Column(String(64), ForeignKey("evolution_tasks.task_id"), index=True, nullable=False)
    symbol = Column(String(16), index=True, nullable=False)

    # 因子定义
    expression = Column(Text, nullable=False)
    generation = Column(Integer, index=True, default=0)
    origin = Column(String(32), default="random")  # random | crossover | mutation | elite

    # 复杂度
    node_count = Column(Integer, default=0)
    tree_depth = Column(Integer, default=0)

    # 性能指标
    sharpe_ratio = Column(Float, default=0.0)
    calmar_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    total_return = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    avg_trade_pnl = Column(Float, default=0.0)
    turnover_rate = Column(Float, default=0.0)

    # IC相关指标
    ic_mean_4h = Column(Float, nullable=True)
    ic_mean_24h = Column(Float, nullable=True)
    ic_mean_168h = Column(Float, nullable=True)
    ic_std = Column(Float, nullable=True)
    ic_ir = Column(Float, nullable=True)
    ic_half_life = Column(Integer, nullable=True)

    # 因子分类
    factor_category = Column(String(32), nullable=True)  # fast/medium/slow

    # 策略选择标记
    is_selected_strategy = Column(Boolean, default=False, index=True)
    strategy_rank = Column(Integer, nullable=True)  # 策略排名1-5

    # 过拟合检验
    pbo_value = Column(Float, nullable=True)
    dsr_value = Column(Float, nullable=True)
    wfe_value = Column(Float, nullable=True)
    overfitting_passed = Column(Boolean, default=False)

    # 排名
    rank_in_generation = Column(Integer, nullable=True)
    overall_rank = Column(Integer, nullable=True)

    # 实盘状态
    is_live = Column(Boolean, default=False, index=True)
    is_candidate = Column(Boolean, default=False, index=True)
    live_since = Column(DateTime, nullable=True)
    last_deployed_at = Column(DateTime, nullable=True)

    # 元数据
    parent_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    task = relationship("EvolutionTask", back_populates="factors_rel")
    live_stats = relationship("FactorLiveStat", back_populates="factor", cascade="all, delete-orphan")

    @classmethod
    def add_factors_batch(cls, db: Session, factors_data: List[Dict[str, Any]]):
        """批量添加因子"""
        for fdata in factors_data:
            factor = cls(**fdata)
            db.add(factor)
        db.commit()

    @classmethod
    def get_best_factors(cls, db: Session, symbol: str, only_passed: bool = True, limit: int = 20) -> List["EvolutionFactor"]:
        """获取最佳因子"""
        query = db.query(cls).filter(cls.symbol == symbol)
        if only_passed:
            query = query.filter(cls.overfitting_passed == True)
        return query.order_by(cls.sharpe_ratio.desc()).limit(limit).all()

    @classmethod
    def get_live_factors(cls, db: Session, symbol: Optional[str] = None) -> List["EvolutionFactor"]:
        """获取实盘因子"""
        query = db.query(cls).filter(cls.is_live == True)
        if symbol:
            query = query.filter(cls.symbol == symbol)
        return query.order_by(cls.live_since.desc()).all()

    @classmethod
    def get_candidate_factors(cls, db: Session, symbol: Optional[str] = None) -> List["EvolutionFactor"]:
        """获取候选因子"""
        query = db.query(cls).filter(cls.is_candidate == True)
        if symbol:
            query = query.filter(cls.symbol == symbol)
        return query.order_by(cls.sharpe_ratio.desc()).all()

    def deploy_to_live(self, db: Session):
        """部署到实盘"""
        self.is_live = True
        self.is_candidate = False
        self.live_since = datetime.utcnow()
        self.last_deployed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.commit()

    def remove_from_live(self, db: Session):
        """从实盘移除"""
        self.is_live = False
        self.updated_at = datetime.utcnow()
        db.commit()

    def mark_as_candidate(self, db: Session):
        """标记为候选"""
        self.is_candidate = True
        self.updated_at = datetime.utcnow()
        db.commit()

    def to_dict(self, include_expression: bool = True) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "factor_id": self.factor_id,
            "task_id": self.task_id,
            "symbol": self.symbol,
            "generation": self.generation,
            "origin": self.origin,
            "node_count": self.node_count,
            "tree_depth": self.tree_depth,
            "sharpe_ratio": self.sharpe_ratio,
            "calmar_ratio": self.calmar_ratio,
            "max_drawdown": self.max_drawdown,
            "total_return": self.total_return,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "avg_trade_pnl": self.avg_trade_pnl,
            "turnover_rate": self.turnover_rate,
            "pbo": self.pbo_value,
            "dsr": self.dsr_value,
            "wfe": self.wfe_value,
            "overfitting_passed": self.overfitting_passed,
            "is_live": self.is_live,
            "is_candidate": self.is_candidate,
            "live_since": self.live_since.isoformat() if self.live_since else None,
            "rank_in_generation": self.rank_in_generation,
            "overall_rank": self.overall_rank,
            "created_at": self.created_at.isoformat(),
        }
        if include_expression:
            result["expression"] = self.expression
        return result


# ---------------------------------------------------------------------------
# 因子实盘统计
# ---------------------------------------------------------------------------

class FactorLiveStat(Base):
    """因子实盘统计"""

    __tablename__ = "factor_live_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(String(64), ForeignKey("evolution_factors.factor_id"), index=True, nullable=False)
    symbol = Column(String(16), index=True, nullable=False)

    # 实盘性能
    live_sharpe_ratio = Column(Float, default=0.0)
    live_total_return = Column(Float, default=0.0)
    live_max_drawdown = Column(Float, default=0.0)
    live_win_rate = Column(Float, default=0.0)
    live_total_trades = Column(Integer, default=0)
    live_pnl_total = Column(Float, default=0.0)
    live_pnl_daily = Column(Float, default=0.0)

    # 回测与实盘对比
    bt_sharpe_ratio = Column(Float, default=0.0)
    bt_total_return = Column(Float, default=0.0)
    bt_max_drawdown = Column(Float, default=0.0)

    # 衰减度
    performance_decay = Column(Float, default=0.0)  # (实盘夏普 - 回测夏普) / |回测夏普|

    # 运行状态
    days_running = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # 时间戳
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    factor = relationship("EvolutionFactor", back_populates="live_stats")

    @classmethod
    def update_or_create(cls, db: Session, factor_id: str, symbol: str, **kwargs) -> "FactorLiveStat":
        """更新或创建实盘统计"""
        existing = db.query(cls).filter(cls.factor_id == factor_id).first()
        if existing:
            for k, v in kwargs.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            existing.last_updated = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            stat = cls(factor_id=factor_id, symbol=symbol, **kwargs)
            db.add(stat)
            db.commit()
            db.refresh(stat)
            return stat

    @classmethod
    def get_by_factor(cls, db: Session, factor_id: str) -> Optional["FactorLiveStat"]:
        """获取因子实盘统计"""
        return db.query(cls).filter(cls.factor_id == factor_id).first()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "factor_id": self.factor_id,
            "symbol": self.symbol,
            "live_sharpe_ratio": self.live_sharpe_ratio,
            "live_total_return": self.live_total_return,
            "live_max_drawdown": self.live_max_drawdown,
            "live_win_rate": self.live_win_rate,
            "live_total_trades": self.live_total_trades,
            "live_pnl_total": self.live_pnl_total,
            "live_pnl_daily": self.live_pnl_daily,
            "performance_decay": self.performance_decay,
            "days_running": self.days_running,
            "is_active": self.is_active,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 因子衰减历史记录
# ---------------------------------------------------------------------------

class FactorDecayHistory(Base):
    """因子衰减历史记录"""
    __tablename__ = "factor_decay_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(String(64), ForeignKey("evolution_factors.factor_id"), index=True, nullable=False)
    symbol = Column(String(16), index=True, nullable=False)
    ic_value = Column(Float, nullable=False)  # 当期IC
    ic_window = Column(Integer, nullable=False)  # IC窗口（4/24/168）
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    @classmethod
    def add_decay_record(cls, db: Session, factor_id: str, symbol: str, ic_value: float, ic_window: int) -> "FactorDecayHistory":
        """添加衰减记录"""
        record = cls(
            factor_id=factor_id,
            symbol=symbol,
            ic_value=ic_value,
            ic_window=ic_window,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def get_factor_history(cls, db: Session, factor_id: str, limit: int = 100) -> List["FactorDecayHistory"]:
        """获取因子衰减历史"""
        return db.query(cls).filter(cls.factor_id == factor_id).order_by(cls.recorded_at.desc()).limit(limit).all()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "factor_id": self.factor_id,
            "symbol": self.symbol,
            "ic_value": self.ic_value,
            "ic_window": self.ic_window,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


# ---------------------------------------------------------------------------
# 策略轮换历史记录
# ---------------------------------------------------------------------------

class StrategyRotationHistory(Base):
    """策略轮换历史记录"""
    __tablename__ = "strategy_rotation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True, nullable=False)
    old_factor_id = Column(String(64), nullable=True)
    new_factor_id = Column(String(64), nullable=False)
    rotation_reason = Column(String(255), nullable=True)
    score_improvement = Column(Float, nullable=True)  # 评分提升幅度
    rotated_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    @classmethod
    def add_rotation_record(
        cls,
        db: Session,
        symbol: str,
        old_factor_id: Optional[str],
        new_factor_id: str,
        rotation_reason: str,
        score_improvement: Optional[float] = None
    ) -> "StrategyRotationHistory":
        """添加轮换记录"""
        record = cls(
            symbol=symbol,
            old_factor_id=old_factor_id,
            new_factor_id=new_factor_id,
            rotation_reason=rotation_reason,
            score_improvement=score_improvement,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def get_symbol_history(cls, db: Session, symbol: str, limit: int = 50) -> List["StrategyRotationHistory"]:
        """获取品种轮换历史"""
        return db.query(cls).filter(cls.symbol == symbol).order_by(cls.rotated_at.desc()).limit(limit).all()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "old_factor_id": self.old_factor_id,
            "new_factor_id": self.new_factor_id,
            "rotation_reason": self.rotation_reason,
            "score_improvement": self.score_improvement,
            "rotated_at": self.rotated_at.isoformat() if self.rotated_at else None,
        }
