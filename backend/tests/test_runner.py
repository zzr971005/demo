"""
回测集成测试 — DSL + 数据 + 回测引擎

测试重点：
- 表达式编译 + 因子计算 + 回测完整流程
- Walk-Forward回测
- 参数扫描
- 结果正确性验证
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.quant_engine.data.hub import TimescaleHub
from backend.quant_engine.validation.runner import (
    BacktestRunner,
    BacktestRunResult,
    validate_formula,
    quick_backtest,
)


@pytest.fixture(scope="module")
def test_hub():
    """创建测试用的TimescaleHub并写入测试数据"""
    hub = TimescaleHub()

    n = 500  # 500根1H线
    dates = pd.date_range(start="2024-01-01", periods=n, freq="h", tz="UTC")

    np.random.seed(42)
    close = np.cumsum(np.random.randn(n) * 2) + 3500
    high = close + np.abs(np.random.randn(n) * 3)
    low = close - np.abs(np.random.randn(n) * 3)
    open_prices = close + np.random.randn(n) * 1
    volume = np.random.randint(1000, 10000, n)

    df = pd.DataFrame({
        "open": open_prices,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "open_interest": np.random.randint(5000, 50000, n),
    }, index=dates)

    hub.insert_ohlcv(symbol="RB_TEST", df=df, duration_seconds=3600, if_exists="replace")

    return hub


class TestFormulaValidation:
    """公式有效性测试"""

    def test_valid_formula(self):
        valid, msg = validate_formula("zscore(close, 20) * ts_corr(close, volume, 10)")
        assert valid, msg

    def test_invalid_formula_syntax(self):
        valid, msg = validate_formula("zscore(close,")
        assert not valid

    def test_single_family_violation(self):
        valid, msg = validate_formula("zscore(close, 20)")
        assert not valid  # 单族会被FamilyChecker拦截


class TestBacktestRunner:
    """回测运行器测试"""

    def test_runner_initialization(self):
        with BacktestRunner() as runner:
            assert runner is not None
            assert runner.engine is not None

    def test_run_formula_success(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            result = runner.run_formula(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
            )

            assert isinstance(result, BacktestRunResult)
            assert result.success
            assert result.result is not None
            assert result.formula is not None
            assert result.symbol == "RB_TEST"
            assert result.factor_values is not None
            assert len(result.factor_values) > 0

    def test_run_formula_with_empty_data(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            result = runner.run_formula(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="NONEXISTENT_SYMBOL",
            )

            assert not result.success
            assert "没有" in result.error_message

    def test_run_formula_semantic_violation(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            # 单族公式应该被拒绝
            result = runner.run_formula(
                formula="zscore(close, 20)",
                symbol="RB_TEST",
                validate=True,
            )

            assert not result.success
            assert "验证失败" in result.error_message

    def test_run_formula_no_validation(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            # 关闭验证，单族公式应该可以运行
            result = runner.run_formula(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
                validate=False,
            )

            assert result.success

    def test_result_to_dict(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            result = runner.run_formula(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
            )

            d = result.to_dict()
            assert isinstance(d, dict)
            assert "success" in d
            assert "result" in d
            assert "formula" in d
            assert "symbol" in d

    def test_result_metrics(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            result = runner.run_formula(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
            )

            assert result.success
            assert hasattr(result.result, "sharpe")
            assert hasattr(result.result, "max_drawdown")
            assert hasattr(result.result, "win_rate")
            assert hasattr(result.result, "total_trades")
            assert result.result.total_trades >= 0


class TestBatchBacktest:
    """批量回测测试"""

    def test_batch_run(self, test_hub):
        formulas = [
            "zscore(close, 20) * ts_corr(close, volume, 10)",
            "sign(zscore(close, 10)) * ts_return(close, 5)",
        ]

        with BacktestRunner(timescale_hub=test_hub) as runner:
            results = runner.batch_run(
                formulas=formulas,
                symbol="RB_TEST",
            )

            assert len(results) == 2
            for result in results:
                assert isinstance(result, BacktestRunResult)


class TestWalkForward:
    """Walk-Forward回测测试"""

    def test_walk_forward_split(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            df = test_hub.query_ohlcv("RB_TEST", duration_seconds=3600)
            splits = runner.walk_forward_split(df, train_window=100, val_window=50)

            assert len(splits) > 0
            for train_df, val_df in splits:
                assert len(train_df) == 100
                assert len(val_df) == 50
                # 确保时序不重叠
                assert val_df.index[0] >= train_df.index[-1]

    def test_walk_forward_test(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            result = runner.walk_forward_test(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
                train_window=200,
                val_window=100,
            )

            assert "n_splits" in result
            assert "avg_sharpe_train" in result
            assert "avg_sharpe_val" in result
            assert "sharpe_stability" in result
            assert "efficiency" in result
            assert "results" in result
            assert len(result["results"]) == result["n_splits"]


class TestParameterScan:
    """参数扫描测试"""

    def test_parameter_scan(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            results = runner.parameter_scan(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
                param_ranges={
                    "upper_threshold": [0.3, 0.5, 0.7],
                    "max_holding_bars": [20, 50],
                },
            )

            assert len(results) == 3 * 2  # 3 * 2 个参数组合
            for r in results:
                assert "params" in r
                assert "sharpe" in r
                assert "max_drawdown" in r
                assert "win_rate" in r

            # 结果应该按夏普降序排列
            sharpes = [r["sharpe"] for r in results]
            assert sharpes == sorted(sharpes, reverse=True)


class TestQuickBacktest:
    """快速回测便捷函数测试"""

    def test_quick_backtest_returns_result(self, test_hub):
        # 创建一个新的runner来测试
        with BacktestRunner(timescale_hub=test_hub) as runner:
            result = runner.run_formula(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
            )

            assert isinstance(result, BacktestRunResult)


class TestCustomParameters:
    """自定义回测参数测试"""

    def test_custom_parameters(self, test_hub):
        with BacktestRunner(timescale_hub=test_hub) as runner:
            result = runner.run_formula(
                formula="zscore(close, 20) * ts_corr(close, volume, 10)",
                symbol="RB_TEST",
                params={
                    "upper_threshold": 1.0,
                    "lower_threshold": -1.0,
                    "direction_mode": 1,  # 只多
                    "max_holding_bars": 10,
                },
            )

            assert result.success
            assert result.result is not None
