"""测试种子加载时的参数验证"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
from quant_engine.ops.gp_individual import create_individual_from_expr
import pandas as pd
import numpy as np

print("=== 测试种子加载时的参数验证 ===")

# 创建测试数据
data = pd.DataFrame({
    'open': np.random.randn(1000).cumsum() + 100,
    'high': np.random.randn(1000).cumsum() + 102,
    'low': np.random.randn(1000).cumsum() + 98,
    'close': np.random.randn(1000).cumsum() + 100,
    'volume': np.random.randint(1000, 10000, 1000),
})

# 创建评估器
config = FitnessConfig()
evaluator = FitnessEvaluator(config)

# 测试从数据库中看到的无效公式
invalid_formulas = [
    "ts_max(open, -2.5052)",
    "ts_max(open, -0.4186)",
    "(trend_strength(close, 60) - ts_max(open, -0.4186))",
    "(ts_max(open, -2.5052) - ts_max(open, 8.1712))",
]

print("\n测试无效公式:")
for formula in invalid_formulas:
    try:
        individual = create_individual_from_expr(formula, generation=0)
        print(f"\n公式: {formula}")
        print(f"  解析成功: {individual is not None}")
        
        if individual:
            validation_result = evaluator._validate_parameter_types(individual)
            print(f"  参数验证: {validation_result}")
            
            result = evaluator.evaluate(individual, data, "RB")
            print(f"  评估结果 valid: {result.valid}")
            print(f"  评估结果 sharpe: {result.sharpe if result.valid else 'N/A'}")
    except Exception as e:
        print(f"\n公式: {formula}")
        print(f"  解析失败: {e}")

print("\n=== 测试完成 ===")
