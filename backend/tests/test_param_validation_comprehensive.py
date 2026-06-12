"""系统性测试参数验证流程"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import GPIndividual, GPNode, random_individual
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
import pandas as pd
import numpy as np

print("=== 系统性测试参数验证流程 ===")

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

print("\n=== 测试1: 验证参数验证是否被调用 ===")

# 创建一个包含浮点数参数的个体
# ts_max(open, -2.5052) - window参数为负数浮点
root = GPNode(
    node_type='func',
    name='ts_max',
    children=[
        GPNode(node_type='var', name='open', value=None),
        GPNode(node_type='const', name='const', value=-2.5052)
    ]
)
individual = GPIndividual(root=root, generation=0, origin='test')

print(f"测试个体表达式: {individual.to_expression()}")
print(f"window参数值: {individual.root.children[1].value}")
print(f"window参数类型: {type(individual.root.children[1].value)}")

# 直接调用参数验证
validation_result = evaluator._validate_parameter_types(individual)
print(f"参数验证结果: {validation_result}")

# 评估个体
result = evaluator.evaluate(individual, data, "RB")
print(f"评估结果 valid: {result.valid}")
print(f"评估结果 error_message: {result.error_message}")

print("\n=== 测试2: 验证编译流程 ===")

# 测试编译
factor_func = evaluator.compiler.compile(individual)
print(f"编译结果: {factor_func is not None}")

if factor_func:
    try:
        factor_values = factor_func(data)
        print(f"因子计算成功，结果长度: {len(factor_values)}")
        print(f"因子值示例（前5个）: {factor_values[:5]}")
    except Exception as e:
        print(f"因子计算失败: {e}")

print("\n=== 测试3: 验证正常参数 ===")

# 创建一个包含正常整数参数的个体
root2 = GPNode(
    node_type='func',
    name='ts_max',
    children=[
        GPNode(node_type='var', name='open', value=None),
        GPNode(node_type='const', name='const', value=20)
    ]
)
individual2 = GPIndividual(root=root2, generation=0, origin='test')

print(f"测试个体表达式: {individual2.to_expression()}")
print(f"window参数值: {individual2.root.children[1].value}")
print(f"window参数类型: {type(individual2.root.children[1].value)}")

validation_result2 = evaluator._validate_parameter_types(individual2)
print(f"参数验证结果: {validation_result2}")

result2 = evaluator.evaluate(individual2, data, "RB")
print(f"评估结果 valid: {result2.valid}")
print(f"评估结果 sharpe: {result2.sharpe if result2.valid else 'N/A'}")

print("\n=== 测试4: 验证随机个体生成 ===")

# 生成10个随机个体
print("生成10个随机个体:")
for i in range(10):
    rand_ind = random_individual(max_depth=3, generation=0)
    expr = rand_ind.to_expression()
    print(f"  个体{i+1}: {expr}")
    
    # 检查是否包含浮点数参数
    import re
    float_matches = re.findall(r'-?\d+\.\d+', expr)
    if float_matches:
        print(f"    警告: 包含浮点数参数: {float_matches}")

print("\n=== 测试完成 ===")
