"""检查不同公式是否产生不同的因子值"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator
from quant_engine.factors.registry import FACTOR_REGISTRY

print("=== 检查不同公式是否产生不同的因子值 ===")

# 创建测试数据
np.random.seed(42)
n = 100
data = pd.DataFrame({
    'open': np.random.randn(n) + 100,
    'high': np.random.randn(n) + 101,
    'low': np.random.randn(n) + 99,
    'close': np.random.randn(n) + 100,
    'volume': np.random.randint(1000, 10000, n),
    'open_interest': np.random.randint(1000, 10000, n),
    'near_close': np.random.randn(n) + 100,
    'far_close': np.random.randn(n) + 100,
    'days_to_expiry': np.random.randint(1, 30, n),
})

# 从数据库中提取的几个不同公式
formulas = [
    "(close - ts_volatility(open, 3.7079, close, close))",
    "(garman_klass_vol(high, low, open, low, 5) - ts_volatility(open, 3.7079, high, close))",
    "(garman_klass_vol(high, low, low, low, 5) - ts_volatility(low, 3.7079, garman_klass_vol(high, low, low, low, 5), close))",
    "ts_volatility(low, 3.7079, high, close)",
]

# 由于公式解析复杂，我们手动构建几个简单的因子来测试
print("\n测试1: 简单因子对比")
test_factors = [
    ("close - open", lambda data: data['close'] - data['open']),
    ("close - high", lambda data: data['close'] - data['high']),
    ("close - low", lambda data: data['close'] - data['low']),
]

factor_values = {}
for name, func in test_factors:
    values = func(data)
    factor_values[name] = values
    print(f"{name}: min={values.min():.4f}, max={values.max():.4f}, mean={values.mean():.4f}, std={values.std():.4f}")

# 检查因子值是否相同
print("\n=== 因子值差异分析 ===")
names = list(factor_values.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        name1, name2 = names[i], names[j]
        if np.allclose(factor_values[name1], factor_values[name2]):
            print(f"❌ {name1} 和 {name2} 因子值完全相同")
        else:
            diff = np.abs(factor_values[name1] - factor_values[name2]).max()
            print(f"✅ {name1} 和 {name2} 因子值不同 (最大差异: {diff:.4f})")

# 测试2: 使用GPIndividual计算因子值
print("\n测试2: 使用GPIndividual计算因子值")
evaluator = FitnessEvaluator()

# 创建几个不同的个体
individuals = []
expressions = [
    "close - open",
    "close - high", 
    "close - low",
]

for expr in expressions:
    # 简化：直接使用简单表达式
    if expr == "close - open":
        node = GPNode(node_type='binop', name='-', children=[
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='open')
        ])
    elif expr == "close - high":
        node = GPNode(node_type='binop', name='-', children=[
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='high')
        ])
    elif expr == "close - low":
        node = GPNode(node_type='binop', name='-', children=[
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='low')
        ])
    
    ind = GPIndividual(root=node, id=f"test_{expr}", generation=0)
    individuals.append((expr, ind))

# 计算因子值
gp_factor_values = {}
for expr, ind in individuals:
    try:
        # 编译因子
        func = evaluator.compiler.compile(ind)
        if func is None:
            print(f"❌ {expr} 编译失败")
            continue
        
        # 计算因子值
        values = func(data)
        values = np.asarray(values, dtype=np.float64)
        gp_factor_values[expr] = values
        print(f"{expr}: min={values.min():.4f}, max={values.max():.4f}, mean={values.mean():.4f}, std={values.std():.4f}")
    except Exception as e:
        print(f"❌ {expr} 计算失败: {e}")

# 检查GP因子值是否相同
print("\n=== GP因子值差异分析 ===")
gp_names = list(gp_factor_values.keys())
for i in range(len(gp_names)):
    for j in range(i+1, len(gp_names)):
        name1, name2 = gp_names[i], gp_names[j]
        if np.allclose(gp_factor_values[name1], gp_factor_values[name2]):
            print(f"❌ {name1} 和 {name2} GP因子值完全相同")
        else:
            diff = np.abs(gp_factor_values[name1] - gp_factor_values[name2]).max()
            print(f"✅ {name1} 和 {name2} GP因子值不同 (最大差异: {diff:.4f})")

print("\n=== 检查完成 ===")
