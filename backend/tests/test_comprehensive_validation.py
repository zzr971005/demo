"""全面测试因子验证逻辑"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 全面测试因子验证逻辑 ===")

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

# 测试用例
test_cases = [
    # (名称, 节点, 预期结果)
    ("正常因子", GPNode(node_type='binop', name='-', children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='var', name='open')
    ]), True),

    ("全NaN因子", GPNode(node_type='const', name='const', value=float('nan')), False),

    ("参数类型错误", GPNode(node_type='func', name='money_flow', children=[
        GPNode(node_type='var', name='high'),
        GPNode(node_type='const', name='const', value=20),  # 应该是var
        GPNode(node_type='var', name='close'),
        GPNode(node_type='var', name='volume'),
        GPNode(node_type='const', name='const', value=20),
    ]), False),

    ("window=0", GPNode(node_type='func', name='ts_mean', children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=0),
    ]), False),

    ("window=-1", GPNode(node_type='func', name='ts_mean', children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=-1),
    ]), False),

    ("window=101", GPNode(node_type='func', name='ts_mean', children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=101),
    ]), False),

    ("window=20", GPNode(node_type='func', name='ts_mean', children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=20),
    ]), True),

    ("window=5", GPNode(node_type='func', name='ts_mean', children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=5),
    ]), True),
]

print("\n测试结果:")
passed = 0
failed = 0
for name, node, expected_valid in test_cases:
    ind = GPIndividual(root=node, id=f"test_{name}", generation=0)
    result = evaluator.evaluate(ind, data, symbol="TEST")
    actual_valid = result.valid

    if actual_valid == expected_valid:
        print(f"✅ {name}: valid={actual_valid} (预期: {expected_valid})")
        passed += 1
    else:
        print(f"❌ {name}: valid={actual_valid} (预期: {expected_valid}), error={result.error_message}")
        failed += 1

print(f"\n总计: {passed} 通过, {failed} 失败")

# 测试预热期NaN
print("\n=== 预热期NaN测试 ===")
warmup_tests = [
    ("window=20", 20, True),
    ("window=30", 30, True),
    ("window=31", 31, False),  # 超过最大填充长度
    ("window=50", 50, False),
]

for name, window, expected_valid in warmup_tests:
    node = GPNode(node_type='func', name='ts_mean', children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='const', name='const', value=window),
    ])
    ind = GPIndividual(root=node, id=f"test_{name}", generation=0)
    result = evaluator.evaluate(ind, data, symbol="TEST")
    actual_valid = result.valid

    if actual_valid == expected_valid:
        print(f"✅ {name}: valid={actual_valid} (预期: {expected_valid})")
    else:
        print(f"❌ {name}: valid={actual_valid} (预期: {expected_valid}), error={result.error_message}")

print("\n=== 测试完成 ===")
