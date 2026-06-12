"""测试GP个体生成"""
import sys
sys.path.insert(0, '.')

try:
    print('=== 测试随机个体生成 ===')
    
    from quant_engine.factors.registry import FACTOR_REGISTRY
    print(f"注册表中的函数数量: {len(FACTOR_REGISTRY)}")
    
    from quant_engine.ops.gp_individual import random_individual
    
    for i in range(5):
        ind = random_individual(max_depth=3, generation=0)
        expr = ind.to_expression()
        print(f'个体 {i+1}: {expr}')
        
except Exception as e:
    print(f'错误: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
