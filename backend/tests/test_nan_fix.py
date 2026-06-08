"""测试全NaN因子检查修复"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试全NaN因子检查修复 ===")

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

# 测试1: 全NaN因子（应该被拒绝）
print("\n测试1: 全NaN因子")
nan_node = GPNode(node_type='const', name='const', value=float('nan'))
ind_nan = GPIndividual(root=nan_node, id="test_nan", generation=0)
result_nan = evaluator.evaluate(ind_nan, data, symbol="TEST")
print(f"结果: valid={result_nan.valid}, error_message={result_nan.error_message}")

# 测试2: 正常因子（应该通过）
print("\n测试2: 正常因子")
normal_node = GPNode(
    node_type='binop',
    name='-',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='var', name='open'),
    ]
)
ind_normal = GPIndividual(root=normal_node, id="test_normal", generation=0)
result_normal = evaluator.evaluate(ind_normal, data, symbol="TEST")
print(f"结果: valid={result_normal.valid}, sharpe={result_normal.sharpe:.4f}")

# 测试3: 预热期NaN因子（应该填充并通过）
print("\n测试3: 预热期NaN因子")
warmup_node = GPNode(
    node_type='func',
    name='ts_mean',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=20),
    ]
)
ind_warmup = GPIndividual(root=warmup_node, id="test_warmup", generation=0)
result_warmup = evaluator.evaluate(ind_warmup, data, symbol="TEST")
print(f"结果: valid={result_warmup.valid}, sharpe={result_warmup.sharpe:.4f}")

# 测试4: 过长预热期NaN（应该被拒绝）
print("\n测试4: 过长预热期NaN因子")
long_warmup_node = GPNode(
    node_type='func',
    name='ts_mean',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=80),
    ]
)
ind_long = GPIndividual(root=long_warmup_node, id="test_long", generation=0)
result_long = evaluator.evaluate(ind_long, data, symbol="TEST")
print(f"结果: valid={result_long.valid}, error_message={result_long.error_message}")

print("\n=== 测试完成 ===")
