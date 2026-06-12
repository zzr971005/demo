"""
quant_engine.validation — 回测与验证层

包含：
- engine: Numba加速的向量化回测引擎
- fee_model: 手续费模型
- runner: DSL+数据+回测集成
- pbo_dsr: PBO过拟合概率测试
- split: 数据分割（训练/验证/测试）
"""

from .engine import BacktestResult, VectorizedBacktestEngine, Direction, OpenClose
from .fee_model import FeeModel, FuturesFeeConfig
from .runner import (
    BacktestRunner,
    BacktestRunResult,
    quick_backtest,
    validate_formula,
    DEFAULT_BACKTEST_PARAMS,
    SYMBOL_SPECIFIC_PARAMS,
)
from .split import TemporalSplitter, TimeSplit, WalkForwardSplit

__all__ = [
    "BacktestResult",
    "VectorizedBacktestEngine",
    "Direction",
    "OpenClose",
    "FeeModel",
    "FuturesFeeConfig",
    "BacktestRunner",
    "BacktestRunResult",
    "quick_backtest",
    "validate_formula",
    "DEFAULT_BACKTEST_PARAMS",
    "SYMBOL_SPECIFIC_PARAMS",
    "TemporalSplitter",
    "TimeSplit",
    "WalkForwardSplit",
]
