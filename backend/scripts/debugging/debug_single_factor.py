
"""调试单个因子"""
import sys
import traceback
from pathlib import Path
import warnings
import numpy as np
warnings.filterwarnings('ignore')

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("调试单个因子执行")
print("=" * 60)

# 1. 加载数据
print("\n1. 加载历史数据...")
from quant_engine.data.hub import TimescaleHub
hub = TimescaleHub()
df = hub.get_ohlcv('RB', frequency='1H')
print(f"   ✓ 数据加载成功: {len(df)} 条记录")

# 2. 测试各个因子函数
from quant_engine.factors.registry import FACTOR_REGISTRY

test_factors = [
    ('oi_change', [df['open_interest'].values, 20]),
    ('night_gap', []),  # 不需要参数？
    ('night_gap', [df['open'].values, df['close'].values]),
    ('am_pm_gap', [df['open'].values, df['close'].values]),
    ('garman_klass_vol', [df['high'].values, df['low'].values, df['close'].values, df['open'].values, 20]),
    ('ts_skew', [df['open'].values, 20]),
]

print("\n2. 测试因子函数执行...")
for name, args in test_factors:
    try:
        meta = FACTOR_REGISTRY[name]
        if meta.func:
            result = meta.func(*args)
            print(f"   ✓ {name}: 成功, shape={result.shape}")
        else:
            print(f"   ! {name}: 函数未绑定")
    except Exception as e:
        print(f"   ✗ {name}: 失败 - {e}")
        traceback.print_exc()

# 3. 测试完整的评估流程
print("\n3. 测试完整评估流程...")
from quant_engine.ops.gp_individual import random_individual
from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig

evaluator = FitnessEvaluator(FitnessConfig())

print("\n创建5个随机个体并逐一测试...")
for i in range(5):
    ind = random_individual(max_depth=2)
    expr = ind.to_expression()
    print(f"\n   个体 {i+1}: {expr}")
    
    try:
        # 先测试编译
        factor_func = evaluator.compiler.compile(ind)
        if factor_func is None:
            print(f"     ! 编译失败")
            continue
        
        # 测试因子计算
        factor_values = factor_func(df)
        print(f"     ✓ 因子计算成功, 有效值: {np.sum(np.isfinite(factor_values))}/{len(factor_values)}")
        
        # 执行回测
        result = evaluator.evaluate(ind, df, 'RB')
        print(f"     ✓ 评估成功: sharpe={result.sharpe:.4f}, valid={result.valid}")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
