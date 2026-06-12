"""测试GPIndividual的独立性和fitness字典是否正确隔离"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from quant_engine.ops.gp_individual import GPIndividual, random_individual
from quant_engine.ops.gp_evolution import PopulationManager, EvolutionConfig
from copy import deepcopy

print("=== 测试1: random_individual创建独立个体 ===")
ind1 = random_individual(max_depth=3, generation=0)
ind2 = random_individual(max_depth=3, generation=0)

print(f"ind1 id: {ind1.id}")
print(f"ind2 id: {ind2.id}")
print(f"ind1 fitness id: {id(ind1.fitness)}")
print(f"ind2 fitness id: {id(ind2.fitness)}")
print(f"fitness字典是同一个对象: {ind1.fitness is ind2.fitness}")

# 修改ind1的fitness
ind1.fitness["sharpe"] = 1.5
print(f"修改后 ind1 fitness: {ind1.fitness}")
print(f"修改后 ind2 fitness: {ind2.fitness}")
print(f"ind2也被修改了: {'sharpe' in ind2.fitness}")

print("\n=== 测试2: clone方法创建独立个体 ===")
ind3 = ind1.clone()
print(f"ind3 id: {ind3.id}")
print(f"ind3 fitness id: {id(ind3.fitness)}")
print(f"ind1 fitness id: {id(ind1.fitness)}")
print(f"clone后fitness字典是同一个对象: {ind1.fitness is ind3.fitness}")

# 修改ind3的fitness
ind3.fitness["sharpe"] = 2.0
print(f"修改后 ind3 fitness: {ind3.fitness}")
print(f"修改后 ind1 fitness: {ind1.fitness}")
print(f"ind1也被修改了: {ind1.fitness.get('sharpe') == 2.0}")

print("\n=== 测试3: PopulationManager初始化 ===")
config = EvolutionConfig(population_size=5, init_max_depth=3)
manager = PopulationManager(config)
manager.initialize(seed=42)

print(f"种群大小: {len(manager.population)}")
fitness_ids = [id(ind.fitness) for ind in manager.population]
print(f"fitness字典ID列表: {fitness_ids}")
print(f"所有fitness字典都唯一: {len(fitness_ids) == len(set(fitness_ids))}")

# 修改一个个体的fitness
manager.population[0].fitness["test"] = 999
print(f"修改后 pop0 fitness: {manager.population[0].fitness}")
print(f"修改后 pop1 fitness: {manager.population[1].fitness}")
print(f"pop1也被修改了: {'test' in manager.population[1].fitness}")

print("\n=== 测试完成 ===")
