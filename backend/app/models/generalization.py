"""
Generalization test related models
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GeneralizationTestResult(Base):
    """泛化测试结果表"""
    __tablename__ = "generalization_test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factor_id: Mapped[str] = mapped_column(String(64), index=True)
    original_symbol: Mapped[str] = mapped_column(String(16), index=True)
    test_symbols: Mapped[str] = mapped_column(Text)  # JSON array
    is_universal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'), index=True)
    generalization_score: Mapped[float] = mapped_column(Float)
    performance_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    performance_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ic_correlation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    symbol_performance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    tested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("factor_id", "original_symbol", name="uq_gen_test_factor_symbol"),
    )


class FactorClassification(Base):
    """因子分类表"""
    __tablename__ = "factor_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factor_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # universal, symbol_specific, sector_specific
    confidence: Mapped[float] = mapped_column(Float)
    applicable_symbols: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    excluded_symbols: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    classification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
