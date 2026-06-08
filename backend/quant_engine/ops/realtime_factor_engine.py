"""
实时因子计算引擎

基于实时行情数据计算因子值
"""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from collections import deque
import numpy as np
from numba import jit

from quant_engine.infra.market_data_service import (
    MarketDataService,
    MarketData,
    KlineData,
    get_market_data_service,
)

logger = logging.getLogger("quant_engine.realtime_factor")


@dataclass
class FactorValue:
    """因子值"""
    factor_id: str
    symbol: str
    timestamp: datetime
    value: float
    raw_value: float  # 原始值（未归一化）
    
    # 统计信息
    mean_20d: float = 0.0
    std_20d: float = 0.0
    zscore: float = 0.0
    rank: int = 0


class FactorCalculator:
    """因子计算器"""
    
    def __init__(self, expression: str, symbol: str):
        self.expression = expression
        self.symbol = symbol
        self.history: deque = deque(maxlen=1000)  # 历史因子值
        
        # 解析表达式
        self._parsed = self._parse_expression(expression)
    
    def _parse_expression(self, expression: str) -> Dict[str, Any]:
        """解析因子表达式"""
        # 简化实现：支持基本的算术运算和技术指标
        # 实际应该使用完整的GP表达式解析器
        
        return {
            "type": "simple",
            "expression": expression,
        }
    
    def calculate(self, klines: List[KlineData]) -> Optional[float]:
        """计算因子值"""
        if len(klines) < 20:
            return None
        
        try:
            # 提取价格数据
            closes = np.array([k.close for k in klines])
            highs = np.array([k.high for k in klines])
            lows = np.array([k.low for k in klines])
            volumes = np.array([k.volume for k in klines])
            
            # 根据表达式计算
            # 这里使用简化的硬编码逻辑，实际应该动态解析表达式
            if "sma" in self.expression.lower():
                # 简单移动平均
                period = 20
                if len(closes) >= period:
                    value = np.mean(closes[-period:])
                else:
                    return None
            elif "rsi" in self.expression.lower():
                # RSI
                value = self._calculate_rsi(closes, 14)
            elif "macd" in self.expression.lower():
                # MACD
                value = self._calculate_macd(closes)[-1]
            elif "volume" in self.expression.lower():
                # 成交量相关
                value = volumes[-1] / np.mean(volumes[-20:]) if len(volumes) >= 20 else 1.0
            else:
                # 默认：价格变化率
                value = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0.0
            
            return float(value)
            
        except Exception as e:
            logger.error(f"Error calculating factor {self.expression}: {e}")
            return None
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """计算RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> np.ndarray:
        """计算MACD"""
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return histogram
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算EMA"""
        multiplier = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]
        
        return ema
    
    def update_history(self, value: float) -> None:
        """更新历史值"""
        self.history.append(value)
    
    def get_statistics(self) -> Dict[str, float]:
        """获取统计信息"""
        if len(self.history) < 20:
            return {"mean": 0.0, "std": 1.0, "zscore": 0.0}
        
        hist_array = np.array(list(self.history)[-20:])
        mean = np.mean(hist_array)
        std = np.std(hist_array)
        
        if std == 0:
            std = 1.0
        
        current = self.history[-1] if self.history else 0.0
        zscore = (current - mean) / std
        
        return {
            "mean": float(mean),
            "std": float(std),
            "zscore": float(zscore),
        }


class RealtimeFactorEngine:
    """实时因子计算引擎"""
    
    def __init__(
        self,
        market_service: Optional[MarketDataService] = None,
    ):
        self.market_service = market_service or get_market_data_service(mock=False)
        self.calculators: Dict[str, FactorCalculator] = {}
        self.factor_values: Dict[str, FactorValue] = {}
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        self._callbacks: List[Callable[[FactorValue], None]] = []
        
        # 计算间隔（秒）
        self._calc_interval = 5
    
    def register_factor(
        self,
        factor_id: str,
        expression: str,
        symbol: str,
    ) -> bool:
        """注册因子"""
        try:
            calculator = FactorCalculator(expression, symbol)
            
            with self._lock:
                self.calculators[factor_id] = calculator
            
            logger.info(f"Registered factor: {factor_id} ({expression})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register factor {factor_id}: {e}")
            return False
    
    def unregister_factor(self, factor_id: str) -> None:
        """注销因子"""
        with self._lock:
            self.calculators.pop(factor_id, None)
            self.factor_values.pop(factor_id, None)
        
        logger.info(f"Unregistered factor: {factor_id}")
    
    def add_callback(self, callback: Callable[[FactorValue], None]) -> None:
        """添加回调函数"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[FactorValue], None]) -> None:
        """移除回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def start(self) -> None:
        """启动引擎"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Realtime factor engine started")
    
    def stop(self) -> None:
        """停止引擎"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Realtime factor engine stopped")
    
    def _run(self) -> None:
        """主循环"""
        import time
        
        while self._running:
            try:
                self._calculate_all_factors()
                time.sleep(self._calc_interval)
                
            except Exception as e:
                logger.error(f"Error in factor calculation loop: {e}")
                time.sleep(1)
    
    def _calculate_all_factors(self) -> None:
        """计算所有因子"""
        with self._lock:
            calculators = dict(self.calculators)
        
        for factor_id, calculator in calculators.items():
            try:
                # 获取K线数据
                klines = self.market_service.get_klines(calculator.symbol, n=100)
                
                if not klines:
                    continue
                
                # 计算因子值
                raw_value = calculator.calculate(klines)
                
                if raw_value is None:
                    continue
                
                # 更新历史
                calculator.update_history(raw_value)
                
                # 获取统计信息
                stats = calculator.get_statistics()
                
                # 创建因子值对象
                factor_value = FactorValue(
                    factor_id=factor_id,
                    symbol=calculator.symbol,
                    timestamp=datetime.now(),
                    value=stats["zscore"],  # 使用zscore作为标准化值
                    raw_value=raw_value,
                    mean_20d=stats["mean"],
                    std_20d=stats["std"],
                    zscore=stats["zscore"],
                )
                
                # 保存
                with self._lock:
                    self.factor_values[factor_id] = factor_value
                
                # 通知回调
                self._notify_callbacks(factor_value)
                
            except Exception as e:
                logger.error(f"Error calculating factor {factor_id}: {e}")
    
    def _notify_callbacks(self, factor_value: FactorValue) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(factor_value)
            except Exception as e:
                logger.error(f"Error in factor callback: {e}")
    
    def get_factor_value(self, factor_id: str) -> Optional[FactorValue]:
        """获取因子值"""
        with self._lock:
            return self.factor_values.get(factor_id)
    
    def get_all_factor_values(self) -> Dict[str, FactorValue]:
        """获取所有因子值"""
        with self._lock:
            return dict(self.factor_values)
    
    def get_factor_values_by_symbol(self, symbol: str) -> List[FactorValue]:
        """获取指定品种的所有因子值"""
        with self._lock:
            return [
                fv for fv in self.factor_values.values()
                if fv.symbol == symbol
            ]


# 全局引擎实例
_factor_engine: Optional[RealtimeFactorEngine] = None


def get_factor_engine(
    market_service: Optional[MarketDataService] = None,
) -> RealtimeFactorEngine:
    """获取全局因子引擎实例"""
    global _factor_engine
    
    if _factor_engine is None:
        _factor_engine = RealtimeFactorEngine(market_service)
    
    return _factor_engine


def reset_factor_engine() -> None:
    """重置全局因子引擎实例"""
    global _factor_engine
    
    if _factor_engine:
        _factor_engine.stop()
        _factor_engine = None
