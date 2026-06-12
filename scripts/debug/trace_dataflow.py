"""深度追踪数据流，从个体创建到数据库保存"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import pandas as pd
import numpy as np
from quant_engine.ops.gp_individual import GPIndividual, GPNode, random_individual
from quant_engine.ops.gp_fitness import FitnessEvaluator
from quant_engine.ops.gp_evolution import PopulationManager, EvolutionConfig

# 重定向日志到文件
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(r'd:\期货自动进化因子挖掘系统\dataflow_trace.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

print("=== 深度数据流追踪 ===")

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

# 创建5个不同的个体
print("\n1. 创建5个不同的个体:")
individuals = []
for i in range(5):
    ind = random_individual(max_depth=3, generation=0)
    ind.id = f"test_{i:03d}"
    individuals.append(ind)
    print(f"  {ind.id}: {ind.to_expression()}")

# 创建Evaluator
evaluator = FitnessEvaluator()

# 逐个评估并追踪
print("\n2. 逐个评估:")
results = []
for i, ind in enumerate(individuals):
    print(f"\n  评估 {ind.id}...")
    
    # 编译
    factor_func = evaluator.compiler.compile(ind)
    if factor_func is None:
        print(f"    编译失败")
        continue
    
    # 计算因子值
    try:
        factor_values = factor_func(data)
        print(f"    因子值: min={factor_values.min():.4f}, max={factor_values.max():.4f}, mean={factor_values.mean():.4f}")
        print(f"    因子值ID: {id(factor_values)}")
        print(f"    因子值前5个: {factor_values[:5]}")
    except Exception as e:
        print(f"    因子计算失败: {e}")
        continue
    
    # 评估
    result = evaluator.evaluate(ind, data, symbol="TEST")
    results.append(result)
    
    print(f"    结果: valid={result.valid}, sharpe={result.sharpe:.4f}, return={result.total_return:.4f}")
    print(f"    个体fitness: {ind.fitness}")
    print(f"    个体metrics: {ind.metrics}")

# 检查是否有重复结果
print("\n3. 检查重复结果:")
valid_results = [r for r in results if r.valid]
if valid_results:
    sharpe_values = [r.sharpe for r in valid_results]
    unique_sharpes = len(set(round(s, 4) for s in sharpe_values))
    print(f"  有效结果数: {len(valid_results)}")
    print(f"  唯一Sharpe值: {unique_sharpes}")
    
    if unique_sharpes < len(valid_results):
        print(f"  ⚠ 有 {len(valid_results) - unique_sharpes} 个重复结果！")
        # 找出重复的
        from collections import Counter
        sharpe_counts = Counter(round(s, 4) for s in sharpe_values)
        for sharpe, count in sharpe_counts.items():
            if count > 1:
                print(f"    Sharpe={sharpe} 出现 {count} 次")

# 检查个体的fitness字典是否被共享
print("\n4. 检查fitness字典独立性:")
fitness_ids = [id(ind.fitness) for ind in individuals]
unique_fitness_ids = len(set(fitness_ids))
print(f"  fitness字典唯一ID数: {unique_fitness_ids}/{len(fitness_ids)}")

if unique_fitness_ids < len(fitness_ids):
    print("  ⚠ fitness字典被共享！")
else:
    print("  ✓ fitness字典是独立的")

# 检查metrics字典
print("\n5. 检查metrics字典独立性:")
metrics_ids = [id(ind.metrics) for ind in individuals]
unique_metrics_ids = len(set(metrics_ids))
print(f"  metrics字典唯一ID数: {unique_metrics_ids}/{len(metrics_ids)}")

if unique_metrics_ids < len(metrics_ids):
    print("  ⚠ metrics字典被共享！")
else:
    print("  ✓ metrics字典是独立的")

print("\n=== 追踪完成，详情见 dataflow_trace.log ===")
