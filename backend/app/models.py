"""
SQLAlchemy 2.0 models - Compatibility layer

This file re-exports all models from the organized module structure for backward compatibility.
All models are now organized by domain in the models/ subdirectory.
"""

# Re-export everything from the organized structure
from app.models.base import (
    Base,
    CandidateStatus,
    EvolutionTaskStatus,
    RiskLevel,
    SymbolMode,
    TradeSide,
    TradeStatus,
)
from app.models.data import FactorValue, OHLCV1D, OHLCV1H
from app.models.evolution import Candidate, EvolutionGeneration, EvolutionTask
from app.models.misc import (
    BaselineComparisonResult,
    FactorValueHistory,
    ValidationPipelineData,
)
from app.models.risk import RiskEvent
from app.models.system import SymbolSwitch
from app.models.trading import Trade

__all__ = [
    # Base and Enums
    "Base",
    "CandidateStatus",
    "EvolutionTaskStatus",
    "RiskLevel",
    "SymbolMode",
    "TradeSide",
    "TradeStatus",
    # Data models
    "FactorValue",
    "OHLCV1D",
    "OHLCV1H",
    # Evolution models
    "Candidate",
    "EvolutionGeneration",
    "EvolutionTask",
    # Misc models
    "BaselineComparisonResult",
    "FactorValueHistory",
    "ValidationPipelineData",
    # Risk models
    "RiskEvent",
    # System models
    "SymbolSwitch",
    # Trading models
    "Trade",
]
