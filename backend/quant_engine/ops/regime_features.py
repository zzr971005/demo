"""
Regime特征计算模块
用于计算趋势强度、波动率等Regime识别所需的特征
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class RegimeType(Enum):
    """市场状态类型"""
    TREND_UP = "trend_up"      # 上升趋势
    TREND_DOWN = "trend_down"  # 下降趋势
    RANGE = "range"            # 震荡
    BREAKOUT = "breakout"      # 突破
    UNKNOWN = "unknown"        # 未知


@dataclass
class RegimeFeatures:
    """Regime特征数据类"""
    # 趋势特征
    adx: float                    # ADX趋势强度 (0-100)
    di_plus: float               # +DI
    di_minus: float              # -DI
    
    # 波动率特征
    atr: float                   # 真实波幅
    atr_percent: float           # ATR百分比
    volatility_regime: str       # 波动率状态: low/medium/high
    
    # 价格位置
    price_position: float        # 价格在通道中的位置 (0-1)
    distance_to_ma: float        # 距移动平均线的距离
    
    # 动量特征
    momentum: float              # 动量
    momentum_regime: str         # 动量状态
    
    # 综合Regime
    regime: RegimeType           # 识别的Regime
    regime_strength: float       # Regime强度 (0-1)
    
    # 原始数据
    timestamp: Optional[pd.Timestamp] = None
    symbol: Optional[str] = None


class RegimeFeatureCalculator:
    """Regime特征计算器"""
    
    def __init__(self, adx_period: int = 14, atr_period: int = 14, ma_period: int = 20):
        self.adx_period = adx_period
        self.atr_period = atr_period
        self.ma_period = ma_period
        
    def calculate_adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算ADX (Average Directional Index)
        返回: (adx, di_plus, di_minus)
        """
        n = self.adx_period
        
        # 计算TR (True Range)
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # 计算+DM和-DM
        plus_dm = high[1:] - high[:-1]
        minus_dm = low[:-1] - low[1:]
        
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
        
        # 平滑处理
        atr = self._smooth(tr, n)
        plus_di = 100 * self._smooth(plus_dm, n) / atr
        minus_di = 100 * self._smooth(minus_dm, n) / atr
        
        # 计算DX和ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = self._smooth(dx, n)
        
        # 对齐长度
        pad_length = len(close) - len(adx)
        adx = np.pad(adx, (pad_length, 0), mode='edge')
        plus_di = np.pad(plus_di, (pad_length, 0), mode='edge')
        minus_di = np.pad(minus_di, (pad_length, 0), mode='edge')
        
        return adx, plus_di, minus_di
    
    def calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """计算ATR (Average True Range)"""
        n = self.atr_period
        
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        atr = self._smooth(tr, n)
        
        # 对齐长度
        pad_length = len(close) - len(atr)
        atr = np.pad(atr, (pad_length, 0), mode='edge')
        
        return atr
    
    def calculate_bollinger_position(self, close: np.ndarray, period: int = 20) -> np.ndarray:
        """
        计算价格在布林带中的位置 (0-1)
        0 = 下轨, 0.5 = 中轨, 1 = 上轨
        """
        ma = pd.Series(close).rolling(window=period).mean().values
        std = pd.Series(close).rolling(window=period).std().values
        
        upper = ma + 2 * std
        lower = ma - 2 * std
        
        position = (close - lower) / (upper - lower + 1e-10)
        position = np.clip(position, 0, 1)
        
        return position
    
    def calculate_momentum(self, close: np.ndarray, period: int = 10) -> np.ndarray:
        """计算动量"""
        momentum = close / np.roll(close, period) - 1
        momentum[:period] = 0
        return momentum
    
    def _smooth(self, data: np.ndarray, period: int) -> np.ndarray:
        """平滑处理 (RMA)"""
        result = np.zeros_like(data)
        result[0] = data[0]
        
        alpha = 1.0 / period
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        
        return result
    
    def calculate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有Regime特征
        
        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        
        Returns:
            DataFrame with regime features added
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # 计算ADX
        adx, di_plus, di_minus = self.calculate_adx(high, low, close)
        df['adx'] = adx
        df['di_plus'] = di_plus
        df['di_minus'] = di_minus
        
        # 计算ATR
        atr = self.calculate_atr(high, low, close)
        df['atr'] = atr
        df['atr_percent'] = atr / close * 100
        
        # 计算波动率状态
        df['volatility_regime'] = self._classify_volatility(df['atr_percent'].values)
        
        # 计算价格位置
        df['price_position'] = self.calculate_bollinger_position(close)
        
        # 计算动量
        df['momentum'] = self.calculate_momentum(close)
        df['momentum_regime'] = self._classify_momentum(df['momentum'].values)
        
        # 计算Regime
        regimes, strengths = self._identify_regime(df)
        df['regime'] = regimes
        df['regime_strength'] = strengths
        
        return df
    
    def _classify_volatility(self, atr_percent: np.ndarray) -> np.ndarray:
        """分类波动率状态"""
        # 使用历史分位数
        low_threshold = np.percentile(atr_percent[~np.isnan(atr_percent)], 33)
        high_threshold = np.percentile(atr_percent[~np.isnan(atr_percent)], 67)
        
        regimes = np.where(atr_percent < low_threshold, 'low',
                  np.where(atr_percent > high_threshold, 'high', 'medium'))
        return regimes
    
    def _classify_momentum(self, momentum: np.ndarray) -> np.ndarray:
        """分类动量状态"""
        std = np.nanstd(momentum)
        threshold = std * 0.5
        
        regimes = np.where(momentum > threshold, 'strong_up',
                  np.where(momentum < -threshold, 'strong_down', 'neutral'))
        return regimes
    
    def _identify_regime(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        识别市场Regime
        返回: (regime_types, regime_strengths)
        """
        regimes = []
        strengths = []
        
        for i in range(len(df)):
            if i < self.adx_period:
                regimes.append(RegimeType.UNKNOWN.value)
                strengths.append(0.0)
                continue
            
            adx = df['adx'].iloc[i]
            di_plus = df['di_plus'].iloc[i]
            di_minus = df['di_minus'].iloc[i]
            momentum = df['momentum'].iloc[i]
            price_pos = df['price_position'].iloc[i]
            
            # 判断逻辑 - 降低阈值使其更灵敏
            if adx > 20:  # 趋势 (从25降低到20)
                if di_plus > di_minus:
                    regime = RegimeType.TREND_UP
                else:
                    regime = RegimeType.TREND_DOWN
                strength = min(adx / 40, 1.0)  # 从50降低到40
            elif adx < 15:  # 弱趋势 -> 震荡 (从20降低到15)
                regime = RegimeType.RANGE
                strength = 1.0 - adx / 20  # 从25降低到20
            else:  # 过渡状态 (ADX在15-20之间)
                # 检查是否有突破迹象 - 需要ADX支持且动量确认
                momentum_confirm = abs(momentum) > 0.005  # 动量确认
                if (price_pos > 0.92 or price_pos < 0.08) and adx > 18 and momentum_confirm:
                    regime = RegimeType.BREAKOUT
                    strength = abs(price_pos - 0.5) * 2
                else:
                    # 在过渡区，根据DI方向判断
                    if abs(di_plus - di_minus) > 10:
                        if di_plus > di_minus:
                            regime = RegimeType.TREND_UP
                        else:
                            regime = RegimeType.TREND_DOWN
                        strength = min(adx / 40, 0.7)
                    else:
                        regime = RegimeType.RANGE
                        strength = 0.5
            
            regimes.append(regime.value)
            strengths.append(strength)
        
        return np.array(regimes), np.array(strengths)
    
    def get_latest_features(self, df: pd.DataFrame) -> RegimeFeatures:
        """获取最新的Regime特征"""
        latest = df.iloc[-1]
        
        return RegimeFeatures(
            adx=float(latest['adx']),
            di_plus=float(latest['di_plus']),
            di_minus=float(latest['di_minus']),
            atr=float(latest['atr']),
            atr_percent=float(latest['atr_percent']),
            volatility_regime=str(latest['volatility_regime']),
            price_position=float(latest['price_position']),
            distance_to_ma=float(latest.get('distance_to_ma', 0)),
            momentum=float(latest['momentum']),
            momentum_regime=str(latest['momentum_regime']),
            regime=RegimeType(latest['regime']),
            regime_strength=float(latest['regime_strength']),
            timestamp=latest.name if isinstance(latest.name, pd.Timestamp) else None,
            symbol=latest.get('symbol', None)
        )
