"""
多市场多品种联动交易 - 跨市场套利、联动交易
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CrossMarketTrader:
    """跨市场交易器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化交易器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.markets = self.config.get("markets", [])
        self.correlation_threshold = self.config.get("correlation_threshold", 0.8)
    
    def find_arbitrage_opportunities(
        self,
        market_data: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        寻找套利机会
        
        Parameters
        ----------
        market_data : Dict[str, Dict[str, Any]]
            市场数据字典
        
        Returns
        -------
        List[Dict[str, Any]]
            套利机会列表
        """
        opportunities = []
        
        # 检查所有市场对
        markets = list(market_data.keys())
        for i, market_a in enumerate(markets):
            for market_b in markets[i+1:]:
                data_a = market_data[market_a]
                data_b = market_data[market_b]
                
                # 计算价差
                price_a = data_a.get("last_price", 0)
                price_b = data_b.get("last_price", 0)
                
                if price_a > 0 and price_b > 0:
                    spread = abs(price_a - price_b)
                    spread_ratio = spread / min(price_a, price_b)
                    
                    # 如果价差超过阈值，视为套利机会
                    if spread_ratio > 0.01:  # 1%价差
                        opportunities.append({
                            "market_a": market_a,
                            "market_b": market_b,
                            "price_a": price_a,
                            "price_b": price_b,
                            "spread": spread,
                            "spread_ratio": spread_ratio,
                            "opportunity_type": "arbitrage"
                        })
        
        return opportunities
    
    def calculate_correlation(
        self,
        returns_a: List[float],
        returns_b: List[float]
    ) -> float:
        """
        计算相关性
        
        Parameters
        ----------
        returns_a : List[float]
            市场A收益率
        returns_b : List[float]
            市场B收益率
        
        Returns
        -------
        float
            相关系数
        """
        import numpy as np
        if len(returns_a) != len(returns_b) or len(returns_a) < 2:
            return 0.0
        
        correlation = np.corrcoef(returns_a, returns_b)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def find_linked_trading_opportunities(
        self,
        market_data: Dict[str, Dict[str, Any]],
        historical_returns: Dict[str, List[float]]
    ) -> List[Dict[str, Any]]:
        """
        寻找联动交易机会
        
        Parameters
        ----------
        market_data : Dict[str, Dict[str, Any]]
            市场数据
        historical_returns : Dict[str, List[float]]
            历史收益率
        
        Returns
        -------
        List[Dict[str, Any]]
            联动交易机会
        """
        opportunities = []
        
        markets = list(market_data.keys())
        for i, market_a in enumerate(markets):
            for market_b in markets[i+1:]:
                returns_a = historical_returns.get(market_a, [])
                returns_b = historical_returns.get(market_b, [])
                
                # 计算相关性
                correlation = self.calculate_correlation(returns_a, returns_b)
                
                # 如果相关性高，检查当前价差
                if correlation > self.correlation_threshold:
                    price_a = market_data[market_a].get("last_price", 0)
                    price_b = market_data[market_b].get("last_price", 0)
                    
                    # 计算历史价差均值
                    if len(returns_a) > 0 and len(returns_b) > 0:
                        # 简化：使用价格比率
                        price_ratio = price_a / price_b if price_b > 0 else 1
                        
                        opportunities.append({
                            "market_a": market_a,
                            "market_b": market_b,
                            "correlation": correlation,
                            "price_ratio": price_ratio,
                            "opportunity_type": "linked_trading"
                        })
        
        return opportunities
    
    def execute_cross_market_trade(
        self,
        opportunity: Dict[str, Any],
        account_balance: float
    ) -> Dict[str, Any]:
        """
        执行跨市场交易
        
        Parameters
        ----------
        opportunity : Dict[str, Any]
            交易机会
        account_balance : float
            账户余额
        
        Returns
        -------
        Dict[str, Any]
            交易结果
        """
        opportunity_type = opportunity.get("opportunity_type")
        
        if opportunity_type == "arbitrage":
            # 套利交易
            market_a = opportunity["market_a"]
            market_b = opportunity["market_b"]
            price_a = opportunity["price_a"]
            price_b = opportunity["price_b"]
            
            # 买入低价，卖出高价
            if price_a < price_b:
                buy_market = market_a
                sell_market = market_b
            else:
                buy_market = market_b
                sell_market = market_a
            
            return {
                "success": True,
                "action": "arbitrage",
                "buy_market": buy_market,
                "sell_market": sell_market,
                "executed_at": datetime.utcnow()
            }
        
        elif opportunity_type == "linked_trading":
            # 联动交易
            return {
                "success": True,
                "action": "linked_trading",
                "markets": [opportunity["market_a"], opportunity["market_b"]],
                "executed_at": datetime.utcnow()
            }
        
        return {"success": False, "message": "未知机会类型"}
