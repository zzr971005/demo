"""
策略相关性分析 - 计算策略间相关性，避免过度集中
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.stats import pearsonr
from datetime import datetime

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """相关性分析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.correlation_threshold = self.config.get("correlation_threshold", 0.7)
    
    def calculate_pearson_correlation(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray
    ) -> float:
        """
        计算皮尔逊相关系数
        
        Parameters
        ----------
        returns1 : np.ndarray
            收益率序列1
        returns2 : np.ndarray
            收益率序列2
        
        Returns
        -------
        float
            相关系数
        """
        if len(returns1) != len(returns2) or len(returns1) < 2:
            return 0.0
        
        try:
            correlation, _ = pearsonr(returns1, returns2)
            return correlation
        except:
            return 0.0
    
    def calculate_correlation_matrix(
        self,
        returns_dict: Dict[str, np.ndarray]
    ) -> Dict[str, Dict[str, float]]:
        """
        计算相关性矩阵
        
        Parameters
        ----------
        returns_dict : Dict[str, np.ndarray]
            策略收益率字典
        
        Returns
        -------
        Dict[str, Dict[str, float]]
            相关性矩阵
        """
        strategies = list(returns_dict.keys())
        n = len(strategies)
        
        correlation_matrix = {}
        
        for i, strategy1 in enumerate(strategies):
            correlation_matrix[strategy1] = {}
            for j, strategy2 in enumerate(strategies):
                if i == j:
                    correlation_matrix[strategy1][strategy2] = 1.0
                else:
                    corr = self.calculate_pearson_correlation(
                        returns_dict[strategy1],
                        returns_dict[strategy2]
                    )
                    correlation_matrix[strategy1][strategy2] = corr
        
        return correlation_matrix
    
    def find_highly_correlated_pairs(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
        threshold: Optional[float] = None
    ) -> List[Tuple[str, str, float]]:
        """
        找出高相关性策略对
        
        Parameters
        ----------
        correlation_matrix : Dict[str, Dict[str, float]]
            相关性矩阵
        threshold : Optional[float]
            相关性阈值
        
        Returns
        -------
        List[Tuple[str, str, float]]
            高相关性策略对列表
        """
        if threshold is None:
            threshold = self.correlation_threshold
        
        highly_correlated = []
        strategies = list(correlation_matrix.keys())
        
        for i, strategy1 in enumerate(strategies):
            for j, strategy2 in enumerate(strategies):
                if i < j:  # 避免重复
                    corr = correlation_matrix[strategy1][strategy2]
                    if abs(corr) >= threshold:
                        highly_correlated.append((strategy1, strategy2, corr))
        
        # 按相关性排序
        highly_correlated.sort(key=lambda x: abs(x[2]), reverse=True)
        
        return highly_correlated
    
    def calculate_portfolio_correlation(
        self,
        weights: Dict[str, float],
        correlation_matrix: Dict[str, Dict[str, float]]
    ) -> float:
        """
        计算组合相关性
        
        Parameters
        ----------
        weights : Dict[str, float]
            权重字典
        correlation_matrix : Dict[str, Dict[str, float]]
            相关性矩阵
        
        Returns
        -------
        float
            组合相关性
        """
        strategies = list(weights.keys())
        weight_vector = np.array([weights[s] for s in strategies])
        
        # 构建相关性矩阵
        corr_array = np.array([
            [correlation_matrix[s1][s2] for s2 in strategies]
            for s1 in strategies
        ])
        
        # 计算组合相关性
        portfolio_correlation = np.sqrt(weight_vector @ corr_array @ weight_vector)
        
        return portfolio_correlation
    
    def diversify_portfolio(
        self,
        strategies: List[Dict[str, Any]],
        returns_dict: Dict[str, np.ndarray],
        max_correlation: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        分散化组合
        
        Parameters
        ----------
        strategies : List[Dict[str, Any]]
            策略列表
        returns_dict : Dict[str, np.ndarray]
            收益率字典
        max_correlation : float
            最大相关性
        
        Returns
        -------
        List[Dict[str, Any]]
            分散化后的策略列表
        """
        if not strategies:
            return []
        
        # 计算相关性矩阵
        correlation_matrix = self.calculate_correlation_matrix(returns_dict)
        
        # 找出高相关性对
        highly_correlated = self.find_highly_correlated_pairs(
            correlation_matrix,
            max_correlation
        )
        
        # 移除高相关性策略
        selected_strategies = strategies.copy()
        strategy_ids = {s["id"] for s in strategies}
        
        for strategy1, strategy2, corr in highly_correlated:
            if strategy1 in strategy_ids and strategy2 in strategy_ids:
                # 移除相关性较高的策略（保留评分较高的）
                s1 = next(s for s in strategies if s["id"] == strategy1)
                s2 = next(s for s in strategies if s["id"] == strategy2)
                
                score1 = s1.get("composite_score", 0)
                score2 = s2.get("composite_score", 0)
                
                if score1 < score2 and strategy1 in strategy_ids:
                    selected_strategies = [s for s in selected_strategies if s["id"] != strategy1]
                    strategy_ids.remove(strategy1)
                elif score2 < score1 and strategy2 in strategy_ids:
                    selected_strategies = [s for s in selected_strategies if s["id"] != strategy2]
                    strategy_ids.remove(strategy2)
        
        logger.info(f"分散化: {len(strategies)} -> {len(selected_strategies)} 个策略")
        
        return selected_strategies
    
    def analyze_correlation(
        self,
        strategies: List[Dict[str, Any]],
        returns_dict: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """
        综合相关性分析
        
        Parameters
        ----------
        strategies : List[Dict[str, Any]]
            策略列表
        returns_dict : Dict[str, np.ndarray]
            收益率字典
        
        Returns
        -------
        Dict[str, Any]
            分析结果
        """
        # 计算相关性矩阵
        correlation_matrix = self.calculate_correlation_matrix(returns_dict)
        
        # 找出高相关性对
        highly_correlated = self.find_highly_correlated_pairs(correlation_matrix)
        
        # 计算平均相关性
        all_correlations = []
        strategies_list = list(correlation_matrix.keys())
        for i, s1 in enumerate(strategies_list):
            for j, s2 in enumerate(strategies_list):
                if i < j:
                    all_correlations.append(abs(correlation_matrix[s1][s2]))
        
        avg_correlation = np.mean(all_correlations) if all_correlations else 0
        max_correlation = max(all_correlations) if all_correlations else 0
        
        return {
            "correlation_matrix": correlation_matrix,
            "highly_correlated_pairs": highly_correlated,
            "avg_correlation": avg_correlation,
            "max_correlation": max_correlation,
            "strategy_count": len(strategies),
            "analyzed_at": datetime.utcnow()
        }
