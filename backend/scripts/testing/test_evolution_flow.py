
"""测试完整的进化流程"""
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("测试完整的进化流程")
print("=" * 60)

# 1. 加载数据
print("\n1. 加载历史数据...")
from quant_engine.data.hub import TimescaleHub
hub = TimescaleHub()
df = hub.get_ohlcv('RB', frequency='1H')
print(f"   ✓ 数据加载成功: {len(df)} 条记录")
print(f"   ✓ 时间范围: {df.index[0]} 到 {df.index[-1]}")

# 2. 创建适应度评估器
print("\n2. 创建适应度评估器...")
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
evaluator = FitnessEvaluator(FitnessConfig())
print("   ✓ FitnessEvaluator 创建成功")

# 3. 创建随机个体
print("\n3. 创建随机个体...")
from quant_engine.ops.gp_individual import random_individual
ind = random_individual(max_depth=3)
print(f"   ✓ 个体创建成功")
print(f"   ✓ 表达式: {ind.to_expression()}")
print(f"   ✓ 节点数: {ind.get_node_count()}")
print(f"   ✓ 深度: {ind.get_depth()}")

# 4. 测试个体评估
print("\n4. 测试个体评估...")
try:
    result = evaluator.evaluate(ind, df, 'RB')
    print(f"   ✓ 评估状态: {result.valid}")
    print(f"   ✓ 夏普比率: {result.sharpe:.4f}")
    print(f"   ✓ 总收益率: {result.total_return:.4f}")
    print(f"   ✓ 最大回撤: {result.max_drawdown:.4f}")
    print(f"   ✓ 交易次数: {result.total_trades}")
    print(f"   ✓ 胜率: {result.win_rate:.4f}")
except Exception as e:
    print(f"   ✗ 评估失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试批量评估
print("\n5. 测试批量评估 (5个个体)...")
individuals = [random_individual(max_depth=3) for _ in range(5)]
for i, ind in enumerate(individuals):
    print(f"   个体 {i+1}: {ind.to_expression()}")

results = evaluator.evaluate_batch(individuals, df, 'RB')
valid_count = sum(1 for r in results if r.valid)
print(f"   ✓ 有效个体数: {valid_count}/{len(individuals)}")

if valid_count > 0:
    valid_results = [r for r in results if r.valid]
    avg_sharpe = sum(r.sharpe for r in valid_results) / len(valid_results)
    best_sharpe = max(r.sharpe for r in valid_results)
    print(f"   ✓ 平均夏普: {avg_sharpe:.4f}")
    print(f"   ✓ 最佳夏普: {best_sharpe:.4f}")

# 6. 测试进化引擎
print("\n6. 测试完整进化流程 (种群10，世代5)...")
from quant_engine.ops.gp_evolution import GeneticProgramming, EvolutionConfig

config = EvolutionConfig(
    population_size=10,
    max_generations=5,
    fitness_config=FitnessConfig(),
)

gp = GeneticProgramming(config)

def callback(gen, stats):
    print(f"   第 {gen} 代: 最佳夏普={stats.max_sharpe:.4f}, 多样性={stats.unique_expressions}/{stats.population_size}")

try:
    result = gp.evolve(df, 'RB', callback=callback)
    print(f"\n   ✓ 进化完成!")
    print(f"   ✓ 总代数: {result.total_generations}")
    print(f"   ✓ 最佳夏普: {result.best_sharpe:.4f}")
    print(f"   ✓ 最佳个体: {result.best_individual.to_expression()}")
except Exception as e:
    print(f"   ✗ 进化失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)
