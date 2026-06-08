"""
策略切换持仓管理器 - 支持渐进式切换和ensemble方法
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class StrategySwitchManager:
    """策略切换持仓管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化策略切换管理器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.allocation_mode = self.config.get("strategy_allocation_mode", "dynamic_weighted")
        self.allocation_method = self.config.get("allocation_method", "risk_parity")
        self.weight_update_frequency = self.config.get("weight_update_frequency", "daily")
        self.min_weight_threshold = self.config.get("min_weight_threshold", 0.05)
        self.max_weight_threshold = self.config.get("max_weight_threshold", 0.6)
        self.ensemble_enabled = self.config.get("ensemble_enabled", True)
        self.ensemble_method = self.config.get("ensemble_method", "gradient_based")
        
        self.switch_cooldown_enabled = self.config.get("switch_cooldown_enabled", True)
        self.switch_cooldown_hours = self.config.get("switch_cooldown_hours", 6)
        self.switch_mode = self.config.get("switch_mode", "gradual")
        self.max_daily_weight_change = self.config.get("max_daily_weight_change", 0.3)
        self.volatility_based_adjustment = self.config.get("volatility_based_adjustment", True)
        
        # 记录最后切换时间
        self.last_switch_time: Dict[str, datetime] = {}
        # 记录当前权重
        self.current_weights: Dict[str, Dict[str, float]] = {}  # symbol -> strategy_id -> weight
    
    def calculate_risk_parity_weights(
        self,
        strategies: List[Dict[str, Any]],
        returns_matrix: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        计算风险平价权重
        
        Parameters
        ----------
        strategies : List[Dict[str, Any]]
            策略列表
        returns_matrix : Optional[np.ndarray]
            收益率矩阵
        
        Returns
        -------
        Dict[str, float]
            策略权重字典
        """
        if not strategies:
            return {}
        
        n = len(strategies)
        
        # 如果没有收益率矩阵，使用夏普比率作为代理
        if returns_matrix is None:
            sharpe_ratios = np.array([s.get("sharpe_train", 1.0) or 1.0 for s in strategies])
            # 归一化
            weights = sharpe_ratios / sharpe_ratios.sum()
        else:
            # 计算协方差矩阵
            cov_matrix = np.cov(returns_matrix.T)
            
            # 简化版：使用对角线（方差）的倒数作为权重
            variances = np.diag(cov_matrix)
            inv_variances = 1.0 / variances
            weights = inv_variances / inv_variances.sum()
        
        # 应用权重限制
        weights = np.clip(weights, self.min_weight_threshold, self.max_weight_threshold)
        weights = weights / weights.sum()
        
        return {s["id"]: float(w) for s, w in zip(strategies, weights)}
    
    def calculate_gradient_based_weights(
        self,
        strategies: List[Dict[str, Any]],
        current_weights: Dict[str, float],
        learning_rate: float = 0.1
    ) -> Dict[str, float]:
        """
        基于梯度的权重更新（ensemble方法）
        
        Parameters
        ----------
        strategies : List[Dict[str, Any]]
            策略列表
        current_weights : Dict[str, float]
            当前权重
        learning_rate : float
            学习率
        
        Returns
        -------
        Dict[str, float]
            更新后的权重
        """
        if not strategies:
            return {}
        
        # 计算每个策略的"梯度"（基于近期表现）
        gradients = {}
        for strategy in strategies:
            strategy_id = strategy["id"]
            # 使用夏普比率作为梯度代理
            sharpe = strategy.get("sharpe_train", 0) or 0
            gradients[strategy_id] = sharpe
        
        # 归一化梯度
        grad_values = np.array(list(gradients.values()))
        grad_values = (grad_values - grad_values.mean()) / (grad_values.std() + 1e-8)
        
        # 更新权重
        new_weights = {}
        for strategy, grad in zip(strategies, grad_values):
            strategy_id = strategy["id"]
            current_weight = current_weights.get(strategy_id, 1.0 / len(strategies))
            new_weight = current_weight + learning_rate * grad
            new_weights[strategy_id] = max(0, new_weight)
        
        # 归一化
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}
        
        # 应用权重限制
        new_weights = {
            k: max(self.min_weight_threshold, min(self.max_weight_threshold, v))
            for k, v in new_weights.items()
        }
        
        # 再次归一化
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}
        
        return new_weights
    
    def check_switch_cooldown(self, symbol: str) -> bool:
        """
        检查切换冷却期
        
        Parameters
        ----------
        symbol : str
            品种代码
        
        Returns
        -------
        bool
            是否可以切换
        """
        if not self.switch_cooldown_enabled:
            return True
        
        last_switch = self.last_switch_time.get(symbol)
        if last_switch is None:
            return True
        
        cooldown_end = last_switch + timedelta(hours=self.switch_cooldown_hours)
        return datetime.utcnow() >= cooldown_end
    
    def calculate_gradual_switch(
        self,
        symbol: str,
        old_strategy_id: str,
        new_strategy_id: str,
        current_weight: float,
        target_weight: float
    ) -> float:
        """
        计算渐进式切换权重
        
        Parameters
        ----------
        symbol : str
            品种代码
        old_strategy_id : str
            旧策略ID
        new_strategy_id : str
            新策略ID
        current_weight : float
            当前权重
        target_weight : float
            目标权重
        
        Returns
        -------
        float
            新权重
        """
        # 检查每日最大权重变化
        max_change = self.max_daily_weight_change
        
        if self.volatility_based_adjustment:
            # 基于波动率调整变化速度 - 暂未实现，需要波动率数据支持
            logger.debug("波动率调整功能暂未启用")
        
        # 计算权重变化
        weight_change = target_weight - current_weight
        
        # 限制变化幅度
        if abs(weight_change) > max_change:
            weight_change = max_change if weight_change > 0 else -max_change
        
        new_weight = current_weight + weight_change
        return max(0, min(1, new_weight))
    
    def switch_strategy(
        self,
        symbol: str,
        old_strategy_id: Optional[str],
        new_strategy_id: str,
        reason: str,
        position_before: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        切换策略
        
        Parameters
        ----------
        symbol : str
            品种代码
        old_strategy_id : Optional[str]
            旧策略ID
        new_strategy_id : str
            新策略ID
        reason : str
            切换原因
        position_before : Optional[Dict[str, Any]]
            切换前持仓
        
        Returns
        -------
        Dict[str, Any]
            切换结果
        """
        # 检查冷却期
        if not self.check_switch_cooldown(symbol):
            return {
                "success": False,
                "message": f"品种 {symbol} 在冷却期内，无法切换"
            }
        
        # 记录切换时间
        self.last_switch_time[symbol] = datetime.utcnow()
        
        # 计算权重
        if symbol not in self.current_weights:
            self.current_weights[symbol] = {}
        
        if old_strategy_id:
            # 渐进式切换
            old_weight = self.current_weights[symbol].get(old_strategy_id, 1.0)
            new_weight = self.calculate_gradual_switch(
                symbol, old_strategy_id, new_strategy_id, old_weight, 0.0
            )
            self.current_weights[symbol][old_strategy_id] = new_weight
            self.current_weights[symbol][new_strategy_id] = 1.0 - new_weight
        else:
            # 直接切换
            self.current_weights[symbol] = {new_strategy_id: 1.0}
        
        logger.info(
            f"策略切换: {symbol} {old_strategy_id} -> {new_strategy_id}, "
            f"原因: {reason}, 模式: {self.switch_mode}"
        )
        
        return {
            "success": True,
            "symbol": symbol,
            "old_strategy_id": old_strategy_id,
            "new_strategy_id": new_strategy_id,
            "reason": reason,
            "switch_mode": self.switch_mode,
            "weights": self.current_weights[symbol],
            "switched_at": datetime.utcnow()
        }
    
    def get_strategy_weights(self, symbol: str) -> Dict[str, float]:
        """
        获取品种的策略权重
        
        Parameters
        ----------
        symbol : str
            品种代码
        
        Returns
        -------
        Dict[str, float]
            策略权重字典
        """
        return self.current_weights.get(symbol, {})
    
    def update_weights_daily(
        self,
        symbol: str,
        strategies: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        每日更新权重
        
        Parameters
        ----------
        symbol : str
            品种代码
        strategies : List[Dict[str, Any]]
            策略列表
        
        Returns
        -------
        Dict[str, float]
            更新后的权重
        """
        if self.allocation_method == "risk_parity":
            new_weights = self.calculate_risk_parity_weights(strategies)
        elif self.ensemble_enabled and self.ensemble_method == "gradient_based":
            current_weights = self.current_weights.get(symbol, {})
            new_weights = self.calculate_gradient_based_weights(strategies, current_weights)
        else:
            # 默认均等权重
            n = len(strategies)
            new_weights = {s["id"]: 1.0 / n for s in strategies}
        
        self.current_weights[symbol] = new_weights
        logger.info(f"品种 {symbol} 权重更新: {new_weights}")
        
        return new_weights
