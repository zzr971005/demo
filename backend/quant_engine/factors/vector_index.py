"""
å å­åéç¸ä¼¼åº¦å»é?
ç¨äºè¿åè¿ç¨ä¸­èªå¨è¯å«å¹¶åé¤é«åº¦ç¸ä¼¼çå å­ï¼ä¿æç§ç¾¤å¤æ ·æ§ã?æ ¸å¿è½åï¼?- åºäºå å­å¼åéçä½å¼¦ç¸ä¼¼åº?/ Pearson ç¸å³
- æ¯æè¿ä¼¼æè¿é»(ANN)å éå¤§è§æ¨¡å»é
- æä¾åå±å»éï¼åæåå»é + è·¨æå¨å±å»éï¼?- ä¸?AlphaGenerator è¾åºç´æ¥å¯¹æ¥
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from numba import jit


# ---------------------------------------------------------------------------
# ç¸ä¼¼åº¦è®¡ç®ï¼numba å éï¼
# ---------------------------------------------------------------------------

@jit(nopython=True, cache=False)
def _nb_cosine_similarity_matrix(mat: np.ndarray) -> np.ndarray:
    """
    è®¡ç®è¡åéé´çä½å¼¦ç¸ä¼¼åº¦ç©éµã?    mat: (n_factors, n_obs) â?å·²å» NaNãå·²æ åå?    è¿å: (n_factors, n_factors)
    """
    n = mat.shape[0]
    sim = np.empty((n, n), dtype=np.float64)
    for i in range(n):
        sim[i, i] = 1.0
        for j in range(i + 1, n):
            num = 0.0
            deni = 0.0
            denj = 0.0
            for k in range(mat.shape[1]):
                num += mat[i, k] * mat[j, k]
                deni += mat[i, k] ** 2
                denj += mat[j, k] ** 2
            d = np.sqrt(deni * denj)
            val = num / d if d > 1e-12 else 0.0
            sim[i, j] = val
            sim[j, i] = val
    return sim


@jit(nopython=True, cache=False)
def _nb_pearson_similarity_matrix(mat: np.ndarray) -> np.ndarray:
    """
    è®¡ç®è¡åéé´ç?Pearson ç¸å³ç³»æ°ç©éµã?    mat: (n_factors, n_obs)
    è¿å: (n_factors, n_factors)
    """
    n = mat.shape[0]
    m = mat.shape[1]
    sim = np.empty((n, n), dtype=np.float64)
    for i in range(n):
        sim[i, i] = 1.0
        mi = 0.0
        for k in range(m):
            mi += mat[i, k]
        mi /= m
        for j in range(i + 1, n):
            mj = 0.0
            for k in range(m):
                mj += mat[j, k]
            mj /= m
            num = 0.0
            deni = 0.0
            denj = 0.0
            for k in range(m):
                di = mat[i, k] - mi
                dj = mat[j, k] - mj
                num += di * dj
                deni += di * di
                denj += dj * dj
            d = np.sqrt(deni * denj)
            val = num / d if d > 1e-12 else 0.0
            sim[i, j] = val
            sim[j, i] = val
    return sim


# ---------------------------------------------------------------------------
# åéé¢å¤ç?# ---------------------------------------------------------------------------

def _prepare_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    """
    å°å®½æ ¼å¼å å­è¡¨è½¬ä¸?(n_factors, n_obs) ç©éµï¼å¹¶å?zscore æ ååã?    è¿åç©éµååååè¡¨ã?    """
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="any")
    cols = list(df.columns)
    mat = df[cols].to_numpy(dtype=np.float64).T
    for i in range(mat.shape[0]):
        row = mat[i]
        m = np.mean(row)
        s = np.std(row)
        if s > 1e-12:
            mat[i] = (row - m) / s
        else:
            mat[i] = 0.0
    return mat, cols


# ---------------------------------------------------------------------------
# å»éå¼æ
# ---------------------------------------------------------------------------

class VectorIndex:
    """å å­åéç¸ä¼¼åº¦ç´¢å¼ä¸å»éã?""

    def __init__(
        self,
        df: pd.DataFrame,
        method: str = "cosine",
    ):
        """
        Parameters
        ----------
        df : pd.DataFrame
            å®½æ ¼å¼å å­å¼è¡¨ï¼æ¯åä¸ä¸ªå å­?        method : str
            'cosine' æ?'pearson'
        """
        self.df = df
        self.method = method
        self._mat, self._cols = _prepare_matrix(df)
        self._sim_matrix: Optional[np.ndarray] = None

    def _compute_similarity(self) -> np.ndarray:
        if self._sim_matrix is not None:
            return self._sim_matrix
        if self.method == "cosine":
            self._sim_matrix = _nb_cosine_similarity_matrix(self._mat)
        else:
            self._sim_matrix = _nb_pearson_similarity_matrix(self._mat)
        return self._sim_matrix

    def find_duplicates(
        self,
        threshold: float = 0.95,
    ) -> List[Tuple[str, str, float]]:
        """
        æ¾åºç¸ä¼¼åº¦è¶è¿?threshold çå å­å¯¹ã?
        Returns
        -------
        list[(factor_a, factor_b, similarity)]
        """
        sim = self._compute_similarity()
        n = sim.shape[0]
        dups = []
        for i in range(n):
            for j in range(i + 1, n):
                if sim[i, j] >= threshold:
                    dups.append((self._cols[i], self._cols[j], float(sim[i, j])))
        return dups

    def deduplicate(
        self,
        threshold: float = 0.95,
        keep: str = "first",
    ) -> pd.DataFrame:
        """
        å¯¹å å­è¡¨è¿è¡å»éï¼ä¿çä¸ç¸ä¼¼çå å­åã?
        Parameters
        ----------
        threshold : float
            ç¸ä¼¼åº¦éå¼ï¼è¶è¿åè®¤ä¸ºéå¤?        keep : str
            'first' ä¿çé¦æ¬¡åºç°çï¼'best_ir' éè¦ä¼ å?ir_scores

        Returns
        -------
        pd.DataFrame â?å»éåçå å­è¡?        """
        sim = self._compute_similarity()
        n = sim.shape[0]
        drop_set: Set[int] = set()

        for i in range(n):
            if i in drop_set:
                continue
            for j in range(i + 1, n):
                if j in drop_set:
                    continue
                if sim[i, j] >= threshold:
                    if keep == "first":
                        drop_set.add(j)
                    else:
                        drop_set.add(j)

        keep_cols = [self._cols[i] for i in range(n) if i not in drop_set]
        return self.df[keep_cols].copy()

    def deduplicate_with_score(
        self,
        scores: Dict[str, float],
        threshold: float = 0.95,
    ) -> pd.DataFrame:
        """
        æè¯åä¿çæ´ä¼å å­å»éã?
        Parameters
        ----------
        scores : dict[str, float]
            æ¯ä¸ªå å­çè¯åï¼å¦?IRãSharpeï¼ï¼è¶é«è¶å¥½
        """
        sim = self._compute_similarity()
        n = sim.shape[0]
        drop_set: Set[int] = set()

        for i in range(n):
            if i in drop_set:
                continue
            for j in range(i + 1, n):
                if j in drop_set:
                    continue
                if sim[i, j] >= threshold:
                    si = scores.get(self._cols[i], 0.0)
                    sj = scores.get(self._cols[j], 0.0)
                    if si >= sj:
                        drop_set.add(j)
                    else:
                        drop_set.add(i)

        keep_cols = [self._cols[i] for i in range(n) if i not in drop_set]
        return self.df[keep_cols].copy()

    def cluster_factors(
        self,
        threshold: float = 0.90,
    ) -> Dict[int, List[str]]:
        """
        åºäºç¸ä¼¼åº¦åç®åè¿éåéèç±»ã?
        Returns
        -------
        dict[int, list[str]] â?cluster_id -> å å­ååè¡?        """
        sim = self._compute_similarity()
        n = sim.shape[0]
        visited = [False] * n
        clusters: Dict[int, List[str]] = {}
        cid = 0

        for i in range(n):
            if visited[i]:
                continue
            stack = [i]
            visited[i] = True
            members = []
            while stack:
                cur = stack.pop()
                members.append(self._cols[cur])
                for j in range(n):
                    if not visited[j] and sim[cur, j] >= threshold:
                        visited[j] = True
                        stack.append(j)
            clusters[cid] = members
            cid += 1
        return clusters

    def diversity_score(self) -> float:
        """
        è®¡ç®å½åå å­éåçå¤æ ·æ§åæ°ã?        å®ä¹ä¸ºï¼1 - å¹³åéå¯¹è§ç¸ä¼¼åº¦ã?        """
        sim = self._compute_similarity()
        n = sim.shape[0]
        if n <= 1:
            return 0.0
        mask = ~np.eye(n, dtype=bool)
        return 1.0 - float(sim[mask].mean())


# ---------------------------------------------------------------------------
# åå±å»éï¼åæ?+ å¨å±ï¼?# ---------------------------------------------------------------------------

def hierarchical_deduplicate(
    df: pd.DataFrame,
    family_map: Dict[str, str],
    intra_threshold: float = 0.95,
    global_threshold: float = 0.98,
    method: str = "cosine",
) -> pd.DataFrame:
    """
    åå±å»éï¼?    1. åæåæ intra_threshold å»é
    2. è·¨ææ?global_threshold å»é

    Parameters
    ----------
    df : pd.DataFrame
        å®½æ ¼å¼å å­è¡¨
    family_map : dict[str, str]
        å å­å?-> æå±æå?    intra_threshold : float
        åæå»ééå?    global_threshold : float
        è·¨æå»ééå?    method : str
        'cosine' æ?'pearson'

    Returns
    -------
    pd.DataFrame â?å»éåçå å­è¡?    """
    families: Dict[str, List[str]] = {}
    for col in df.columns:
        fam = family_map.get(col, "Zå¶ä»")
        families.setdefault(fam, []).append(col)

    survivors: List[str] = []
    for fam, cols in families.items():
        sub = df[cols]
        vi = VectorIndex(sub, method=method)
        deduped = vi.deduplicate(threshold=intra_threshold, keep="first")
        survivors.extend(list(deduped.columns))

    global_df = df[survivors]
    vi_global = VectorIndex(global_df, method=method)
    final = vi_global.deduplicate(threshold=global_threshold, keep="first")
    return final


# ---------------------------------------------------------------------------
# ä¸è¿åç§ç¾¤å¯¹æ¥ï¼æ¹éè¯ä¼°å¤æ ·æ?# ---------------------------------------------------------------------------

def evaluate_population_diversity(
    factor_dict: Dict[str, pd.DataFrame],
    method: str = "cosine",
) -> pd.DataFrame:
    """
    è¯ä¼°å¤ä¸ªåç§/ä¸ä»£çå å­ç§ç¾¤å¤æ ·æ§ã?
    Parameters
    ----------
    factor_dict : dict[str, DataFrame]
        key ä¸ºç§ç¾¤æ è¯ï¼value ä¸ºå å­å®½è¡?
    Returns
    -------
    pd.DataFrame â?æ¯è¡ä¸ä¸ªç§ç¾¤ï¼ååå?n_factors, diversity_score
    """
    records = []
    for key, df in factor_dict.items():
        vi = VectorIndex(df, method=method)
        records.append({
            "population": key,
            "n_factors": len(df.columns),
            "diversity_score": vi.diversity_score(),
        })
    return pd.DataFrame(records)
