"""检查不同因子值是否产生不同的回测结果"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator
from quant_engine.validation.engine import VectorizedBacktestEngine

print("=== 检查不同因子值是否产生不同的回测结果 ===")

# 创建测试数据
np.random.seed(42)
n = 300
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

# 创建几个不同的因子
factor_cases = [
    ("close - open", data['close'] - data['open']),
    ("close - high", data['close'] - data['high']),
    ("close - low", data['close'] - data['low']),
]

# 回测参数
backtest_params = {
    "upper_threshold": 0.5,
    "lower_threshold": -0.5,
    "direction_mode": 0,
    "max_holding_bars": 0,
    "position_size_pct": 0.95,
    "contract_value_per_lot": 50000,
    "contract_multiplier": 10.0,
    "slippage_ticks": 1,
    "margin_rate": 0.12,
}

# 执行回测
backtest_engine = VectorizedBacktestEngine()
results = {}

for name, factor_values in factor_cases:
    factor_values = np.asarray(factor_values, dtype=np.float64)
    result = backtest_engine.run(
        factor=factor_values,
        open_px=data['open'].values,
        high_px=data['high'].values,
        low_px=data['low'].values,
        close_px=data['close'].values,
        params=backtest_params
    )
    results[name] = result
    print(f"\n{name}:")
    print(f"  sharpe: {result.sharpe:.4f}")
    print(f"  total_return: {result.total_return:.4f}")
    print(f"  total_trades: {result.total_trades}")
    print(f"  win_rate: {result.win_rate:.4f}")
    print(f"  max_drawdown: {result.max_drawdown:.4f}")

# 检查回测结果是否相同
print("\n=== 回测结果差异分析 ===")
names = list(results.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        name1, name2 = names[i], names[j]
        result1 = results[name1]
        result2 = results[name2]
        
        sharpe_same = abs(result1.sharpe - result2.sharpe) < 0.001
        return_same = abs(result1.total_return - result2.total_return) < 0.001
        trades_same = result1.total_trades == result2.total_trades
        
        if sharpe_same and return_same and trades_same:
            print(f"❌ {name1} 和 {name2} 回测结果完全相同")
        else:
            print(f"✅ {name1} 和 {name2} 回测结果不同")
            print(f"   sharpe差异: {abs(result1.sharpe - result2.sharpe):.4f}")
            print(f"   return差异: {abs(result1.total_return - result2.total_return):.4f}")
            print(f"   trades差异: {result1.total_trades - result2.total_trades}")

print("\n=== 检查完成 ===")
