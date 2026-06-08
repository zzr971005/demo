"""
DEAP遗传编程核心 — 因子表达式进化引擎

封装 DEAP 库实现遗传编程：
- PrimitiveSet 按族注册原语（从 registry.py 导入）
- 多目标适应度函数：0.4*sharpe + 0.3*calmar + 0.2*ic_mean - 0.5*max_dd - 0.3*turnover - 0.2*complexity
- 种子保护机制（前10代保留20%种子）
- 早停机制（连续5代无提升则停止）
- 支持按品种独立进化
- 多进程并行评估
"""

from __future__ import annotations

import json
import logging
import multiprocessing as mp
import os
import random
import sqlite3
import time
import uuid
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from deap import algorithms, base, creator, gp, tools

import operator
from ..factors.formula_dsl import (
    ExprNode,
    expr_to_func,
    expr_to_string,
    parse_expr,
    tree_depth,
)
from ..factors.ic_analysis import ic_stats, rank_ic, rolling_ic
from ..factors.registry import (
    FACTOR_REGISTRY,
    PrimitiveFamily,
    list_primitives,
)
from ..factors.semantic_validator import (
    SemanticValidator,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 包装器函数（模块级别，用于支持多进程 pickle）
# ---------------------------------------------------------------------------

def _safe_div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.divide(a, b, out=np.zeros_like(a, dtype=np.float64), where=np.abs(b) > 1e-12)

def _safe_log(x: np.ndarray) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.log(np.clip(x, 1e-12, None))

def _safe_sqrt(x: np.ndarray) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.sqrt(np.clip(x, 0.0, None))


class _PrimitiveWrapper:
    """可被 pickle 的原语包装器，用于处理异常"""
    def __init__(self, func: Callable, name: str):
        self._func = func
        self._name = name
        self.__name__ = name

    def __call__(self, *args):
        try:
            return self._func(*args)
        except Exception:
            return np.full_like(args[0] if args else np.array([]), np.nan)

    def __reduce__(self):
        return (_PrimitiveWrapper, (self._func, self._name))

# ---------------------------------------------------------------------------
# 全局配置
# ---------------------------------------------------------------------------

POPULATION_SIZE = 300
ELITE_COUNT = 30
CROSSOVER_RATE = 0.7
MUTATION_RATE = 0.2
SEED_RESERVE_GENS = 10
SEED_RESERVE_RATIO = 0.2
EARLY_STOP_PATIENCE = 5
MAX_GENERATIONS = 60

# 适应度权重
W_SHARPE = 0.4
W_CALMAR = 0.3
W_IC = 0.2
W_MAX_DD = -0.5
W_TURNOVER = -0.3
W_COMPLEXITY = -0.2

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/runtime.db")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class FitnessMetrics:
    sharpe: float = 0.0
    calmar: float = 0.0
    ic_mean: float = 0.0
    max_dd: float = 0.0
    turnover: float = 0.0
    complexity: float = 0.0
    raw_fitness: float = 0.0
    penalty_factor: float = 1.0

    def composite_score(self) -> float:
        return (
            W_SHARPE * self.sharpe
            + W_CALMAR * self.calmar
            + W_IC * self.ic_mean
            + W_MAX_DD * self.max_dd
            + W_TURNOVER * self.turnover
            + W_COMPLEXITY * self.complexity
        ) * self.penalty_factor


@dataclass
class EvolutionResult:
    symbol: str
    generation: int
    best_expr: str
    best_fitness: float
    metrics: FitnessMetrics
    population_stats: Dict[str, float]
    runtime_seconds: float
    stopped_early: bool = False


# ---------------------------------------------------------------------------
# PrimitiveSet 构建（按族注册）
# ---------------------------------------------------------------------------

class FamilyPrimitiveSet:
    """按族构建 DEAP PrimitiveSet，支持灵活组合。"""

    def __init__(
        self,
        families: Optional[List[PrimitiveFamily]] = None,
        max_tree_depth: int = 8,
        min_tree_depth: int = 1,
    ) -> None:
        self.families = families or list(PrimitiveFamily)
        self.max_tree_depth = max_tree_depth
        self.min_tree_depth = min_tree_depth
        self.pset: Optional[gp.PrimitiveSet] = None
        self._build()

    def _build(self) -> None:
        self.pset = gp.PrimitiveSet("MAIN", 0)
        self.pset.addTerminal(1.0)
        self.pset.addTerminal(0.0)
        self.pset.addTerminal(-1.0)

        for fam in self.families:
            names = list_primitives(family=fam)
            for name in names:
                meta = FACTOR_REGISTRY.get(name)
                if meta is None or meta.func is None:
                    continue
                arity = self._infer_arity(meta.func)
                self.pset.addPrimitive(_PrimitiveWrapper(meta.func, name), arity, name=name)

        self.pset.addPrimitive(np.add, 2, name="add")
        self.pset.addPrimitive(np.subtract, 2, name="sub")
        self.pset.addPrimitive(np.multiply, 2, name="mul")
        self.pset.addPrimitive(_safe_div, 2, name="div")
        self.pset.addPrimitive(np.negative, 1, name="neg")
        self.pset.addPrimitive(np.abs, 1, name="abs")
        self.pset.addPrimitive(_safe_log, 1, name="log")
        self.pset.addPrimitive(np.sign, 1, name="sign")
        self.pset.addPrimitive(_safe_sqrt, 1, name="sqrt")

        self.pset.renameArguments(ARG0="close")

    @staticmethod
    def _infer_arity(func: Callable) -> int:
        try:
            code = func.__code__
            return code.co_argcount - len(func.__defaults__ or ())
        except Exception:
            return 1


# ---------------------------------------------------------------------------
# 适应度评估
# ---------------------------------------------------------------------------

def evaluate_individual(
    individual: gp.PrimitiveTree,
    data: pd.DataFrame,
    symbol: str,
    validator: SemanticValidator,
    forward_periods: int = 5,
) -> Tuple[float,]:
    """评估单个 GP 树个体的适应度。返回 (fitness,) 元组。"""
    expr_str = str(individual)
    try:
        ast = parse_expr(expr_str)
    except Exception:
        return (-999.0,)

    val_result = validator.validate(ast, symbol=symbol)
    if not val_result.is_valid:
        return (-999.0,)

    try:
        fn, _ = expr_to_func(expr_str)
        factor = fn(
            data["open"].values,
            data["high"].values,
            data["low"].values,
            data["close"].values,
            data["volume"].values,
            data.get("open_interest", data["close"]).values,
        )
    except Exception:
        return (-999.0,)

    if factor is None or not np.isfinite(factor).any():
        return (-999.0,)

    metrics = _compute_metrics(factor, data, forward_periods)
    metrics.penalty_factor = val_result.penalty_factor
    fitness = metrics.composite_score()
    return (fitness,)


def _compute_metrics(
    factor: np.ndarray,
    data: pd.DataFrame,
    forward_periods: int = 5,
) -> FitnessMetrics:
    close = data["close"].values
    n = len(factor)
    if n < forward_periods + 10:
        return FitnessMetrics()

    fwd_ret = np.empty_like(close)
    fwd_ret[:] = np.nan
    valid = close[:-forward_periods] > 0
    fwd_ret[:-forward_periods][valid] = np.log(
        close[forward_periods:][valid] / close[:-forward_periods][valid]
    )

    f_s = pd.Series(factor)
    r_s = pd.Series(fwd_ret)
    aligned = pd.concat([f_s, r_s], axis=1).dropna()
    if len(aligned) < 30:
        return FitnessMetrics()

    f_clean = aligned.iloc[:, 0].values
    r_clean = aligned.iloc[:, 1].values

    ic_val = rank_ic(f_clean, r_clean)
    ic_val = ic_val if np.isfinite(ic_val) else 0.0

    ic_s = rolling_ic(f_s, r_s, window=60, method="rank").dropna()
    ic_mean = ic_s.mean() if len(ic_s) > 0 else 0.0
    ic_mean = ic_mean if np.isfinite(ic_mean) else 0.0

    signal = np.sign(f_clean)
    signal = np.where(np.isnan(signal), 0, signal)
    strat_ret = signal[:-1] * r_clean[1:]
    strat_ret = strat_ret[np.isfinite(strat_ret)]
    if len(strat_ret) < 10:
        return FitnessMetrics(ic_mean=ic_mean)

    sharpe = np.mean(strat_ret) / (np.std(strat_ret) + 1e-12) * np.sqrt(252)

    cum = np.cumsum(strat_ret)
    running_max = np.maximum.accumulate(cum)
    dd = cum - running_max
    max_dd = dd.min() if len(dd) > 0 else 0.0

    calmar = np.mean(strat_ret) * 252 / (abs(max_dd) + 1e-12)

    turnover = np.mean(np.abs(np.diff(signal))) if len(signal) > 1 else 0.0

    # 简单基于因子绝对值的复杂度指标（越复杂的因子通常波动更大）
    complexity = np.nanstd(factor) if np.isfinite(factor).any() else 0.0
    complexity = np.clip(complexity, 0.0, 1.0)

    return FitnessMetrics(
        sharpe=float(sharpe),
        calmar=float(calmar),
        ic_mean=float(ic_mean),
        max_dd=float(max_dd),
        turnover=float(turnover),
        complexity=float(complexity),
    )


# ---------------------------------------------------------------------------
# 进化引擎
# ---------------------------------------------------------------------------

class DEAPEvolutionEngine:
    """DEAP 遗传编程进化引擎。"""

    def __init__(
        self,
        symbol: str,
        data: pd.DataFrame,
        families: Optional[List[PrimitiveFamily]] = None,
        population_size: int = POPULATION_SIZE,
        elite_count: int = ELITE_COUNT,
        crossover_rate: float = CROSSOVER_RATE,
        mutation_rate: float = MUTATION_RATE,
        max_generations: int = MAX_GENERATIONS,
        seed_reserve_gens: int = SEED_RESERVE_GENS,
        seed_reserve_ratio: float = SEED_RESERVE_RATIO,
        early_stop_patience: int = EARLY_STOP_PATIENCE,
        max_tree_depth: int = 8,
        min_tree_depth: int = 1,
        forward_periods: int = 5,
        n_jobs: int = -1,
    ) -> None:
        self.symbol = symbol
        self.data = data
        self.families = families
        self.population_size = population_size
        self.elite_count = elite_count
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.max_generations = max_generations
        self.seed_reserve_gens = seed_reserve_gens
        self.seed_reserve_ratio = seed_reserve_ratio
        self.early_stop_patience = early_stop_patience
        self.max_tree_depth = max_tree_depth
        self.min_tree_depth = min_tree_depth
        self.forward_periods = forward_periods
        self.n_jobs = n_jobs if n_jobs > 0 else mp.cpu_count()

        self.fps = FamilyPrimitiveSet(
            families=families,
            max_tree_depth=max_tree_depth,
            min_tree_depth=min_tree_depth,
        )
        self.validator = SemanticValidator(max_tree_depth=max_tree_depth)
        self.toolbox = self._build_toolbox()
        self.history: List[Dict[str, Any]] = []
        self.best_fitness_history: List[float] = []

    def _build_toolbox(self) -> base.Toolbox:
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()
        pset = self.fps.pset
        assert pset is not None

        toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=self.min_tree_depth, max_=self.max_tree_depth)
        toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("compile", gp.compile, pset=pset)

        toolbox.register("evaluate", self._evaluate_wrapper)
        toolbox.register("select", tools.selTournament, tournsize=3)
        toolbox.register("mate", gp.cxOnePoint)
        toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
        toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

        toolbox.decorate(
            "mate",
            gp.staticLimit(key=operator.attrgetter("height"), max_value=self.max_tree_depth),
        )
        toolbox.decorate(
            "mutate",
            gp.staticLimit(key=operator.attrgetter("height"), max_value=self.max_tree_depth),
        )
        return toolbox

    def _evaluate_wrapper(self, individual: gp.PrimitiveTree) -> Tuple[float,]:
        return evaluate_individual(
            individual,
            self.data,
            self.symbol,
            self.validator,
            self.forward_periods,
        )

    def run(self) -> EvolutionResult:
        t0 = time.perf_counter()
        random.seed(hash(self.symbol) % (2**31))

        pop = self.toolbox.population(n=self.population_size)
        hof = tools.HallOfFame(self.elite_count)
        stats = tools.Statistics(lambda ind: ind.fitness.values[0])
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)

        best_ever = -float("inf")
        patience_counter = 0
        stopped_early = False

        for gen in range(1, self.max_generations + 1):
            if self.n_jobs > 1:
                from multiprocessing import Pool
                with Pool(processes=self.n_jobs) as pool:
                    fitnesses = pool.map(self.toolbox.evaluate, pop)
                for ind, fit in zip(pop, fitnesses):
                    ind.fitness.values = fit
            else:
                fitnesses = map(self.toolbox.evaluate, pop)
                for ind, fit in zip(pop, fitnesses):
                    ind.fitness.values = fit

            hof.update(pop)
            record = stats.compile(pop)
            self.history.append({"gen": gen, **record})
            current_best = record["max"]
            self.best_fitness_history.append(current_best)

            if current_best > best_ever + 1e-6:
                best_ever = current_best
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= self.early_stop_patience:
                stopped_early = True
                logger.info(f"[{self.symbol}] 早停于第 {gen} 代，连续 {patience_counter} 代无提升")
                break

            offspring = self.toolbox.select(pop, len(pop))
            offspring = list(map(self.toolbox.clone, offspring))

            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < self.crossover_rate:
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            for mutant in offspring:
                if random.random() < self.mutation_rate:
                    self.toolbox.mutate(mutant)
                    del mutant.fitness.values

            pop[:] = offspring

            if gen <= self.seed_reserve_gens:
                n_seed = int(self.population_size * self.seed_reserve_ratio)
                seeds = self.toolbox.population(n=n_seed)
                # 评估新种子的适应度
                for seed in seeds:
                    seed.fitness.values = self._evaluate_wrapper(seed)
                pop[-n_seed:] = seeds

        # 确保所有个体都有适应度（最后一代的后代可能没有被评估）
        invalid_ind = [ind for ind in pop if not ind.fitness.valid]
        for ind in invalid_ind:
            ind.fitness.values = self._evaluate_wrapper(ind)

        best_ind = tools.selBest(pop, 1)[0]
        best_expr = str(best_ind)
        best_fit = best_ind.fitness.values[0]

        metrics = FitnessMetrics(raw_fitness=best_fit)
        try:
            ast = parse_expr(best_expr)
            fn, _ = expr_to_func(best_expr)
            factor = fn(
                self.data["open"].values,
                self.data["high"].values,
                self.data["low"].values,
                self.data["close"].values,
                self.data["volume"].values,
                self.data.get("open_interest", self.data["close"]).values,
            )
            if factor is not None and np.isfinite(factor).any():
                metrics = _compute_metrics(factor, self.data, self.forward_periods)
                val_result = self.validator.validate(ast, symbol=self.symbol)
                metrics.penalty_factor = val_result.penalty_factor
        except Exception as e:
            logger.debug(f"验证失败: {e}")

        runtime = time.perf_counter() - t0
        result = EvolutionResult(
            symbol=self.symbol,
            generation=len(self.best_fitness_history),
            best_expr=best_expr,
            best_fitness=best_fit,
            metrics=metrics,
            population_stats={
                "avg": float(np.mean([ind.fitness.values[0] for ind in pop])),
                "std": float(np.std([ind.fitness.values[0] for ind in pop])),
                "max": float(max([ind.fitness.values[0] for ind in pop])),
                "min": float(min([ind.fitness.values[0] for ind in pop])),
            },
            runtime_seconds=runtime,
            stopped_early=stopped_early,
        )
        self._persist(result)
        return result

    def _persist(self, result: EvolutionResult) -> None:
        try:
            os.makedirs(os.path.dirname(SQLITE_PATH) if os.path.dirname(SQLITE_PATH) else ".", exist_ok=True)
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_results (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    generation INTEGER,
                    best_expr TEXT,
                    best_fitness REAL,
                    sharpe REAL,
                    calmar REAL,
                    ic_mean REAL,
                    max_dd REAL,
                    turnover REAL,
                    complexity REAL,
                    penalty_factor REAL,
                    runtime_seconds REAL,
                    stopped_early INTEGER,
                    created_at TEXT
                )
                """
            )
            cur.execute(
                """
                INSERT INTO evolution_results
                (id, symbol, generation, best_expr, best_fitness, sharpe, calmar, ic_mean,
                 max_dd, turnover, complexity, penalty_factor, runtime_seconds, stopped_early, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    result.symbol,
                    result.generation,
                    result.best_expr,
                    result.best_fitness,
                    result.metrics.sharpe,
                    result.metrics.calmar,
                    result.metrics.ic_mean,
                    result.metrics.max_dd,
                    result.metrics.turnover,
                    result.metrics.complexity,
                    result.metrics.penalty_factor,
                    result.runtime_seconds,
                    int(result.stopped_early),
                    pd.Timestamp.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"持久化进化结果失败: {e}")
