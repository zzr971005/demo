"""
Data related models
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
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OHLCV1H(Base):
    __tablename__ = "ohlcv_1h"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    volume: Mapped[int] = mapped_column(BigInteger)
    open_interest: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "ts", name="uq_ohlcv_1h_symbol_ts"),
    )


class OHLCV1D(Base):
    __tablename__ = "ohlcv_1d"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    volume: Mapped[int] = mapped_column(BigInteger)
    open_interest: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "ts", name="uq_ohlcv_1d_symbol_ts"),
    )


class FactorValue(Base):
    __tablename__ = "factor_values"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    factor_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    generation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "symbol", "ts", "factor_name",
            name="uq_factor_values_symbol_ts_name"
        ),
    )


class DataQualityReport(Base):
    """数据质量报告表"""
    __tablename__ = "data_quality_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    data_type: Mapped[str] = mapped_column(String(32), index=True)  # ohlcv_1h, ohlcv_1d, term_structure
    
    # 质量指标
    completeness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 完整性
    consistency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 一致性
    timeliness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 及时性
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 准确性
    
    # 统计信息
    total_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    missing_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duplicate_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    outlier_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 时间范围
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, completed, failed
    overall_quality: Mapped[str] = mapped_column(String(16), default="unknown")  # excellent, good, fair, poor
    
    # 详细报告 (JSON格式)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
