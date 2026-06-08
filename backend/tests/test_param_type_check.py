"""测试参数类型检查是否仍然有效"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator
from quant_engine.factors.registry import FACTOR_REGISTRY

print("=== 测试参数类型检查 ===")

# 检查money_flow函数的参数定义
func_meta = FACTOR_REGISTRY.get('money_flow')
print(f"\nmoney_flow函数参数定义:")
for i, (param_name, param_type, param_default) in enumerate(func_meta.params):
    print(f"  参数{i}: {param_name}, 类型: {param_type}, 默认值: {param_default}")

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

# 测试1: 正确的money_flow调用
print("\n测试1: 正确的money_flow调用")
correct_node = GPNode(
    node_type='func',
    name='money_flow',
    children=[
        GPNode(node_type='var', name='high'),
        GPNode(node_type='var', name='low'),
        GPNode(node_type='var', name='close'),
        GPNode(node_type='var', name='volume'),
        GPNode(node_type='const', name='const', value=20),
    ]
)
ind_correct = GPIndividual(root=correct_node, id="test_correct", generation=0)
result_correct = evaluator.evaluate(ind_correct, data, symbol="TEST")
print(f"结果: valid={result_correct.valid}, sharpe={result_correct.sharpe:.4f}, error={result_correct.error_message}")

# 测试2: 错误的money_flow调用（参数类型错误）
print("\n测试2: 错误的money_flow调用（参数类型错误）")
wrong_node = GPNode(
    node_type='func',
    name='money_flow',
    children=[
        GPNode(node_type='var', name='high'),
        GPNode(node_type='const', name='const', value=20),  # 应该是low变量
        GPNode(node_type='var', name='close'),
        GPNode(node_type='var', name='volume'),
        GPNode(node_type='const', name='const', value=20),
    ]
)
ind_wrong = GPIndividual(root=wrong_node, id="test_wrong", generation=0)
result_wrong = evaluator.evaluate(ind_wrong, data, symbol="TEST")
print(f"结果: valid={result_wrong.valid}, sharpe={result_wrong.sharpe:.4f}, error={result_wrong.error_message}")

print("\n=== 测试完成 ===")
