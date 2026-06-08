"""
流程编排器 (Orchestrator)

三阶段流水线编排：
- Stage 1: 单因子挖掘 (BroadAlphaSearch)
- Stage 2: 双因子组合 + 剪枝 (ComboSearch + ComboPruner)
- Stage 3: 组合调优 (ComboTuner)

特性：
- 错误处理和重试
- 每阶段结果持久化到 SQLite
- 支持单品种与批量品种执行
- 超时控制与日志追踪
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from ops.broad_alpha_search import BroadAlphaSearch, SingleFactorCandidate
from ops.combo_search import ComboSearch, ComboCandidate
from ops.combo_search_prune import ComboPruner, PrunedCombo
from ops.combo_tune import ComboTuner, TunedCandidate

logger = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/runtime.db")

DEFAULT_MAX_RETRIES = 2
DEFAULT_STAGE_TIMEOUT = 1800  # 30分钟


@dataclass
class StageResult:
    stage: int
    status: str  # success | failed | timeout | skipped
    candidates_count: int
    duration_seconds: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    symbol: str
    status: str
    stages: List[StageResult]
    total_duration: float
    final_candidates: List[TunedCandidate] = field(default_factory=list)
    error: Optional[str] = None


class EvolutionOrchestrator:
    """三阶段进化流水线编排器。"""

    def __init__(
        self,
        symbol: str,
        train_data: pd.DataFrame,
        val_data: Optional[pd.DataFrame] = None,
        test_data: Optional[pd.DataFrame] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        stage_timeout: int = DEFAULT_STAGE_TIMEOUT,
        forward_periods: int = 5,
    ) -> None:
        self.symbol = symbol
        self.train_data = train_data
        self.val_data = val_data
        self.test_data = test_data
        self.max_retries = max_retries
        self.stage_timeout = stage_timeout
        self.forward_periods = forward_periods
        self.results: List[StageResult] = []

    def _run_with_retry(
        self,
        stage_name: str,
        func: Callable[[], Any],
        min_results: int = 0,
    ) -> Tuple[Any, StageResult]:
        """带重试机制的阶段执行。"""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                logger.info(f"[{self.symbol}] {stage_name} 尝试 {attempt}/{self.max_retries}")
                result = func()
                duration = time.perf_counter() - t0

                count = len(result) if isinstance(result, list) else (1 if result else 0)
                if count < min_results:
                    logger.warning(f"[{self.symbol}] {stage_name} 结果不足: {count} < {min_results}")
                    return result, StageResult(
                        stage=int(stage_name[5]),
                        status="skipped",
                        candidates_count=count,
                        duration_seconds=duration,
                        details={"attempt": attempt, "reason": "insufficient_results"},
                    )

                stage_result = StageResult(
                    stage=int(stage_name[5]),
                    status="success",
                    candidates_count=count,
                    duration_seconds=duration,
                    details={"attempt": attempt},
                )
                logger.info(f"[{self.symbol}] {stage_name} 成功: {count} 个候选, {duration:.1f}s")
                return result, stage_result

            except Exception as e:
                duration = time.perf_counter() - t0
                last_error = str(e)
                logger.warning(f"[{self.symbol}] {stage_name} 失败 (尝试 {attempt}): {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        return None, StageResult(
            stage=int(stage_name[5]),
            status="failed",
            candidates_count=0,
            duration_seconds=duration,
            error=last_error,
            details={"attempts": self.max_retries},
        )

    def run(self) -> PipelineResult:
        """执行完整三阶段流水线。"""
        t0_total = time.perf_counter()
        logger.info(f"[{self.symbol}] 流水线启动")

        final_candidates: List[TunedCandidate] = []
        stages: List[StageResult] = []

        # Stage 1: 单因子挖掘
        stage1_search = BroadAlphaSearch(
            symbol=self.symbol,
            data=self.train_data,
            forward_periods=self.forward_periods,
        )
        stage1_results, stage1_meta = self._run_with_retry(
            "Stage1", stage1_search.run, min_results=1
        )
        stages.append(stage1_meta)
        if stage1_meta.status != "success":
            return PipelineResult(
                symbol=self.symbol,
                status="failed",
                stages=stages,
                total_duration=time.perf_counter() - t0_total,
                error=f"Stage 1 失败: {stage1_meta.error}",
            )

        # Stage 2: 双因子组合
        stage2_search = ComboSearch(
            symbol=self.symbol,
            data=self.train_data,
            stage1_candidates=stage1_results,
            forward_periods=self.forward_periods,
        )
        stage2_results, stage2_meta = self._run_with_retry(
            "Stage2", stage2_search.run, min_results=1
        )
        stages.append(stage2_meta)
        if stage2_meta.status != "success":
            return PipelineResult(
                symbol=self.symbol,
                status="failed",
                stages=stages,
                total_duration=time.perf_counter() - t0_total,
                error=f"Stage 2 失败: {stage2_meta.error}",
            )

        # 剪枝
        pruner = ComboPruner(symbol=self.symbol, data=self.train_data)
        pruned_results = pruner.prune(stage2_results)
        prune_meta = StageResult(
            stage=2,
            status="success" if len(pruned_results) > 0 else "skipped",
            candidates_count=len(pruned_results),
            duration_seconds=0.0,
            details={"pruned_from": len(stage2_results)},
        )
        stages.append(prune_meta)
        if prune_meta.status != "success":
            return PipelineResult(
                symbol=self.symbol,
                status="failed",
                stages=stages,
                total_duration=time.perf_counter() - t0_total,
                error="剪枝后无候选",
            )

        # Stage 3: 组合调优
        if self.val_data is None or self.test_data is None:
            logger.warning(f"[{self.symbol}] 缺少验证/测试数据，跳过 Stage 3")
            stage3_meta = StageResult(
                stage=3,
                status="skipped",
                candidates_count=0,
                duration_seconds=0.0,
                details={"reason": "missing_val_test_data"},
            )
            stages.append(stage3_meta)
        else:
            stage3_tuner = ComboTuner(
                symbol=self.symbol,
                train_data=self.train_data,
                val_data=self.val_data,
                test_data=self.test_data,
                pruned_combos=pruned_results,
                forward_periods=self.forward_periods,
            )
            stage3_results, stage3_meta = self._run_with_retry(
                "Stage3", stage3_tuner.run, min_results=1
            )
            stages.append(stage3_meta)
            if stage3_meta.status == "success" and stage3_results:
                final_candidates = stage3_results

        total_duration = time.perf_counter() - t0_total
        status = "success" if final_candidates else "partial"
        if not final_candidates and stage3_meta.status == "failed":
            status = "failed"

        result = PipelineResult(
            symbol=self.symbol,
            status=status,
            stages=stages,
            total_duration=total_duration,
            final_candidates=final_candidates,
        )
        self._persist_pipeline(result)
        logger.info(
            f"[{self.symbol}] 流水线完成: status={status}, duration={total_duration:.1f}s, final={len(final_candidates)}"
        )
        return result

    def _persist_pipeline(self, result: PipelineResult) -> None:
        try:
            os.makedirs(os.path.dirname(SQLITE_PATH) if os.path.dirname(SQLITE_PATH) else ".", exist_ok=True)
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pipeline_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    status TEXT,
                    stage1_status TEXT,
                    stage1_count INTEGER,
                    stage2_status TEXT,
                    stage2_count INTEGER,
                    prune_count INTEGER,
                    stage3_status TEXT,
                    stage3_count INTEGER,
                    total_duration REAL,
                    final_count INTEGER,
                    error TEXT,
                    created_at TEXT
                )
                """
            )
            s1 = next((s for s in result.stages if s.stage == 1), None)
            s2 = next((s for s in result.stages if s.stage == 2 and "pruned_from" not in s.details), None)
            sp = next((s for s in result.stages if s.stage == 2 and "pruned_from" in s.details), None)
            s3 = next((s for s in result.stages if s.stage == 3), None)

            cur.execute(
                """
                INSERT INTO pipeline_results
                (symbol, status, stage1_status, stage1_count, stage2_status, stage2_count,
                 prune_count, stage3_status, stage3_count, total_duration, final_count, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.symbol,
                    result.status,
                    s1.status if s1 else "unknown",
                    s1.candidates_count if s1 else 0,
                    s2.status if s2 else "unknown",
                    s2.candidates_count if s2 else 0,
                    sp.candidates_count if sp else 0,
                    s3.status if s3 else "unknown",
                    s3.candidates_count if s3 else 0,
                    result.total_duration,
                    len(result.final_candidates),
                    result.error,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"流水线持久化失败: {e}")


class BatchOrchestrator:
    """批量品种流水线编排。"""

    def __init__(
        self,
        data_provider: Callable[[str], Optional[pd.DataFrame]],
        max_workers: int = 4,
        forward_periods: int = 5,
    ) -> None:
        self.data_provider = data_provider
        self.max_workers = max_workers
        self.forward_periods = forward_periods
        self.results: List[PipelineResult] = []

    def run_single(self, symbol: str) -> PipelineResult:
        df = self.data_provider(symbol)
        if df is None or len(df) < 1000:
            return PipelineResult(
                symbol=symbol,
                status="failed",
                stages=[],
                total_duration=0.0,
                error="数据不足",
            )

        n = len(df)
        train_end = int(n * 0.5)
        val_end = int(n * 0.75)
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()

        orch = EvolutionOrchestrator(
            symbol=symbol,
            train_data=train_df,
            val_data=val_df,
            test_data=test_df,
            forward_periods=self.forward_periods,
        )
        return orch.run()

    def run_batch(self, symbols: List[str]) -> List[PipelineResult]:
        logger.info(f"批量流水线启动: 品种数={len(symbols)}, workers={self.max_workers}")
        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as exe:
            futures = {sym: exe.submit(self.run_single, sym) for sym in symbols}
            for sym, fut in futures.items():
                try:
                    result = fut.result(timeout=3600)
                except Exception as e:
                    result = PipelineResult(
                        symbol=sym,
                        status="failed",
                        stages=[],
                        total_duration=0.0,
                        error=str(e),
                    )
                results.append(result)
        self.results = results
        return results

    def summary(self) -> pd.DataFrame:
        if not self.results:
            return pd.DataFrame()
        records = []
        for r in self.results:
            records.append({
                "symbol": r.symbol,
                "status": r.status,
                "total_duration": r.total_duration,
                "final_count": len(r.final_candidates),
                "error": r.error,
            })
        return pd.DataFrame(records)
