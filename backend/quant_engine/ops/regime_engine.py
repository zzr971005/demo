"""
Regime状态识别引擎
用于实时识别市场状态（趋势/震荡/突破）
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import deque

from .regime_features import RegimeFeatureCalculator, RegimeFeatures, RegimeType


logger = logging.getLogger("regime_engine")


@dataclass
class RegimeState:
    """Regime状态数据"""
    symbol: str
    regime: RegimeType
    strength: float                    # 0-1
    features: RegimeFeatures
    timestamp: datetime
    duration: int = 0                  # 当前Regime持续K线数
    previous_regime: Optional[RegimeType] = None
    transition_confidence: float = 0.0  # 状态转换置信度


@dataclass
class RegimeConfig:
    """Regime引擎配置"""
    adx_period: int = 14
    atr_period: int = 14
    ma_period: int = 20
    min_bars: int = 30                 # 最小K线数
    regime_confirmation: int = 2       # Regime确认所需连续K线
    history_size: int = 100            # 历史数据保留数量


class RegimeEngine:
    """
    Regime状态识别引擎
    
    功能：
    1. 实时计算Regime特征
    2. 识别市场状态（趋势/震荡/突破）
    3. 检测状态转换
    4. 提供Regime过滤信号
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()
        self.calculator = RegimeFeatureCalculator(
            adx_period=self.config.adx_period,
            atr_period=self.config.atr_period,
            ma_period=self.config.ma_period
        )
        
        # 数据缓存: symbol -> deque of bars
        self._bar_cache: Dict[str, deque] = {}
        
        # 当前Regime状态: symbol -> RegimeState
        self._current_regime: Dict[str, RegimeState] = {}
        
        # 历史Regime: symbol -> List[RegimeState]
        self._regime_history: Dict[str, List[RegimeState]] = {}
        
        # 回调函数: symbol -> List[Callable]
        self._callbacks: Dict[str, List[Callable]] = {}
        
        # 统计信息
        self._stats = {
            'total_updates': 0,
            'regime_transitions': 0,
            'symbols_tracked': set()
        }
        
        logger.info(f"RegimeEngine initialized with config: {self.config}")
    
    def subscribe(self, symbol: str, callback: Optional[Callable] = None):
        """
        订阅品种的Regime更新
        
        Args:
            symbol: 品种代码
            callback: 状态变化回调函数 (RegimeState) -> None
        """
        if symbol not in self._bar_cache:
            self._bar_cache[symbol] = deque(maxlen=self.config.history_size)
            self._regime_history[symbol] = []
            self._stats['symbols_tracked'].add(symbol)
            logger.info(f"Subscribed to regime updates for {symbol}")
        
        if callback:
            if symbol not in self._callbacks:
                self._callbacks[symbol] = []
            self._callbacks[symbol].append(callback)
    
    def unsubscribe(self, symbol: str, callback: Optional[Callable] = None):
        """取消订阅"""
        if callback and symbol in self._callbacks:
            self._callbacks[symbol] = [cb for cb in self._callbacks[symbol] if cb != callback]
        else:
            # 清除所有数据
            self._bar_cache.pop(symbol, None)
            self._current_regime.pop(symbol, None)
            self._regime_history.pop(symbol, None)
            self._callbacks.pop(symbol, None)
            self._stats['symbols_tracked'].discard(symbol)
            logger.info(f"Unsubscribed from regime updates for {symbol}")
    
    def on_bar(self, symbol: str, bar: Dict) -> Optional[RegimeState]:
        """
        接收K线数据并更新Regime状态
        
        Args:
            symbol: 品种代码
            bar: K线数据 {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        
        Returns:
            最新的RegimeState，如果数据不足返回None
        """
        if symbol not in self._bar_cache:
            self.subscribe(symbol)
        
        # 添加K线到缓存
        self._bar_cache[symbol].append(bar)
        self._stats['total_updates'] += 1
        
        # 检查数据是否足够
        if len(self._bar_cache[symbol]) < self.config.min_bars:
            logger.debug(f"{symbol}: Insufficient data ({len(self._bar_cache[symbol])}/{self.config.min_bars})")
            return None
        
        # 计算Regime特征
        df = pd.DataFrame(list(self._bar_cache[symbol]))
        df.set_index('timestamp', inplace=True)
        
        try:
            df = self.calculator.calculate_all_features(df)
            features = self.calculator.get_latest_features(df)
            features.symbol = symbol
            
            # 创建新的RegimeState
            new_state = self._create_regime_state(symbol, features)
            
            # 检查状态转换
            old_state = self._current_regime.get(symbol)
            if old_state and old_state.regime != new_state.regime:
                new_state.previous_regime = old_state.regime
                new_state.transition_confidence = self._calculate_transition_confidence(
                    old_state, new_state
                )
                self._stats['regime_transitions'] += 1
                logger.info(f"{symbol}: Regime transition {old_state.regime.value} -> {new_state.regime.value} "
                          f"(confidence: {new_state.transition_confidence:.2f})")
                
                # 触发回调
                self._notify_callbacks(symbol, new_state)
            else:
                # 持续同一Regime，增加持续时间
                if old_state:
                    new_state.duration = old_state.duration + 1
            
            # 更新当前状态和历史
            self._current_regime[symbol] = new_state
            self._regime_history[symbol].append(new_state)
            
            return new_state
            
        except Exception as e:
            logger.error(f"{symbol}: Error calculating regime features: {e}")
            return None
    
    def _create_regime_state(self, symbol: str, features: RegimeFeatures) -> RegimeState:
        """创建RegimeState对象"""
        return RegimeState(
            symbol=symbol,
            regime=features.regime,
            strength=features.regime_strength,
            features=features,
            timestamp=features.timestamp or datetime.now(),
            duration=1
        )
    
    def _calculate_transition_confidence(self, old_state: RegimeState, new_state: RegimeState) -> float:
        """计算状态转换置信度"""
        # 基于ADX和Regime强度计算
        adx_factor = min(new_state.features.adx / 50, 1.0)
        strength_factor = new_state.strength
        
        # 持续时间因子（持续时间越长，转换越可信）
        duration_factor = min(old_state.duration / 10, 1.0)
        
        return (adx_factor + strength_factor + duration_factor) / 3
    
    def _notify_callbacks(self, symbol: str, state: RegimeState):
        """通知所有回调函数"""
        if symbol in self._callbacks:
            for callback in self._callbacks[symbol]:
                try:
                    callback(state)
                except Exception as e:
                    logger.error(f"Error in regime callback: {e}")
    
    def get_current_regime(self, symbol: str) -> Optional[RegimeState]:
        """获取当前Regime状态"""
        return self._current_regime.get(symbol)
    
    def get_regime_history(self, symbol: str, n: int = 100) -> List[RegimeState]:
        """获取Regime历史"""
        history = self._regime_history.get(symbol, [])
        return history[-n:] if n < len(history) else history
    
    def is_tradable(self, symbol: str, strategy_type: str = "trend") -> bool:
        """
        判断当前Regime是否适合交易
        
        Args:
            symbol: 品种代码
            strategy_type: 策略类型 (trend/mean_reversion/breakout)
        
        Returns:
            是否适合交易
        """
        state = self._current_regime.get(symbol)
        if not state:
            return False
        
        regime = state.regime
        strength = state.strength
        
        # 强度阈值
        min_strength = 0.3
        if strength < min_strength:
            return False
        
        # 根据策略类型判断
        if strategy_type == "trend":
            return regime in [RegimeType.TREND_UP, RegimeType.TREND_DOWN]
        elif strategy_type == "mean_reversion":
            return regime == RegimeType.RANGE
        elif strategy_type == "breakout":
            return regime == RegimeType.BREAKOUT
        else:
            return True
    
    def get_regime_distribution(self, symbol: str, n: int = 50) -> Dict[str, float]:
        """
        获取最近N根K线的Regime分布
        
        Returns:
            {regime_type: percentage}
        """
        history = self.get_regime_history(symbol, n)
        if not history:
            return {}
        
        counts = {}
        for state in history[-n:]:
            regime = state.regime.value
            counts[regime] = counts.get(regime, 0) + 1
        
        total = len(history[-n:])
        return {k: v/total for k, v in counts.items()}
    
    def get_stats(self) -> Dict:
        """获取引擎统计信息"""
        return {
            'total_updates': self._stats['total_updates'],
            'regime_transitions': self._stats['regime_transitions'],
            'symbols_tracked': len(self._stats['symbols_tracked']),
            'current_regimes': {
                symbol: {
                    'regime': state.regime.value,
                    'strength': state.strength,
                    'duration': state.duration
                }
                for symbol, state in self._current_regime.items()
            }
        }
    
    def reset(self, symbol: Optional[str] = None):
        """重置引擎状态"""
        if symbol:
            self._bar_cache.pop(symbol, None)
            self._current_regime.pop(symbol, None)
            self._regime_history.pop(symbol, None)
            logger.info(f"Reset regime state for {symbol}")
        else:
            self._bar_cache.clear()
            self._current_regime.clear()
            self._regime_history.clear()
            self._stats = {
                'total_updates': 0,
                'regime_transitions': 0,
                'symbols_tracked': set()
            }
            logger.info("Reset all regime states")


# 全局Regime引擎实例
_regime_engine: Optional[RegimeEngine] = None


def get_regime_engine(config: Optional[RegimeConfig] = None) -> RegimeEngine:
    """获取全局Regime引擎实例（单例模式）"""
    global _regime_engine
    if _regime_engine is None:
        _regime_engine = RegimeEngine(config)
    return _regime_engine
