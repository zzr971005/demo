"""
模拟交易引擎 - 支持TqKq实时模拟和TqSim历史回放
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SimulationMode(Enum):
    """模拟模式"""
    TQKQ = "tqkq"  # 快期实时模拟
    TQSIM = "tqsim"  # 本地历史回放


class SimulationEngine:
    """模拟交易引擎"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化模拟交易引擎
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.mode = SimulationMode(self.config.get("simulation_mode", "tqkq"))
        self.replay_enabled = self.config.get("replay_enabled", True)
        self.replay_data_source = self.config.get("replay_data_source", "database")
        
        self.is_running = False
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: List[Dict[str, Any]] = []
        
    async def start(self):
        """启动模拟交易引擎"""
        if self.is_running:
            logger.warning("模拟交易引擎已在运行")
            return
        
        self.is_running = True
        logger.info(f"模拟交易引擎启动: 模式={self.mode.value}")
        
        if self.mode == SimulationMode.TQKQ:
            await self._start_tqkq_simulation()
        elif self.mode == SimulationMode.TQSIM:
            await self._start_tqsim_replay()
    
    async def stop(self):
        """停止模拟交易引擎"""
        if not self.is_running:
            logger.warning("模拟交易引擎未运行")
            return
        
        self.is_running = False
        logger.info("模拟交易引擎停止")
    
    async def _start_tqkq_simulation(self):
        """启动TqKq实时模拟"""
        logger.info("启动TqKq实时模拟")
        # TQSDK TqKq模式集成 - 需要扩展tqsdk_executor.py以支持模拟交易
        # 当前版本暂不支持，需要天勤账号和模拟交易环境配置
        logger.warning("TqKq实时模拟功能暂未实现，需要TQSDK模拟交易环境配置")
        raise NotImplementedError("TqKq实时模拟功能暂未实现")
    
    async def _start_tqsim_replay(self):
        """启动TqSim历史回放"""
        logger.info("启动TqSim历史回放")
        # TQSDK TqSim回放功能集成 - 需要从数据库读取历史K线数据
        # 当前版本暂不支持，需要实现历史数据回放引擎
        logger.warning("TqSim历史回放功能暂未实现，需要历史数据回放引擎")
        raise NotImplementedError("TqSim历史回放功能暂未实现")
    
    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        下单
        
        Parameters
        ----------
        order : Dict[str, Any]
            订单字典
        
        Returns
        -------
        Dict[str, Any]
            订单结果
        """
        if not self.is_running:
            return {"success": False, "message": "引擎未运行"}
        
        order_id = f"sim_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        order["order_id"] = order_id
        order["status"] = "FILLED"
        order["filled_at"] = datetime.utcnow()
        
        self.orders.append(order)
        
        # 更新持仓
        self._update_position(order)
        
        logger.info(f"模拟下单成功: {order_id}")
        return {"success": True, "order_id": order_id, "status": "FILLED"}
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        撤单
        
        Parameters
        ----------
        order_id : str
            订单ID
        
        Returns
        -------
        Dict[str, Any]
            撤单结果
        """
        for order in self.orders:
            if order["order_id"] == order_id:
                order["status"] = "CANCELLED"
                order["cancelled_at"] = datetime.utcnow()
                logger.info(f"模拟撤单成功: {order_id}")
                return {"success": True, "order_id": order_id, "status": "CANCELLED"}
        
        return {"success": False, "message": "订单不存在"}
    
    def _update_position(self, order: Dict[str, Any]):
        """
        更新持仓
        
        Parameters
        ----------
        order : Dict[str, Any]
            订单字典
        """
        symbol = order["symbol"]
        direction = order["direction"]
        offset = order["offset"]
        volume = order["volume"]
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                "symbol": symbol,
                "volume": 0,
                "direction": None,
                "avg_price": 0.0,
                "pnl": 0.0
            }
        
        position = self.positions[symbol]
        
        if offset == "OPEN":
            # 开仓
            if position["volume"] == 0:
                position["direction"] = "LONG" if direction == "BUY" else "SHORT"
                position["avg_price"] = order.get("price", 0)
            position["volume"] += volume
        elif offset == "CLOSE":
            # 平仓
            position["volume"] -= volume
            if position["volume"] <= 0:
                position["volume"] = 0
                position["direction"] = None
                position["avg_price"] = 0.0
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取持仓
        
        Parameters
        ----------
        symbol : str
            品种代码
        
        Returns
        -------
        Optional[Dict[str, Any]]
            持仓信息
        """
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有持仓
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            持仓字典
        """
        return self.positions
    
    def get_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取订单
        
        Parameters
        ----------
        symbol : Optional[str]
            品种代码，None表示获取所有
        
        Returns
        -------
        List[Dict[str, Any]]
            订单列表
        """
        if symbol:
            return [o for o in self.orders if o["symbol"] == symbol]
        return self.orders
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        获取账户信息
        
        Returns
        -------
        Dict[str, Any]
            账户信息
        """
        return {
            "balance": 1000000.0,  # 模拟账户余额
            "available": 1000000.0,
            "margin": 0.0,
            "position_profit": 0.0,
            "close_profit": 0.0,
            "mode": self.mode.value
        }
