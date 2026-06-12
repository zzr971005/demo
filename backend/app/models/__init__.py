"""
Database models - organized by domain
"""

from app.models.base import (
    Base,
    CandidateStatus,
    EvolutionTaskStatus,
    RiskLevel,
    SymbolMode,
    TradeSide,
    TradeStatus,
)
from app.models.data import DataQualityReport, FactorValue, OHLCV1D, OHLCV1H
from app.models.evolution import Candidate, EvolutionGeneration, EvolutionTask, GenerationStats
from app.models.generalization import FactorClassification, GeneralizationTestResult
from app.models.misc import (
    ABTestResult,
    ArbitrageOpportunity,
    BacktestLiveComparison,
    BaselineComparisonResult,
    CorrelationMatrix,
    CrossMarketTrade,
    FactorValueHistory,
    MicrostructureData,
    PortfolioOptimization,
    StrategyMonitorStatus,
    StrategySwitchHistory,
    StrategyWeight,
    SystemAnomaly,
    ValidationPipelineData,
)
from app.models.risk import AlertHistory, CapitalAllocation, LiveRiskEvent, LiquidityRiskAnalysis, PortfolioMetrics, PositionLimitConfig, RiskConfig, RiskEvent
from app.models.system import SymbolSwitch
from app.models.trading import GeneratedReport, LiveTransitionCandidate, OrderCost, OrderTypeConfig, ReplaySession, SimulationOrder, SimulationPosition, SimulationSession, Trade

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
    "DataQualityReport",
    "FactorValue",
    "OHLCV1D",
    "OHLCV1H",
    # Evolution models
    "Candidate",
    "EvolutionGeneration",
    "EvolutionTask",
    "GenerationStats",
    # Generalization models
    "FactorClassification",
    "GeneralizationTestResult",
    # Misc models
    "ABTestResult",
    "ArbitrageOpportunity",
    "BacktestLiveComparison",
    "BaselineComparisonResult",
    "CorrelationMatrix",
    "CrossMarketTrade",
    "FactorValueHistory",
    "MicrostructureData",
    "PortfolioOptimization",
    "StrategyMonitorStatus",
    "StrategySwitchHistory",
    "StrategyWeight",
    "SystemAnomaly",
    "ValidationPipelineData",
    # Risk models
    "AlertHistory",
    "CapitalAllocation",
    "LiveRiskEvent",
    "LiquidityRiskAnalysis",
    "PortfolioMetrics",
    "PositionLimitConfig",
    "RiskConfig",
    "RiskEvent",
    # System models
    "SymbolSwitch",
    # Trading models
    "GeneratedReport",
    "LiveTransitionCandidate",
    "OrderCost",
    "OrderTypeConfig",
    "ReplaySession",
    "SimulationOrder",
    "SimulationPosition",
    "SimulationSession",
    "Trade",
]
