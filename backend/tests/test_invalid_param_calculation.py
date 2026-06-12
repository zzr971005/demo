"""测试无效参数的实际计算结果"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import GPNode, GPIndividual
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
import pandas as pd
import numpy as np

print("=== 测试无效参数的实际计算结果 ===")

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

# 测试不同的无效参数
test_cases = [
    ("ts_max(open, -2.5052)", -2.5052),
    ("ts_max(open, -0.4186)", -0.4186),
    ("ts_max(open, 0.4186)", 0.4186),
    ("ts_max(open, 20)", 20),
]

print("\n测试不同参数的计算结果:")
for formula, param_value in test_cases:
    root = GPNode(
        node_type='func',
        name='ts_max',
        children=[
            GPNode(node_type='var', name='open', value=None),
            GPNode(node_type='const', name='const', value=param_value)
        ]
    )
    individual = GPIndividual(root=root, generation=0)
    
    print(f"\n公式: {formula}")
    print(f"参数值: {param_value}")
    
    # 编译
    factor_func = evaluator.compiler.compile(individual)
    print(f"编译成功: {factor_func is not None}")
    
    if factor_func:
        try:
            factor_values = factor_func(data)
            print(f"因子计算成功")
            print(f"因子值统计: mean={np.nanmean(factor_values):.4f}, std={np.nanstd(factor_values):.4f}")
            print(f"因子值示例（前5个）: {factor_values[:5]}")
            
            # 检查是否所有值都相同
            unique_values = np.unique(factor_values[~np.isnan(factor_values)])
            print(f"唯一值数量: {len(unique_values)}")
        except Exception as e:
            print(f"因子计算失败: {e}")

print("\n=== 测试完成 ===")
