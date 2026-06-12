"""测试回测引擎的独立性"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.validation.engine import VectorizedBacktestEngine, BacktestResult

print("=== 测试: 回测引擎独立性 ===")

# 创建测试数据
np.random.seed(42)
n = 100
open_px = np.random.randn(n) + 100
high_px = np.random.randn(n) + 101
low_px = np.random.randn(n) + 99
close_px = np.random.randn(n) + 100

# 创建两个不同的因子
factor1 = np.random.randn(n)  # 随机因子1
factor2 = np.random.randn(n) * 2  # 随机因子2（不同）

print(f"因子1前5个值: {factor1[:5]}")
print(f"因子2前5个值: {factor2[:5]}")
print(f"因子1和因子2是否相同: {np.allclose(factor1, factor2)}")

# 创建回测引擎
engine = VectorizedBacktestEngine()

# 执行两个回测
params = {
    'upper_threshold': 0.5,
    'lower_threshold': -0.5,
    'direction_mode': 0,
    'max_holding_bars': 0,
    'position_size_pct': 0.95,
    'contract_value_per_lot': 50000,
    'tick_size': 1.0,
    'slippage_ticks': 1,
    'use_margin': True,
    'margin_rate': 0.12,
}

print("\n执行回测1...")
result1 = engine.run(factor1, open_px, high_px, low_px, close_px, params, symbol="TEST")
print(f"  Sharpe: {result1.sharpe:.4f}, Return: {result1.total_return:.4f}")
print(f"  Trades: {result1.total_trades}")
print(f"  结果对象ID: {id(result1)}")

print("\n执行回测2...")
result2 = engine.run(factor2, open_px, high_px, low_px, close_px, params, symbol="TEST")
print(f"  Sharpe: {result2.sharpe:.4f}, Return: {result2.total_return:.4f}")
print(f"  Trades: {result2.total_trades}")
print(f"  结果对象ID: {id(result2)}")

# 检查结果是否独立
print(f"\n结果对象是否相同: {result1 is result2}")
print(f"Sharpe是否相同: {result1.sharpe == result2.sharpe}")

if result1.sharpe == result2.sharpe:
    print("⚠ 警告: 两个不同因子产生相同Sharpe！")
else:
    print("✓ 不同因子产生不同Sharpe")

# 测试多次调用同一引擎
print("\n=== 测试多次调用 ===")
results = []
for i in range(3):
    factor = np.random.randn(n) * (i + 1)
    result = engine.run(factor, open_px, high_px, low_px, close_px, params, symbol="TEST")
    results.append(result)
    print(f"  调用{i+1}: Sharpe={result.sharpe:.4f}, ID={id(result)}")

# 检查是否有重复结果
sharpes = [r.sharpe for r in results]
if len(set(sharpes)) < len(sharpes):
    print("⚠ 有重复结果！")
else:
    print("✓ 所有结果各不相同")

# 检查BacktestResult对象的独立性
print("\n=== 检查BacktestResult对象 ===")
print(f"result1.equity_curve ID: {id(result1.equity_curve)}")
print(f"result2.equity_curve ID: {id(result2.equity_curve)}")
print(f"equity_curve是否共享: {result1.equity_curve is result2.equity_curve}")

print("\n=== 测试完成 ===")
