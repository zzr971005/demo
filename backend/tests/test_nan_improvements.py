"""测试NaN填充改进的效果"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试: NaN填充改进效果 ===")

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

# 测试1: 滚动窗口预热期NaN（ts_mean, window=20）
print("\n测试1: 滚动窗口预热期NaN填充")
node1 = GPNode(
    node_type='func',
    name='ts_mean',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=20),
    ]
)
ind1 = GPIndividual(root=node1, id="test_warmup", generation=0)
print(f"表达式: {ind1.to_expression()}")

evaluator = FitnessEvaluator()
result1 = evaluator.evaluate(ind1, data, symbol="TEST")
print(f"结果: valid={result1.valid}, sharpe={result1.sharpe:.4f}")
print(f"错误信息: {result1.error_message}")

# 测试2: 正常因子（无NaN）
print("\n测试2: 正常因子（无NaN）")
node2 = GPNode(
    node_type='binop',
    name='-',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='var', name='open'),
    ]
)
ind2 = GPIndividual(root=node2, id="test_normal", generation=0)
print(f"表达式: {ind2.to_expression()}")

result2 = evaluator.evaluate(ind2, data, symbol="TEST")
print(f"结果: valid={result2.valid}, sharpe={result2.sharpe:.4f}")
print(f"错误信息: {result2.error_message}")

# 测试3: 高NaN比例因子（应被拒绝）
print("\n测试3: 高NaN比例因子（应被拒绝）")
# 创建一个只有20%有效值的因子
node3 = GPNode(
    node_type='func',
    name='ts_mean',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=80),  # 大窗口
    ]
)
ind3 = GPIndividual(root=node3, id="test_high_nan", generation=0)
print(f"表达式: {ind3.to_expression()}")

result3 = evaluator.evaluate(ind3, data, symbol="TEST")
print(f"结果: valid={result3.valid}, sharpe={result3.sharpe:.4f}")
print(f"错误信息: {result3.error_message}")

# 测试4: 手动验证LOCF填充逻辑
print("\n测试4: 手动验证LOCF填充逻辑")
test_array = np.array([np.nan, np.nan, np.nan, 1.5, 2.0, 2.5, 3.0])
nan_mask = np.isnan(test_array)
first_valid_idx = np.where(~nan_mask)[0]
if len(first_valid_idx) > 0:
    warmup_end = first_valid_idx[0]
    first_valid_value = test_array[warmup_end]
    test_array[:warmup_end] = first_valid_value
    print(f"原始数组: [nan, nan, nan, 1.5, 2.0, 2.5, 3.0]")
    print(f"填充后数组: {test_array}")
    print(f"预热期长度: {warmup_end}, 填充值: {first_valid_value}")

print("\n=== 测试完成 ===")
