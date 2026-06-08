"""调试GP个体生成问题"""
import sys
sys.path.insert(0, '.')

from quant_engine.factors.registry import FACTOR_REGISTRY

print('=== 函数参数定义 ===')
for name, meta in FACTOR_REGISTRY.items():
    params = meta.params
    print(f'{name}: {params}')
    if not params:
        print(f'   -> 无参数')
    else:
        for p_name, p_type, p_default in params:
            print(f'   -> {p_name}: {p_type.__name__} = {p_default}')

print('\n=== 需要价格输入的函数 ===')
for name, meta in FACTOR_REGISTRY.items():
    if meta.params and meta.params[0][0] not in ['window', 'days_to_expiry', 'threshold', 'fast', 'slow', 'nb_std']:
        print(f'{name}: 第一个参数是 {meta.params[0][0]}')
