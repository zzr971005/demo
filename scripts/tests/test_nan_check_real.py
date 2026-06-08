"""测试真实的NaN检查行为"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试: 真实NaN检查行为 ===")

# 创建一个有效的表达式和一个NaN表达式
# 有效表达式: close - open
valid_node = GPNode(
    node_type='binop',
    name='-',
    children=[
        GPNode(node_type='var', name='close'),
        GPNode(node_type='var', name='open'),
    ]
)
ind_valid = GPIndividual(root=valid_node, id="valid_expr", generation=0)

# NaN表达式: money_flow(high, 20, close, volume, 20) - 参数错位
# 注意：money_flow需要 (high, low, close, volume, window)，但我们传入 (high, 20, close, volume, 20)
# 第二个参数应该是low（变量），但传入了20（常量），这会导致错误
nan_node = GPNode(
    node_type='func',
    name='money_flow',
    children=[
        GPNode(node_type='var', name='high'),  # high - 正确
        GPNode(node_type='const', name='const', value=20),  # 应该是low，但传入了20 - 错误！
        GPNode(node_type='var', name='close'),  # close - 正确
        GPNode(node_type='var', name='volume'),  # volume - 正确
        GPNode(node_type='const', name='const', value=20),  # window - 正确
    ]
)
ind_nan = GPIndividual(root=nan_node, id="nan_expr", generation=0)

print(f"有效个体表达式: {ind_valid.to_expression()}")
print(f"NaN个体表达式: {ind_nan.to_expression()}")

# 创建测试数据
np.random.seed(42)
n = 300
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

# 评估
evaluator = FitnessEvaluator()

print("\n评估有效个体:")
result_valid = evaluator.evaluate(ind_valid, data, symbol="TEST")
print(f"  valid={result_valid.valid}, sharpe={result_valid.sharpe:.4f}, return={result_valid.total_return:.4f}")

print("\n评估NaN个体:")
result_nan = evaluator.evaluate(ind_nan, data, symbol="TEST")
print(f"  valid={result_nan.valid}, sharpe={result_nan.sharpe:.4f}, return={result_nan.total_return:.4f}")
print(f"  error_message={result_nan.error_message}")

# 打印NaN个体的因子值
print("\n手动计算NaN个体的因子值:")
from quant_engine.factors.registry import FACTOR_REGISTRY

# 获取函数
func_meta = FACTOR_REGISTRY.get('money_flow')
if func_meta:
    print(f"函数参数定义: {func_meta.params}")
    
    # 手动调用函数
    try:
        high = data['high'].values
        low_const = np.full(n, 20)  # 用常量20代替low
        close = data['close'].values
        volume = data['volume'].values
        window = 20
        
        result = func_meta.func(high, low_const, close, volume, window)
        print(f"函数返回: min={np.min(result):.4f}, max={np.max(result):.4f}, mean={np.mean(result):.4f}")
        print(f"是否全NaN: {np.all(np.isnan(result))}")
    except Exception as e:
        print(f"函数执行失败: {e}")

print("\n=== 测试完成 ===")
