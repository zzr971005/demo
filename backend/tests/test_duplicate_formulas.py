"""测试不同公式是否产生不同的因子值"""
import sys
sys.path.insert(0, '.')

from quant_engine.data.unified_hub import DataHub
from quant_engine.ops.gp_fitness import FactorCompiler
from quant_engine.ops.gp_individual import GPIndividual
from quant_engine.factors.registry import FACTOR_REGISTRY
import pandas as pd
import numpy as np

# 测试公式
formulas = [
    "(vwap_ratio(close, volume, 30) - money_flow(low, low, low, volume, 20))",
    "(ts_corr(close, volume, 30) - money_flow(low, low, close, volume, 20))",
    "(vwap_ratio(close, volume, 30) - open)",
    "(vwap_ratio(close, volume, 30) - money_flow(low, volume, low, volume, 20))",
    "(vwap_ratio(close, low, 30) - money_flow(low, low, low, volume, 20))",
    "(am_pm_gap(close, open) - money_flow(low, low, low, volume, 20))",
]

# 加载数据
hub = DataHub()
data = hub.get_ohlcv('RB', '1h')
print(f"数据形状: {data.shape}")
print(f"数据列: {list(data.columns)}")

# 创建编译器
compiler = FactorCompiler(data_columns=list(data.columns))

# 计算每个公式的因子值
factor_values = []
for i, formula in enumerate(formulas):
    print(f"\n公式 {i+1}: {formula}")
    try:
        # 从表达式创建GPIndividual
        individual = GPIndividual.from_expression(formula, FACTOR_REGISTRY)
        # 编译为因子函数
        factor_func = compiler.compile(individual)
        if factor_func is None:
            print(f"  编译失败")
            factor_values.append(None)
            continue
        values = factor_func(data)
        print(f"  因子值统计: min={values.min():.6f}, max={values.max():.6f}, mean={values.mean():.6f}, std={values.std():.6f}")
        print(f"  前5个值: {values[:5]}")
        print(f"  后5个值: {values[-5:]}")
        factor_values.append(values)
    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()
        factor_values.append(None)

# 比较因子值
print("\n=== 比较因子值 ===")
for i in range(len(factor_values)):
    for j in range(i+1, len(factor_values)):
        if factor_values[i] is not None and factor_values[j] is not None:
            diff = np.abs(factor_values[i] - factor_values[j])
            max_diff = diff.max()
            mean_diff = diff.mean()
            print(f"公式{i+1} vs 公式{j+1}: 最大差异={max_diff:.6f}, 平均差异={mean_diff:.6f}")
            if max_diff < 1e-10:
                print(f"  *** 警告: 这两个公式产生几乎相同的因子值 ***")
