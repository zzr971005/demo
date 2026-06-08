"""测试因子值唯一性和回测调试"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import GPNode, GPIndividual
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
import pandas as pd
import numpy as np

print("=== 测试因子值唯一性和回测调试 ===")

# 创建测试数据
data = pd.DataFrame({
    'open': np.random.randn(3360).cumsum() + 3000,
    'high': np.random.randn(3360).cumsum() + 3020,
    'low': np.random.randn(3360).cumsum() + 2980,
    'close': np.random.randn(3360).cumsum() + 3000,
    'volume': np.random.randint(10000, 200000, 3360),
})

# 创建评估器
config = FitnessConfig()
evaluator = FitnessEvaluator(config)

# 测试不同的公式
test_formulas = [
    ("ts_max(open, 20)", GPNode(
        node_type='func',
        name='ts_max',
        children=[
            GPNode(node_type='var', name='open', value=None),
            GPNode(node_type='const', name='const', value=20)
        ]
    )),
    ("ts_max(open, 30)", GPNode(
        node_type='func',
        name='ts_max',
        children=[
            GPNode(node_type='var', name='open', value=None),
            GPNode(node_type='const', name='const', value=30)
        ]
    )),
    ("close - open", GPNode(
        node_type='binop',
        name='-',
        children=[
            GPNode(node_type='var', name='close', value=None),
            GPNode(node_type='var', name='open', value=None)
        ]
    )),
]

print("\n测试不同公式的因子值和回测结果:")
for formula_name, root in test_formulas:
    individual = GPIndividual(root=root, generation=0)
    print(f"\n{'='*60}")
    print(f"公式: {formula_name}")
    print(f"{'='*60}")
    
    result = evaluator.evaluate(individual, data, "RB")
    print(f"回测结果 valid: {result.valid}")
    if result.valid:
        print(f"Sharpe: {result.sharpe:.4f}")
        print(f"Calmar: {result.calmar:.4f}")
        print(f"Max Drawdown: {result.max_drawdown:.4f}")
        print(f"Total Return: {result.total_return:.4f}")
        print(f"Total Trades: {result.total_trades}")
        print(f"Win Rate: {result.win_rate:.4f}")

print("\n=== 测试完成 ===")
