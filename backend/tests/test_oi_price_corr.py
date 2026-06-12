"""测试oi_price_corr函数的输出特征"""
import sys
sys.path.insert(0, '.')

from quant_engine.data.unified_hub import DataHub
from quant_engine.factors.registry import FACTOR_REGISTRY
import numpy as np
import pandas as pd

# 加载数据
hub = DataHub()
data = hub.get_ohlcv('RB', '1h')
print(f"数据形状: {data.shape}")

# 检查是否有open_interest列
if 'open_interest' not in data.columns:
    print("数据中没有open_interest列，添加模拟数据")
    data['open_interest'] = np.random.randn(len(data)) * 1000 + 50000

# 测试oi_price_corr的不同参数组合
test_cases = [
    ("open_interest, low", data['open_interest'], data['low']),
    ("open_interest, close", data['open_interest'], data['close']),
    ("open_interest, open", data['open_interest'], data['open']),
    ("open_interest, volume", data['open_interest'], data['volume']),
    ("open, low", data['open'], data['low']),
    ("volume, low", data['volume'], data['low']),
]

print("\n=== oi_price_corr 不同参数组合测试 ===")
for name, oi, price in test_cases:
    result = FACTOR_REGISTRY.get('oi_price_corr').func(oi, price, 13)
    valid = result[np.isfinite(result)]
    print(f"\n参数: {name}")
    print(f"  输出统计: min={valid.min():.6f}, max={valid.max():.6f}, mean={valid.mean():.6f}, std={valid.std():.6f}")
    print(f"  前10个值: {result[:10]}")

# 测试不同窗口大小
print(f"\n=== oi_price_corr 不同窗口大小测试 ===")
for window in [5, 10, 13, 20, 60]:
    result = FACTOR_REGISTRY.get('oi_price_corr').func(data['open_interest'], data['close'], window)
    valid = result[np.isfinite(result)]
    print(f"窗口={window}: min={valid.min():.6f}, max={valid.max():.6f}, mean={valid.mean():.6f}, std={valid.std():.6f}")

# 测试相关性
print(f"\n=== 不同参数组合之间的相关性 ===")
results = {}
for name, oi, price in test_cases:
    results[name] = FACTOR_REGISTRY.get('oi_price_corr').func(oi, price, 13)

names = list(results.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        v1 = results[names[i]]
        v2 = results[names[j]]
        valid_mask = np.isfinite(v1) & np.isfinite(v2)
        if valid_mask.sum() > 0:
            corr = np.corrcoef(v1[valid_mask], v2[valid_mask])[0, 1]
            print(f"{names[i]} vs {names[j]}: {corr:.4f}")
