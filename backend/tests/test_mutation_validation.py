"""测试变异操作后的参数验证"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import random_individual
from quant_engine.ops.gp_operators import point_mutation, mutate
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
import pandas as pd
import numpy as np

print("=== 测试变异操作后的参数验证 ===")

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

print("\n=== 测试1: 随机个体变异 ===")

# 生成一个随机个体
ind = random_individual(max_depth=3, generation=0)
print(f"原始个体: {ind.to_expression()}")

# 验证原始个体
validation_original = evaluator._validate_parameter_types(ind)
print(f"原始参数验证: {validation_original}")

# 进行点变异
mutated = point_mutation(ind, mutation_rate=1.0)
print(f"变异后个体: {mutated.to_expression()}")

# 验证变异后个体
validation_mutated = evaluator._validate_parameter_types(mutated)
print(f"变异后参数验证: {validation_mutated}")

print("\n=== 测试2: 多次变异 ===")

# 创建一个正常个体
from quant_engine.ops.gp_individual import GPNode, GPIndividual
root = GPNode(
    node_type='func',
    name='ts_max',
    children=[
        GPNode(node_type='var', name='open', value=None),
        GPNode(node_type='const', name='const', value=20)
    ]
)
ind = GPIndividual(root=root, generation=0)
print(f"初始个体: {ind.to_expression()}")

# 进行10次变异
for i in range(10):
    mutated = point_mutation(ind, mutation_rate=1.0)
    validation = evaluator._validate_parameter_types(mutated)
    print(f"变异{i+1}: {mutated.to_expression()}, 验证: {validation}")
    ind = mutated

print("\n=== 测试3: 综合变异 ===")

# 生成一个随机个体
ind = random_individual(max_depth=3, generation=0)
print(f"原始个体: {ind.to_expression()}")

# 进行综合变异
mutated = mutate(ind, mutation_rate=1.0, subtree_rate=0.4, point_rate=0.3)
print(f"变异后个体: {mutated.to_expression()}")

validation_mutated = evaluator._validate_parameter_types(mutated)
print(f"变异后参数验证: {validation_mutated}")

print("\n=== 测试完成 ===")
