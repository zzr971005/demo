"""统一的多空信号配置模块

确保在整个流程中多空信号生成的一致性
"""

from dataclasses import dataclass
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TradingSignalConfig:
    """交易信号配置"""
    upper_threshold: float = 0.5      # 做多阈值
    lower_threshold: float = -0.5     # 做空阈值
    direction_mode: int = 0           # 0=双向, 1=只多, -1=只空
    
    def __post_init__(self):
        """参数验证"""
        if self.upper_threshold <= self.lower_threshold:
            raise ValueError("upper_threshold must be greater than lower_threshold")
        
        if self.direction_mode not in [0, 1, -1]:
            raise ValueError("direction_mode must be 0 (both), 1 (long only), or -1 (short only)")
    
    def generate_signal(self, factor_value: float) -> int:
        """生成交易信号
        
        Args:
            factor_value: 因子值
            
        Returns:
            1: 做多信号
            -1: 做空信号
            0: 无信号
        """
        if factor_value > self.upper_threshold:
            signal = 1
        elif factor_value < self.lower_threshold:
            signal = -1
        else:
            signal = 0
        
        # 方向模式过滤
        if self.direction_mode == 1 and signal < 0:
            return 0  # 只多模式，过滤做空信号
        elif self.direction_mode == -1 and signal > 0:
            return 0  # 只空模式，过滤做多信号
        
        return signal
    
    def validate_signal_consistency(self, factor_value: float, signal: int) -> bool:
        """验证信号生成的一致性
        
        Args:
            factor_value: 因子值
            signal: 生成的信号
            
        Returns:
            bool: 信号是否一致
        """
        expected_signal = self.generate_signal(factor_value)
        return signal == expected_signal
    
    def get_signal_description(self, signal: int) -> str:
        """获取信号描述"""
        if signal > 0:
            return "做多"
        elif signal < 0:
            return "做空"
        else:
            return "无信号"
    
    def log_signal_details(self, factor_value: float, signal: int, 
                          timestamp: Optional[datetime] = None):
        """记录信号详情用于调试"""
        if timestamp is None:
            timestamp = datetime.now()
        
        logger.info(f"信号生成: {timestamp}, 因子值={factor_value:.4f}, "
                   f"阈值=[{self.lower_threshold}, {self.upper_threshold}], "
                   f"信号={signal}, 方向={self.get_signal_description(signal)}")
    
    def get_trading_direction(self, signal: int) -> str:
        """获取交易方向
        
        Args:
            signal: 交易信号
            
        Returns:
            "BUY" 或 "SELL"
        """
        if signal > 0:
            return "BUY"
        elif signal < 0:
            return "SELL"
        else:
            return None
    
    def get_close_direction(self, position: int) -> str:
        """获取平仓方向
        
        Args:
            position: 当前持仓 (1=多, -1=空)
            
        Returns:
            "SELL" (平多) 或 "BUY" (平空)
        """
        if position > 0:
            return "SELL"
        elif position < 0:
            return "BUY"
        else:
            return None
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "upper_threshold": self.upper_threshold,
            "lower_threshold": self.lower_threshold,
            "direction_mode": self.direction_mode,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TradingSignalConfig':
        """从字典创建配置"""
        return cls(
            upper_threshold=data.get("upper_threshold", 0.5),
            lower_threshold=data.get("lower_threshold", -0.5),
            direction_mode=data.get("direction_mode", 0),
        )
    
    @classmethod
    def from_params(cls, params: dict) -> 'TradingSignalConfig':
        """从参数字典创建配置"""
        return cls(
            upper_threshold=params.get("upper_threshold", 0.5),
            lower_threshold=params.get("lower_threshold", -0.5),
            direction_mode=params.get("direction_mode", 0),
        )


class SignalValidator:
    """信号验证器"""
    
    def __init__(self, config: TradingSignalConfig):
        self.config = config
        self.validation_errors = []
    
    def validate_batch_signals(self, factor_values: list, signals: list) -> bool:
        """批量验证信号一致性
        
        Args:
            factor_values: 因子值列表
            signals: 信号列表
            
        Returns:
            bool: 所有信号是否一致
        """
        self.validation_errors.clear()
        
        if len(factor_values) != len(signals):
            self.validation_errors.append("因子值和信号数量不匹配")
            return False
        
        all_consistent = True
        for i, (factor_val, signal) in enumerate(zip(factor_values, signals)):
            if not self.config.validate_signal_consistency(factor_val, signal):
                self.validation_errors.append(
                    f"索引{i}: 因子值={factor_val:.4f}, 信号={signal}, "
                    f"期望信号={self.config.generate_signal(factor_val)}"
                )
                all_consistent = False
        
        return all_consistent
    
    def get_validation_report(self) -> str:
        """获取验证报告"""
        if not self.validation_errors:
            return "所有信号验证通过"
        
        report = f"发现 {len(self.validation_errors)} 个错误:\n"
        for error in self.validation_errors:
            report += f"- {error}\n"
        
        return report


# 默认配置实例
DEFAULT_SIGNAL_CONFIG = TradingSignalConfig()


def get_signal_config(params: Optional[dict] = None) -> TradingSignalConfig:
    """获取信号配置实例"""
    if params is None:
        return DEFAULT_SIGNAL_CONFIG
    
    return TradingSignalConfig.from_params(params)


def generate_signals_batch(config: TradingSignalConfig, factor_values: list) -> list:
    """批量生成信号"""
    return [config.generate_signal(fv) for fv in factor_values]


def validate_strategy_consistency(strategy_params: dict, 
                                 historical_factor_values: list,
                                 historical_signals: list) -> bool:
    """验证策略一致性
    
    Args:
        strategy_params: 策略参数
        historical_factor_values: 历史因子值
        historical_signals: 历史信号
        
    Returns:
        bool: 策略是否一致
    """
    config = TradingSignalConfig.from_params(strategy_params)
    validator = SignalValidator(config)
    
    is_consistent = validator.validate_batch_signals(
        historical_factor_values, 
        historical_signals
    )
    
    if not is_consistent:
        logger.error(f"策略一致性验证失败:\n{validator.get_validation_report()}")
    
    return is_consistent
