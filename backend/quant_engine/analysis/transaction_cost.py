"""
交易成本分析 - 手续费、滑点、冲击成本、总成本
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class TransactionCostAnalyzer:
    """交易成本分析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.commission_rate = self.config.get("commission_rate", 0.0001)
        self.slippage_rate = self.config.get("slippage_rate", 0.0002)
    
    def calculate_commission(
        self,
        volume: float,
        price: float,
        commission_rate: Optional[float] = None
    ) -> float:
        """
        计算手续费
        
        Parameters
        ----------
        volume : float
            成交量
        price : float
            成交价格
        commission_rate : Optional[float]
            手续费率
        
        Returns
        -------
        float
            手续费
        """
        rate = commission_rate or self.commission_rate
        return volume * price * rate
    
    def calculate_slippage(
        self,
        expected_price: float,
        executed_price: float,
        volume: float,
        direction: str
    ) -> float:
        """
        计算滑点成本
        
        Parameters
        ----------
        expected_price : float
            预期价格
        executed_price : float
            执行价格
        volume : float
            成交量
        direction : str
            方向
        
        Returns
        -------
        float
            滑点成本
        """
        if direction == "BUY":
            slippage = (executed_price - expected_price) * volume
        else:
            slippage = (expected_price - executed_price) * volume
        
        return slippage
    
    def calculate_impact_cost(
        self,
        order_volume: float,
        avg_volume: float,
        volatility: float,
        price: float
    ) -> float:
        """
        计算冲击成本
        
        Parameters
        ----------
        order_volume : float
            订单量
        avg_volume : float
            平均成交量
        volatility : float
            波动率
        price : float
            价格
        
        Returns
        -------
        float
            冲击成本
        """
        participation_rate = order_volume / avg_volume if avg_volume > 0 else 0
        impact_ratio = participation_rate * volatility
        impact_cost = impact_ratio * price * order_volume
        
        return impact_cost
    
    def calculate_total_cost(
        self,
        order: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        计算总交易成本
        
        Parameters
        ----------
        order : Dict[str, Any]
            订单信息
        market_data : Dict[str, Any]
            市场数据
        
        Returns
        -------
        Dict[str, float]
            成本明细
        """
        volume = order.get("volume", 0)
        direction = order.get("direction", "BUY")
        expected_price = order.get("expected_price", market_data.get("last_price", 0))
        executed_price = order.get("executed_price", expected_price)
        price = executed_price
        
        # 手续费
        commission = self.calculate_commission(volume, price)
        
        # 滑点
        slippage = self.calculate_slippage(expected_price, executed_price, volume, direction)
        
        # 冲击成本
        avg_volume = market_data.get("avg_volume", volume)
        volatility = market_data.get("volatility", 0.01)
        impact = self.calculate_impact_cost(volume, avg_volume, volatility, price)
        
        # 总成本
        total_cost = commission + abs(slippage) + impact
        
        return {
            "commission": commission,
            "slippage": slippage,
            "impact_cost": impact,
            "total_cost": total_cost,
            "cost_ratio": total_cost / (volume * price) if volume * price > 0 else 0
        }
    
    def analyze_cost_series(
        self,
        orders: List[Dict[str, Any]],
        market_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析交易成本序列
        
        Parameters
        ----------
        orders : List[Dict[str, Any]]
            订单列表
        market_data_list : List[Dict[str, Any]]
            市场数据列表
        
        Returns
        -------
        Dict[str, Any]
            成本分析结果
        """
        costs = []
        for order, market_data in zip(orders, market_data_list):
            cost = self.calculate_total_cost(order, market_data)
            costs.append(cost)
        
        total_costs = [c["total_cost"] for c in costs]
        commissions = [c["commission"] for c in costs]
        slippages = [c["slippage"] for c in costs]
        impacts = [c["impact_cost"] for c in costs]
        
        return {
            "total_cost": sum(total_costs),
            "avg_cost": np.mean(total_costs),
            "total_commission": sum(commissions),
            "total_slippage": sum(slippages),
            "total_impact": sum(impacts),
            "cost_breakdown": {
                "commission_ratio": sum(commissions) / sum(total_costs) if sum(total_costs) > 0 else 0,
                "slippage_ratio": sum(abs(s) for s in slippages) / sum(total_costs) if sum(total_costs) > 0 else 0,
                "impact_ratio": sum(impacts) / sum(total_costs) if sum(total_costs) > 0 else 0
            },
            "order_count": len(orders)
        }
