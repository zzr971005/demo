"""测试oi_trend函数的参数问题"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试oi_trend函数的参数问题 ===")

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

# 测试1: 正常参数
print("\n测试1: 正常参数 (window=5)")
node1 = GPNode(
    node_type='func',
    name='oi_trend',
    children=[
        GPNode(node_type='var', name='open_interest'),
        GPNode(node_type='const', name='const', value=5),
    ]
)
ind1 = GPIndividual(root=node1, id="test_normal", generation=0)
result1 = evaluator.evaluate(ind1, data, symbol="TEST")
print(f"结果: valid={result1.valid}, sharpe={result1.sharpe:.4f}, error={result1.error_message}")

# 测试2: window为浮点数
print("\n测试2: window为浮点数 (window=6.1282)")
node2 = GPNode(
    node_type='func',
    name='oi_trend',
    children=[
        GPNode(node_type='var', name='open_interest'),
        GPNode(node_type='const', name='const', value=6.1282),
    ]
)
ind2 = GPIndividual(root=node2, id="test_float", generation=0)
result2 = evaluator.evaluate(ind2, data, symbol="TEST")
print(f"结果: valid={result2.valid}, sharpe={result2.sharpe:.4f}, error={result2.error_message}")

# 测试3: window为负浮点数
print("\n测试3: window为负浮点数 (window=-3.2645)")
node3 = GPNode(
    node_type='func',
    name='oi_trend',
    children=[
        GPNode(node_type='var', name='open_interest'),
        GPNode(node_type='const', name='const', value=-3.2645),
    ]
)
ind3 = GPIndividual(root=node3, id="test_neg_float", generation=0)
result3 = evaluator.evaluate(ind3, data, symbol="TEST")
print(f"结果: valid={result3.valid}, sharpe={result3.sharpe:.4f}, error={result3.error_message}")

print("\n=== 测试完成 ===")
