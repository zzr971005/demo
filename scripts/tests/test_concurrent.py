"""测试并发评估是否会导致结果混乱"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试: 并发评估 ===")

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

# 创建两个个体：一个返回有效因子，一个返回NaN
# 个体1：有效的常量因子
valid_node = GPNode(node_type='const', name='const', value=1.0)
ind_valid = GPIndividual(root=valid_node, id="valid_001", generation=0)

# 个体2：NaN因子
nan_node = GPNode(node_type='const', name='const', value=float('nan'))
ind_nan = GPIndividual(root=nan_node, id="nan_001", generation=0)

individuals = [ind_valid, ind_nan]

# 创建单个共享的evaluator
evaluator = FitnessEvaluator()

print("顺序评估:")
for ind in individuals:
    result = evaluator.evaluate(ind, data, symbol="TEST")
    print(f"  {ind.id}: valid={result.valid}, sharpe={result.sharpe:.4f}, return={result.total_return:.4f}")

print("\n并发评估（使用ThreadPool）:")
# 重置个体状态
ind_valid.fitness = {}
ind_valid.metrics = {}
ind_nan.fitness = {}
ind_nan.metrics = {}

# 重新创建evaluator
evaluator2 = FitnessEvaluator()

def eval_ind(args):
    ind, data, symbol = args
    result = evaluator2.evaluate(ind, data, symbol)
    return (ind.id, result)

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(eval_ind, (ind, data, "TEST")) for ind in individuals]
    for future in futures:
        ind_id, result = future.result()
        print(f"  {ind_id}: valid={result.valid}, sharpe={result.sharpe:.4f}, return={result.total_return:.4f}")

print("\n=== 测试完成 ===")
