"""
Stage 1: 单因子挖掘 (Broad Alpha Search)

- 树深 <= 4
- 筛选 IC > 0.03
- 生成单因子候选
- 使用 evolve_search.py 中的 DEAPEvolutionEngine
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from factors.formula_dsl import parse_expr, tree_depth
from factors.ic_analysis import rank_ic
from factors.registry import PrimitiveFamily, list_primitives
from factors.semantic_validator import SemanticValidator
from ops.evolve_search import DEAPEvolutionEngine, FitnessMetrics

logger = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/runtime.db")

# Stage 1 约束
STAGE1_MAX_TREE_DEPTH = 4
STAGE1_MIN_IC = 0.03
STAGE1_POPULATION = 300
STAGE1_GENERATIONS = 40
STAGE1_EARLY_STOP = 5


@dataclass
class SingleFactorCandidate:
    candidate_id: str
    symbol: str
    formula: str
    family: str
    ic: float
    sharpe: float
    calmar: float
    max_dd: float
    tree_depth: int
    fitness: float
    created_at: str


class BroadAlphaSearch:
    """Stage 1: 在各族内独立进化单因子，筛选高IC候选。"""

    def __init__(
        self,
        symbol: str,
        data: pd.DataFrame,
        families: Optional[List[PrimitiveFamily]] = None,
        min_ic: float = STAGE1_MIN_IC,
        max_tree_depth: int = STAGE1_MAX_TREE_DEPTH,
        population_size: int = STAGE1_POPULATION,
        max_generations: int = STAGE1_GENERATIONS,
        early_stop_patience: int = STAGE1_EARLY_STOP,
        forward_periods: int = 5,
    ) -> None:
        self.symbol = symbol
        self.data = data
        self.families = families or list(PrimitiveFamily)
        self.min_ic = min_ic
        self.max_tree_depth = max_tree_depth
        self.population_size = population_size
        self.max_generations = max_generations
        self.early_stop_patience = early_stop_patience
        self.forward_periods = forward_periods
        self.validator = SemanticValidator(max_tree_depth=max_tree_depth)
        self.candidates: List[SingleFactorCandidate] = []

    def run(self) -> List[SingleFactorCandidate]:
        logger.info(f"[{self.symbol}] Stage 1 开始: 单因子挖掘, 族数={len(self.families)}")
        all_candidates: List[SingleFactorCandidate] = []

        for family in self.families:
            family_name = family.value
            logger.info(f"[{self.symbol}] 进化族: {family_name}")
            engine = DEAPEvolutionEngine(
                symbol=self.symbol,
                data=self.data,
                families=[family],
                population_size=self.population_size,
                max_generations=self.max_generations,
                early_stop_patience=self.early_stop_patience,
                max_tree_depth=self.max_tree_depth,
                min_tree_depth=1,
                forward_periods=self.forward_periods,
                n_jobs=1,
            )
            result = engine.run()

            if result.metrics.ic_mean < self.min_ic:
                logger.info(
                    f"[{self.symbol}] {family_name} IC={result.metrics.ic_mean:.4f} < {self.min_ic}, 跳过"
                )
                continue

            try:
                depth = tree_depth(parse_expr(result.best_expr))
            except Exception as e:
                logger.debug(f"计算表达式深度失败: {e}")
                depth = 0

            candidate = SingleFactorCandidate(
                candidate_id=str(uuid.uuid4())[:8],
                symbol=self.symbol,
                formula=result.best_expr,
                family=family_name,
                ic=result.metrics.ic_mean,
                sharpe=result.metrics.sharpe,
                calmar=result.metrics.calmar,
                max_dd=result.metrics.max_dd,
                tree_depth=depth,
                fitness=result.best_fitness,
                created_at=pd.Timestamp.now().isoformat(),
            )
            all_candidates.append(candidate)
            logger.info(
                f"[{self.symbol}] {family_name} 候选: IC={candidate.ic:.4f}, Sharpe={candidate.sharpe:.4f}"
            )

        self.candidates = all_candidates
        self._persist(all_candidates)
        logger.info(f"[{self.symbol}] Stage 1 完成: 产生 {len(all_candidates)} 个单因子候选")
        return all_candidates

    def _persist(self, candidates: List[SingleFactorCandidate]) -> None:
        try:
            os.makedirs(os.path.dirname(SQLITE_PATH) if os.path.dirname(SQLITE_PATH) else ".", exist_ok=True)
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stage1_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    formula TEXT,
                    family TEXT,
                    ic REAL,
                    sharpe REAL,
                    calmar REAL,
                    max_dd REAL,
                    tree_depth INTEGER,
                    fitness REAL,
                    created_at TEXT
                )
                """
            )
            for c in candidates:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO stage1_candidates
                    (candidate_id, symbol, formula, family, ic, sharpe, calmar, max_dd, tree_depth, fitness, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c.candidate_id,
                        c.symbol,
                        c.formula,
                        c.family,
                        c.ic,
                        c.sharpe,
                        c.calmar,
                        c.max_dd,
                        c.tree_depth,
                        c.fitness,
                        c.created_at,
                    ),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Stage 1 持久化失败: {e}")

    def get_top_candidates(self, n: int = 10, by: str = "ic") -> List[SingleFactorCandidate]:
        if not self.candidates:
            return []
        sorted_candidates = sorted(
            self.candidates, key=lambda x: getattr(x, by, x.ic), reverse=True
        )
        return sorted_candidates[:n]
