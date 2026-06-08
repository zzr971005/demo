"""
回测vs实盘差异分析 - 识别过拟合、市场环境变化
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class BacktestLiveComparator:
    """回测实盘对比器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化对比器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.performance_thresholds = self.config.get("performance_thresholds", {
            "sharpe_diff": 0.5,
            "return_diff": 0.1,
            "drawdown_diff": 0.05
        })
    
    def calculate_performance_metrics(
        self,
        returns: np.ndarray
    ) -> Dict[str, float]:
        """
        计算绩效指标
        
        Parameters
        ----------
        returns : np.ndarray
            收益率序列
        
        Returns
        -------
        Dict[str, float]
            绩效指标
        """
        if len(returns) == 0:
            return {}
        
        # 年化收益率
        annual_return = np.mean(returns) * 252
        
        # 年化波动率
        annual_volatility = np.std(returns) * np.sqrt(252)
        
        # 夏普比率
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        # 最大回撤
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # 胜率
        win_rate = np.sum(returns > 0) / len(returns)
        
        return {
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate
        }
    
    def compare_performance(
        self,
        backtest_returns: np.ndarray,
        live_returns: np.ndarray
    ) -> Dict[str, Any]:
        """
        对比回测和实盘绩效
        
        Parameters
        ----------
        backtest_returns : np.ndarray
            回测收益率
        live_returns : np.ndarray
            实盘收益率
        
        Returns
        -------
        Dict[str, Any]
            对比结果
        """
        backtest_metrics = self.calculate_performance_metrics(backtest_returns)
        live_metrics = self.calculate_performance_metrics(live_returns)
        
        # 计算差异
        sharpe_diff = backtest_metrics.get("sharpe_ratio", 0) - live_metrics.get("sharpe_ratio", 0)
        return_diff = backtest_metrics.get("annual_return", 0) - live_metrics.get("annual_return", 0)
        drawdown_diff = abs(backtest_metrics.get("max_drawdown", 0) - live_metrics.get("max_drawdown", 0))
        
        # 判断是否显著差异
        significant_sharpe = abs(sharpe_diff) > self.performance_thresholds["sharpe_diff"]
        significant_return = abs(return_diff) > self.performance_thresholds["return_diff"]
        significant_drawdown = drawdown_diff > self.performance_thresholds["drawdown_diff"]
        
        # 过拟合检测
        overfitting_detected = significant_sharpe and sharpe_diff > 0
        
        return {
            "backtest_metrics": backtest_metrics,
            "live_metrics": live_metrics,
            "differences": {
                "sharpe_diff": sharpe_diff,
                "return_diff": return_diff,
                "drawdown_diff": drawdown_diff
            },
            "significant_differences": {
                "sharpe": significant_sharpe,
                "return": significant_return,
                "drawdown": significant_drawdown
            },
            "overfitting_detected": overfitting_detected,
            "regime_change_detected": significant_return and return_diff < 0
        }
    
    def calculate_pbo(
        self,
        returns_matrix: np.ndarray,
        n_splits: int = 10
    ) -> float:
        """
        计算回测过拟合概率 (PBO)
        
        Parameters
        ----------
        returns_matrix : np.ndarray
            收益率矩阵 (n_samples, n_strategies)
        n_splits : int
            分割数
        
        Returns
        -------
        float
            PBO值
        """
        n_samples = returns_matrix.shape[0]
        split_size = n_samples // n_splits
        
        # 简化实现：使用交叉验证
        sharpe_scores = []
        
        for i in range(n_splits):
            train_start = 0
            train_end = (i + 1) * split_size
            test_start = train_end
            test_end = min((i + 2) * split_size, n_samples)
            
            if test_end <= test_start:
                continue
            
            train_returns = returns_matrix[train_start:train_end]
            test_returns = returns_matrix[test_start:test_end]
            
            # 训练集夏普
            train_sharpe = np.mean(train_returns, axis=0) / (np.std(train_returns, axis=0) + 1e-8)
            # 测试集夏普
            test_sharpe = np.mean(test_returns, axis=0) / (np.std(test_returns, axis=0) + 1e-8)
            
            # 选择训练集最优策略
            best_train_idx = np.argmax(train_sharpe)
            best_test_sharpe = test_sharpe[best_train_idx]
            
            sharpe_scores.append(best_test_sharpe)
        
        if not sharpe_scores:
            return 0.0
        
        # PBO = (最优策略在测试集表现差于平均的概率)
        avg_sharpe = np.mean(sharpe_scores)
        pbo = np.mean([s < avg_sharpe for s in sharpe_scores])
        
        return pbo
    
    def detect_regime_change(
        self,
        returns: np.ndarray,
        window: int = 20
    ) -> Dict[str, Any]:
        """
        检测市场环境变化
        
        Parameters
        ----------
        returns : np.ndarray
            收益率序列
        window : int
            窗口大小
        
        Returns
        -------
        Dict[str, Any]
            检测结果
        """
        if len(returns) < window * 2:
            return {"regime_change_detected": False, "reason": "数据不足"}
        
        # 计算滚动统计量
        rolling_mean = np.convolve(returns, np.ones(window)/window, mode='valid')
        rolling_std = np.array([
            np.std(returns[i:i+window])
            for i in range(len(returns) - window)
        ])
        
        # 检测均值变化
        mean_change = abs(rolling_mean[-1] - rolling_mean[0])
        std_change = abs(rolling_std[-1] - rolling_std[0])
        
        # 简化检测：如果变化超过2倍标准差
        regime_change = mean_change > 2 * np.std(rolling_mean) or std_change > 2 * np.std(rolling_std)
        
        return {
            "regime_change_detected": regime_change,
            "mean_change": mean_change,
            "std_change": std_change,
            "current_mean": rolling_mean[-1],
            "current_std": rolling_std[-1]
        }
    
    def generate_comparison_report(
        self,
        strategy_id: str,
        backtest_returns: np.ndarray,
        live_returns: np.ndarray
    ) -> Dict[str, Any]:
        """
        生成对比报告
        
        Parameters
        ----------
        strategy_id : str
            策略ID
        backtest_returns : np.ndarray
            回测收益率
        live_returns : np.ndarray
            实盘收益率
        
        Returns
        -------
        Dict[str, Any]
            对比报告
        """
        # 绩效对比
        performance_comparison = self.compare_performance(backtest_returns, live_returns)
        
        # 过拟合检测
        returns_matrix = np.column_stack([backtest_returns, live_returns])
        pbo = self.calculate_pbo(returns_matrix)
        
        # 市场环境检测
        regime_change = self.detect_regime_change(live_returns)
        
        # 综合评估
        issues = []
        if performance_comparison["overfitting_detected"]:
            issues.append("检测到过拟合")
        if performance_comparison["regime_change_detected"]:
            issues.append("市场环境变化")
        if pbo > 0.5:
            issues.append(f"过拟合概率高 (PBO={pbo:.2f})")
        
        return {
            "strategy_id": strategy_id,
            "performance_comparison": performance_comparison,
            "pbo": pbo,
            "regime_change": regime_change,
            "issues": issues,
            "overall_health": len(issues) == 0,
            "report_date": datetime.utcnow()
        }
