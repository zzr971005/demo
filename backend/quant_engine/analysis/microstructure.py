"""
市场微观结构分析 - 订单流、流动性、滑点、冲击成本
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class MicrostructureAnalyzer:
    """市场微观结构分析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
    
    def calculate_bid_ask_spread(
        self,
        bid_price: float,
        ask_price: float
    ) -> float:
        """
        计算买卖价差
        
        Parameters
        ----------
        bid_price : float
            买价
        ask_price : float
            卖价
        
        Returns
        -------
        float
            价差
        """
        return ask_price - bid_price
    
    def calculate_relative_spread(
        self,
        bid_price: float,
        ask_price: float,
        mid_price: Optional[float] = None
    ) -> float:
        """
        计算相对价差
        
        Parameters
        ----------
        bid_price : float
            买价
        ask_price : float
            卖价
        mid_price : Optional[float]
            中间价
        
        Returns
        -------
        float
            相对价差
        """
        if mid_price is None:
            mid_price = (bid_price + ask_price) / 2
        
        spread = self.calculate_bid_ask_spread(bid_price, ask_price)
        return spread / mid_price if mid_price > 0 else 0
    
    def calculate_order_flow(
        self,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        计算订单流
        
        Parameters
        ----------
        trades : List[Dict[str, Any]]
            交易列表
        
        Returns
        -------
        Dict[str, float]
            订单流指标
        """
        if not trades:
            return {"buy_volume": 0, "sell_volume": 0, "net_flow": 0}
        
        buy_volume = sum(t.get("volume", 0) for t in trades if t.get("direction") == "BUY")
        sell_volume = sum(t.get("volume", 0) for t in trades if t.get("direction") == "SELL")
        net_flow = buy_volume - sell_volume
        
        return {
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "net_flow": net_flow,
            "buy_ratio": buy_volume / (buy_volume + sell_volume) if (buy_volume + sell_volume) > 0 else 0
        }
    
    def calculate_liquidity_score(
        self,
        bid_ask_spread: float,
        volume: float,
        volatility: float
    ) -> float:
        """
        计算流动性评分
        
        Parameters
        ----------
        bid_ask_spread : float
            买卖价差
        volume : float
            成交量
        volatility : float
            波动率
        
        Returns
        -------
        float
            流动性评分 (0-1)
        """
        # 价差越小，流动性越高
        spread_score = 1.0 / (1.0 + bid_ask_spread * 100)
        
        # 成交量越大，流动性越高
        volume_score = np.tanh(volume / 10000)
        
        # 波动率越低，流动性越高
        volatility_score = 1.0 / (1.0 + volatility * 10)
        
        # 综合评分
        liquidity_score = (spread_score * 0.4 + volume_score * 0.4 + volatility_score * 0.2)
        
        return liquidity_score
    
    def calculate_slippage(
        self,
        expected_price: float,
        executed_price: float,
        direction: str
    ) -> float:
        """
        计算滑点
        
        Parameters
        ----------
        expected_price : float
            预期价格
        executed_price : float
            执行价格
        direction : str
            方向
        
        Returns
        -------
        float
            滑点
        """
        if direction == "BUY":
            slippage = (executed_price - expected_price) / expected_price
        else:
            slippage = (expected_price - executed_price) / expected_price
        
        return slippage
    
    def calculate_impact_cost(
        self,
        order_volume: float,
        avg_volume: float,
        volatility: float
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
        
        Returns
        -------
        float
            冲击成本
        """
        # 简化模型：冲击成本与订单占比和波动率成正比
        participation_rate = order_volume / avg_volume if avg_volume > 0 else 0
        impact_cost = participation_rate * volatility
        
        return impact_cost
    
    def analyze_microstructure(
        self,
        market_data: Dict[str, Any],
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        综合分析市场微观结构
        
        Parameters
        ----------
        market_data : Dict[str, Any]
            市场数据
        trades : List[Dict[str, Any]]
            交易数据
        
        Returns
        -------
        Dict[str, Any]
            分析结果
        """
        bid_price = market_data.get("bid_price", 0)
        ask_price = market_data.get("ask_price", 0)
        mid_price = (bid_price + ask_price) / 2
        
        spread = self.calculate_bid_ask_spread(bid_price, ask_price)
        relative_spread = self.calculate_relative_spread(bid_price, ask_price, mid_price)
        
        order_flow = self.calculate_order_flow(trades)
        
        volume = sum(t.get("volume", 0) for t in trades)
        volatility = market_data.get("volatility", 0.01)
        
        liquidity_score = self.calculate_liquidity_score(spread, volume, volatility)
        
        return {
            "bid_ask_spread": spread,
            "relative_spread": relative_spread,
            "order_flow": order_flow,
            "liquidity_score": liquidity_score,
            "volume": volume,
            "volatility": volatility,
            "analyzed_at": datetime.utcnow()
        }
