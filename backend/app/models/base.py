"""
Base model and common types
"""

from enum import Enum as PyEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CandidateStatus(str, PyEnum):
    SEED = "SEED"
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    VALIDATED = "VALIDATED"
    DEPLOYABLE = "DEPLOYABLE"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    RETIRED = "RETIRED"


class TradeSide(str, PyEnum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, PyEnum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class SymbolMode(str, PyEnum):
    OFF = "OFF"
    PAPER = "PAPER"
    LIVE = "LIVE"


class RiskLevel(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvolutionTaskStatus(str, PyEnum):
    """进化任务状态（多进程任务追踪用）"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ZOMBIE = "ZOMBIE"      # 心跳超时
    CANCELLED = "CANCELLED"
