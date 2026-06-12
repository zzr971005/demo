"""
实时信号生成器
将因子值转换为交易信号
"""

import logging
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np

from .regime_engine import RegimeEngine, RegimeType


logger = logging.getLogger("signal_generator")


class SignalDirection(Enum):
    """信号方向"""
    LONG = 1       # 做多
    SHORT = -1     # 做空
    NEUTRAL = 0    # 中性


class SignalStrength(Enum):
    """信号强度"""
    STRONG = 3     # 强
    MODERATE = 2   # 中等
    WEAK = 1       # 弱
    NONE = 0       # 无


@dataclass
class TradingSignal:
    """交易信号"""
    symbol: str
    direction: SignalDirection
    strength: SignalStrength
    factor_value: float           # 原始因子值
    zscore: float                 # Z-score标准化值
    regime: RegimeType           # 当前市场状态
    regime_match: bool           # 是否匹配当前Regime
    
    # 信号元数据
    timestamp: datetime
    factor_name: str             # 因子名称
    confidence: float            # 信号置信度 (0-1)
    
    # 可选：附加信息
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalConfig:
    """信号生成配置"""
    # Z-score阈值
    long_threshold: float = 1.5     # 做多阈值
    short_threshold: float = -1.5   # 做空阈值
    
    # 信号强度分级
    strong_threshold: float = 2.5   # 强信号阈值
    moderate_threshold: float = 1.5 # 中等信号阈值
    
    # Regime过滤
    enable_regime_filter: bool = True
    trend_factors: List[str] = field(default_factory=lambda: ['momentum', 'trend'])
    mr_factors: List[str] = field(default_factory=lambda: ['mean_reversion', 'oscillator'])
    
    # 信号平滑
    smoothing_window: int = 3       # 平滑窗口
    min_consecutive: int = 2        # 最小连续信号数


class SignalGenerator:
    """
    实时信号生成器
    
    功能：
    1. 将因子值转换为交易信号
    2. 应用Z-score标准化
    3. 根据Regime过滤信号
    4. 计算信号强度和置信度
    """
    
    def __init__(self, config: Optional[SignalConfig] = None):
        self.config = config or SignalConfig()
        self.regime_engine = RegimeEngine()
        
        # 信号历史缓存: symbol -> List[TradingSignal]
        self._signal_history: Dict[str, List[TradingSignal]] = {}
        
        # 因子值历史: symbol -> {factor_name -> deque of values}
        self._factor_history: Dict[str, Dict[str, Any]] = {}
        
        # 回调函数
        self._callbacks: List[Callable[[TradingSignal], None]] = []
        
        logger.info(f"SignalGenerator initialized with config: {self.config}")
    
    def register_callback(self, callback: Callable[[TradingSignal], None]):
        """注册信号回调函数"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[TradingSignal], None]):
        """注销信号回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def on_factor_update(self, symbol: str, factor_name: str, 
                        factor_value: float, timestamp: datetime,
                        bar_data: Optional[Dict] = None) -> Optional[TradingSignal]:
        """
        接收因子更新并生成信号
        
        Args:
            symbol: 品种代码
            factor_name: 因子名称
            factor_value: 因子值
            timestamp: 时间戳
            bar_data: 可选的K线数据（用于Regime计算）
        
        Returns:
            TradingSignal或None
        """
        # 初始化历史缓存
        if symbol not in self._factor_history:
            self._factor_history[symbol] = {}
        if symbol not in self._signal_history:
            self._signal_history[symbol] = []
        
        # 更新Regime引擎
        current_regime = None
        if bar_data:
            regime_state = self.regime_engine.on_bar(symbol, bar_data)
            if regime_state:
                current_regime = regime_state.regime
        
        if current_regime is None:
            regime_state = self.regime_engine.get_current_regime(symbol)
            if regime_state:
                current_regime = regime_state.regime
            else:
                current_regime = RegimeType.UNKNOWN
        
        # 计算Z-score
        zscore = self._calculate_zscore(symbol, factor_name, factor_value)
        
        # 生成信号
        signal = self._generate_signal(
            symbol=symbol,
            factor_name=factor_name,
            factor_value=factor_value,
            zscore=zscore,
            regime=current_regime,
            timestamp=timestamp
        )
        
        if signal:
            # 保存信号历史
            self._signal_history[symbol].append(signal)
            
            # 限制历史长度
            if len(self._signal_history[symbol]) > 1000:
                self._signal_history[symbol] = self._signal_history[symbol][-500:]
            
            # 触发回调
            self._notify_callbacks(signal)
            
            logger.debug(f"Generated signal for {symbol}: {signal.direction.name} "
                        f"(strength: {signal.strength.name}, confidence: {signal.confidence:.2f})")
        
        return signal
    
    def _calculate_zscore(self, symbol: str, factor_name: str, 
                         value: float, window: int = 50) -> float:
        """
        计算Z-score
        
        使用历史数据计算标准化分数
        """
        # 获取或初始化历史值
        if factor_name not in self._factor_history[symbol]:
            self._factor_history[symbol][factor_name] = []
        
        history = self._factor_history[symbol][factor_name]
        history.append(value)
        
        # 限制历史长度
        if len(history) > window * 2:
            history = history[-window:]
            self._factor_history[symbol][factor_name] = history
        
        # 需要足够数据才能计算
        if len(history) < 10:
            return 0.0
        
        # 计算Z-score
        values = np.array(history[-window:])
        mean = np.mean(values)
        std = np.std(values)
        
        if std < 1e-10:
            return 0.0
        
        zscore = (value - mean) / std
        return zscore
    
    def _generate_signal(self, symbol: str, factor_name: str,
                        factor_value: float, zscore: float,
                        regime: RegimeType, timestamp: datetime) -> Optional[TradingSignal]:
        """生成交易信号"""
        
        # 确定方向
        if zscore > self.config.long_threshold:
            direction = SignalDirection.LONG
        elif zscore < self.config.short_threshold:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL
        
        # 确定强度
        abs_zscore = abs(zscore)
        if abs_zscore > self.config.strong_threshold:
            strength = SignalStrength.STRONG
        elif abs_zscore > self.config.moderate_threshold:
            strength = SignalStrength.MODERATE
        elif abs_zscore > 0.5:
            strength = SignalStrength.WEAK
        else:
            strength = SignalStrength.NONE
        
        # Regime匹配检查
        regime_match = self._check_regime_match(factor_name, direction, regime)
        
        # 如果启用了Regime过滤且不匹配，降低信号强度
        if self.config.enable_regime_filter and not regime_match:
            if strength == SignalStrength.STRONG:
                strength = SignalStrength.MODERATE
            elif strength == SignalStrength.MODERATE:
                strength = SignalStrength.WEAK
            elif strength == SignalStrength.WEAK:
                strength = SignalStrength.NONE
        
        # 计算置信度
        confidence = self._calculate_confidence(zscore, strength, regime_match)
        
        # 如果信号太弱，返回None
        if strength == SignalStrength.NONE or direction == SignalDirection.NEUTRAL:
            return None
        
        return TradingSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            factor_value=factor_value,
            zscore=zscore,
            regime=regime,
            regime_match=regime_match,
            timestamp=timestamp,
            factor_name=factor_name,
            confidence=confidence
        )
    
    def _check_regime_match(self, factor_name: str, direction: SignalDirection, 
                           regime: RegimeType) -> bool:
        """检查因子是否匹配当前Regime"""
        
        # 趋势因子
        if any(tf in factor_name.lower() for tf in self.config.trend_factors):
            if direction == SignalDirection.LONG:
                return regime in [RegimeType.TREND_UP, RegimeType.BREAKOUT]
            elif direction == SignalDirection.SHORT:
                return regime in [RegimeType.TREND_DOWN, RegimeType.BREAKOUT]
        
        # 均值回归因子
        if any(mf in factor_name.lower() for mf in self.config.mr_factors):
            return regime == RegimeType.RANGE
        
        # 默认匹配
        return True
    
    def _calculate_confidence(self, zscore: float, strength: SignalStrength, 
                             regime_match: bool) -> float:
        """计算信号置信度"""
        
        # 基于Z-score的置信度
        abs_z = abs(zscore)
        base_confidence = min(abs_z / 3.0, 1.0)
        
        # 强度加成
        strength_bonus = {
            SignalStrength.STRONG: 0.2,
            SignalStrength.MODERATE: 0.1,
            SignalStrength.WEAK: 0.0,
            SignalStrength.NONE: -0.5
        }[strength]
        
        # Regime匹配加成
        regime_bonus = 0.15 if regime_match else -0.1
        
        confidence = base_confidence + strength_bonus + regime_bonus
        return np.clip(confidence, 0.0, 1.0)
    
    def _notify_callbacks(self, signal: TradingSignal):
        """通知所有回调函数"""
        for callback in self._callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Error in signal callback: {e}")
    
    def get_latest_signal(self, symbol: str) -> Optional[TradingSignal]:
        """获取最新信号"""
        history = self._signal_history.get(symbol, [])
        return history[-1] if history else None
    
    def get_signal_history(self, symbol: str, n: int = 100) -> List[TradingSignal]:
        """获取信号历史"""
        history = self._signal_history.get(symbol, [])
        return history[-n:] if n < len(history) else history
    
    def get_signal_stats(self, symbol: str) -> Dict:
        """获取信号统计"""
        history = self._signal_history.get(symbol, [])
        
        if not history:
            return {
                'total_signals': 0,
                'long_signals': 0,
                'short_signals': 0,
                'avg_confidence': 0.0,
                'regime_match_rate': 0.0
            }
        
        total = len(history)
        long_count = sum(1 for s in history if s.direction == SignalDirection.LONG)
        short_count = sum(1 for s in history if s.direction == SignalDirection.SHORT)
        avg_confidence = np.mean([s.confidence for s in history])
        regime_match_rate = sum(1 for s in history if s.regime_match) / total
        
        return {
            'total_signals': total,
            'long_signals': long_count,
            'short_signals': short_count,
            'avg_confidence': avg_confidence,
            'regime_match_rate': regime_match_rate
        }
    
    def reset(self, symbol: Optional[str] = None):
        """重置生成器状态"""
        if symbol:
            self._signal_history.pop(symbol, None)
            self._factor_history.pop(symbol, None)
            logger.info(f"Reset signal generator for {symbol}")
        else:
            self._signal_history.clear()
            self._factor_history.clear()
            logger.info("Reset all signal generator states")


# 全局信号生成器实例
_signal_generator: Optional[SignalGenerator] = None


def get_signal_generator(config: Optional[SignalConfig] = None) -> SignalGenerator:
    """获取全局信号生成器实例（单例模式）"""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = SignalGenerator(config)
    return _signal_generator
