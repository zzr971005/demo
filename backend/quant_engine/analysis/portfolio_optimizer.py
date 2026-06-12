"""
多策略组合优化 - 风险平价、马科维茨优化、ensemble方法
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """组合优化器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化优化器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.optimization_method = self.config.get("optimization_method", "risk_parity")
        self.max_weight = self.config.get("max_weight", 0.6)
        self.min_weight = self.config.get("min_weight", 0.05)
    
    def optimize_risk_parity(
        self,
        returns_matrix: np.ndarray
    ) -> np.ndarray:
        """
        风险平价优化
        
        Parameters
        ----------
        returns_matrix : np.ndarray
            收益率矩阵 (n_samples, n_assets)
        
        Returns
        -------
        np.ndarray
            优化权重
        """
        n_assets = returns_matrix.shape[1]
        
        # 计算协方差矩阵
        cov_matrix = np.cov(returns_matrix.T)
        
        # 目标函数：最小化风险贡献差异
        def objective(weights):
            portfolio_variance = weights @ cov_matrix @ weights
            marginal_risk = cov_matrix @ weights
            risk_contributions = weights * marginal_risk
            risk_contributions = risk_contributions / np.sum(risk_contributions)
            
            # 最小化风险贡献的方差
            return np.sum((risk_contributions - 1/n_assets) ** 2)
        
        # 约束条件
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        ]
        
        # 边界条件
        bounds = [(self.min_weight, self.max_weight) for _ in range(n_assets)]
        
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
            logger.warning("风险平价优化失败，使用等权重")
            return initial_weights
    
    def optimize_markowitz(
        self,
        returns_matrix: np.ndarray,
        target_return: Optional[float] = None
    ) -> np.ndarray:
        """
        马科维茨优化
        
        Parameters
        ----------
        returns_matrix : np.ndarray
            收益率矩阵 (n_samples, n_assets)
        target_return : Optional[float]
            目标收益率
        
        Returns
        -------
        np.ndarray
            优化权重
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
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        ]
        
        if target_return is not None:
            constraints.append({
                "type": "eq",
                "fun": lambda w: w @ mean_returns - target_return
            })
        
        # 边界条件
        bounds = [(self.min_weight, self.max_weight) for _ in range(n_assets)]
        
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
    
    def optimize_sharpe_ratio(
        self,
        returns_matrix: np.ndarray,
        risk_free_rate: float = 0.0
    ) -> np.ndarray:
        """
        最大夏普比率优化
        
        Parameters
        ----------
        returns_matrix : np.ndarray
            收益率矩阵 (n_samples, n_assets)
        risk_free_rate : float
            无风险利率
        
        Returns
        -------
        np.ndarray
            优化权重
        """
        n_assets = returns_matrix.shape[1]
        
        # 计算期望收益和协方差矩阵
        mean_returns = np.mean(returns_matrix, axis=0)
        cov_matrix = np.cov(returns_matrix.T)
        
        # 目标函数：最大化夏普比率（最小化负夏普比率）
        def objective(weights):
            portfolio_return = weights @ mean_returns
            portfolio_variance = weights @ cov_matrix @ weights
            portfolio_std = np.sqrt(portfolio_variance)
            sharpe = (portfolio_return - risk_free_rate) / portfolio_std if portfolio_std > 0 else 0
            return -sharpe
        
        # 约束条件
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        ]
        
        # 边界条件
        bounds = [(self.min_weight, self.max_weight) for _ in range(n_assets)]
        
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
            logger.warning("夏普比率优化失败，使用等权重")
            return initial_weights
    
    def optimize_hrp(self, returns_matrix: np.ndarray) -> np.ndarray:
        """层次风险平价（HRP, López de Prado 2016）。

        步骤：相关→距离 d=sqrt((1-corr)/2) → 层次聚类 → 拟对角化 →
        递归二分按逆方差分配权重。对相关结构稳健，无需矩阵求逆。
        """
        n_assets = returns_matrix.shape[1]
        if n_assets == 1:
            return np.ones(1)

        cov = np.cov(returns_matrix.T)
        std = np.sqrt(np.diag(cov))
        with np.errstate(divide="ignore", invalid="ignore"):
            corr = cov / np.outer(std, std)
        corr = np.nan_to_num(corr, nan=0.0)
        np.fill_diagonal(corr, 1.0)

        # 1) 距离矩阵 + 层次聚类
        try:
            from scipy.cluster.hierarchy import leaves_list, linkage
            from scipy.spatial.distance import squareform

            dist = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, 1.0))
            np.fill_diagonal(dist, 0.0)
            condensed = squareform(dist, checks=False)
            link = linkage(condensed, method="single")
            sort_ix = list(leaves_list(link))
        except Exception as e:  # noqa: BLE001
            logger.warning("HRP 聚类失败，退回逆方差: %s", e)
            sort_ix = list(np.argsort(std))

        # 2) 递归二分
        def _ivp(sub_cov: np.ndarray) -> np.ndarray:
            ivp = 1.0 / np.diag(sub_cov)
            return ivp / ivp.sum()

        def _cluster_var(items: List[int]) -> float:
            sub = cov[np.ix_(items, items)]
            w = _ivp(sub)
            return float(w @ sub @ w)

        weights = np.ones(n_assets)
        clusters = [sort_ix]
        while clusters:
            new_clusters: List[List[int]] = []
            for cl in clusters:
                if len(cl) <= 1:
                    continue
                half = len(cl) // 2
                left, right = cl[:half], cl[half:]
                var_l, var_r = _cluster_var(left), _cluster_var(right)
                alpha = 1.0 - var_l / (var_l + var_r + 1e-12)
                for i in left:
                    weights[i] *= alpha
                for i in right:
                    weights[i] *= 1.0 - alpha
                new_clusters.extend([left, right])
            clusters = new_clusters

        total = weights.sum()
        return weights / total if total > 0 else np.ones(n_assets) / n_assets

    def optimize_portfolio(
        self,
        strategies: List[Dict[str, Any]],
        returns_matrix: Optional[np.ndarray] = None,
        target_return: Optional[float] = None
    ) -> Dict[str, float]:
        """
        组合优化
        
        Parameters
        ----------
        strategies : List[Dict[str, Any]]
            策略列表
        returns_matrix : Optional[np.ndarray]
            收益率矩阵
        target_return : Optional[float]
            目标收益率
        
        Returns
        -------
        Dict[str, float]
            策略权重字典
        """
        if not strategies:
            return {}
        
        n = len(strategies)
        
        if returns_matrix is None:
            # 如果没有收益率矩阵，使用等权重
            weights = np.ones(n) / n
        elif self.optimization_method == "risk_parity":
            weights = self.optimize_risk_parity(returns_matrix)
        elif self.optimization_method == "markowitz":
            weights = self.optimize_markowitz(returns_matrix, target_return)
        elif self.optimization_method == "sharpe":
            weights = self.optimize_sharpe_ratio(returns_matrix)
        elif self.optimization_method == "hrp":
            weights = self.optimize_hrp(returns_matrix)
        else:
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
        
        # 夏普比率
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        # 最大回撤
        cumulative = np.cumprod(1 + portfolio_returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # 风险贡献
        cov_matrix = np.cov(returns_matrix.T)
        marginal_risk = cov_matrix @ weight_vector
        risk_contributions = weight_vector * marginal_risk
        risk_contributions = risk_contributions / np.sum(risk_contributions)
        
        return {
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "risk_contributions": dict(zip(weights.keys(), risk_contributions))
        }


def ic_ir_weights(factors: List[Dict[str, Any]], key: str = "ic_ir") -> Dict[str, float]:
    """IC_IR 加权合成多因子最优组合。

    权重 ∝ max(IC_IR, 0)，归一化求和为 1（López de Prado / Grinold-Kahn 的
    信息比率加权思想）。全部非正时退回等权。

    Parameters
    ----------
    factors : list of dict
        每项含 ``id`` 与 IC_IR 字段（默认键 ``ic_ir``）。
    """
    if not factors:
        return {}
    raw = np.array([max(float(f.get(key) or 0.0), 0.0) for f in factors])
    total = raw.sum()
    if total <= 0:
        n = len(factors)
        return {f["id"]: 1.0 / n for f in factors}
    return {f["id"]: float(w / total) for f, w in zip(factors, raw)}
