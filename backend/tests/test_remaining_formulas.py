"""测试剩余的公式是否产生不同结果"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试剩余的公式是否产生不同结果 ===")

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

# 测试数据库中剩余的几个公式
formulas = [
    "(volume - close)",
    "(ts_max(high, 20) - close)",
    "high",
    "close",
    "(open - close)",
    "(high - close)",
    "(high - low)",
]

results = []
for i, formula in enumerate(formulas):
    if formula == "(volume - close)":
        node = GPNode(
            node_type='binop',
            name='-',
            children=[
                GPNode(node_type='var', name='volume'),
                GPNode(node_type='var', name='close')
            ]
        )
    elif formula == "(ts_max(high, 20) - close)":
        node = GPNode(
            node_type='binop',
            name='-',
            children=[
                GPNode(
                    node_type='func',
                    name='ts_max',
                    children=[
                        GPNode(node_type='var', name='high'),
                        GPNode(node_type='const', name='const', value=20)
                    ]
                ),
                GPNode(node_type='var', name='close')
            ]
        )
    elif formula == "high":
        node = GPNode(node_type='var', name='high')
    elif formula == "close":
        node = GPNode(node_type='var', name='close')
    elif formula == "(open - close)":
        node = GPNode(
            node_type='binop',
            name='-',
            children=[
                GPNode(node_type='var', name='open'),
                GPNode(node_type='var', name='close')
            ]
        )
    elif formula == "(high - close)":
        node = GPNode(
            node_type='binop',
            name='-',
            children=[
                GPNode(node_type='var', name='high'),
                GPNode(node_type='var', name='close')
            ]
        )
    elif formula == "(high - low)":
        node = GPNode(
            node_type='binop',
            name='-',
            children=[
                GPNode(node_type='var', name='high'),
                GPNode(node_type='var', name='low')
            ]
        )

    ind = GPIndividual(root=node, id=f"test_{i}", generation=0)
    result = evaluator.evaluate(ind, data, symbol="TEST")
    results.append((formula, result))
    print(f"{formula}: valid={result.valid}, sharpe={result.sharpe:.4f}, total_return={result.total_return:.4f}, total_trades={result.total_trades}")

# 检查结果是否相同
print("\n=== 结果差异分析 ===")
for i, (formula1, result1) in enumerate(results):
    for j, (formula2, result2) in enumerate(results):
        if i < j and result1.valid and result2.valid:
            sharpe_same = abs(result1.sharpe - result2.sharpe) < 0.001
            return_same = abs(result1.total_return - result2.total_return) < 0.001
            trades_same = result1.total_trades == result2.total_trades

            if sharpe_same and return_same and trades_same:
                print(f"❌ {formula1} 和 {formula2} 结果相同")
            else:
                print(f"✅ {formula1} 和 {formula2} 结果不同")

print("\n=== 测试完成 ===")
