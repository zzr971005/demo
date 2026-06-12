"""
Stage 2: 双因子组合搜索 (Combo Search)

- 跨族组合（至少2个不同族）
- 筛选夏普 > 0.8
- 使用 FamilyChecker 验证
- 基于 Stage 1 候选进行组合进化
"""

from __future__ import annotations

import itertools
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from factors.formula_dsl import (
    BinOpNode,
    ExprNode,
    FuncNode,
    collect_functions,
    expr_to_func,
    parse_expr,
    tree_depth,
)
from factors.ic_analysis import rank_ic, rolling_ic
from factors.registry import FACTOR_REGISTRY, PrimitiveFamily
from factors.semantic_validator import SemanticValidator
from ops.broad_alpha_search import SingleFactorCandidate
from ops.evolve_search import DEAPEvolutionEngine, FitnessMetrics

logger = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/runtime.db")

STAGE2_MIN_SHARPE = 0.8
STAGE2_MAX_TREE_DEPTH = 6
STAGE2_POPULATION = 300
STAGE2_GENERATIONS = 40
STAGE2_EARLY_STOP = 5


@dataclass
class ComboCandidate:
    candidate_id: str
    symbol: str
    formula: str
    families: List[str]
    sharpe: float
    calmar: float
    ic_mean: float
    max_dd: float
    turnover: float
    fitness: float
    parent_ids: List[str]
    created_at: str


class FamilyChecker:
    """验证表达式是否包含至少 2 个不同族。"""

    def __init__(self) -> None:
        pass

    def check(self, expr_str: str) -> Tuple[bool, List[str]]:
        try:
            ast = parse_expr(expr_str)
        except Exception as e:
            logger.debug(f"解析表达式失败: {e}")
            return False, []
        funcs = collect_functions(ast)
        families: Set[PrimitiveFamily] = set()
        for fn in funcs:
            meta = FACTOR_REGISTRY.get(fn)
            if meta and meta.family:
                families.add(meta.family)
        return len(families) >= 2, [f.value for f in families]


class ComboSearch:
    """Stage 2: 跨族双因子组合进化。"""

    def __init__(
        self,
        symbol: str,
        data: pd.DataFrame,
        stage1_candidates: List[SingleFactorCandidate],
        min_sharpe: float = STAGE2_MIN_SHARPE,
        max_tree_depth: int = STAGE2_MAX_TREE_DEPTH,
        population_size: int = STAGE2_POPULATION,
        max_generations: int = STAGE2_GENERATIONS,
        early_stop_patience: int = STAGE2_EARLY_STOP,
        forward_periods: int = 5,
    ) -> None:
        self.symbol = symbol
        self.data = data
        self.stage1_candidates = stage1_candidates
        self.min_sharpe = min_sharpe
        self.max_tree_depth = max_tree_depth
        self.population_size = population_size
        self.max_generations = max_generations
        self.early_stop_patience = early_stop_patience
        self.forward_periods = forward_periods
        self.validator = SemanticValidator(max_tree_depth=max_tree_depth)
        self.family_checker = FamilyChecker()
        self.combos: List[ComboCandidate] = []

    def _generate_cross_family_pairs(self) -> List[Tuple[SingleFactorCandidate, SingleFactorCandidate]]:
        pairs = []
        for c1, c2 in itertools.combinations(self.stage1_candidates, 2):
            if c1.family != c2.family:
                pairs.append((c1, c2))
        logger.info(f"[{self.symbol}] Stage 2 跨族组合对数: {len(pairs)}")
        return pairs

    def _build_combo_expr(self, c1: SingleFactorCandidate, c2: SingleFactorCandidate, op: str = "add") -> str:
        expr = f"({c1.formula} {op} {c2.formula})"
        return expr

    def _evaluate_combo(self, expr: str, parent_ids: List[str]) -> Optional[ComboCandidate]:
        ok, families = self.family_checker.check(expr)
        if not ok:
            return None

        val_result = self.validator.validate(parse_expr(expr), symbol=self.symbol)
        if not val_result.is_valid:
            return None

        try:
            fn, _ = expr_to_func(expr)
            factor = fn(
                self.data["open"].values,
                self.data["high"].values,
                self.data["low"].values,
                self.data["close"].values,
                self.data["volume"].values,
                self.data.get("open_interest", self.data["close"]).values,
            )
        except Exception as e:
            logger.debug(f"计算因子失败: {e}")
            return None

        if factor is None or not np.isfinite(factor).any():
            return None

        metrics = self._compute_combo_metrics(factor)
        metrics.penalty_factor = val_result.penalty_factor
        fitness = metrics.composite_score()

        if metrics.sharpe < self.min_sharpe:
            return None

        return ComboCandidate(
            candidate_id=str(uuid.uuid4())[:8],
            symbol=self.symbol,
            formula=expr,
            families=families,
            sharpe=metrics.sharpe,
            calmar=metrics.calmar,
            ic_mean=metrics.ic_mean,
            max_dd=metrics.max_dd,
            turnover=metrics.turnover,
            fitness=fitness,
            parent_ids=parent_ids,
            created_at=pd.Timestamp.now().isoformat(),
        )

    def _compute_combo_metrics(self, factor: np.ndarray) -> FitnessMetrics:
        from ops.evolve_search import _compute_metrics
        return _compute_metrics(factor, self.data, self.forward_periods)

    def run(self) -> List[ComboCandidate]:
        logger.info(f"[{self.symbol}] Stage 2 开始: 双因子组合搜索")
        pairs = self._generate_cross_family_pairs()
        results: List[ComboCandidate] = []

        ops = ["add", "sub", "mul"]
        for c1, c2 in pairs:
            for op in ops:
                expr = self._build_combo_expr(c1, c2, op=op)
                if tree_depth(parse_expr(expr)) > self.max_tree_depth:
                    continue
                combo = self._evaluate_combo(expr, [c1.candidate_id, c2.candidate_id])
                if combo:
                    results.append(combo)

        if len(results) < 10:
            logger.info(f"[{self.symbol}] Stage 2 组合数不足，启动 GP 进化补充")
            engine = DEAPEvolutionEngine(
                symbol=self.symbol,
                data=self.data,
                families=None,
                population_size=self.population_size,
                max_generations=self.max_generations,
                early_stop_patience=self.early_stop_patience,
                max_tree_depth=self.max_tree_depth,
                forward_periods=self.forward_periods,
                n_jobs=1,
            )
            gp_result = engine.run()
            ok, families = self.family_checker.check(gp_result.best_expr)
            if ok and gp_result.metrics.sharpe >= self.min_sharpe:
                results.append(
                    ComboCandidate(
                        candidate_id=str(uuid.uuid4())[:8],
                        symbol=self.symbol,
                        formula=gp_result.best_expr,
                        families=families,
                        sharpe=gp_result.metrics.sharpe,
                        calmar=gp_result.metrics.calmar,
                        ic_mean=gp_result.metrics.ic_mean,
                        max_dd=gp_result.metrics.max_dd,
                        turnover=gp_result.metrics.turnover,
                        fitness=gp_result.best_fitness,
                        parent_ids=[],
                        created_at=pd.Timestamp.now().isoformat(),
                    )
                )

        self.combos = results
        self._persist(results)
        logger.info(f"[{self.symbol}] Stage 2 完成: 产生 {len(results)} 个组合候选")
        return results

    def _persist(self, combos: List[ComboCandidate]) -> None:
        try:
            os.makedirs(os.path.dirname(SQLITE_PATH) if os.path.dirname(SQLITE_PATH) else ".", exist_ok=True)
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stage2_combos (
                    candidate_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    formula TEXT,
                    families TEXT,
                    sharpe REAL,
                    calmar REAL,
                    ic_mean REAL,
                    max_dd REAL,
                    turnover REAL,
                    fitness REAL,
                    parent_ids TEXT,
                    created_at TEXT
                )
                """
            )
            for c in combos:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO stage2_combos
                    (candidate_id, symbol, formula, families, sharpe, calmar, ic_mean, max_dd, turnover, fitness, parent_ids, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c.candidate_id,
                        c.symbol,
                        c.formula,
                        json.dumps(c.families, ensure_ascii=False),
                        c.sharpe,
                        c.calmar,
                        c.ic_mean,
                        c.max_dd,
                        c.turnover,
                        c.fitness,
                        json.dumps(c.parent_ids),
                        c.created_at,
                    ),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Stage 2 持久化失败: {e}")

    def get_top_combos(self, n: int = 10, by: str = "sharpe") -> List[ComboCandidate]:
        if not self.combos:
            return []
        sorted_combos = sorted(self.combos, key=lambda x: getattr(x, by, x.sharpe), reverse=True)
        return sorted_combos[:n]


import json
