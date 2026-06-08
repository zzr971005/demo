"""
策略选择器 - 从因子池中选择最优策略

负责：
- 从50个最优因子中选择5个策略
- 按IC半衰期分类
- 计算因子相关性
- 确保策略多样性
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)


def classify_factor_by_half_life(half_life: Optional[int]) -> Optional[str]:
    """按IC半衰期分类因子"""
    if half_life is None:
        return None
    if half_life <= 2:
        return "fast"  # 快速衰减（动量、情绪）
    elif half_life <= 3:
        return "medium"  # 中等衰减（价值、技术）
    else:
        return "slow"  # 慢速衰减（成长、质量）


def calculate_composite_score(factor: Dict[str, Any]) -> float:
    """计算综合评分（IC + 回测绩效）"""
    # IC评分
    ic_mean_4h = factor.get("ic_mean_4h", 0) or 0
    ic_mean_24h = factor.get("ic_mean_24h", 0) or 0
    ic_mean_168h = factor.get("ic_mean_168h", 0) or 0
    
    ic_score = ic_mean_4h * 0.5 + ic_mean_24h * 0.3 + ic_mean_168h * 0.2
    
    # 回测绩效评分
    sharpe = factor.get("sharpe_train", 0) or 0
    calmar = factor.get("calmar", 0) or 0
    max_drawdown = factor.get("max_drawdown", 0) or 0
    win_rate = factor.get("win_rate", 0) or 0
    total_trades = factor.get("total_trades", 0) or 0
    
    # 归一化
    sharpe_norm = max(0, min(1, (sharpe + 2) / 7))
    calmar_norm = max(0, min(1, calmar / 5))
    drawdown_score = max(0, 1 - max_drawdown)
    win_rate_norm = win_rate
    trades_norm = min(1, total_trades / 100)
    
    performance_score = (
        sharpe_norm * 0.4 +
        calmar_norm * 0.2 +
        drawdown_score * 0.2 +
        win_rate_norm * 0.1 +
        trades_norm * 0.1
    )
    
    # 混合评分
    composite_score = ic_score * 0.5 + performance_score * 0.5
    
    return composite_score


def calculate_factor_correlation(factor1: Dict[str, Any], factor2: Dict[str, Any]) -> float:
    """
    计算两个因子的相关性
    
    简化版：使用公式相似度作为相关性代理
    实际应该使用因子值序列计算相关性
    """
    # 简化实现：使用公式相似度
    formula1 = factor1.get("formula", "")
    formula2 = factor2.get("formula", "")
    
    # 计算Jaccard相似度
    set1 = set(formula1.replace("(", " ").replace(")", " ").split())
    set2 = set(formula2.replace("(", " ").replace(")", " ").split())
    
    if len(set1) == 0 or len(set2) == 0:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    similarity = intersection / union if union > 0 else 0.0
    
    return similarity


def has_high_correlation(
    factor: Dict[str, Any],
    selected_factors: List[Dict[str, Any]],
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
    threshold: float = 0.7
) -> bool:
    """检查因子是否与已选因子高相关"""
    for selected in selected_factors:
        if correlation_matrix:
            corr = correlation_matrix.get(factor["id"], {}).get(selected["id"], 0.0)
        else:
            corr = calculate_factor_correlation(factor, selected)
        
        if corr > threshold:
            return True
    
    return False


def select_top_strategies(
    top_factors: List[Dict[str, Any]],
    count: int = 5,
    category_distribution: Optional[Dict[str, int]] = None
) -> List[Dict[str, Any]]:
    """
    从最优因子池中选择策略
    
    Parameters
    ----------
    top_factors : List[Dict[str, Any]]
        最优因子列表
    count : int
        选择策略数量
    category_distribution : Dict[str, int]
        分类分配，如 {"fast": 2, "medium": 2, "slow": 1}
    
    Returns
    -------
    List[Dict[str, Any]]
        选择的策略列表
    """
    if category_distribution is None:
        category_distribution = {"fast": 2, "medium": 2, "slow": 1}
    
    # 1. 按IC半衰期分类
    categorized = {"fast": [], "medium": [], "slow": []}
    for factor in top_factors:
        half_life = factor.get("ic_half_life")
        category = classify_factor_by_half_life(half_life)
        if category:
            categorized[category].append(factor)
    
    # 2. 每类按综合评分排序
    for category in categorized:
        categorized[category].sort(
            key=lambda x: calculate_composite_score(x),
            reverse=True
        )
    
    # 3. 按配置分配数量
    candidates = []
    for category, target_count in category_distribution.items():
        candidates.extend(categorized[category][:target_count])
    
    # 4. 如果候选不足，放宽限制
    if len(candidates) < count:
        # 从所有因子中补充
        all_sorted = sorted(top_factors, key=lambda x: calculate_composite_score(x), reverse=True)
        for factor in all_sorted:
            if factor not in candidates:
                candidates.append(factor)
            if len(candidates) >= count:
                break
    
    # 5. 计算相关性矩阵（简化版）
    correlation_matrix = {}
    for i, f1 in enumerate(candidates):
        correlation_matrix[f1["id"]] = {}
        for j, f2 in enumerate(candidates):
            if i != j:
                correlation_matrix[f1["id"]][f2["id"]] = calculate_factor_correlation(f1, f2)
    
    # 6. 移除高相关性因子
    selected = []
    for factor in candidates:
        if not has_high_correlation(factor, selected, correlation_matrix, threshold=0.7):
            selected.append(factor)
        if len(selected) >= count:
            break
    
    # 7. 如果仍然不足，放宽相关性阈值
    if len(selected) < count:
        for factor in candidates:
            if factor not in selected:
                selected.append(factor)
            if len(selected) >= count:
                break
    
    # 8. 设置策略排名
    for i, factor in enumerate(selected):
        factor["strategy_rank"] = i + 1
    
    return selected[:count]


class StrategySelector:
    """策略选择器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化策略选择器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.strategy_count = self.config.get("strategy_selection", {}).get("count", 5)
        self.category_distribution = self.config.get("strategy_selection", {}).get("category_distribution", {"fast": 2, "medium": 2, "slow": 1})
        self.correlation_threshold = self.config.get("strategy_selection", {}).get("min_correlation_threshold", 0.7)
    
    def select_strategies(self, top_factors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        选择策略
        
        Parameters
        ----------
        top_factors : List[Dict[str, Any]]
            最优因子列表
        
        Returns
        -------
        List[Dict[str, Any]]
            选择的策略列表
        """
        return select_top_strategies(
            top_factors,
            count=self.strategy_count,
            category_distribution=self.category_distribution
        )
