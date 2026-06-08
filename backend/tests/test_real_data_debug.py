"""测试真实数据下的因子值和回测"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import GPNode, GPIndividual
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
from quant_engine.data.unified_hub import DataHub
import pandas as pd
import numpy as np

print("=== 测试真实数据下的因子值和回测 ===")

# 加载真实数据
data_hub = DataHub()
data = data_hub.get_ohlcv(
    symbol="RB",
    start_date="2024-01-01",
    end_date="2024-12-31",
    frequency="1H"
)

# 添加期限结构所需的列
data['near_close'] = data['close']
data['far_close'] = data['close']
data['days_to_expiry'] = 30

print(f"加载数据: {len(data)} 条")
print(f"数据列: {list(data.columns)}")

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
