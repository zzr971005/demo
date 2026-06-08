"""测试garman_klass_vol函数的输出"""
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

# 测试garman_klass_vol的不同参数组合
test_cases = [
    ("high, low, close, open", data['high'], data['low'], data['close'], data['open']),
    ("high, low, close, close", data['high'], data['low'], data['close'], data['close']),
    ("high, low, open, open", data['high'], data['low'], data['open'], data['open']),
    ("high, high, open, open", data['high'], data['high'], data['open'], data['open']),
    ("close, close, close, close", data['close'], data['close'], data['close'], data['close']),
    ("high, low, low, open", data['high'], data['low'], data['low'], data['open']),
]

print("\n=== garman_klass_vol 不同参数组合测试 ===")
for name, h, l, c, o in test_cases:
    result = FACTOR_REGISTRY.get('garman_klass_vol').func(h, l, c, o, 20)
    valid = result[np.isfinite(result)]
    print(f"\n参数: {name}")
    print(f"  输出统计: min={valid.min():.6f}, max={valid.max():.6f}, mean={valid.mean():.6f}, std={valid.std():.6f}")
    print(f"  前10个值: {result[:10]}")

# 测试不同窗口大小
print(f"\n=== garman_klass_vol 不同窗口大小测试 ===")
for window in [5, 10, 20, 60]:
    result = FACTOR_REGISTRY.get('garman_klass_vol').func(data['high'], data['low'], data['close'], data['open'], window)
    valid = result[np.isfinite(result)]
    print(f"窗口={window}: min={valid.min():.6f}, max={valid.max():.6f}, mean={valid.mean():.6f}, std={valid.std():.6f}")
