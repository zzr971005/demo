"""测试公式解析和编译"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
from quant_engine.factors.formula_dsl import parse_expression
import pandas as pd
import numpy as np

print("=== 测试公式解析和编译 ===")

# 创建测试数据
data = pd.DataFrame({
    'open': np.random.randn(1000).cumsum() + 100,
    'high': np.random.randn(1000).cumsum() + 102,
    'low': np.random.randn(1000).cumsum() + 98,
    'close': np.random.randn(1000).cumsum() + 100,
    'volume': np.random.randint(1000, 10000, 1000),
})

# 创建评估器
config = FitnessConfig()
evaluator = FitnessEvaluator(config)

# 测试不同格式的公式
test_formulas = [
    "ts_max(open, 20)",  # 正常
    "ts_max(open, -2.5052)",  # 负数浮点
    "ts_max(open, 0.4186)",  # 正数浮点
    "bb_position(close, 20, 1.42)",  # 浮点参数（合法）
]

print("\n测试公式解析:")
for formula in test_formulas:
    print(f"\n公式: {formula}")
    try:
        parsed = parse_expression(formula)
        print(f"  解析成功: {parsed}")
        print(f"  解析类型: {type(parsed)}")
    except Exception as e:
        print(f"  解析失败: {e}")

print("\n=== 测试完成 ===")
