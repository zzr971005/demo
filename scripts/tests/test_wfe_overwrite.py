"""测试WFE检验是否会覆盖个体fitness并导致相同结果"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import random_individual
from quant_engine.ops.gp_evolution import PopulationManager, EvolutionConfig
from quant_engine.ops.gp_fitness import FitnessEvaluator
from quant_engine.ops.gp_overfitting import compute_wfe

print("=== 测试: WFE检验覆盖个体fitness ===")

# 创建小种群
config = EvolutionConfig(population_size=3, init_max_depth=3)
manager = PopulationManager(config)
manager.initialize(seed=42)

print(f"种群大小: {len(manager.population)}")
for i, ind in enumerate(manager.population):
    print(f"  ind[{i}]: {ind.id}, expr={ind.to_expression()[:50]}")

# 创建测试数据
np.random.seed(42)
n = 300  # 需要足够的数据进行WFE分割
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

# 主进化评估
evaluator = FitnessEvaluator()
results, _ = manager.evaluate_fitness(data, symbol="TEST", evaluator=evaluator)

print("\n=== 主进化评估后 ===")
for i, (ind, result) in enumerate(zip(manager.population, results)):
    print(f"  ind[{i}]: sharpe={result.sharpe:.4f}, fitness_sharpe={ind.fitness.get('sharpe'):.4f}")

# 找到最佳个体
best_ind = max(manager.population, key=lambda x: x.fitness.get("sharpe", 0))
print(f"\n最佳个体: {best_ind.id}, sharpe={best_ind.fitness.get('sharpe'):.4f}")

# 记录WFE评估前的fitness
wfe_before = best_ind.fitness.copy()
print(f"\nWFE评估前最佳个体fitness: {wfe_before}")

# 执行WFE检验（使用同一个evaluator）
wfe_value = compute_wfe(
    best_ind,
    data,
    n_windows=5,
    evaluator=evaluator,  # 使用同一个evaluator
    symbol="TEST",
)

print(f"\nWFE值: {wfe_value:.4f}")
print(f"WFE评估后最佳个体fitness: {best_ind.fitness}")
print(f"fitness被覆盖: {wfe_before != best_ind.fitness}")

# 检查其他个体的fitness是否也被修改
print(f"\n其他个体的fitness:")
for i, ind in enumerate(manager.population):
    if ind.id != best_ind.id:
        print(f"  ind[{i}]: {ind.id}, sharpe={ind.fitness.get('sharpe'):.4f}")
        print(f"         fitness被修改: {True}")  # 如果看到不同的值，说明被修改了

print("\n=== 测试完成 ===")
