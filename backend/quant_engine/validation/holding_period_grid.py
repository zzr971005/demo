"""1小时K线因子持仓周期网格测试配置

基于豆包建议的持仓周期网格，用于系统性地测试不同持仓时间的效果
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np


@dataclass
class HoldingPeriodConfig:
    """持仓周期配置"""
    name: str                    # 配置名称
    bars: List[int]              # K线数量列表
    hours: List[float]           # 小时数列表
    description: str             # 描述
    factor_types: List[str]      # 适用的因子类型


class HoldingPeriodGrid:
    """持仓周期网格测试配置"""
    
    # 基于豆包建议的核心配置
    CORE_CONFIGS = {
        "极短线": HoldingPeriodConfig(
            name="极短线",
            bars=[1, 2],
            hours=[1.0, 2.0],
            description="1-2根1H K线，适用于高频交易因子",
            factor_types=["volume", "momentum", "reversal"]
        ),
        "短线匹配": HoldingPeriodConfig(
            name="短线匹配",
            bars=[2, 4, 6],
            hours=[2.0, 4.0, 6.0],
            description="2-6根1H K线，最常用的持仓周期",
            factor_types=["momentum", "reversal", "volume", "volatility"]
        ),
        "中短波段": HoldingPeriodConfig(
            name="中短波段",
            bars=[8, 12, 16, 24],
            hours=[8.0, 12.0, 16.0, 24.0],
            description="8-24根1H K线，适用于趋势类因子",
            factor_types=["momentum", "trend", "seasonal"]
        ),
    }
    
    # 因子类型专用配置
    FACTOR_SPECIFIC_CONFIGS = {
        "momentum": HoldingPeriodConfig(
            name="趋势类因子",
            bars=[4, 8, 12],
            hours=[4.0, 8.0, 12.0],
            description="趋势类因子：均线突破、MACD、动量等",
            factor_types=["momentum"]
        ),
        "reversal": HoldingPeriodConfig(
            name="反转类因子",
            bars=[2, 4],
            hours=[2.0, 4.0],
            description="反转类因子：乖离率、RSI超买超卖等",
            factor_types=["reversal"]
        ),
        "volume": HoldingPeriodConfig(
            name="量价类因子",
            bars=[2, 4, 6],
            hours=[2.0, 4.0, 6.0],
            description="量价类因子：成交量异常、资金流向等",
            factor_types=["volume"]
        ),
        "volatility": HoldingPeriodConfig(
            name="波动率类因子",
            bars=[2, 3, 4],
            hours=[2.0, 3.0, 4.0],
            description="波动率类因子：波动率极值、ATR等",
            factor_types=["volatility"]
        ),
    }
    
    @classmethod
    def get_all_configs(cls) -> Dict[str, HoldingPeriodConfig]:
        """获取所有配置"""
        configs = {}
        configs.update(cls.CORE_CONFIGS)
        configs.update(cls.FACTOR_SPECIFIC_CONFIGS)
        return configs
    
    @classmethod
    def get_core_configs(cls) -> Dict[str, HoldingPeriodConfig]:
        """获取核心配置"""
        return cls.CORE_CONFIGS
    
    @classmethod
    def get_factor_specific_config(cls, factor_type: str) -> HoldingPeriodConfig:
        """获取因子类型专用配置"""
        return cls.FACTOR_SPECIFIC_CONFIGS.get(factor_type, cls.CORE_CONFIGS["短线匹配"])
    
    @classmethod
    def generate_test_grid(cls) -> List[Tuple[str, int, float]]:
        """生成测试网格
        
        Returns:
            List of (config_name, bars, hours)
        """
        grid = []
        for config_name, config in cls.get_all_configs().items():
            for bars, hours in zip(config.bars, config.hours):
                grid.append((config_name, bars, hours))
        return grid
    
    @classmethod
    def get_recommended_bars(cls, factor_type: str = None) -> List[int]:
        """获取推荐的持仓K线数量"""
        if factor_type:
            config = cls.get_factor_specific_config(factor_type)
            return config.bars
        else:
            # 默认返回短线匹配配置
            return cls.CORE_CONFIGS["短线匹配"].bars
    
    @classmethod
    def validate_holding_period(cls, bars: int, factor_type: str = None) -> bool:
        """验证持仓周期是否合理"""
        if factor_type:
            config = cls.get_factor_specific_config(factor_type)
            return bars in config.bars
        
        # 检查是否在核心配置中
        for config in cls.CORE_CONFIGS.values():
            if bars in config.bars:
                return True
        return False


class GridTestRunner:
    """网格测试运行器"""
    
    def __init__(self, factor_type: str = None):
        self.factor_type = factor_type
        self.grid = HoldingPeriodGrid.generate_test_grid()
        self.results = {}
    
    def run_grid_test(self, factor_values: np.ndarray, price_data: np.ndarray) -> Dict:
        """运行网格测试
        
        Args:
            factor_values: 因子值数组
            price_data: 价格数据数组
            
        Returns:
            测试结果字典
        """
        from quant_engine.validation.engine import backtest_with_params
        
        results = {}
        
        for config_name, bars, hours in self.grid:
            # 跳过不适用于当前因子类型的配置
            if self.factor_type:
                config = HoldingPeriodGrid.get_factor_specific_config(self.factor_type)
                if self.factor_type not in config.factor_types:
                    continue
            
            # 运行回测
            try:
                result = backtest_with_params(
                    factor_values=factor_values,
                    price_data=price_data,
                    max_holding_bars=bars,
                    # 其他参数使用默认值
                )
                
                results[f"{config_name}_{bars}bars"] = {
                    "config_name": config_name,
                    "bars": bars,
                    "hours": hours,
                    "sharpe": result.get("sharpe", 0),
                    "total_return": result.get("total_return", 0),
                    "max_drawdown": result.get("max_drawdown", 0),
                    "win_rate": result.get("win_rate", 0),
                    "trade_count": result.get("trade_count", 0),
                }
                
            except Exception as e:
                print(f"测试失败 {config_name}_{bars}bars: {e}")
                results[f"{config_name}_{bars}bars"] = {
                    "config_name": config_name,
                    "bars": bars,
                    "hours": hours,
                    "error": str(e),
                }
        
        return results
    
    def get_best_config(self, results: Dict, metric: str = "sharpe") -> Tuple[str, Dict]:
        """获取最佳配置
        
        Args:
            results: 测试结果
            metric: 评估指标
            
        Returns:
            (配置名称, 结果数据)
        """
        best_config = None
        best_value = -np.inf
        
        for config_key, result in results.items():
            if "error" in result:
                continue
            
            value = result.get(metric, 0)
            if value > best_value:
                best_value = value
                best_config = config_key
        
        if best_config:
            return best_config, results[best_config]
        else:
            return None, {}


def backtest_with_params(factor_values, price_data, max_holding_bars, **params):
    """使用指定参数运行回测的简化函数"""
    # 这里应该调用实际的回测引擎
    # 为了演示，返回模拟结果
    return {
        "sharpe": np.random.randn(),
        "total_return": np.random.randn() * 0.2,
        "max_drawdown": abs(np.random.randn() * 0.1),
        "win_rate": np.random.rand(),
        "trade_count": np.random.randint(10, 100),
    }


# 使用示例
if __name__ == "__main__":
    # 创建网格测试运行器
    runner = GridTestRunner(factor_type="momentum")
    
    # 生成测试网格
    grid = HoldingPeriodGrid.generate_test_grid()
    print("持仓周期测试网格:")
    for config_name, bars, hours in grid:
        print(f"  {config_name}: {bars}根K线 = {hours}小时")
    
    # 获取推荐配置
    recommended = HoldingPeriodGrid.get_recommended_bars("momentum")
    print(f"\n趋势类因子推荐持仓: {recommended}根K线")
    
    # 验证持仓周期
    is_valid = HoldingPeriodGrid.validate_holding_period(4, "momentum")
    print(f"\n4小时持仓对趋势类因子是否合理: {is_valid}")
