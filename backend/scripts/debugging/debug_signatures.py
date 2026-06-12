"""调试函数签名"""
import sys
sys.path.insert(0, '.')
import inspect

try:
    from quant_engine.factors.registry import ts_return, ts_corr, obv, atr, zscore, ts_mean, night_gap
    
    print('=== 函数实际签名 ===')
    print(f'ts_return: {inspect.signature(ts_return)}')
    print(f'ts_corr: {inspect.signature(ts_corr)}')
    print(f'obv: {inspect.signature(obv)}')
    print(f'atr: {inspect.signature(atr)}')
    print(f'zscore: {inspect.signature(zscore)}')
    print(f'ts_mean: {inspect.signature(ts_mean)}')
    print(f'night_gap: {inspect.signature(night_gap)}')
    
except Exception as e:
    print(f'错误: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
