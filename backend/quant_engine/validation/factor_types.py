"""期货因子分类配置

基于学术研究，定义不同类型的期货因子及其持仓特性
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class FactorType(Enum):
    """因子类型枚举"""
    MOMENTUM = "momentum"          # 动量因子
    REVERSAL = "reversal"          # 反转因子
    TREND = "trend"               # 趋势因子
    MEAN_REVERSION = "mean_reversion"  # 均值回归因子
    VOLATILITY = "volatility"      # 波动率因子
    VOLUME = "volume"             # 成交量因子
    SEASONAL = "seasonal"          # 季节性因子
    CROSS_SECTIONAL = "cross_sectional"  # 截面因子


class DirectionBias(Enum):
    """方向性偏向"""
    LONG_ONLY = "long_only"       # 仅做多
    SHORT_ONLY = "short_only"     # 仅做空
    LONG_SHORT = "long_short"     # 多空双向
    MARKET_NEUTRAL = "market_neutral"  # 市场中性


@dataclass
class FactorConfig:
    """因子配置"""
    factor_type: FactorType
    direction_bias: DirectionBias
    holding_period_hours: int     # 推荐持仓时间（小时）
    description: str
    typical_performance: str      # 典型表现特征


# 基于豆包专家建议的1H因子配置
FACTOR_CONFIGS: Dict[FactorType, FactorConfig] = {
    FactorType.MOMENTUM: FactorConfig(
        factor_type=FactorType.MOMENTUM,
        direction_bias=DirectionBias.LONG_SHORT,
        holding_period_hours=8,    # 8小时，趋势类因子：4-12小时
        description="时间序列动量因子，基于过去收益预测未来收益",
        typical_performance="1H尺度：4-12小时趋势持续性"
    ),
    
    FactorType.REVERSAL: FactorConfig(
        factor_type=FactorType.REVERSAL,
        direction_bias=DirectionBias.LONG_SHORT,
        holding_period_hours=3,    # 3小时，反转类因子：2-4小时
        description="短期反转因子，基于过度反应预测价格回调",
        typical_performance="1H尺度：2-4小时快速反转"
    ),
    
    FactorType.TREND: FactorConfig(
        factor_type=FactorType.TREND,
        direction_bias=DirectionBias.LONG_SHORT,
        holding_period_hours=12,   # 12小时，趋势跟踪因子：8-24小时
        description="趋势跟踪因子，基于价格趋势方向",
        typical_performance="1H尺度：8-24小时趋势持续性"
    ),
    
    FactorType.MEAN_REVERSION: FactorConfig(
        factor_type=FactorType.MEAN_REVERSION,
        direction_bias=DirectionBias.LONG_SHORT,
        holding_period_hours=3,    # 3小时，均值回归因子：2-4小时
        description="均值回归因子，基于价格偏离均值的回归",
        typical_performance="1H尺度：2-4小时快速回归"
    ),
    
    FactorType.VOLATILITY: FactorConfig(
        factor_type=FactorType.VOLATILITY,
        direction_bias=DirectionBias.MARKET_NEUTRAL,
        holding_period_hours=3,    # 3小时，波动率因子：2-4小时
        description="波动率因子，基于波动率预测收益",
        typical_performance="1H尺度：2-4小时波动率效应"
    ),
    
    FactorType.VOLUME: FactorConfig(
        factor_type=FactorType.VOLUME,
        direction_bias=DirectionBias.LONG_SHORT,
        holding_period_hours=4,    # 4小时，量价因子：2-6小时
        description="成交量因子，基于成交量变化预测价格",
        typical_performance="1H尺度：2-6小时量价关系"
    ),
    
    FactorType.SEASONAL: FactorConfig(
        factor_type=FactorType.SEASONAL,
        direction_bias=DirectionBias.LONG_SHORT,
        holding_period_hours=16,   # 16小时，日内季节性因子：8-24小时
        description="日内季节性因子，基于交易时段模式",
        typical_performance="1H尺度：8-24小时季节性效应"
    ),
    
    FactorType.CROSS_SECTIONAL: FactorConfig(
        factor_type=FactorType.CROSS_SECTIONAL,
        direction_bias=DirectionBias.MARKET_NEUTRAL,
        holding_period_hours=8,    # 8小时，截面因子：4-12小时
        description="截面因子，基于品种间相对强弱",
        typical_performance="1H尺度：4-12小时品种轮动效应"
    ),
}


def get_factor_config(factor_type: FactorType) -> FactorConfig:
    """获取因子配置"""
    return FACTOR_CONFIGS.get(factor_type, FACTOR_CONFIGS[FactorType.MOMENTUM])


def get_holding_period_for_factor(factor_type: FactorType) -> int:
    """获取因子推荐持仓时间（小时）"""
    config = get_factor_config(factor_type)
    return config.holding_period_hours


def get_direction_bias_for_factor(factor_type: FactorType) -> DirectionBias:
    """获取因子方向性偏向"""
    config = get_factor_config(factor_type)
    return config.direction_bias


def validate_factor_signal(
    factor_value: float,
    factor_type: FactorType,
    upper_threshold: float = 0.5,
    lower_threshold: float = -0.5
) -> int:
    """
    根据因子类型和方向性偏向验证交易信号
    
    Returns:
        1: 做多信号
        -1: 做空信号
        0: 无信号
    """
    config = get_factor_config(factor_type)
    
    if config.direction_bias == DirectionBias.LONG_ONLY:
        # 仅做多
        return 1 if factor_value > upper_threshold else 0
    elif config.direction_bias == DirectionBias.SHORT_ONLY:
        # 仅做空
        return -1 if factor_value < lower_threshold else 0
    elif config.direction_bias == DirectionBias.LONG_SHORT:
        # 多空双向
        if factor_value > upper_threshold:
            return 1
        elif factor_value < lower_threshold:
            return -1
        else:
            return 0
    elif config.direction_bias == DirectionBias.MARKET_NEUTRAL:
        # 市场中性，需要配对交易
        # 这里简化处理，实际需要构建多空组合
        if abs(factor_value) > upper_threshold:
            return 1 if factor_value > 0 else -1
        else:
            return 0
    
    return 0


# 基于研究的最优持仓时间配置
OPTIMAL_HOLDING_PERIODS = {
    "ultra_short": 24,      # 1天，超高频
    "short": 72,            # 3天，短期
    "medium": 168,          # 1周，中期
    "long": 720,            # 1个月，长期
    "very_long": 2160,      # 3个月，超长期
}


def get_optimal_holding_period(period_type: str) -> int:
    """获取最优持仓时间"""
    return OPTIMAL_HOLDING_PERIODS.get(period_type, 720)  # 默认1个月
