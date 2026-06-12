"""测试全NaN因子时的回测结果"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试: 全NaN因子的回测结果 ===")

# 创建一个返回NaN的个体（无效表达式）
# 创建一个常量节点，值为NaN
nan_node = GPNode(node_type='const', name='const', value=float('nan'))
individual = GPIndividual(root=nan_node, id="test_nan", generation=0)

print(f"个体表达式: {individual.to_expression()}")
print(f"个体根节点类型: {individual.root.node_type}")

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

# 评估个体
evaluator = FitnessEvaluator()
result = evaluator.evaluate(individual, data, symbol="TEST")

print(f"\n评估结果:")
print(f"  valid: {result.valid}")
print(f"  error_message: {result.error_message}")
print(f"  sharpe: {result.sharpe}")
print(f"  total_return: {result.total_return}")
print(f"  total_trades: {result.total_trades}")

# 检查个体fitness
print(f"\n个体fitness: {individual.fitness}")
print(f"  individual.fitness.get('sharpe'): {individual.fitness.get('sharpe')}")

# 创建另一个返回NaN的个体
nan_node2 = GPNode(node_type='const', name='const', value=float('nan'))
individual2 = GPIndividual(root=nan_node2, id="test_nan_2", generation=0)

result2 = evaluator.evaluate(individual2, data, symbol="TEST")

print(f"\n第二个个体:")
print(f"  valid: {result2.valid}")
print(f"  sharpe: {result2.sharpe}")
print(f"  individual2.fitness: {individual2.fitness}")

print(f"\n两个个体的sharpe相同: {result.sharpe == result2.sharpe}")
print(f"两个个体的total_return相同: {result.total_return == result2.total_return}")

print("\n=== 测试完成 ===")
