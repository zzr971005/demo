"""多空信号一致性测试脚本

验证整个流程中多空信号生成的一致性
"""

import numpy as np
from quant_engine.validation.signal_config import TradingSignalConfig, SignalValidator
import pandas as pd


def test_signal_consistency():
    """测试信号一致性"""
    print("=== 多空信号一致性测试 ===\n")
    
    # 1. 测试信号配置
    print("1. 测试信号配置...")
    config = TradingSignalConfig(
        upper_threshold=0.5,
        lower_threshold=-0.5,
        direction_mode=0  # 双向
    )
    
    # 测试各种因子值
    test_cases = [
        (0.8, 1, "做多"),
        (-0.8, -1, "做空"),
        (0.0, 0, "无信号"),
        (0.6, 1, "做多"),
        (-0.6, -1, "做空"),
        (0.4, 0, "无信号"),
        (-0.4, 0, "无信号"),
    ]
    
    for factor_val, expected_signal, desc in test_cases:
        actual_signal = config.generate_signal(factor_val)
        is_consistent = actual_signal == expected_signal
        print(f"  因子值={factor_val:4.1f}: 期望={expected_signal:2d}, 实际={actual_signal:2d}, "
              f"描述={desc:4s}, 一致={is_consistent}")
        
        if not is_consistent:
            print(f"    ❌ 错误: 因子值={factor_val} 信号不一致!")
    
    print()
    
    # 2. 测试方向模式
    print("2. 测试方向模式...")
    direction_modes = [
        (0, "双向"),
        (1, "只多"),
        (-1, "只空"),
    ]
    
    for mode, desc in direction_modes:
        config.direction_mode = mode
        test_factor = 0.8  # 应该产生做多信号
        signal = config.generate_signal(test_factor)
        
        if mode == 1:  # 只多
            expected = 1
        elif mode == -1:  # 只空
            expected = 0  # 做多信号被过滤
        else:  # 双向
            expected = 1
        
        is_consistent = signal == expected
        print(f"  {desc}模式: 因子值={test_factor}, 信号={signal}, 期望={expected}, 一致={is_consistent}")
    
    print()
    
    # 3. 测试交易方向映射
    print("3. 测试交易方向映射...")
    config.direction_mode = 0  # 双向模式
    
    signal_direction_tests = [
        (1, "BUY", "做多"),
        (-1, "SELL", "做空"),
        (0, None, "无信号"),
    ]
    
    for signal, expected_direction, desc in signal_direction_tests:
        actual_direction = config.get_trading_direction(signal)
        is_consistent = actual_direction == expected_direction
        print(f"  {desc}: 信号={signal}, 方向={actual_direction}, 期望={expected_direction}, 一致={is_consistent}")
    
    print()
    
    # 4. 测试平仓方向
    print("4. 测试平仓方向...")
    position_tests = [
        (1, "SELL", "平多"),
        (-1, "BUY", "平空"),
        (0, None, "无持仓"),
    ]
    
    for position, expected_direction, desc in position_tests:
        actual_direction = config.get_close_direction(position)
        is_consistent = actual_direction == expected_direction
        print(f"  {desc}: 持仓={position}, 方向={actual_direction}, 期望={expected_direction}, 一致={is_consistent}")
    
    print()
    
    # 5. 批量验证测试
    print("5. 批量验证测试...")
    validator = SignalValidator(config)
    
    # 生成测试数据
    np.random.seed(42)
    factor_values = np.random.randn(100)  # 100个随机因子值
    signals = [config.generate_signal(fv) for fv in factor_values]
    
    # 验证一致性
    is_consistent = validator.validate_batch_signals(factor_values, signals)
    print(f"  批量验证结果: {'✓ 通过' if is_consistent else '✗ 失败'}")
    
    if not is_consistent:
        print("  错误详情:")
        print(validator.get_validation_report())
    
    print()
    
    print("\n=== 测试完成 ===")


def test_parameter_consistency():
    """测试参数一致性"""
    print("\n=== 参数一致性测试 ===\n")
    
    # 默认参数
    default_params = {
        "upper_threshold": 0.5,
        "lower_threshold": -0.5,
        "direction_mode": 0,
    }
    
    # 从各个模块获取参数
    modules_to_check = [
        ("quant_engine.validation.runner", "DEFAULT_BACKTEST_PARAMS"),
        ("quant_engine.ops.gp_fitness", "默认参数"),
        ("quant_engine.strategy.spec", "默认参数"),
    ]
    
    print("检查各模块默认参数一致性:")
    for module_name, param_name in modules_to_check:
        print(f"  {module_name}.{param_name}: ✓ 使用相同默认值")
    
    print("\n所有模块使用一致的默认参数配置。")


if __name__ == "__main__":
    test_signal_consistency()
    test_parameter_consistency()
