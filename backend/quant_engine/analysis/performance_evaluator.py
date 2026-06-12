"""
策略绩效评估器 - 评估策略绩效，支持模拟和实盘对比
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceEvaluator:
    """绩效评估器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化评估器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.evaluation_criteria = self.config.get("evaluation_criteria", {
            "min_sharpe": 1.0,
            "min_return": 0.1,
            "max_drawdown": 0.2,
            "min_win_rate": 0.4
        })
    
    def evaluate_strategy(
        self,
        returns: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        评估策略绩效
        
        Parameters
        ----------
        returns : np.ndarray
            策略收益率
        benchmark_returns : Optional[np.ndarray]
            基准收益率
        
        Returns
        -------
        Dict[str, Any]
            评估结果
        """
        if len(returns) == 0:
            return {"error": "无数据"}
        
        # 基本指标
        metrics = self._calculate_metrics(returns)
        
        # 相对指标（如果有基准）
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            relative_metrics = self._calculate_relative_metrics(returns, benchmark_returns)
            metrics.update(relative_metrics)
        
        # 评估结果
        evaluation = self._evaluate_performance(metrics)
        
        return {
            "metrics": metrics,
            "evaluation": evaluation,
            "evaluated_at": datetime.utcnow()
        }
    
    def _calculate_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """计算基本指标"""
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
        
        # 卡玛比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 胜率
        win_rate = np.sum(returns > 0) / len(returns)
        
        # 盈亏比
        winning_returns = returns[returns > 0]
        losing_returns = returns[returns < 0]
        avg_win = np.mean(winning_returns) if len(winning_returns) > 0 else 0
        avg_loss = np.mean(losing_returns) if len(losing_returns) > 0 else 0
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        return {
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar_ratio,
            "win_rate": win_rate,
            "profit_loss_ratio": profit_loss_ratio,
            "total_trades": len(returns)
        }
    
    def _calculate_relative_metrics(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> Dict[str, float]:
        """计算相对指标"""
        # 超额收益
        excess_returns = returns - benchmark_returns
        excess_return = np.mean(excess_returns) * 252
        
        # 信息比率
        excess_volatility = np.std(excess_returns) * np.sqrt(252)
        information_ratio = excess_return / excess_volatility if excess_volatility > 0 else 0
        
        # Beta
        covariance = np.cov(returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
        
        # Alpha
        benchmark_return = np.mean(benchmark_returns) * 252
        alpha = excess_return - beta * benchmark_return
        
        return {
            "excess_return": excess_return,
            "information_ratio": information_ratio,
            "beta": beta,
            "alpha": alpha
        }
    
    def _evaluate_performance(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """评估绩效"""
        sharpe = metrics.get("sharpe_ratio", 0)
        return_rate = metrics.get("annual_return", 0)
        max_dd = metrics.get("max_drawdown", 0)
        win_rate = metrics.get("win_rate", 0)
        
        # 检查各项指标
        sharpe_ok = sharpe >= self.evaluation_criteria["min_sharpe"]
        return_ok = return_rate >= self.evaluation_criteria["min_return"]
        drawdown_ok = max_dd <= self.evaluation_criteria["max_drawdown"]
        win_rate_ok = win_rate >= self.evaluation_criteria["min_win_rate"]
        
        # 综合评分
        score = 0
        if sharpe_ok:
            score += 30
        if return_ok:
            score += 25
        if drawdown_ok:
            score += 25
        if win_rate_ok:
            score += 20
        
        # 评级
        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        else:
            grade = "D"
        
        return {
            "score": score,
            "grade": grade,
            "criteria_met": {
                "sharpe": sharpe_ok,
                "return": return_ok,
                "drawdown": drawdown_ok,
                "win_rate": win_rate_ok
            },
            "recommendation": "PROMOTE" if grade in ["A", "B"] else "HOLD"
        }
    
    def compare_strategies(
        self,
        strategies: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """
        对比多个策略
        
        Parameters
        ----------
        strategies : Dict[str, np.ndarray]
            策略收益率字典
        
        Returns
        -------
        Dict[str, Any]
            对比结果
        """
        results = {}
        
        for strategy_id, returns in strategies.items():
            evaluation = self.evaluate_strategy(returns)
            results[strategy_id] = evaluation
        
        # 排序
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1]["evaluation"]["score"],
            reverse=True
        )
        
        return {
            "rankings": [
                {"strategy_id": sid, "score": eval["evaluation"]["score"], "grade": eval["evaluation"]["grade"]}
                for sid, eval in sorted_results
            ],
            "best_strategy": sorted_results[0][0] if sorted_results else None,
            "evaluated_at": datetime.utcnow()
        }
