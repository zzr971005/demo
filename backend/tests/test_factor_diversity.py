"""直接测试因子值的多样性"""
import sys
sys.path.insert(0, '.')

from quant_engine.data.unified_hub import DataHub
from quant_engine.factors.registry import FACTOR_REGISTRY
import pandas as pd
import numpy as np

# 加载数据
hub = DataHub()
data = hub.get_ohlcv('RB', '1h')
print(f"数据形状: {data.shape}")
print(f"数据列: {list(data.columns)}")
print(f"数据类型:\n{data.dtypes}")
print(f"前5行:\n{data.head()}")
print(f"是否有NaN: {data.isna().any().any()}")

# 填充NaN值
data = data.fillna(0)
print(f"填充NaN后，是否有NaN: {data.isna().any().any()}")

# 测试几个不同的因子调用
test_cases = [
    ("vwap_ratio(close, volume, 30)", FACTOR_REGISTRY.get('vwap_ratio')),
    ("money_flow(low, low, low, volume, 20)", FACTOR_REGISTRY.get('money_flow')),
    ("money_flow(low, low, close, volume, 20)", FACTOR_REGISTRY.get('money_flow')),
    ("ts_corr(close, volume, 30)", FACTOR_REGISTRY.get('ts_corr')),
]

factor_values = []
for name, func_meta in test_cases:
    if func_meta is None:
        print(f"{name}: 函数未找到")
        continue
    print(f"\n测试: {name}")
    try:
        # 提取参数
        import re
        params = re.findall(r'\w+', name)
        # 调用函数
        if name.startswith('vwap_ratio'):
            values = func_meta.func(data['close'], data['volume'], 30)
        elif name.startswith('money_flow'):
            if 'close' in name:
                values = func_meta.func(data['low'], data['low'], data['close'], data['volume'], 20)
            else:
                values = func_meta.func(data['low'], data['low'], data['low'], data['volume'], 20)
        elif name.startswith('ts_corr'):
            values = func_meta.func(data['close'], data['volume'], 30)
        else:
            print(f"  未知的函数类型")
            continue

        # 跳过NaN值
        valid_values = values[~np.isnan(values)]
        if len(valid_values) == 0:
            print(f"  全部为NaN")
            continue
            
        print(f"  因子值统计: min={valid_values.min():.6f}, max={valid_values.max():.6f}, mean={valid_values.mean():.6f}, std={valid_values.std():.6f}")
        print(f"  前5个有效值: {valid_values[:5]}")
        print(f"  NaN数量: {np.isnan(values).sum()}")
        factor_values.append((name, values))
    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()

# 比较因子值
print("\n=== 比较因子值 ===")
for i, (name1, values1) in enumerate(factor_values):
    for j, (name2, values2) in enumerate(factor_values[i+1:], i+1):
        # 只比较两个数组都有有效值的位置
        valid_mask = ~np.isnan(values1) & ~np.isnan(values2)
        if valid_mask.sum() == 0:
            print(f"{name1} vs {name2}: 没有共同的有效值")
            continue

        diff = np.abs(values1[valid_mask] - values2[valid_mask])
        max_diff = diff.max()
        mean_diff = diff.mean()
        print(f"{name1} vs {name2}: 最大差异={max_diff:.6f}, 平均差异={mean_diff:.6f}, 共同有效值数={valid_mask.sum()}")
        if max_diff < 1e-6:
            print(f"  *** 警告: 这两个因子产生几乎相同的值 ***")
