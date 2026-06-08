"""检查garman_klass_vol函数的不同参数是否产生不同结果"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.factors.registry import garman_klass_vol

print("=== 检查garman_klass_vol函数的不同参数 ===")

# 创建测试数据
np.random.seed(42)
n = 100
high = np.random.randn(n) + 101
low = np.random.randn(n) + 99
close = np.random.randn(n) + 100
open_ = np.random.randn(n) + 100

# 测试不同的window参数
test_cases = [
    ("window=20", 20),
    ("window=-2", -2),
    ("window=-0.2", -0.2),
    ("window=5", 5),
    ("window=10", 10),
]

results = {}
for name, window in test_cases:
    try:
        result = garman_klass_vol(high, low, close, open_, window)
        results[name] = result
        print(f"{name}: min={result.min():.4f}, max={result.max():.4f}, mean={result.mean():.4f}, std={result.std():.4f}, NaN数量={np.isnan(result).sum()}")
    except Exception as e:
        print(f"{name}: 错误 - {e}")

# 检查结果是否相同
print("\n=== 结果差异分析 ===")
names = list(results.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        name1, name2 = names[i], names[j]
        if np.allclose(results[name1], results[name2]):
            print(f"❌ {name1} 和 {name2} 结果完全相同")
        else:
            diff = np.abs(results[name1] - results[name2]).max()
            print(f"✅ {name1} 和 {name2} 结果不同 (最大差异: {diff:.4f})")

print("\n=== 检查完成 ===")
