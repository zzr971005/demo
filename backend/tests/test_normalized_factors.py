"""测试标准化后的因子值是否相似"""
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
    "(vwap_ratio(close, volume, 30) - money_flow(low, volume, low, volume, 20))",
]

from quant_engine.ops.gp_individual import GPIndividual
from quant_engine.ops.gp_fitness import FactorCompiler

compiler = FactorCompiler(data_columns=list(data.columns))

normalized_factors = []
for i, formula in enumerate(formulas):
    print(f"\n公式 {i+1}: {formula}")
    try:
        # 创建简单的GPIndividual（这里需要手动构建）
        # 由于from_expression不存在，我们直接测试因子函数
        # 先提取公式中的主要部分
        if 'vwap_ratio' in formula:
            factor_func = FACTOR_REGISTRY.get('vwap_ratio').func
            raw_values = factor_func(data['close'], data['volume'], 30)
        elif 'ts_corr' in formula:
            factor_func = FACTOR_REGISTRY.get('ts_corr').func
            raw_values = factor_func(data['close'], data['volume'], 30)
        else:
            print(f"  跳过")
            continue

        # 标准化
        normalized = evaluator._normalize_factor(raw_values)

        # 统计
        valid_normalized = normalized[~np.isnan(normalized)]
        print(f"  标准化后统计: min={valid_normalized.min():.6f}, max={valid_normalized.max():.6f}, mean={valid_normalized.mean():.6f}, std={valid_normalized.std():.6f}")
        print(f"  超过0.5的数量: {(normalized > 0.5).sum()}")
        print(f"  低于-0.5的数量: {(normalized < -0.5).sum()}")
        print(f"  在[-0.5, 0.5]之间的数量: {((normalized >= -0.5) & (normalized <= 0.5)).sum()}")

        normalized_factors.append((formula, normalized))
    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()

# 比较标准化因子值
print("\n=== 比较标准化因子值 ===")
for i, (name1, values1) in enumerate(normalized_factors):
    for j, (name2, values2) in enumerate(normalized_factors[i+1:], i+1):
        valid_mask = ~np.isnan(values1) & ~np.isnan(values2)
        if valid_mask.sum() == 0:
            print(f"{name1} vs {name2}: 没有共同的有效值")
            continue

        diff = np.abs(values1[valid_mask] - values2[valid_mask])
        max_diff = diff.max()
        mean_diff = diff.mean()
        print(f"{name1} vs {name2}: 最大差异={max_diff:.6f}, 平均差异={mean_diff:.6f}")
        if max_diff < 0.1:
            print(f"  *** 警告: 标准化后的因子值非常相似 ***")
