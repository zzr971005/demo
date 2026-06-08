
"""调试导入错误"""
import sys
import traceback
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("测试进化流程中的导入问题")
print("=" * 60)

try:
    from quant_engine.data.hub import TimescaleHub
    print("✓ TimescaleHub 导入成功")
except Exception as e:
    print(f"✗ TimescaleHub 导入失败: {e}")
    traceback.print_exc()

try:
    hub = TimescaleHub()
    df = hub.get_ohlcv('RB', frequency='1H')
    print(f"✓ 数据加载成功: {len(df)} 条")
except Exception as e:
    print(f"✗ 数据加载失败: {e}")
    traceback.print_exc()

try:
    from quant_engine.ops.gp_individual import GPIndividual, create_individual
    print("✓ GPIndividual 导入成功")
except Exception as e:
    print(f"✗ GPIndividual 导入失败: {e}")
    traceback.print_exc()

try:
    from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
    print("✓ FitnessEvaluator 导入成功")
except Exception as e:
    print(f"✗ FitnessEvaluator 导入失败: {e}")
    traceback.print_exc()

try:
    # 创建一个简单的个体
    ind = create_individual(max_depth=3, population_seed=42)
    print(f"✓ 个体创建成功: {ind.to_expression()}")
except Exception as e:
    print(f"✗ 个体创建失败: {e}")
    traceback.print_exc()

try:
    evaluator = FitnessEvaluator(FitnessConfig())
    print("✓ FitnessEvaluator 创建成功")
except Exception as e:
    print(f"✗ FitnessEvaluator 创建失败: {e}")
    traceback.print_exc()

try:
    print(f"\n开始评估个体...")
    print(f"数据列: {list(df.columns)}")
    print(f"数据形状: {df.shape}")
    
    result = evaluator.evaluate(ind, df, 'RB')
    print(f"✓ 评估完成: valid={result.valid}, sharpe={result.sharpe:.4f}")
except Exception as e:
    print(f"✗ 评估失败: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
