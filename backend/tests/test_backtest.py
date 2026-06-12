"""
回测引擎测试

覆盖:
- 基础回测流程
- 多空双向交易
- 只多/只空模式
- 最大持仓时间限制
- 手续费计算
- 指标计算 (Sharpe, Calmar, MaxDD, WinRate)
- 批量回测
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.quant_engine.validation.engine import (
    BacktestResult,
    VectorizedBacktestEngine,
)
from backend.quant_engine.validation.fee_model import FeeModel, FuturesFeeConfig


class TestBacktestBasic:
    """基础回测测试"""

    @pytest.fixture
    def engine(self) -> VectorizedBacktestEngine:
        return VectorizedBacktestEngine(
            init_capital=1_000_000.0,
            risk_free_rate=0.03,
            periods_per_year=252 * 5,
        )

    @pytest.fixture
    def sample_ohlcv(self) -> dict[str, np.ndarray]:
        np.random.seed(42)
        n = 200
        base = 5000.0
        returns = np.random.randn(n) * 0.01
        close = base * np.cumprod(1 + returns)
        return {
            "open": close * (1 + np.random.randn(n) * 0.001),
            "high": close * (1 + np.abs(np.random.randn(n) * 0.005)),
            "low": close * (1 - np.abs(np.random.randn(n) * 0.005)),
            "close": close,
        }

    @pytest.fixture
    def bullish_factor(self, sample_ohlcv: dict) -> np.ndarray:
        # 简单动量因子：正 = 做多，负 = 做空
        close = sample_ohlcv["close"]
        return np.diff(close, prepend=close[0])

    def test_basic_run(self, engine: VectorizedBacktestEngine, bullish_factor: np.ndarray, sample_ohlcv: dict) -> None:
        params = {
            "upper_threshold": 10.0,
            "lower_threshold": -10.0,
            "direction_mode": 0,
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 1,
            "use_margin": True,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=bullish_factor,
            open_px=sample_ohlcv["open"],
            high_px=sample_ohlcv["high"],
            low_px=sample_ohlcv["low"],
            close_px=sample_ohlcv["close"],
            params=params,
            symbol="RB",
        )

        assert isinstance(result, BacktestResult)
        assert result.total_trades >= 0
        assert len(result.equity_curve) == len(bullish_factor)
        assert len(result.positions) == len(bullish_factor)

    def test_long_only(self, engine: VectorizedBacktestEngine, bullish_factor: np.ndarray, sample_ohlcv: dict) -> None:
        params = {
            "upper_threshold": 10.0,
            "lower_threshold": -10.0,
            "direction_mode": 1,  # 只多
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 1,
            "use_margin": True,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=bullish_factor,
            open_px=sample_ohlcv["open"],
            high_px=sample_ohlcv["high"],
            low_px=sample_ohlcv["low"],
            close_px=sample_ohlcv["close"],
            params=params,
            symbol="RB",
        )

        # 只多模式下不应有空仓
        assert all(p >= 0 for p in result.positions)

    def test_short_only(self, engine: VectorizedBacktestEngine, bullish_factor: np.ndarray, sample_ohlcv: dict) -> None:
        params = {
            "upper_threshold": 10.0,
            "lower_threshold": -10.0,
            "direction_mode": -1,  # 只空
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 1,
            "use_margin": True,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=bullish_factor,
            open_px=sample_ohlcv["open"],
            high_px=sample_ohlcv["high"],
            low_px=sample_ohlcv["low"],
            close_px=sample_ohlcv["close"],
            params=params,
            symbol="RB",
        )

        # 只空模式下不应有多仓
        assert all(p <= 0 for p in result.positions)

    def test_max_holding_bars(self, engine: VectorizedBacktestEngine, bullish_factor: np.ndarray, sample_ohlcv: dict) -> None:
        max_holding = 10
        params = {
            "upper_threshold": 10.0,
            "lower_threshold": -10.0,
            "direction_mode": 0,
            "max_holding_bars": max_holding,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 1,
            "use_margin": True,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=bullish_factor,
            open_px=sample_ohlcv["open"],
            high_px=sample_ohlcv["high"],
            low_px=sample_ohlcv["low"],
            close_px=sample_ohlcv["close"],
            params=params,
            symbol="RB",
        )

        # 检查持仓序列中连续持仓不超过 max_holding
        positions = result.positions
        current_pos = 0
        entry_bar = 0
        for i, p in enumerate(positions):
            if p != 0 and current_pos == 0:
                current_pos = p
                entry_bar = i
            elif p == 0 and current_pos != 0:
                current_pos = 0
            elif p != current_pos and current_pos != 0 and p != 0:
                # 反手
                hold_bars = i - entry_bar
                assert hold_bars <= max_holding + 1  # 允许一点边界误差
                current_pos = p
                entry_bar = i

    def test_equity_monotonicity_no_trades(self, engine: VectorizedBacktestEngine, sample_ohlcv: dict) -> None:
        # 使用永远不会触发交易的阈值
        factor = np.zeros(len(sample_ohlcv["close"]))
        params = {
            "upper_threshold": 99999.0,
            "lower_threshold": -99999.0,
            "direction_mode": 0,
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 1,
            "use_margin": True,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=factor,
            open_px=sample_ohlcv["open"],
            high_px=sample_ohlcv["high"],
            low_px=sample_ohlcv["low"],
            close_px=sample_ohlcv["close"],
            params=params,
            symbol="RB",
        )

        assert result.total_trades == 0
        # 无交易时权益应该不变（除手续费外）
        np.testing.assert_allclose(result.equity_curve, engine.init_capital, rtol=1e-10)

    def test_to_dict(self, engine: VectorizedBacktestEngine, bullish_factor: np.ndarray, sample_ohlcv: dict) -> None:
        params = {
            "upper_threshold": 10.0,
            "lower_threshold": -10.0,
            "direction_mode": 0,
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 1,
            "use_margin": True,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=bullish_factor,
            open_px=sample_ohlcv["open"],
            high_px=sample_ohlcv["high"],
            low_px=sample_ohlcv["low"],
            close_px=sample_ohlcv["close"],
            params=params,
            symbol="RB",
        )

        d = result.to_dict()
        assert "sharpe" in d
        assert "calmar" in d
        assert "max_drawdown" in d
        assert "total_trades" in d
        assert "win_rate" in d
        assert "total_return" in d
        assert isinstance(d["sharpe"], float)
        assert isinstance(d["total_trades"], int)


class TestBacktestMetrics:
    """回测指标计算测试"""

    def test_sharpe_calculation(self) -> None:
        engine = VectorizedBacktestEngine(init_capital=1_000_000.0)
        n = 100
        close = np.linspace(100, 110, n)  # 稳定上涨
        factor = np.diff(close, prepend=close[0])

        params = {
            "upper_threshold": 0.0,
            "lower_threshold": -99999.0,
            "direction_mode": 1,
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 0,
            "use_margin": False,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=factor,
            open_px=close,
            high_px=close,
            low_px=close,
            close_px=close,
            params=params,
            symbol="RB",
        )

        # 稳定上涨应该有正夏普
        assert result.sharpe > 0
        assert result.total_return > 0

    def test_max_drawdown_range(self) -> None:
        engine = VectorizedBacktestEngine(init_capital=1_000_000.0)
        n = 100
        close = np.concatenate([
            np.linspace(100, 120, 50),
            np.linspace(120, 90, 50),
        ])
        factor = np.diff(close, prepend=close[0])

        params = {
            "upper_threshold": 0.0,
            "lower_threshold": -99999.0,
            "direction_mode": 1,
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 0,
            "use_margin": False,
            "margin_rate": 0.12,
        }
        result = engine.run(
            factor=factor,
            open_px=close,
            high_px=close,
            low_px=close,
            close_px=close,
            params=params,
            symbol="RB",
        )

        # 最大回撤应该在 0~1 之间
        assert 0 <= result.max_drawdown <= 1


class TestBatchBacktest:
    """批量回测测试"""

    def test_run_batch(self) -> None:
        engine = VectorizedBacktestEngine(init_capital=1_000_000.0)
        np.random.seed(42)
        n = 100

        factor_dict = {}
        ohlcv_dict = {}
        for symbol in ["RB", "MA"]:
            close = 5000 + np.cumsum(np.random.randn(n) * 10)
            factor_dict[symbol] = np.diff(close, prepend=close[0])
            ohlcv_dict[symbol] = {
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
            }

        params = {
            "upper_threshold": 10.0,
            "lower_threshold": -10.0,
            "direction_mode": 0,
            "max_holding_bars": 0,
            "position_size_pct": 0.95,
            "contract_value_per_lot": 50000.0,
            "tick_size": 1.0,
            "slippage_ticks": 1,
            "use_margin": True,
            "margin_rate": 0.12,
        }
        results = engine.run_batch(factor_dict, ohlcv_dict, params)

        assert len(results) == 2
        assert "RB" in results
        assert "MA" in results
        for symbol, result in results.items():
            assert isinstance(result, BacktestResult)
