"""
仓位管理器 - 控制仓位，避免高仓位
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class PositionManager:
    """仓位管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化仓位管理器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.max_position_ratio = self.config.get("max_position_ratio", 0.3)
        self.max_total_margin_ratio = self.config.get("max_total_margin_ratio", 0.5)
        
    def calculate_position_size(
        self,
        symbol: str,
        account_balance: float,
        current_positions: Dict[str, Dict[str, Any]],
        symbol_config: Dict[str, Any]
    ) -> int:
        """
        计算建议仓位大小
        
        Parameters
        ----------
        symbol : str
            品种代码
        account_balance : float
            账户余额
        current_positions : Dict[str, Dict[str, Any]]
            当前持仓
        symbol_config : Dict[str, Any]
            品种配置
        
        Returns
        -------
        int
            建议手数
        """
        # 计算当前总保证金占用
        total_margin = self._calculate_total_margin(current_positions, symbol_config)
        
        # 计算最大可用保证金
        max_available_margin = account_balance * self.max_total_margin_ratio
        available_margin = max_available_margin - total_margin
        
        if available_margin <= 0:
            logger.warning(f"可用保证金不足，无法开仓: {symbol}")
            return 0
        
        # 计算单品种最大保证金
        max_symbol_margin = account_balance * self.max_position_ratio
        
        # 计算单手保证金
        margin_per_lot = symbol_config.get("margin_per_lot", 5000)
        
        # 计算最大手数
        max_lots_by_available = int(available_margin / margin_per_lot)
        max_lots_by_symbol = int(max_symbol_margin / margin_per_lot)
        
        # 取较小值
        max_lots = min(max_lots_by_available, max_lots_by_symbol)
        
        # 确保至少1手（如果可用）
        if max_lots == 0 and available_margin >= margin_per_lot:
            max_lots = 1
        
        logger.info(
            f"品种 {symbol} 建议仓位: {max_lots}手 "
            f"(可用保证金: {available_margin:.2f}, 单手保证金: {margin_per_lot})"
        )
        
        return max_lots
    
    def _calculate_total_margin(
        self,
        positions: Dict[str, Dict[str, Any]],
        symbol_config: Dict[str, Any]
    ) -> float:
        """
        计算总保证金占用
        
        Parameters
        ----------
        positions : Dict[str, Dict[str, Any]]
            持仓字典
        symbol_config : Dict[str, Any]
            品种配置
        
        Returns
        -------
        float
            总保证金
        """
        total_margin = 0.0
        
        for symbol, position in positions.items():
            volume = position.get("volume", 0)
            margin_per_lot = symbol_config.get("margin_per_lot", 5000)
            total_margin += volume * margin_per_lot
        
        return total_margin
    
    def check_position_limit(
        self,
        symbol: str,
        volume: int,
        account_balance: float,
        current_positions: Dict[str, Dict[str, Any]],
        symbol_config: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        检查仓位限制
        
        Parameters
        ----------
        symbol : str
            品种代码
        volume : int
            建议手数
        account_balance : float
            账户余额
        current_positions : Dict[str, Dict[str, Any]]
            当前持仓
        symbol_config : Dict[str, Any]
            品种配置
        
        Returns
        -------
        tuple[bool, str]
            (是否通过, 原因)
        """
        # 计算当前总保证金
        total_margin = self._calculate_total_margin(current_positions, symbol_config)
        
        # 计算新增保证金
        margin_per_lot = symbol_config.get("margin_per_lot", 5000)
        new_margin = volume * margin_per_lot
        
        # 检查总保证金限制
        total_margin_after = total_margin + new_margin
        max_total_margin = account_balance * self.max_total_margin_ratio
        
        if total_margin_after > max_total_margin:
            return False, f"总保证金超限: {total_margin_after:.2f} > {max_total_margin:.2f}"
        
        # 检查单品种保证金限制
        max_symbol_margin = account_balance * self.max_position_ratio
        current_symbol_margin = current_positions.get(symbol, {}).get("volume", 0) * margin_per_lot
        symbol_margin_after = current_symbol_margin + new_margin
        
        if symbol_margin_after > max_symbol_margin:
            return False, f"单品种保证金超限: {symbol_margin_after:.2f} > {max_symbol_margin:.2f}"
        
        return True, "仓位检查通过"
    
    def get_position_summary(
        self,
        positions: Dict[str, Dict[str, Any]],
        account_balance: float,
        symbol_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取仓位摘要
        
        Parameters
        ----------
        positions : Dict[str, Dict[str, Any]]
            持仓字典
        account_balance : float
            账户余额
        symbol_config : Dict[str, Any]
            品种配置
        
        Returns
        -------
        Dict[str, Any]
            仓位摘要
        """
        total_margin = self._calculate_total_margin(positions, symbol_config)
        total_margin_ratio = total_margin / account_balance if account_balance > 0 else 0
        
        # 计算各品种仓位占比
        symbol_positions = {}
        for symbol, position in positions.items():
            volume = position.get("volume", 0)
            margin_per_lot = symbol_config.get("margin_per_lot", 5000)
            symbol_margin = volume * margin_per_lot
            symbol_ratio = symbol_margin / account_balance if account_balance > 0 else 0
            symbol_positions[symbol] = {
                "volume": volume,
                "margin": symbol_margin,
                "ratio": symbol_ratio
            }
        
        return {
            "total_margin": total_margin,
            "total_margin_ratio": total_margin_ratio,
            "max_total_margin_ratio": self.max_total_margin_ratio,
            "available_margin": account_balance * self.max_total_margin_ratio - total_margin,
            "symbol_positions": symbol_positions,
            "position_count": len(positions)
        }
