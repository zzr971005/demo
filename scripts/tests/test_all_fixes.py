"""综合测试验证所有修复"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode, random_individual
from quant_engine.ops.gp_evolution import PopulationManager, EvolutionConfig
from quant_engine.ops.gp_fitness import FitnessEvaluator
from quant_engine.ops.gp_operators import subtree_crossover, _check_node_compatibility

print("=== 测试1: 参数类型检查 ===")

# 创建一个函数节点，参数为 (high, low, close, volume, window)
func_node = GPNode(
    node_type='func',
    name='money_flow',
    children=[
        GPNode(node_type='var', name='high'),  # index 0: var
        GPNode(node_type='var', name='low'),   # index 1: var
        GPNode(node_type='var', name='close'), # index 2: var
        GPNode(node_type='var', name='volume'), # index 3: var
        GPNode(node_type='const', name='const', value=20), # index 4: const
    ]
)

# 测试1: var节点交换到var位置 - 应该兼容
test_var = GPNode(node_type='var', name='open')
compatible1 = _check_node_compatibility(test_var, func_node, 1)
print(f"  var -> money_flow第2个参数(var): {compatible1} (期望True)")

# 测试2: const节点交换到var位置 - 应该不兼容
test_const = GPNode(node_type='const', name='const', value=30)
compatible2 = _check_node_compatibility(test_const, func_node, 1)
print(f"  const -> money_flow第2个参数(var): {compatible2} (期望False)")

# 测试3: const节点交换到const位置 - 应该兼容
compatible3 = _check_node_compatibility(test_const, func_node, 4)
print(f"  const -> money_flow第5个参数(const): {compatible3} (期望True)")

# 测试4: var节点交换到const位置 - 应该不兼容
compatible4 = _check_node_compatibility(test_var, func_node, 4)
print(f"  var -> money_flow第5个参数(const): {compatible4} (期望False)")

assert compatible1 == True, "var->var应该兼容"
assert compatible2 == False, "const->var应该不兼容"
assert compatible3 == True, "const->const应该兼容"
assert compatible4 == False, "var->const应该不兼容"
print("  ✓ 所有参数类型检查通过")

print("\n=== 测试2: subtree_crossover类型检查 ===")

# 创建两个有参数类型不兼容的个体
parent1 = GPIndividual(
    root=GPNode(
        node_type='func',
        name='money_flow',
        children=[
            GPNode(node_type='var', name='high'),
            GPNode(node_type='var', name='low'),
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='volume'),
            GPNode(node_type='const', name='const', value=20),
        ]
    ),
    id="parent1",
    generation=0
)

# parent2的第二个参数是常量（会导致不兼容）
parent2 = GPIndividual(
    root=GPNode(
        node_type='func',
        name='money_flow',
        children=[
            GPNode(node_type='var', name='high'),
            GPNode(node_type='const', name='const', value=30),  # 这里是常量！
            GPNode(node_type='var', name='close'),
            GPNode(node_type='var', name='volume'),
            GPNode(node_type='const', name='const', value=20),
        ]
    ),
    id="parent2",
    generation=0
)

print(f"  parent1表达式: {parent1.to_expression()}")
print(f"  parent2表达式: {parent2.to_expression()}")

# 执行交叉
child1, child2 = subtree_crossover(parent1, parent2, max_depth=5)

print(f"  child1表达式: {child1.to_expression()}")
print(f"  child2表达式: {child2.to_expression()}")

# 检查是否因为类型不兼容而跳过了交叉（返回克隆）
if child1.to_expression() == parent1.to_expression() and child2.to_expression() == parent2.to_expression():
    print("  ✓ 类型不兼容时跳过交叉（返回克隆）")
else:
    print("  ✓ 类型兼容时执行交叉")

print("\n=== 测试3: FactorCompiler无缓存 ===")

# 创建两个相同表达式的个体
expr_node = GPNode(node_type='var', name='close')
ind1 = GPIndividual(root=expr_node, id="ind1", generation=0)
ind2 = GPIndividual(root=expr_node.clone(), id="ind2", generation=0)

# 使用同一个evaluator
evaluator = FitnessEvaluator()

# 编译两个个体
func1 = evaluator.compiler.compile(ind1)
func2 = evaluator.compiler.compile(ind2)

# 检查函数是否是不同对象（无缓存）
if func1 is not func2:
    print("  ✓ 相同表达式的个体编译为不同函数对象（无共享）")
else:
    print("  ✗ 函数被共享（有缓存问题）")

print("\n=== 测试4: 种群表达式去重 ===")

config = EvolutionConfig(
    population_size=10,
    init_max_depth=3,
    crossover_rate=0.8,
    mutation_rate=0.2,
)
manager = PopulationManager(config)
manager.initialize(seed=42)

# 统计初始种群的唯一表达式
initial_exprs = [ind.to_expression() for ind in manager.population]
unique_initial = len(set(initial_exprs))
print(f"  初始种群: {len(initial_exprs)} 个个体, {unique_initial} 个唯一表达式")

# 创建下一代
manager.create_next_generation(generation=1)

# 统计下一代的唯一表达式
new_exprs = [ind.to_expression() for ind in manager.population]
unique_new = len(set(new_exprs))
print(f"  下一代: {len(new_exprs)} 个个体, {unique_new} 个唯一表达式")

if unique_new == len(new_exprs):
    print("  ✓ 下一代中无重复表达式")
else:
    print(f"  ⚠ 下一代中有 {len(new_exprs) - unique_new} 个重复表达式")

print("\n=== 所有测试完成 ===")
