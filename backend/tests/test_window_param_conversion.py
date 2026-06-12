"""测试window参数转换问题"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import numpy as np
from quant_engine.factors.registry import ts_mean

print("=== 测试window参数转换问题 ===")

# 创建测试数据
data = np.random.randn(100).cumsum() + 100

# 测试不同的window参数
windows = [6.0, 6.1, 6.2176, 6.5134, 6.9064, 7.0, 7.4119]

for w in windows:
    result = ts_mean(data, w)
    print(f"window={w} (int={int(w)}): 前5个值={result[:5]}")

print("\n=== 结论 ===")
print("所有6.x的参数都会被int()转换为6，产生相同结果")
print("所有7.x的参数都会被int()转换为7，产生相同结果")
