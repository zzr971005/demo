"""检查保存逻辑是否有共享状态问题"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 检查保存逻辑是否有共享状态问题 ===")

# 创建测试数据
np.random.seed(42)
n = 100
data = pd.DataFrame({
    'open': np.random.randn(n) + 100,
    'high': np.random.randn(n) + 101,
    'low': np.random.randn(n) + 99,
    'close': np.random.randn(n) + 100,
    'volume': np.random.randint(1000, 10000, n),
    'open_interest': np.random.randint(1000, 10000, n),
    'near_close': np.random.randn(n) + 100,
    'far_close': np.random.randn(n) + 100,
    'days_to_expiry': np.random.randint(1, 30, n),
})

evaluator = FitnessEvaluator()

# 创建多个不同的个体
individuals = []
formulas = [
    "close - open",
    "close - high",
    "close - low",
    "high - low",
    "(close + open) / 2",
]

for i, formula in enumerate(formulas):
    if formula == "close - open":
        node = GPNode(node_type='binop', name='-', children=[
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='open')
        ])
    elif formula == "close - high":
        node = GPNode(node_type='binop', name='-', children=[
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='high')
        ])
    elif formula == "close - low":
        node = GPNode(node_type='binop', name='-', children=[
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='low')
        ])
    elif formula == "high - low":
        node = GPNode(node_type='binop', name='-', children=[
            GPNode(node_type='var', name='high'),
            GPNode(node_type='var', name='low')
        ])
    elif formula == "(close + open) / 2":
        node = GPNode(node_type='binop', name='/', children=[
            GPNode(node_type='binop', name='+', children=[
                GPNode(node_type='var', name='close'),
                GPNode(node_type='var', name='open')
            ]),
            GPNode(node_type='const', name='const', value=2)
        ])

    ind = GPIndividual(root=node, id=f"test_{i}", generation=0)
    individuals.append((formula, ind))

# 评估所有个体
results = []
for formula, ind in individuals:
    result = evaluator.evaluate(ind, data, symbol="TEST")
    results.append((formula, ind, result))
    print(f"{formula}: sharpe={result.sharpe:.4f}, total_return={result.total_return:.4f}, total_trades={result.total_trades}")

# 检查个体的fitness和metrics是否独立
print("\n=== 检查fitness和metrics独立性 ===")
for i, (formula1, ind1, result1) in enumerate(results):
    for j, (formula2, ind2, result2) in enumerate(results):
        if i < j:
            fitness_same = ind1.fitness is ind2.fitness
            metrics_same = ind1.metrics is ind2.metrics
            print(f"{formula1} vs {formula2}: fitness共享={fitness_same}, metrics共享={metrics_same}")

# 检查fitness和metrics的值是否相同
print("\n=== 检查fitness和metrics值 ===")
for formula, ind, result in results:
    print(f"{formula}:")
    print(f"  fitness id: {id(ind.fitness)}, sharpe={ind.fitness.get('sharpe', 0):.4f}")
    print(f"  metrics id: {id(ind.metrics)}, total_return={ind.metrics.get('total_return', 0):.4f}")

print("\n=== 检查完成 ===")
