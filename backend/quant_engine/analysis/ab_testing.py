"""
策略A/B测试框架 - 对比两个策略的表现
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from scipy import stats
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ABTestFramework:
    """A/B测试框架"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化框架
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.significance_level = self.config.get("significance_level", 0.05)
        self.min_sample_size = self.config.get("min_sample_size", 30)
    
    def create_test(
        self,
        strategy_a_id: str,
        strategy_b_id: str,
        test_duration_days: int = 30
    ) -> Dict[str, Any]:
        """
        创建A/B测试
        
        Parameters
        ----------
        strategy_a_id : str
            策略A ID
        strategy_b_id : str
            策略B ID
        test_duration_days : int
            测试天数
        
        Returns
        -------
        Dict[str, Any]
            测试信息
        """
        test_id = str(uuid.uuid4())
        
        test = {
            "test_id": test_id,
            "test_name": f"AB Test {strategy_a_id} vs {strategy_b_id}",
            "group_a": strategy_a_id,
            "group_b": strategy_b_id,
            "status": "RUNNING",
            "started_at": datetime.utcnow(),
            "test_duration_days": test_duration_days,
            "metrics": {},
            "result": None
        }
        
        logger.info(f"创建A/B测试: {test_id}")
        return test
    
    def collect_metrics(
        self,
        test_id: str,
        returns_a: np.ndarray,
        returns_b: np.ndarray
    ) -> Dict[str, Any]:
        """
        收集指标
        
        Parameters
        ----------
        test_id : str
            测试ID
        returns_a : np.ndarray
            策略A收益率
        returns_b : np.ndarray
            策略B收益率
        
        Returns
        -------
        Dict[str, Any]
            指标数据
        """
        # 计算基本指标
        metrics_a = self._calculate_metrics(returns_a)
        metrics_b = self._calculate_metrics(returns_b)
        
        # 统计检验
        if len(returns_a) >= self.min_sample_size and len(returns_b) >= self.min_sample_size:
            t_stat, p_value = stats.ttest_ind(returns_a, returns_b)
            
            # 判断显著性
            is_significant = p_value < self.significance_level
            
            # 确定胜者
            if is_significant:
                winner = "A" if np.mean(returns_a) > np.mean(returns_b) else "B"
            else:
                winner = "TIE"
        else:
            t_stat = 0
            p_value = 1.0
            is_significant = False
            winner = "TIE"
        
        return {
            "test_id": test_id,
            "metrics_a": metrics_a,
            "metrics_b": metrics_b,
            "statistical_test": {
                "t_statistic": t_stat,
                "p_value": p_value,
                "is_significant": is_significant,
                "significance_level": self.significance_level
            },
            "result": winner,
            "sample_sizes": {
                "group_a": len(returns_a),
                "group_b": len(returns_b)
            }
        }
    
    def _calculate_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """计算指标"""
        if len(returns) == 0:
            return {}
        
        annual_return = np.mean(returns) * 252
        annual_volatility = np.std(returns) * np.sqrt(252)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        return {
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": np.sum(returns > 0) / len(returns)
        }
    
    def finalize_test(
        self,
        test_id: str,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        完成测试
        
        Parameters
        ----------
        test_id : str
            测试ID
        metrics : Dict[str, Any]
            指标数据
        
        Returns
        -------
        Dict[str, Any]
            最终结果
        """
        result = metrics.get("result", "TIE")
        
        final_report = {
            "test_id": test_id,
            "status": "COMPLETED",
            "finished_at": datetime.utcnow(),
            "result": result,
            "metrics": metrics,
            "recommendation": self._generate_recommendation(result, metrics)
        }
        
        logger.info(f"A/B测试完成: {test_id}, 结果: {result}")
        return final_report
    
    def _generate_recommendation(
        self,
        result: str,
        metrics: Dict[str, Any]
    ) -> str:
        """生成建议"""
        if result == "A":
            return "策略A表现显著优于策略B，建议采用策略A"
        elif result == "B":
            return "策略B表现显著优于策略A，建议采用策略B"
        else:
            return "两个策略表现无显著差异，可继续观察或选择其他指标"
