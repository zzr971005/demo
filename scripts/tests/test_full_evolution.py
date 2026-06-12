"""测试完整进化流程，模拟实际环境"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import random_individual
from quant_engine.ops.gp_evolution import PopulationManager, EvolutionConfig
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试: 完整进化流程 ===")

# 创建种群配置
config = EvolutionConfig(
    population_size=5,
    init_max_depth=3,
    max_generations=3,
    elite_size=2,
    crossover_rate=0.8,
    mutation_rate=0.2,
)
manager = PopulationManager(config)
manager.initialize(seed=42)

print(f"初始种群大小: {len(manager.population)}")
for i, ind in enumerate(manager.population):
    print(f"  ind[{i}]: {ind.id}, expr={ind.to_expression()[:60]}")

# 创建测试数据
np.random.seed(42)
n = 500
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

print("\n=== 模拟多代进化 ===")

for generation in range(3):
    print(f"\n--- 第{generation}代 ---")
    
    # 评估
    evaluator = FitnessEvaluator(config.fitness_config)
    results, _ = manager.evaluate_fitness(data, symbol="TEST", evaluator=evaluator)
    
    # 打印评估结果
    for i, (ind, result) in enumerate(zip(manager.population, results)):
        if result.valid:
            print(f"  ind[{i}]: {ind.id}, sharpe={result.sharpe:.4f}, trades={result.total_trades}")
        else:
            print(f"  ind[{i}]: {ind.id}, valid=False, error={result.error_message[:30]}")
    
    # 创建下一代
    if generation < 2:  # 最后一代不创建下一代
        evolution_time, offspring_count = manager.create_next_generation(generation + 1)
        print(f"  创建下一代: {offspring_count} 个子代")

print("\n=== 最终种群 ===")
for i, ind in enumerate(manager.population):
    print(f"  ind[{i}]: {ind.id}, sharpe={ind.fitness.get('sharpe', 0):.4f}")

# 检查所有个体的sharpe是否相同
sharpe_values = [ind.fitness.get('sharpe', 0) for ind in manager.population]
print(f"\n所有sharpe值: {sharpe_values}")
print(f"所有sharpe值相同: {len(set(sharpe_values)) == 1}")

print("\n=== 测试完成 ===")
