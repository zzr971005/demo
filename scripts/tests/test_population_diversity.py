"""测试种群多样性，排查所有因子表现相同的问题"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import random_individual
from quant_engine.ops.gp_evolution import PopulationManager, EvolutionConfig
from quant_engine.ops.gp_fitness import FitnessEvaluator

print("=== 测试: 种群多样性和因子评估 ===")

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

# 1. 测试初始化种群的表达式唯一性
print("\n1. 初始化种群:")
config = EvolutionConfig(
    population_size=20,
    init_max_depth=3,
    crossover_rate=0.8,
    mutation_rate=0.2,
)
manager = PopulationManager(config)
manager.initialize(seed=42)

expressions = [ind.to_expression() for ind in manager.population]
unique_exprs = set(expressions)

print(f"  种群大小: {len(expressions)}")
print(f"  唯一表达式数量: {len(unique_exprs)}")
print(f"  重复表达式数量: {len(expressions) - len(unique_exprs)}")

if len(unique_exprs) < len(expressions):
    print("  ⚠ 警告: 初始化种群中有重复表达式！")
    # 找出重复的表达式
    from collections import Counter
    expr_counts = Counter(expressions)
    for expr, count in expr_counts.items():
        if count > 1:
            print(f"    重复 {count} 次: {expr}")
else:
    print("  ✓ 初始化种群表达式全部唯一")

# 2. 评估种群适应度
print("\n2. 评估种群适应度:")
evaluator = FitnessEvaluator()
results, _ = manager.evaluate_fitness(data, symbol="TEST")

# 统计评估结果
valid_results = [r for r in results if r.valid]
print(f"  有效个体数: {len(valid_results)}/{len(results)}")

if valid_results:
    sharpes = [r.sharpe for r in valid_results]
    returns = [r.total_return for r in valid_results]
    
    print(f"  Sharpe 值: min={min(sharpes):.4f}, max={max(sharpes):.4f}, mean={np.mean(sharpes):.4f}")
    print(f"  Return 值: min={min(returns):.4f}, max={max(returns):.4f}, mean={np.mean(returns):.4f}")
    
    # 检查所有Sharpe是否相同
    if len(set(round(s, 4) for s in sharpes)) == 1:
        print(f"  ⚠ 致命错误: 所有有效个体的 Sharpe 值完全相同 ({sharpes[0]:.4f})！")
    else:
        print(f"  ✓ 有效个体的 Sharpe 值各不相同")

# 3. 检查个体的fitness字典
print("\n3. 检查个体的fitness字典:")
fitness_values = [ind.fitness.get("penalized", 0) for ind in manager.population]
valid_fitness = [f for f in fitness_values if f > 0]

if valid_fitness:
    if len(set(round(f, 4) for f in valid_fitness)) == 1:
        print(f"  ⚠ 致命错误: 所有个体的 fitness 值完全相同 ({valid_fitness[0]:.4f})！")
    else:
        print(f"  ✓ 个体 fitness 各不相同: {len(set(round(f, 4) for f in valid_fitness))} 个唯一值")
        print(f"    范围: {min(valid_fitness):.4f} - {max(valid_fitness):.4f}")

# 4. 打印前5个个体的详细信息
print("\n4. 前5个个体详情:")
for i, (ind, result) in enumerate(zip(manager.population[:5], results[:5])):
    print(f"\n  个体 {i+1}: {ind.id}")
    print(f"    表达式: {ind.to_expression()}")
    print(f"    有效: {result.valid}")
    if result.valid:
        print(f"    Sharpe: {result.sharpe:.4f}")
        print(f"    Return: {result.total_return:.4f}")
        print(f"    Trades: {result.total_trades}")
    else:
        print(f"    错误: {result.error_message}")

print("\n=== 测试完成 ===")
