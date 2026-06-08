"""
流动性风险管理 - 流动性指标、流动性风险计算
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class LiquidityRiskManager:
    """流动性风险管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化管理器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.liquidity_thresholds = self.config.get("liquidity_thresholds", {
            "min_volume": 100,
            "max_spread_ratio": 0.01,
            "min_depth": 10
        })
    
    def calculate_liquidity_ratio(
        self,
        volume: float,
        avg_volume: float
    ) -> float:
        """
        计算流动性比率
        
        Parameters
        ----------
        volume : float
            当前成交量
        avg_volume : float
            平均成交量
        
        Returns
        -------
        float
            流动性比率
        """
        return volume / avg_volume if avg_volume > 0 else 0
    
    def calculate_amihud_illiquidity(
        self,
        returns: np.ndarray,
        volume: np.ndarray
    ) -> float:
        """
        计算Amihud非流动性指标
        
        Parameters
        ----------
        returns : np.ndarray
            收益率数组
        volume : np.ndarray
            成交量数组
        
        Returns
        -------
        float
            Amihud指标
        """
        # Amihud = |return| / volume
        illiquidity = np.abs(returns) / (volume + 1e-8)
        return np.mean(illiquidity)
    
    def calculate_turnover_ratio(
        self,
        volume: float,
        total_supply: float
    ) -> float:
        """
        计算换手率
        
        Parameters
        ----------
        volume : float
            成交量
        total_supply : float
            总供应量
        
        Returns
        -------
        float
            换手率
        """
        return volume / total_supply if total_supply > 0 else 0
    
    def calculate_liquidity_risk(
        self,
        market_data: Dict[str, Any],
        historical_data: Optional[Dict[str, np.ndarray]] = None
    ) -> Dict[str, Any]:
        """
        计算流动性风险
        
        Parameters
        ----------
        market_data : Dict[str, Any]
            市场数据
        historical_data : Optional[Dict[str, np.ndarray]]
            历史数据
        
        Returns
        -------
        Dict[str, Any]
            流动性风险指标
        """
        current_volume = market_data.get("volume", 0)
        bid_price = market_data.get("bid_price", 0)
        ask_price = market_data.get("ask_price", 0)
        mid_price = (bid_price + ask_price) / 2
        
        # 价差比率
        spread_ratio = (ask_price - bid_price) / mid_price if mid_price > 0 else 0
        
        # 流动性检查
        volume_ok = current_volume >= self.liquidity_thresholds["min_volume"]
        spread_ok = spread_ratio <= self.liquidity_thresholds["max_spread_ratio"]
        
        # 计算历史指标
        if historical_data:
            avg_volume = np.mean(historical_data.get("volume", np.array([current_volume])))
            liquidity_ratio = self.calculate_liquidity_ratio(current_volume, avg_volume)
            
            returns = np.diff(historical_data.get("close", np.array([mid_price]))) / historical_data.get("close", np.array([mid_price]))[:-1]
            volume_hist = historical_data.get("volume", np.array([current_volume]))
            amihud = self.calculate_amihud_illiquidity(returns, volume_hist)
        else:
            liquidity_ratio = 1.0
            amihud = 0.0
        
        # 综合风险评分
        risk_score = 0.0
        if not volume_ok:
            risk_score += 0.4
        if not spread_ok:
            risk_score += 0.3
        if liquidity_ratio < 0.5:
            risk_score += 0.2
        if amihud > 0.001:
            risk_score += 0.1
        
        return {
            "current_volume": current_volume,
            "spread_ratio": spread_ratio,
            "liquidity_ratio": liquidity_ratio,
            "amihud_illiquidity": amihud,
            "risk_score": risk_score,
            "volume_ok": volume_ok,
            "spread_ok": spread_ok,
            "high_risk": risk_score > 0.5
        }
    
    def check_liquidity_for_order(
        self,
        order_volume: float,
        market_data: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        检查订单流动性
        
        Parameters
        ----------
        order_volume : float
            订单量
        market_data : Dict[str, Any]
            市场数据
        
        Returns
        -------
        tuple[bool, str]
            (是否通过, 原因)
        """
        current_volume = market_data.get("volume", 0)
        avg_volume = market_data.get("avg_volume", current_volume)
        
        # 订单占比
        order_ratio = order_volume / avg_volume if avg_volume > 0 else 1
        
        if order_ratio > 0.1:
            return False, f"订单量过大，占平均成交量的 {order_ratio:.1%}"
        
        return True, "流动性检查通过"
