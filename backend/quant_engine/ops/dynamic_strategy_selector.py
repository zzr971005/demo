"""
动态策略选择器 - 模拟交易专用
每品种选择1个最优策略，支持动态权重分配
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DynamicStrategySelector:
    """动态策略选择器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化动态策略选择器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.selection_mode = self.config.get("strategy_selection_mode", "dynamic")
        self.evaluation_window_days = self.config.get("strategy_evaluation_window", 7)
        
    def select_best_strategy(
        self,
        symbol: str,
        candidates: List[Dict[str, Any]],
        current_strategy_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        为指定品种选择最优策略
        
        Parameters
        ----------
        symbol : str
            品种代码
        candidates : List[Dict[str, Any]]
            候选策略列表
        current_strategy_id : Optional[str]
            当前策略ID
        
        Returns
        -------
        Optional[Dict[str, Any]]
            最优策略，如果没有则返回None
        """
        if not candidates:
            logger.warning(f"品种 {symbol} 没有候选策略")
            return None
        
        # 过滤有效候选
        valid_candidates = [
            c for c in candidates
            if c.get("status") in ["DEPLOYABLE", "RUNNING", "VALIDATED"]
        ]
        
        if not valid_candidates:
            logger.warning(f"品种 {symbol} 没有有效候选策略")
            return None
        
        # 计算综合评分
        for candidate in valid_candidates:
            candidate["composite_score"] = self._calculate_composite_score(candidate)
        
        # 按评分排序
        valid_candidates.sort(
            key=lambda x: x["composite_score"],
            reverse=True
        )
        
        # 动态选择模式：考虑当前策略表现
        if self.selection_mode == "dynamic" and current_strategy_id:
            current_strategy = next(
                (c for c in valid_candidates if c["id"] == current_strategy_id),
                None
            )
            
            if current_strategy:
                # 检查当前策略是否需要切换
                if self._should_switch_strategy(current_strategy, valid_candidates[0]):
                    logger.info(f"品种 {symbol} 切换策略: {current_strategy_id} -> {valid_candidates[0]['id']}")
                    return valid_candidates[0]
                else:
                    logger.info(f"品种 {symbol} 保持当前策略: {current_strategy_id}")
                    return current_strategy
        
        # 静态选择模式：直接返回最优
        return valid_candidates[0]
    
    def _calculate_composite_score(self, candidate: Dict[str, Any]) -> float:
        """
        计算综合评分
        
        Parameters
        ----------
        candidate : Dict[str, Any]
            候选策略
        
        Returns
        -------
        float
            综合评分
        """
        # IC评分
        ic_mean_4h = candidate.get("ic_mean_4h", 0) or 0
        ic_mean_24h = candidate.get("ic_mean_24h", 0) or 0
        ic_mean_168h = candidate.get("ic_mean_168h", 0) or 0
        
        ic_score = ic_mean_4h * 0.5 + ic_mean_24h * 0.3 + ic_mean_168h * 0.2
        
        # 回测绩效评分
        sharpe = candidate.get("sharpe_train", 0) or 0
        calmar = candidate.get("calmar", 0) or 0
        max_drawdown = candidate.get("max_drawdown", 0) or 0
        win_rate = candidate.get("win_rate", 0) or 0
        total_trades = candidate.get("total_trades", 0) or 0
        
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
    
    def _should_switch_strategy(
        self,
        current_strategy: Dict[str, Any],
        best_strategy: Dict[str, Any]
    ) -> bool:
        """
        判断是否应该切换策略
        
        Parameters
        ----------
        current_strategy : Dict[str, Any]
            当前策略
        best_strategy : Dict[str, Any]
            最优策略
        
        Returns
        -------
        bool
            是否应该切换
        """
        # 如果是同一个策略，不需要切换
        if current_strategy["id"] == best_strategy["id"]:
            return False
        
        # 计算评分差异
        score_diff = best_strategy["composite_score"] - current_strategy["composite_score"]
        
        # 如果差异大于阈值，建议切换
        threshold = 0.1  # 评分差异阈值
        if score_diff > threshold:
            return True
        
        return False
    
    def select_strategies_for_symbols(
        self,
        symbol_candidates: Dict[str, List[Dict[str, Any]]],
        current_strategies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        为多个品种选择策略
        
        Parameters
        ----------
        symbol_candidates : Dict[str, List[Dict[str, Any]]]
            品种到候选策略列表的映射
        current_strategies : Optional[Dict[str, str]]
            当前品种到策略ID的映射
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            品种到最优策略的映射
        """
        if current_strategies is None:
            current_strategies = {}
        
        selected = {}
        
        for symbol, candidates in symbol_candidates.items():
            current_strategy_id = current_strategies.get(symbol)
            best_strategy = self.select_best_strategy(symbol, candidates, current_strategy_id)
            
            if best_strategy:
                selected[symbol] = best_strategy
        
        return selected
