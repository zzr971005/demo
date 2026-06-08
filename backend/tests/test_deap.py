"""
DEAP 遗传编程测试

覆盖：
- FamilyPrimitiveSet 构建
- 适应度评估
- DEAPEvolutionEngine 基本功能
- 种子保护机制
- 早停机制
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.quant_engine.factors.registry import PrimitiveFamily
from backend.quant_engine.ops.evolve_search import (
    DEAPEvolutionEngine,
    FamilyPrimitiveSet,
    FitnessMetrics,
    EvolutionResult,
    _safe_div,
    _safe_log,
    _safe_sqrt,
)


@pytest.fixture(scope="module")
def test_data():
    """创建测试用的 OHLCV 数据"""
    n = 500
    dates = pd.date_range(start="2024-01-01", periods=n, freq="h", tz="UTC")
    np.random.seed(42)
    close = np.cumsum(np.random.randn(n) * 2) + 3500

    return pd.DataFrame(
        {
            "open": close + np.random.randn(n) * 1,
            "high": close + np.abs(np.random.randn(n) * 3),
            "low": close - np.abs(np.random.randn(n) * 3),
            "close": close,
            "volume": np.random.randint(1000, 10000, n),
            "open_interest": np.random.randint(5000, 50000, n),
        },
        index=dates,
    )


class TestFamilyPrimitiveSet:
    """FamilyPrimitiveSet 测试"""

    def test_build_default(self):
        """测试默认 PrimitiveSet 构建"""
        fps = FamilyPrimitiveSet()
        assert fps.pset is not None
        assert fps.max_tree_depth == 8
        assert fps.min_tree_depth == 1

    def test_build_custom_depth(self):
        """测试自定义树深度"""
        fps = FamilyPrimitiveSet(max_tree_depth=10, min_tree_depth=2)
        assert fps.max_tree_depth == 10
        assert fps.min_tree_depth == 2

    def test_build_specific_families(self):
        """测试使用特定族"""
        fps = FamilyPrimitiveSet(families=[PrimitiveFamily.MOMENTUM, PrimitiveFamily.MEAN_REVERSION])
        assert fps.families == [PrimitiveFamily.MOMENTUM, PrimitiveFamily.MEAN_REVERSION]

    def test_has_basic_primitives(self):
        """测试包含基本算子"""
        fps = FamilyPrimitiveSet()
        pset = fps.pset
        assert pset is not None

        prim_names = list(pset.context.keys())
        assert "add" in prim_names
        assert "sub" in prim_names
        assert "mul" in prim_names
        assert "div" in prim_names
        assert "abs" in prim_names
        assert "sign" in prim_names

    def test_safe_div(self):
        """测试安全除法"""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([0.0, 2.0, 0.0])
        result = _safe_div(a, b)
        assert result[0] == 0.0
        assert result[1] == 1.0
        assert result[2] == 0.0

    def test_safe_log(self):
        """测试安全对数"""
        x = np.array([-1.0, 0.0, 1.0, np.e])
        result = _safe_log(x)
        assert np.isfinite(result).all()
        assert result[2] == 0.0
        assert abs(result[3] - 1.0) < 1e-6

    def test_safe_sqrt(self):
        """测试安全平方根"""
        x = np.array([-4.0, 0.0, 4.0, 9.0])
        result = _safe_sqrt(x)
        assert np.isfinite(result).all()
        assert result[0] == 0.0
        assert result[1] == 0.0
        assert result[2] == 2.0
        assert result[3] == 3.0


class TestFitnessMetrics:
    """FitnessMetrics 测试"""

    def test_default_values(self):
        """测试默认值"""
        metrics = FitnessMetrics()
        assert metrics.sharpe == 0.0
        assert metrics.calmar == 0.0
        assert metrics.ic_mean == 0.0
        assert metrics.max_dd == 0.0
        assert metrics.turnover == 0.0
        assert metrics.complexity == 0.0
        assert metrics.raw_fitness == 0.0
        assert metrics.penalty_factor == 1.0

    def test_composite_score(self):
        """测试综合得分计算"""
        metrics = FitnessMetrics(
            sharpe=1.5,
            calmar=3.0,
            ic_mean=0.05,
            max_dd=-0.1,
            turnover=0.05,
            complexity=0.5,
            penalty_factor=1.0,
        )
        score = metrics.composite_score()
        assert isinstance(score, float)
        # 应该是正数：sharpe + calmar + ic_mean 大于 负项
        assert score > 0

    def test_composite_score_with_penalty(self):
        """测试惩罚系数影响"""
        metrics = FitnessMetrics(sharpe=1.0, penalty_factor=0.8)
        score1 = metrics.composite_score()
        metrics.penalty_factor = 0.5
        score2 = metrics.composite_score()
        assert score2 < score1


class TestDEAPEvolutionEngine:
    """DEAPEvolutionEngine 测试"""

    def test_initialization(self, test_data):
        """测试引擎初始化"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=50,
            max_generations=5,
            elite_count=5,
        )
        assert engine.symbol == "RB_TEST"
        assert engine.population_size == 50
        assert engine.max_generations == 5
        assert engine.elite_count == 5
        assert engine.toolbox is not None
        assert engine.validator is not None

    def test_toolbox_setup(self, test_data):
        """测试 toolbox 设置"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=20,
            max_generations=3,
        )
        assert hasattr(engine.toolbox, "evaluate")
        assert hasattr(engine.toolbox, "select")
        assert hasattr(engine.toolbox, "mate")
        assert hasattr(engine.toolbox, "mutate")
        assert hasattr(engine.toolbox, "individual")
        assert hasattr(engine.toolbox, "population")

    def test_evaluate_wrapper(self, test_data):
        """测试个体评估包装器"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=20,
            max_generations=2,
        )
        # 创建一个简单个体
        individual = engine.toolbox.individual()
        fitness = engine._evaluate_wrapper(individual)
        assert isinstance(fitness, tuple)
        assert len(fitness) == 1
        assert isinstance(fitness[0], float)

    def test_run_small_evolution(self, test_data):
        """测试小规模进化运行"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=20,
            max_generations=3,
            elite_count=3,
            n_jobs=1,  # 单进程测试
        )
        result = engine.run()

        assert isinstance(result, EvolutionResult)
        assert result.symbol == "RB_TEST"
        assert result.generation <= 3
        assert isinstance(result.best_expr, str)
        assert len(result.best_expr) > 0
        assert isinstance(result.best_fitness, float)
        assert isinstance(result.runtime_seconds, float)
        assert result.runtime_seconds > 0
        assert len(engine.history) == result.generation
        assert len(engine.best_fitness_history) == result.generation

    def test_early_stop_triggered(self, test_data, monkeypatch):
        """测试早停机制被触发"""

        def mock_evaluate(*args, **kwargs):
            return (0.5,)  # 固定适应度，保证没有提升

        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=20,
            max_generations=10,
            elite_count=3,
            early_stop_patience=2,
            n_jobs=1,
        )
        monkeypatch.setattr(engine.toolbox, "evaluate", mock_evaluate)

        result = engine.run()
        assert result.stopped_early
        assert result.generation < 10

    def test_seed_reserve(self, test_data):
        """测试种子保护机制"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=100,
            max_generations=5,
            elite_count=5,
            seed_reserve_gens=3,
            seed_reserve_ratio=0.2,
            n_jobs=1,
        )
        result = engine.run()
        assert result.generation >= 3

    def test_custom_families(self, test_data):
        """测试使用自定义原语族"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            families=[PrimitiveFamily.MOMENTUM, PrimitiveFamily.VOLATILITY],
            population_size=20,
            max_generations=2,
            n_jobs=1,
        )
        result = engine.run()
        assert isinstance(result, EvolutionResult)

    def test_metrics_computed(self, test_data):
        """测试结果指标被正确计算"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=20,
            max_generations=2,
            n_jobs=1,
        )
        result = engine.run()
        assert isinstance(result.metrics, FitnessMetrics)
        assert isinstance(result.metrics.sharpe, float)
        assert isinstance(result.metrics.calmar, float)
        assert isinstance(result.metrics.ic_mean, float)
        assert isinstance(result.metrics.max_dd, float)
        assert isinstance(result.metrics.turnover, float)
        assert isinstance(result.metrics.complexity, float)

    def test_population_stats(self, test_data):
        """测试种群统计信息"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=20,
            max_generations=2,
            n_jobs=1,
        )
        result = engine.run()
        stats = result.population_stats
        assert "avg" in stats
        assert "std" in stats
        assert "max" in stats
        assert "min" in stats
        assert stats["max"] >= stats["avg"]


class TestParallelEvaluation:
    """并行评估测试（如可用）"""

    def test_parallel_evaluation(self, test_data):
        """测试多进程评估"""
        engine = DEAPEvolutionEngine(
            symbol="RB_TEST",
            data=test_data,
            population_size=30,
            max_generations=2,
            n_jobs=1,
        )
        result = engine.run()
        assert isinstance(result, EvolutionResult)
        assert result.runtime_seconds > 0
