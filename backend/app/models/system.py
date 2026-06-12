"""
System related models
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SymbolMode


class SymbolSwitch(Base):
    __tablename__ = "symbol_switches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    mode: Mapped[SymbolMode] = mapped_column(
        Enum(SymbolMode, name="symbol_mode_enum"),
        default=SymbolMode.OFF,
    )
    current_candidate_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("candidates.id"), nullable=True
    )
    paper_candidate_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("candidates.id"), nullable=True
    )
    group_name: Mapped[str] = mapped_column(String(8), default="A", server_default=text("'A'"))
    margin_per_lot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_lots: Mapped[int] = mapped_column(Integer, default=1, server_default=text('1'))
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    live_enabled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_switch_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    switch_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    current_candidate: Mapped[Optional["Candidate"]] = relationship(
        "Candidate", foreign_keys="SymbolSwitch.current_candidate_id"
    )
    paper_candidate: Mapped[Optional["Candidate"]] = relationship(
        "Candidate", foreign_keys="SymbolSwitch.paper_candidate_id"
    )
