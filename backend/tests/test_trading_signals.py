"""测试不同公式产生的交易信号是否相同"""
import sys
sys.path.insert(0, '.')

from quant_engine.data.unified_hub import DataHub
from quant_engine.factors.registry import FACTOR_REGISTRY
from quant_engine.ops.gp_fitness import FitnessEvaluator
import pandas as pd
import numpy as np

# 加载数据
hub = DataHub()
data = hub.get_ohlcv('RB', '1h')
print(f"数据形状: {data.shape}")

# 创建适应度评估器
evaluator = FitnessEvaluator()

# 测试几个不同的公式
formulas = [
    "(vwap_ratio(close, volume, 30) - money_flow(low, low, low, volume, 20))",
    "(ts_corr(close, volume, 30) - money_flow(low, low, close, volume, 20))",
    "(vwap_ratio(close, volume, 30) - open)",
    "volume",
]

# 由于无法直接解析表达式，我们手动计算这些公式
print("\n=== 手动计算复合公式 ===")

# 先计算各个组成部分
vwap = FACTOR_REGISTRY.get('vwap_ratio').func(data['close'], data['volume'], 30)
money_flow1 = FACTOR_REGISTRY.get('money_flow').func(data['low'], data['low'], data['low'], data['volume'], 20)
money_flow2 = FACTOR_REGISTRY.get('money_flow').func(data['low'], data['low'], data['close'], data['volume'], 20)
ts_corr = FACTOR_REGISTRY.get('ts_corr').func(data['close'], data['volume'], 30)

# 计算复合公式
formula_values = {
    "vwap - money_flow1": vwap - money_flow1,
    "ts_corr - money_flow2": ts_corr - money_flow2,
    "vwap - open": vwap - data['open'],
    "volume": data['volume'],
}

# 标准化每个公式
for name, values in formula_values.items():
    normalized = evaluator._normalize_factor(values)
    valid = normalized[~np.isnan(normalized)]
    print(f"\n{name}:")
    print(f"  标准化后: min={valid.min():.4f}, max={valid.max():.4f}, mean={valid.mean():.4f}, std={valid.std():.4f}")
    print(f"  超过0.5: {(normalized > 0.5).sum()}, 低于-0.5: {(normalized < -0.5).sum()}")

    # 生成交易信号
    upper_threshold = 0.5
    lower_threshold = -0.5
    signals = np.zeros_like(normalized)
    signals[normalized > upper_threshold] = 1
    signals[normalized < lower_threshold] = -1
    print(f"  信号分布: 多={np.sum(signals == 1)}, 空={np.sum(signals == -1)}, 平={np.sum(signals == 0)}")

# 比较信号
print("\n=== 比较交易信号 ===")
names = list(formula_values.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        name1, name2 = names[i], names[j]
        norm1 = evaluator._normalize_factor(formula_values[name1])
        norm2 = evaluator._normalize_factor(formula_values[name2])

        sig1 = np.zeros_like(norm1)
        sig1[norm1 > 0.5] = 1
        sig1[norm1 < -0.5] = -1

        sig2 = np.zeros_like(norm2)
        sig2[norm2 > 0.5] = 1
        sig2[norm2 < -0.5] = -1

        # 只比较有效位置
        valid_mask = ~np.isnan(norm1) & ~np.isnan(norm2)
        same_signals = np.sum(sig1[valid_mask] == sig2[valid_mask])
        total_valid = valid_mask.sum()
        print(f"{name1} vs {name2}: 相同信号={same_signals}/{total_valid} ({100*same_signals/total_valid:.1f}%)")
