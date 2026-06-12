"""
组合剪枝 (Combo Search Prune)

- 基于相关性剪枝：剔除高度相关（|corr| > 0.85）的冗余组合
- 基于IC稳定性剪枝：剔除 IC 滚动标准差过大（IR < 0.3）的不稳定组合
- 输出精简后的高质量组合列表
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from factors.formula_dsl import expr_to_func
from factors.ic_analysis import ic_stats, rolling_ic
from ops.combo_search import ComboCandidate

logger = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/runtime.db")

# 剪枝阈值
CORR_THRESHOLD = 0.85
MIN_IR = 0.3
MAX_TURNOVER = 0.5


@dataclass
class PrunedCombo:
    candidate_id: str
    symbol: str
    formula: str
    families: List[str]
    sharpe: float
    calmar: float
    ic_mean: float
    ic_std: float
    ir: float
    max_dd: float
    turnover: float
    avg_correlation: float
    prune_reason: Optional[str] = None
    kept: bool = True


class ComboPruner:
    """组合剪枝器：相关性与IC稳定性双重过滤。"""

    def __init__(
        self,
        symbol: str,
        data: pd.DataFrame,
        corr_threshold: float = CORR_THRESHOLD,
        min_ir: float = MIN_IR,
        max_turnover: float = MAX_TURNOVER,
        forward_periods: int = 5,
    ) -> None:
        self.symbol = symbol
        self.data = data
        self.corr_threshold = corr_threshold
        self.min_ir = min_ir
        self.max_turnover = max_turnover
        self.forward_periods = forward_periods
        self.pruned: List[PrunedCombo] = []

    def _compute_factor_values(self, combos: List[ComboCandidate]) -> Optional[pd.DataFrame]:
        series_list = []
        valid_ids = []
        for combo in combos:
            try:
                fn, _ = expr_to_func(combo.formula)
                factor = fn(
                    self.data["open"].values,
                    self.data["high"].values,
                    self.data["low"].values,
                    self.data["close"].values,
                    self.data["volume"].values,
                    self.data.get("open_interest", self.data["close"]).values,
                )
                if factor is not None and np.isfinite(factor).any():
                    series_list.append(pd.Series(factor, index=self.data.index, name=combo.candidate_id))
                    valid_ids.append(combo.candidate_id)
            except Exception as e:
                logger.debug(f"计算因子失败: {e}")
                continue
        if not series_list:
            return None
        return pd.concat(series_list, axis=1)

    def _ic_stability_filter(self, factor_df: pd.DataFrame, combos: List[ComboCandidate]) -> Set[str]:
        close = self.data["close"]
        fwd_ret = np.empty_like(close.values)
        fwd_ret[:] = np.nan
        valid = close.values[:-self.forward_periods] > 0
        fwd_ret[:-self.forward_periods][valid] = np.log(
            close.values[self.forward_periods:][valid] / close.values[:-self.forward_periods][valid]
        )
        fwd_s = pd.Series(fwd_ret, index=self.data.index)

        keep_ids = set()
        for combo in combos:
            cid = combo.candidate_id
            if cid not in factor_df.columns:
                continue
            f = factor_df[cid]
            ic_s = rolling_ic(f, fwd_s, window=60, method="rank").dropna()
            if len(ic_s) < 10:
                continue
            st = ic_stats(ic_s)
            ir = st.ir if np.isfinite(st.ir) else 0.0
            if ir >= self.min_ir:
                keep_ids.add(cid)
            else:
                logger.info(f"[{self.symbol}] {cid} IR={ir:.3f} < {self.min_ir}, 剔除")
        return keep_ids

    def _correlation_prune(self, factor_df: pd.DataFrame, keep_ids: Set[str]) -> Set[str]:
        if len(keep_ids) <= 1:
            return keep_ids

        sub_df = factor_df[list(keep_ids)].dropna()
        if sub_df.empty or sub_df.shape[1] < 2:
            return keep_ids

        corr_matrix = sub_df.corr().abs()
        final_ids = set(keep_ids)
        removed = set()

        ids_sorted = sorted(keep_ids, key=lambda x: corr_matrix.loc[x, x], reverse=False)

        for i, cid1 in enumerate(ids_sorted):
            if cid1 in removed:
                continue
            for cid2 in ids_sorted[i + 1:]:
                if cid2 in removed:
                    continue
                c = corr_matrix.loc[cid1, cid2]
                if c > self.corr_threshold:
                    removed.add(cid2)
                    logger.info(f"[{self.symbol}] {cid1}-{cid2} 相关={c:.3f} > {self.corr_threshold}, 剔除 {cid2}")

        return final_ids - removed

    def prune(self, combos: List[ComboCandidate]) -> List[PrunedCombo]:
        logger.info(f"[{self.symbol}] 开始组合剪枝: 初始 {len(combos)} 个")
        factor_df = self._compute_factor_values(combos)
        if factor_df is None:
            logger.warning(f"[{self.symbol}] 无法计算因子值，跳过剪枝")
            return []

        keep_ids = self._ic_stability_filter(factor_df, combos)
        logger.info(f"[{self.symbol}] IC稳定性过滤后: {len(keep_ids)} 个")

        final_ids = self._correlation_prune(factor_df, keep_ids)
        logger.info(f"[{self.symbol}] 相关性剪枝后: {len(final_ids)} 个")

        results = []
        for combo in combos:
            cid = combo.candidate_id
            f = factor_df.get(cid)
            avg_corr = 0.0
            if f is not None and len(final_ids) > 1:
                other_cols = [c for c in final_ids if c != cid and c in factor_df.columns]
                if other_cols:
                    avg_corr = float(factor_df[cid].corr(factor_df[other_cols].mean(axis=1)))
                    avg_corr = abs(avg_corr) if np.isfinite(avg_corr) else 0.0

            close = self.data["close"]
            fwd_ret = np.empty_like(close.values)
            fwd_ret[:] = np.nan
            valid = close.values[:-self.forward_periods] > 0
            fwd_ret[:-self.forward_periods][valid] = np.log(
                close.values[self.forward_periods:][valid] / close.values[:-self.forward_periods][valid]
            )
            fwd_s = pd.Series(fwd_ret, index=self.data.index)
            ic_s = rolling_ic(factor_df[cid], fwd_s, window=60, method="rank").dropna() if cid in factor_df.columns else pd.Series()
            st = ic_stats(ic_s) if len(ic_s) > 0 else None

            pruned = PrunedCombo(
                candidate_id=cid,
                symbol=combo.symbol,
                formula=combo.formula,
                families=combo.families,
                sharpe=combo.sharpe,
                calmar=combo.calmar,
                ic_mean=st.mean_ic if st else combo.ic_mean,
                ic_std=st.std_ic if st else 0.0,
                ir=st.ir if st else 0.0,
                max_dd=combo.max_dd,
                turnover=combo.turnover,
                avg_correlation=avg_corr,
                kept=cid in final_ids,
                prune_reason=None if cid in final_ids else (
                    "high_corr" if cid not in final_ids and cid in keep_ids else "low_ir"
                ),
            )
            results.append(pruned)

        self.pruned = results
        self._persist(results)
        kept = [r for r in results if r.kept]
        logger.info(f"[{self.symbol}] 剪枝完成: 保留 {len(kept)} 个")
        return kept

    def _persist(self, pruned: List[PrunedCombo]) -> None:
        try:
            os.makedirs(os.path.dirname(SQLITE_PATH) if os.path.dirname(SQLITE_PATH) else ".", exist_ok=True)
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stage2_pruned (
                    candidate_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    formula TEXT,
                    families TEXT,
                    sharpe REAL,
                    calmar REAL,
                    ic_mean REAL,
                    ic_std REAL,
                    ir REAL,
                    max_dd REAL,
                    turnover REAL,
                    avg_correlation REAL,
                    kept INTEGER,
                    prune_reason TEXT,
                    created_at TEXT
                )
                """
            )
            for p in pruned:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO stage2_pruned
                    (candidate_id, symbol, formula, families, sharpe, calmar, ic_mean, ic_std, ir, max_dd, turnover, avg_correlation, kept, prune_reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p.candidate_id,
                        p.symbol,
                        p.formula,
                        json.dumps(p.families, ensure_ascii=False),
                        p.sharpe,
                        p.calmar,
                        p.ic_mean,
                        p.ic_std,
                        p.ir,
                        p.max_dd,
                        p.turnover,
                        p.avg_correlation,
                        int(p.kept),
                        p.prune_reason,
                        pd.Timestamp.now().isoformat(),
                    ),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"剪枝持久化失败: {e}")


import json
