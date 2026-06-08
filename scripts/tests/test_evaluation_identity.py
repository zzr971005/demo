"""测试评估过程中是否保持个体独立性"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import random_individual
from quant_engine.ops.gp_evolution import PopulationManager, EvolutionConfig
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试: 评估过程中个体独立性 ===")

# 创建小种群
config = EvolutionConfig(population_size=3, init_max_depth=3)
manager = PopulationManager(config)
manager.initialize(seed=42)

print(f"种群大小: {len(manager.population)}")
for i, ind in enumerate(manager.population):
    print(f"  ind[{i}]: {ind.id}, fitness_id={id(ind.fitness)}, metrics_id={id(ind.metrics)}")

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

print("\n=== 评估前 ===")
for i, ind in enumerate(manager.population):
    print(f"  ind[{i}]: fitness={ind.fitness}, metrics={ind.metrics}")

# 评估种群
evaluator = FitnessEvaluator()
results, _ = manager.evaluate_fitness(data, symbol="TEST")

print("\n=== 评估后 ===")
for i, (ind, result) in enumerate(zip(manager.population, results)):
    print(f"  ind[{i}]: valid={result.valid}, sharpe={result.sharpe:.4f}")
    print(f"         fitness={ind.fitness}")
    print(f"         metrics={ind.metrics}")

# 检查所有个体的fitness是否相同
fitness_values = [ind.fitness.get("sharpe", 0) for ind in manager.population]
print(f"\n所有个体的sharpe值: {fitness_values}")
print(f"所有sharpe值相同: {len(set(fitness_values)) == 1}")

# 检查fitness字典是否仍然是独立的对象
fitness_ids = [id(ind.fitness) for ind in manager.population]
print(f"fitness字典ID列表: {fitness_ids}")
print(f"所有fitness字典都唯一: {len(fitness_ids) == len(set(fitness_ids))}")

print("\n=== 测试完成 ===")
