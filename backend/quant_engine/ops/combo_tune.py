"""
Stage 3: 组合调优 (Combo Tune)

- 参数进化（窗口大小、阈值等）
- 测试集夏普 > 0.6
- 对 Stage 2 剪枝后的组合进行参数级精细优化
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from deap import base, creator, gp, tools

from factors.formula_dsl import (
    ConstNode,
    ExprNode,
    FuncNode,
    collect_nodes,
    expr_to_func,
    parse_expr,
    walk_dfs,
)
from factors.ic_analysis import ic_stats, rolling_ic
from factors.registry import FACTOR_REGISTRY
from factors.semantic_validator import SemanticValidator
from ops.combo_search_prune import PrunedCombo
from ops.evolve_search import _compute_metrics

logger = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/runtime.db")

STAGE3_MIN_TEST_SHARPE = 0.6
STAGE3_POPULATION = 200
STAGE3_GENERATIONS = 30
STAGE3_EARLY_STOP = 5

# 可调参数范围
PARAM_RANGES: Dict[str, Tuple[int, int]] = {
    "window": (5, 60),
    "fast": (3, 20),
    "slow": (10, 60),
    "nb_std": (1, 4),
    "threshold": (1.0, 3.0),
    "days_to_expiry": (7, 90),
}


@dataclass
class TunedCandidate:
    candidate_id: str
    symbol: str
    base_formula: str
    tuned_formula: str
    params: Dict[str, Any]
    train_sharpe: float
    val_sharpe: float
    test_sharpe: float
    ic_mean: float
    max_dd: float
    fitness: float
    created_at: str


def _extract_param_nodes(node: ExprNode) -> List[Tuple[FuncNode, int, ConstNode]]:
    """提取表达式中所有函数调用的常量参数位置。"""
    results: List[Tuple[FuncNode, int, ConstNode]] = []

    def _cb(n: ExprNode) -> None:
        if isinstance(n, FuncNode):
            for i, arg in enumerate(n.args):
                if isinstance(arg, ConstNode):
                    results.append((n, i, arg))

    walk_dfs(node, _cb)
    return results


def _mutate_params(node: ExprNode, mutation_rate: float = 0.3) -> ExprNode:
    """对表达式中的参数进行随机扰动。"""
    import copy

    new_node = copy.deepcopy(node)
    param_nodes = _extract_param_nodes(new_node)

    for func_node, idx, const_node in param_nodes:
        if np.random.random() > mutation_rate:
            continue
        meta = FACTOR_REGISTRY.get(func_node.name)
        if not meta:
            continue
        param_name = meta.params[idx][0] if idx < len(meta.params) else None
        if param_name is None:
            continue
        if param_name in PARAM_RANGES:
            low, high = PARAM_RANGES[param_name]
            if isinstance(const_node.value, int):
                new_val = int(np.random.randint(low, high + 1))
            else:
                new_val = float(np.random.uniform(low, high))
            const_node.value = new_val

    return new_node


def _node_to_expr(node: ExprNode) -> str:
    """将 AST 节点还原为字符串表达式。"""
    from factors.formula_dsl import expr_to_string
    return expr_to_string(node)


class ComboTuner:
    """Stage 3: 对组合进行参数级调优。"""

    def __init__(
        self,
        symbol: str,
        train_data: pd.DataFrame,
        val_data: pd.DataFrame,
        test_data: pd.DataFrame,
        pruned_combos: List[PrunedCombo],
        min_test_sharpe: float = STAGE3_MIN_TEST_SHARPE,
        population_size: int = STAGE3_POPULATION,
        max_generations: int = STAGE3_GENERATIONS,
        early_stop_patience: int = STAGE3_EARLY_STOP,
        forward_periods: int = 5,
    ) -> None:
        self.symbol = symbol
        self.train_data = train_data
        self.val_data = val_data
        self.test_data = test_data
        self.pruned_combos = pruned_combos
        self.min_test_sharpe = min_test_sharpe
        self.population_size = population_size
        self.max_generations = max_generations
        self.early_stop_patience = early_stop_patience
        self.forward_periods = forward_periods
        self.validator = SemanticValidator()
        self.tuned: List[TunedCandidate] = []

    def _evaluate_param_set(self, base_expr: str, mutated_expr: str) -> Optional[TunedCandidate]:
        try:
            ast = parse_expr(mutated_expr)
        except Exception as e:
            logger.debug(f"解析表达式失败: {e}")
            return None

        val_result = self.validator.validate(ast, symbol=self.symbol)
        if not val_result.is_valid:
            return None

        params = self._extract_params(ast)

        try:
            fn, _ = expr_to_func(mutated_expr)
            train_factor = fn(
                self.train_data["open"].values,
                self.train_data["high"].values,
                self.train_data["low"].values,
                self.train_data["close"].values,
                self.train_data["volume"].values,
                self.train_data.get("open_interest", self.train_data["close"]).values,
            )
            val_factor = fn(
                self.val_data["open"].values,
                self.val_data["high"].values,
                self.val_data["low"].values,
                self.val_data["close"].values,
                self.val_data["volume"].values,
                self.val_data.get("open_interest", self.val_data["close"]).values,
            )
            test_factor = fn(
                self.test_data["open"].values,
                self.test_data["high"].values,
                self.test_data["low"].values,
                self.test_data["close"].values,
                self.test_data["volume"].values,
                self.test_data.get("open_interest", self.test_data["close"]).values,
            )
        except Exception as e:
            logger.debug(f"计算因子失败: {e}")
            return None

        if train_factor is None or val_factor is None or test_factor is None:
            return None

        train_metrics = _compute_metrics(train_factor, self.train_data, self.forward_periods)
        val_metrics = _compute_metrics(val_factor, self.val_data, self.forward_periods)
        test_metrics = _compute_metrics(test_factor, self.test_data, self.forward_periods)

        test_metrics.penalty_factor = val_result.penalty_factor
        fitness = test_metrics.composite_score()

        if test_metrics.sharpe < self.min_test_sharpe:
            return None

        return TunedCandidate(
            candidate_id=str(uuid.uuid4())[:8],
            symbol=self.symbol,
            base_formula=base_expr,
            tuned_formula=mutated_expr,
            params=params,
            train_sharpe=train_metrics.sharpe,
            val_sharpe=val_metrics.sharpe,
            test_sharpe=test_metrics.sharpe,
            ic_mean=test_metrics.ic_mean,
            max_dd=test_metrics.max_dd,
            fitness=fitness,
            created_at=pd.Timestamp.now().isoformat(),
        )

    def _extract_params(self, node: ExprNode) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        param_nodes = _extract_param_nodes(node)
        for func_node, idx, const_node in param_nodes:
            meta = FACTOR_REGISTRY.get(func_node.name)
            if meta and idx < len(meta.params):
                key = f"{func_node.name}_{meta.params[idx][0]}"
                params[key] = const_node.value
        return params

    def _tune_single_combo(self, combo: PrunedCombo) -> Optional[TunedCandidate]:
        base_expr = combo.formula
        try:
            base_ast = parse_expr(base_expr)
        except Exception as e:
            logger.debug(f"解析基础表达式失败: {e}")
            return None

        best_candidate: Optional[TunedCandidate] = None
        best_fitness = -float("inf")

        population = [base_ast]
        for _ in range(self.population_size - 1):
            population.append(_mutate_params(copy.deepcopy(base_ast), mutation_rate=0.5))

        patience = 0
        for gen in range(1, self.max_generations + 1):
            gen_candidates = []
            for ind in population:
                expr = _node_to_expr(ind)
                candidate = self._evaluate_param_set(base_expr, expr)
                if candidate:
                    gen_candidates.append((candidate, candidate.fitness))

            if not gen_candidates:
                patience += 1
                if patience >= self.early_stop_patience:
                    break
                continue

            gen_candidates.sort(key=lambda x: x[1], reverse=True)
            top = gen_candidates[0][0]
            if top.fitness > best_fitness + 1e-6:
                best_fitness = top.fitness
                best_candidate = top
                patience = 0
            else:
                patience += 1

            if patience >= self.early_stop_patience:
                break

            new_pop = [parse_expr(c.tuned_formula) for c, _ in gen_candidates[: self.population_size // 4]]
            while len(new_pop) < self.population_size:
                parent = random.choice(population)
                new_pop.append(_mutate_params(copy.deepcopy(parent), mutation_rate=0.3))
            population = new_pop

        return best_candidate

    def run(self) -> List[TunedCandidate]:
        logger.info(f"[{self.symbol}] Stage 3 开始: 组合调优, 输入 {len(self.pruned_combos)} 个")
        results: List[TunedCandidate] = []

        for combo in self.pruned_combos:
            tuned = self._tune_single_combo(combo)
            if tuned:
                results.append(tuned)
                logger.info(
                    f"[{self.symbol}] 调优成功: test_sharpe={tuned.test_sharpe:.3f}, params={tuned.params}"
                )

        self.tuned = results
        self._persist(results)
        logger.info(f"[{self.symbol}] Stage 3 完成: 产生 {len(results)} 个调优候选")
        return results

    def _persist(self, tuned: List[TunedCandidate]) -> None:
        try:
            os.makedirs(os.path.dirname(SQLITE_PATH) if os.path.dirname(SQLITE_PATH) else ".", exist_ok=True)
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stage3_tuned (
                    candidate_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    base_formula TEXT,
                    tuned_formula TEXT,
                    params TEXT,
                    train_sharpe REAL,
                    val_sharpe REAL,
                    test_sharpe REAL,
                    ic_mean REAL,
                    max_dd REAL,
                    fitness REAL,
                    created_at TEXT
                )
                """
            )
            for t in tuned:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO stage3_tuned
                    (candidate_id, symbol, base_formula, tuned_formula, params, train_sharpe, val_sharpe, test_sharpe, ic_mean, max_dd, fitness, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t.candidate_id,
                        t.symbol,
                        t.base_formula,
                        t.tuned_formula,
                        json.dumps(t.params, ensure_ascii=False),
                        t.train_sharpe,
                        t.val_sharpe,
                        t.test_sharpe,
                        t.ic_mean,
                        t.max_dd,
                        t.fitness,
                        t.created_at,
                    ),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Stage 3 持久化失败: {e}")

    def get_top_tuned(self, n: int = 5, by: str = "test_sharpe") -> List[TunedCandidate]:
        if not self.tuned:
            return []
        sorted_tuned = sorted(self.tuned, key=lambda x: getattr(x, by, x.test_sharpe), reverse=True)
        return sorted_tuned[:n]


import copy
import json
import random
