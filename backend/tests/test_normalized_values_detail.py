"""详细检查标准化后的因子值序列"""
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

# 创建适应度评估器
evaluator = FitnessEvaluator()

# 计算各个组成部分
vwap = FACTOR_REGISTRY.get('vwap_ratio').func(data['close'], data['volume'], 30)
money_flow1 = FACTOR_REGISTRY.get('money_flow').func(data['low'], data['low'], data['low'], data['volume'], 20)
money_flow2 = FACTOR_REGISTRY.get('money_flow').func(data['low'], data['low'], data['close'], data['volume'], 20)
ts_corr = FACTOR_REGISTRY.get('ts_corr').func(data['close'], data['volume'], 30)

# 计算复合公式
formula1 = vwap - money_flow1
formula2 = ts_corr - money_flow2

# 标准化
norm1 = evaluator._normalize_factor(formula1)
norm2 = evaluator._normalize_factor(formula2)

print("=== 标准化后的因子值对比 ===")
print(f"前20个值:")
for i in range(20):
    print(f"  {i}: norm1={norm1[i]:.6f}, norm2={norm2[i]:.6f}, diff={abs(norm1[i]-norm2[i]):.6f}")

print(f"\n后20个值:")
for i in range(-20, 0):
    print(f"  {3360+i}: norm1={norm1[i]:.6f}, norm2={norm2[i]:.6f}, diff={abs(norm1[i]-norm2[i]):.6f}")

# 检查是否完全相同
valid_mask = ~np.isnan(norm1) & ~np.isnan(norm2)
diff = np.abs(norm1[valid_mask] - norm2[valid_mask])
print(f"\n最大差异: {diff.max():.10f}")
print(f"平均差异: {diff.mean():.10f}")
print(f"差异<1e-6的数量: {(diff < 1e-6).sum()}/{len(diff)}")
print(f"差异<1e-10的数量: {(diff < 1e-10).sum()}/{len(diff)}")

# 检查原始因子值
print(f"\n=== 原始因子值对比 ===")
print(f"formula1统计: min={formula1.min():.6f}, max={formula1.max():.6f}, mean={formula1.mean():.6f}, std={formula1.std():.6f}")
print(f"formula2统计: min={formula2.min():.6f}, max={formula2.max():.6f}, mean={formula2.mean():.6f}, std={formula2.std():.6f}")

# 检查money_flow的差异
print(f"\n=== money_flow差异 ===")
print(f"money_flow1统计: min={money_flow1.min():.6f}, max={money_flow1.max():.6f}, mean={money_flow1.mean():.6f}, std={money_flow1.std():.6f}")
print(f"money_flow2统计: min={money_flow2.min():.6f}, max={money_flow2.max():.6f}, mean={money_flow2.mean():.6f}, std={money_flow2.std():.6f}")
print(f"money_flow差异: max={np.abs(money_flow1 - money_flow2).max():.6f}, mean={np.abs(money_flow1 - money_flow2).mean():.6f}")
