"""
精细化资金管理系统 - Kelly公式、风险平价、组合优化
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class CapitalManager:
    """资金管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化资金管理器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.allocation_method = self.config.get("allocation_method", "kelly")  # kelly/risk_parity/markowitz
        self.max_leverage = self.config.get("max_leverage", 1.0)
        self.min_position_size = self.config.get("min_position_size", 0.01)
        
    def calculate_kelly_fraction(
        self,
        expected_return: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        计算Kelly公式仓位
        
        Parameters
        ----------
        expected_return : float
            期望收益率
        win_rate : float
            胜率
        avg_win : float
            平均盈利
        avg_loss : float
            平均亏损
        
        Returns
        -------
        float
            Kelly仓位比例
        """
        if avg_loss == 0:
            return 0.0
        
        # Kelly公式: f = (bp - q) / b
        # b = avg_win / avg_loss (盈亏比)
        # p = win_rate (胜率)
        # q = 1 - p (败率)
        
        b = avg_win / abs(avg_loss)
        p = win_rate
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # 限制在合理范围内
        kelly_fraction = max(0, min(kelly_fraction, self.max_leverage))
        
        # 使用半Kelly（更保守）
        kelly_fraction = kelly_fraction * 0.5
        
        return kelly_fraction
    
    def calculate_risk_parity_weights(
        self,
        returns_matrix: np.ndarray
    ) -> np.ndarray:
        """
        计算风险平价权重
        
        Parameters
        ----------
        returns_matrix : np.ndarray
            收益率矩阵 (n_samples, n_assets)
        
        Returns
        -------
        np.ndarray
            权重向量
        """
        # 计算协方差矩阵
        cov_matrix = np.cov(returns_matrix.T)
        
        # 简化版：使用对角线（方差）的倒数作为权重
        variances = np.diag(cov_matrix)
        inv_variances = 1.0 / (variances + 1e-8)
        weights = inv_variances / inv_variances.sum()
        
        return weights
    
    def calculate_markowitz_weights(
        self,
        returns_matrix: np.ndarray,
        target_return: Optional[float] = None
    ) -> np.ndarray:
        """
        计算马科维茨最优权重
        
        Parameters
        ----------
        returns_matrix : np.ndarray
            收益率矩阵 (n_samples, n_assets)
        target_return : Optional[float]
            目标收益率
        
        Returns
        -------
        np.ndarray
            权重向量
        """
        n_assets = returns_matrix.shape[1]
        
        # 计算期望收益和协方差矩阵
        mean_returns = np.mean(returns_matrix, axis=0)
        cov_matrix = np.cov(returns_matrix.T)
        
        # 目标函数：最小化方差
        def objective(weights):
            return np.sqrt(weights @ cov_matrix @ weights)
        
        # 约束条件
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}  # 权重和为1
        ]
        
        if target_return is not None:
            constraints.append({
                "type": "eq",
                "fun": lambda w: w @ mean_returns - target_return
            })
        
        # 边界条件
        bounds = [(0, 1) for _ in range(n_assets)]
        
        # 初始猜测：等权重
        initial_weights = np.ones(n_assets) / n_assets
        
        # 优化
        result = minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return result.x
        else:
            logger.warning("马科维茨优化失败，使用等权重")
            return initial_weights
    
    def calculate_position_size(
        self,
        account_balance: float,
        strategy_performance: Dict[str, Any],
        current_positions: Dict[str, float],
        symbol: str
    ) -> float:
        """
        计算仓位大小
        
        Parameters
        ----------
        account_balance : float
            账户余额
        strategy_performance : Dict[str, Any]
            策略绩效
        current_positions : Dict[str, float]
            当前持仓
        symbol : str
            品种代码
        
        Returns
        -------
        float
            仓位大小（保证金占比）
        """
        if self.allocation_method == "kelly":
            # 使用Kelly公式
            expected_return = strategy_performance.get("total_return", 0) or 0
            win_rate = strategy_performance.get("win_rate", 0.5) or 0.5
            avg_win = strategy_performance.get("avg_win", 0.01) or 0.01
            avg_loss = strategy_performance.get("avg_loss", -0.01) or -0.01
            
            kelly_fraction = self.calculate_kelly_fraction(
                expected_return, win_rate, avg_win, avg_loss
            )
            
            # 考虑当前持仓
            current_total = sum(current_positions.values())
            available = 1.0 - current_total
            
            position_size = min(kelly_fraction, available)
            
        elif self.allocation_method == "risk_parity":
            # 风险平价：均匀分配
            n_positions = len(current_positions) + 1
            position_size = 1.0 / n_positions
            
        else:
            # 默认：等权重
            n_positions = len(current_positions) + 1
            position_size = 1.0 / n_positions
        
        # 应用最小仓位限制
        position_size = max(self.min_position_size, position_size)
        
        return position_size
    
    def calculate_portfolio_allocation(
        self,
        strategies: List[Dict[str, Any]],
        returns_matrix: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        计算组合配置
        
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
        
        if self.allocation_method == "risk_parity" and returns_matrix is not None:
            weights = self.calculate_risk_parity_weights(returns_matrix)
        elif self.allocation_method == "markowitz" and returns_matrix is not None:
            weights = self.calculate_markowitz_weights(returns_matrix)
        else:
            # 默认等权重
            weights = np.ones(n) / n
        
        return {s["id"]: float(w) for s, w in zip(strategies, weights)}
    
    def calculate_portfolio_metrics(
        self,
        weights: Dict[str, float],
        returns_matrix: np.ndarray
    ) -> Dict[str, float]:
        """
        计算组合指标
        
        Parameters
        ----------
        weights : Dict[str, float]
            权重字典
        returns_matrix : np.ndarray
            收益率矩阵
        
        Returns
        -------
        Dict[str, float]
            组合指标
        """
        weight_vector = np.array(list(weights.values()))
        
        # 组合收益
        portfolio_returns = returns_matrix @ weight_vector
        
        # 年化收益率
        annual_return = np.mean(portfolio_returns) * 252
        
        # 年化波动率
        annual_volatility = np.std(portfolio_returns) * np.sqrt(252)
        
        # 夏普比率（假设无风险利率为0）
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        # 最大回撤
        cumulative = np.cumprod(1 + portfolio_returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        return {
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown
        }
