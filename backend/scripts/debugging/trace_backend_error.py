
"""追踪 'No module named backend' 错误"""
import sys
import traceback
from pathlib import Path
import warnings
import numpy as np
warnings.filterwarnings('ignore')

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("追踪 backend 导入错误")
print("=" * 60)

# 1. 加载数据
print("\n1. 加载历史数据...")
from quant_engine.data.hub import TimescaleHub
hub = TimescaleHub()
df = hub.get_ohlcv('RB', frequency='1H')
print(f"   ✓ 数据加载成功: {len(df)} 条记录")

# 2. 测试 fee_model
print("\n2. 测试 FeeModel.get_config()...")
from quant_engine.validation.fee_model import FeeModel
fee_model = FeeModel()
try:
    cfg = fee_model.get_config('RB')
    print(f"   ✓ 获取配置成功: rate={cfg.open_rate}")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    traceback.print_exc()

# 3. 测试 VectorizedBacktestEngine.run()
print("\n3. 测试完整回测...")
from quant_engine.validation.engine import VectorizedBacktestEngine

engine = VectorizedBacktestEngine(fee_model=fee_model)

# 创建一个简单的因子序列（随机信号）
np.random.seed(42)
factor = np.random.randn(len(df))

params = {
    "upper_threshold": 0.5,
    "lower_threshold": -0.5,
    "direction_mode": 0,
    "max_holding_bars": 0,
    "position_size_pct": 0.95,
    "contract_value_per_lot": 50000.0,
    "tick_size": 1.0,
    "slippage_ticks": 1,
    "use_margin": True,
    "margin_rate": 0.12,
}

try:
    print("   执行回测...")
    result = engine.run(
        factor=factor,
        open_px=df['open'].values,
        high_px=df['high'].values,
        low_px=df['low'].values,
        close_px=df['close'].values,
        params=params,
        symbol='RB',
    )
    print(f"   ✓ 回测成功: sharpe={result.sharpe:.4f}, trades={result.total_trades}")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
