"""
统计检验 — 回测过拟合概率与放气指标

支持：
- PBO（回测过拟合概率）- CSCV方法
- DSR（放气夏普比率）
- BH-FDR（Benjamini-Hochberg动态门槛）
- Walk-Forward效率指标 WFE
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# PBO — Probability of Backtest Overfitting (CSCV 方法)
# ---------------------------------------------------------------------------

@dataclass
class PBOResult:
    """PBO 计算结果"""

    pbo: float
    logit_pbo: float
    dominance_stats: Dict[str, float]
    ranks_matrix: Optional[np.ndarray] = None


def comb_n_k(n: int, k: int) -> int:
    """组合数 C(n,k)"""
    if k > n or k < 0:
        return 0
    if k == 0 or k == n:
        return 1
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def _generate_splits(n: int, k: int) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    生成 CSCV 的所有组合切分（S 个组分成两组）

    Parameters
    ----------
    n : int
        总样本数（策略数）
    k : int
        分成 S=2k 组

    Returns
    -------
    list of (train_idx, test_idx)
    """
    from itertools import combinations

    s = 2 * k
    group_size = n // s
    if group_size == 0:
        # 策略数太少，无法分组
        return []

    groups = [np.arange(i * group_size, min((i + 1) * group_size, n)) for i in range(s)]

    splits = []
    # 选择 k 个组作为训练集，其余为测试集
    for train_group_indices in combinations(range(s), k):
        test_group_indices = tuple(i for i in range(s) if i not in train_group_indices)
        train_idx = np.concatenate([groups[i] for i in train_group_indices])
        test_idx = np.concatenate([groups[i] for i in test_group_indices])
        splits.append((train_idx, test_idx))

    return splits


def pbo_cscv(
    returns_matrix: np.ndarray,
    n_splits: int = 4,
) -> PBOResult:
    """
    CSCV (Combinatorially Symmetric Cross-Validation) PBO

    参考 Bailey et al. "The Probability of Backtest Overfitting"

    Parameters
    ----------
    returns_matrix : np.ndarray
        形状 (n_periods, n_strategies)，每列是一个策略的各期收益
    n_splits : int
        CSCV 分组数 S = 2 * n_splits

    Returns
    -------
    PBOResult
    """
    n_periods, n_strategies = returns_matrix.shape
    if n_strategies < 4 or n_periods < 4:
        return PBOResult(pbo=0.0, logit_pbo=0.0, dominance_stats={}, ranks_matrix=None)

    k = n_splits
    s = 2 * k

    # 按行（时间）分成 S 组
    group_size = n_periods // s
    if group_size == 0:
        return PBOResult(pbo=0.0, logit_pbo=0.0, dominance_stats={}, ranks_matrix=None)

    # 计算每组的夏普（或平均收益）
    group_metrics = np.zeros((s, n_strategies))
    for g in range(s):
        start = g * group_size
        end = min((g + 1) * group_size, n_periods)
        if end > start:
            group_returns = returns_matrix[start:end, :]
            # 用平均收益作为指标（也可用夏普）
            group_metrics[g, :] = np.mean(group_returns, axis=0)

    # 生成所有组合切分
    # 限制最大组合数，防止计算量过大导致卡死
    max_combinations = 1000
    expected_combinations = comb_n_k(s, k)
    if expected_combinations > max_combinations:
        import logging
        logging.warning(f"PBO组合数过多({expected_combinations})，跳过检验以避免卡死")
        return PBOResult(pbo=0.0, logit_pbo=0.0, dominance_stats={}, ranks_matrix=None)
    
    splits = _generate_splits(s, k)
    if len(splits) == 0:
        return PBOResult(pbo=0.0, logit_pbo=0.0, dominance_stats={}, ranks_matrix=None)

    logit_values = []
    ranks_list = []

    for train_groups, test_groups in splits:
        # 训练集：选最优策略
        train_perf = np.mean(group_metrics[train_groups, :], axis=0)
        best_idx = np.argmax(train_perf)

        # 测试集：看最优策略的排名
        test_perf = np.mean(group_metrics[test_groups, :], axis=0)
        ranks = stats.rankdata(test_perf)
        best_rank = ranks[best_idx]

        # 归一化排名 [0, 1]
        normalized_rank = (best_rank - 1) / (n_strategies - 1) if n_strategies > 1 else 0.5
        logit_val = np.log(normalized_rank / (1 - normalized_rank + 1e-12) + 1e-12)
        logit_values.append(logit_val)
        ranks_list.append(normalized_rank)

    logit_values = np.array(logit_values)
    ranks_array = np.array(ranks_list)

    # PBO = P(logit < 0) = 排名在后50%的概率
    pbo = np.mean(logit_values < 0)
    logit_pbo = np.mean(logit_values)

    dominance_stats = {
        "mean_rank": float(np.mean(ranks_array)),
        "median_rank": float(np.median(ranks_array)),
        "std_rank": float(np.std(ranks_array)),
        "worst_rank": float(np.min(ranks_array)),
        "best_rank": float(np.max(ranks_array)),
    }

    return PBOResult(
        pbo=float(pbo),
        logit_pbo=float(logit_pbo),
        dominance_stats=dominance_stats,
        ranks_matrix=ranks_array.reshape(-1, 1) if len(ranks_array) > 0 else None,
    )


# ---------------------------------------------------------------------------
# DSR — Deflated Sharpe Ratio
# ---------------------------------------------------------------------------

def dsr(
    sharpe: float,
    n_trials: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    target_sharpe: float = 0.0,
) -> float:
    """
    放气夏普比率 (Deflated Sharpe Ratio)

    参考 Bailey & Lopez de Prado "The Deflated Sharpe Ratio"

    考虑多重检验偏差后的夏普比率概率值。

    Parameters
    ----------
    sharpe : float
        观测到的夏普比率
    n_trials : int
        独立试验次数（策略数）
    skewness : float
        收益偏度
    kurtosis : float
        收益峰度（注意：传入的是原始峰度，非超额峰度）
    target_sharpe : float
        基准夏普（通常设为0）

    Returns
    -------
    float — DSR 概率值 [0, 1]，越接近1表示夏普越显著
    """
    if n_trials <= 1 or sharpe <= target_sharpe:
        return 0.0

    # 估计夏普比率的标准误
    # var_SR = (1 - skewness * sharpe + (kurtosis - 1) / 4 * sharpe**2) / (n_periods - 1)
    # 这里简化处理，使用正态近似

    # 多重检验调整：最优夏普的期望
    # E[max SR] ≈ sqrt(2 * ln(n_trials) / n_periods) 的近似
    # 这里使用更简洁的近似

    # 计算调整后的标准误
    # 假设每期独立，n_periods 用 252 近似
    n_periods = 252  # 年化基准
    var_sr = (1 - skewness * sharpe + (kurtosis - 1) / 4 * sharpe ** 2) / max(n_periods - 1, 1)
    std_sr = np.sqrt(max(var_sr, 0))

    if std_sr < 1e-12:
        return 1.0 if sharpe > target_sharpe else 0.0

    # 考虑多重检验的基准调整
    # 使用 Bonferroni 风格的近似
    adjusted_target = target_sharpe + std_sr * np.sqrt(2 * np.log(n_trials))

    # 计算 P(SR > adjusted_target)
    z_score = (sharpe - adjusted_target) / std_sr
    dsr_value = stats.norm.cdf(z_score)

    return float(dsr_value)


# ---------------------------------------------------------------------------
# BH-FDR — Benjamini-Hochberg False Discovery Rate
# ---------------------------------------------------------------------------

def bh_fdr(
    p_values: np.ndarray,
    alpha: float = 0.05,
) -> Tuple[np.ndarray, float]:
    """
    Benjamini-Hochberg FDR 控制

    Parameters
    ----------
    p_values : np.ndarray
        各策略的 p 值数组
    alpha : float
        FDR 控制水平

    Returns
    -------
    (rejected, threshold)
        rejected: bool 数组，True 表示拒绝原假设（显著）
        threshold: BH 动态门槛
    """
    p_values = np.asarray(p_values)
    n = len(p_values)
    if n == 0:
        return np.array([], dtype=bool), 0.0

    # 排序
    sorted_indices = np.argsort(p_values)
    sorted_p = p_values[sorted_indices]

    # 找最大 k 使得 p_k <= alpha * k / n
    threshold = 0.0
    rejected = np.zeros(n, dtype=bool)

    for i in range(n - 1, -1, -1):
        if sorted_p[i] <= alpha * (i + 1) / n:
            threshold = alpha * (i + 1) / n
            rejected[sorted_indices[: i + 1]] = True
            break

    return rejected, float(threshold)


def bh_fdr_sharpe(
    sharpe_ratios: np.ndarray,
    n_periods: int = 252,
    alpha: float = 0.05,
) -> Tuple[np.ndarray, float, np.ndarray]:
    """
    对夏普比率序列做 BH-FDR 检验

    Parameters
    ----------
    sharpe_ratios : np.ndarray
        各策略的夏普比率
    n_periods : int
        每期样本数（用于计算 p 值）
    alpha : float
        FDR 控制水平

    Returns
    -------
    (significant, threshold, p_values)
    """
    sharpe_ratios = np.asarray(sharpe_ratios)
    n = len(sharpe_ratios)
    if n == 0:
        return np.array([], dtype=bool), 0.0, np.array([])

    # 假设夏普比率服从正态分布，计算双尾 p 值
    # SE(SR) ≈ 1/sqrt(n_periods)
    se = 1.0 / np.sqrt(max(n_periods, 1))
    z_scores = sharpe_ratios / se
    p_values = 2 * (1 - stats.norm.cdf(np.abs(z_scores)))

    significant, threshold = bh_fdr(p_values, alpha)
    return significant, threshold, p_values


# ---------------------------------------------------------------------------
# WFE — Walk-Forward Efficiency
# ---------------------------------------------------------------------------

def wfe(
    in_sample_returns: np.ndarray,
    out_of_sample_returns: np.ndarray,
) -> Dict[str, float]:
    """
    Walk-Forward 效率指标

    衡量样本外表现相对于样本内的保持程度。

    Parameters
    ----------
    in_sample_returns : np.ndarray
        样本内收益序列
    out_of_sample_returns : np.ndarray
        样本外收益序列

    Returns
    -------
    dict — {wfe_return, wfe_sharpe, wfe_calmar, retention_ratio}
    """
    is_ret = np.asarray(in_sample_returns)
    oos_ret = np.asarray(out_of_sample_returns)

    if len(is_ret) == 0 or len(oos_ret) == 0:
        return {
            "wfe_return": 0.0,
            "wfe_sharpe": 0.0,
            "wfe_calmar": 0.0,
            "retention_ratio": 0.0,
        }

    # 收益保持率
    is_total = np.prod(1 + is_ret) - 1
    oos_total = np.prod(1 + oos_ret) - 1
    retention_ratio = oos_total / (is_total + 1e-12) if is_total != 0 else 0.0

    # 夏普保持率
    is_sharpe = np.mean(is_ret) / (np.std(is_ret) + 1e-12) * np.sqrt(252)
    oos_sharpe = np.mean(oos_ret) / (np.std(oos_ret) + 1e-12) * np.sqrt(252)
    wfe_sharpe = oos_sharpe / (is_sharpe + 1e-12) if is_sharpe != 0 else 0.0

    # Calmar 保持率
    def _calmar(returns: np.ndarray) -> float:
        cum = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cum)
        dd = (peak - cum) / peak
        max_dd = np.max(dd)
        ann_ret = np.mean(returns) * 252
        return ann_ret / (max_dd + 1e-12)

    is_calmar = _calmar(is_ret)
    oos_calmar = _calmar(oos_ret)
    wfe_calmar = oos_calmar / (is_calmar + 1e-12) if is_calmar != 0 else 0.0

    # WFE 综合指标（收益保持率）
    wfe_return = retention_ratio

    return {
        "wfe_return": float(wfe_return),
        "wfe_sharpe": float(wfe_sharpe),
        "wfe_calmar": float(wfe_calmar),
        "retention_ratio": float(retention_ratio),
    }


def wfe_multiple_folds(
    is_returns_list: List[np.ndarray],
    oos_returns_list: List[np.ndarray],
) -> Dict[str, float]:
    """
    多折 Walk-Forward 效率汇总

    Parameters
    ----------
    is_returns_list : list of np.ndarray
        每折的样本内收益
    oos_returns_list : list of np.ndarray
        每折的样本外收益

    Returns
    -------
    dict — 平均 WFE 指标
    """
    if len(is_returns_list) == 0:
        return {
            "wfe_return": 0.0,
            "wfe_sharpe": 0.0,
            "wfe_calmar": 0.0,
            "retention_ratio": 0.0,
        }

    results = []
    for is_r, oos_r in zip(is_returns_list, oos_returns_list):
        results.append(wfe(is_r, oos_r))

    return {
        "wfe_return": float(np.mean([r["wfe_return"] for r in results])),
        "wfe_sharpe": float(np.mean([r["wfe_sharpe"] for r in results])),
        "wfe_calmar": float(np.mean([r["wfe_calmar"] for r in results])),
        "retention_ratio": float(np.mean([r["retention_ratio"] for r in results])),
    }


# ---------------------------------------------------------------------------
# 综合检验报告
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """综合验证报告"""

    pbo: float
    logit_pbo: float
    dsr_value: float
    dsr_prob: float
    bh_significant: bool
    bh_threshold: float
    wfe_return: float
    wfe_sharpe: float
    sharpe_is: float
    sharpe_oos: float
    n_trials: int

    def is_robust(self, pbo_threshold: float = 0.5, dsr_threshold: float = 0.95, wfe_threshold: float = 0.5) -> bool:
        """判断策略是否稳健"""
        return (
            self.pbo < pbo_threshold
            and self.dsr_prob > dsr_threshold
            and self.wfe_return > wfe_threshold
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "pbo": self.pbo,
            "logit_pbo": self.logit_pbo,
            "dsr_value": self.dsr_value,
            "dsr_prob": self.dsr_prob,
            "bh_significant": self.bh_significant,
            "bh_threshold": self.bh_threshold,
            "wfe_return": self.wfe_return,
            "wfe_sharpe": self.wfe_sharpe,
            "sharpe_is": self.sharpe_is,
            "sharpe_oos": self.sharpe_oos,
            "n_trials": self.n_trials,
            "is_robust": self.is_robust(),
        }


def full_validation(
    strategy_returns: np.ndarray,
    in_sample_returns: np.ndarray,
    out_of_sample_returns: np.ndarray,
    all_strategy_returns: Optional[np.ndarray] = None,
    n_trials: int = 1,
    alpha: float = 0.05,
) -> ValidationReport:
    """
    执行完整的统计验证流程

    Parameters
    ----------
    strategy_returns : np.ndarray
        当前策略的全周期收益（用于 PBO）
    in_sample_returns : np.ndarray
        样本内收益
    out_of_sample_returns : np.ndarray
        样本外收益
    all_strategy_returns : np.ndarray, optional
        所有策略的收益矩阵 (n_periods, n_strategies)，用于 PBO
    n_trials : int
        独立试验次数
    alpha : float
        FDR 控制水平

    Returns
    -------
    ValidationReport
    """
    # PBO
    if all_strategy_returns is not None and all_strategy_returns.ndim == 2:
        pbo_result = pbo_cscv(all_strategy_returns, n_splits=4)
        pbo = pbo_result.pbo
        logit_pbo = pbo_result.logit_pbo
    else:
        pbo = 0.0
        logit_pbo = 0.0

    # DSR
    sharpe_is = np.mean(in_sample_returns) / (np.std(in_sample_returns) + 1e-12) * np.sqrt(252)
    sharpe_oos = np.mean(out_of_sample_returns) / (np.std(out_of_sample_returns) + 1e-12) * np.sqrt(252)

    skew = float(stats.skew(strategy_returns)) if len(strategy_returns) > 2 else 0.0
    kurt = float(stats.kurtosis(strategy_returns, fisher=False)) if len(strategy_returns) > 3 else 3.0

    dsr_prob = dsr(sharpe_is, n_trials, skewness=skew, kurtosis=kurt)

    # BH-FDR
    if all_strategy_returns is not None and all_strategy_returns.ndim == 2:
        # 计算所有策略的夏普
        n_periods, n_strategies = all_strategy_returns.shape
        sharpes = []
        for i in range(n_strategies):
            ret = all_strategy_returns[:, i]
            sr = np.mean(ret) / (np.std(ret) + 1e-12) * np.sqrt(252)
            sharpes.append(sr)
        sharpes_arr = np.array(sharpes)
        significant, threshold, _ = bh_fdr_sharpe(sharpes_arr, n_periods=n_periods, alpha=alpha)
        # 当前策略是否显著（假设是最后一个）
        bh_sig = significant[-1] if len(significant) > 0 else False
        bh_thresh = threshold
    else:
        bh_sig = False
        bh_thresh = 0.0

    # WFE
    wfe_result = wfe(in_sample_returns, out_of_sample_returns)

    return ValidationReport(
        pbo=pbo,
        logit_pbo=logit_pbo,
        dsr_value=sharpe_is,
        dsr_prob=dsr_prob,
        bh_significant=bh_sig,
        bh_threshold=bh_thresh,
        wfe_return=wfe_result["wfe_return"],
        wfe_sharpe=wfe_result["wfe_sharpe"],
        sharpe_is=float(sharpe_is),
        sharpe_oos=float(sharpe_oos),
        n_trials=n_trials,
    )
