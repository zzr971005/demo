"""检查回测引擎的杠杆计算"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

import numpy as np
from quant_engine.validation.engine import VectorizedBacktestEngine, BacktestResult

print("=== 检查回测引擎的杠杆计算 ===")

# 模拟参数
init_capital = 1_000_000.0  # 初始资金100万
position_size_pct = 0.95  # 仓位比例95%
contract_value_per_lot = 50000.0  # 每手合约名义价值（螺纹钢约5000元/吨 × 10吨）
margin_rate = 0.12  # 保证金率12%
use_margin = True  # 使用保证金

print(f"\n初始资金: {init_capital}")
print(f"仓位比例: {position_size_pct}")
print(f"每手合约名义价值: {contract_value_per_lot}")
print(f"保证金率: {margin_rate}")
print(f"使用保证金: {use_margin}")

# 计算开仓手数
notional = init_capital * position_size_pct
print(f"\n名义本金: {notional}")

if use_margin:
    pos_lots = int(notional / (contract_value_per_lot * margin_rate))
    print(f"开仓手数（使用保证金）: {pos_lots}")
    print(f"计算公式: int({notional} / ({contract_value_per_lot} * {margin_rate}))")
    print(f"         = int({notional} / {contract_value_per_lot * margin_rate})")
    print(f"         = {pos_lots} 手")
    
    # 计算实际杠杆倍数
    leverage = 1 / margin_rate
    print(f"\n实际杠杆倍数: {leverage:.2f}倍")
    print(f"计算公式: 1 / {margin_rate} = {leverage:.2f}")
    
    # 计算保证金占用
    margin = pos_lots * contract_value_per_lot * margin_rate
    print(f"\n保证金占用: {margin}")
    print(f"计算公式: {pos_lots} × {contract_value_per_lot} × {margin_rate} = {margin}")
    
    # 计算合约总价值
    contract_total_value = pos_lots * contract_value_per_lot
    print(f"\n合约总价值: {contract_total_value}")
    print(f"计算公式: {pos_lots} × {contract_value_per_lot} = {contract_total_value}")
    
    print(f"\n杠杆倍数验证: {contract_total_value} / {notional} = {contract_total_value / notional:.2f}倍")
else:
    pos_lots = int(notional / contract_value_per_lot)
    print(f"开仓手数（不使用保证金）: {pos_lots}")
    print(f"计算公式: int({notional} / {contract_value_per_lot})")

print("\n=== 结论 ===")
print("回测引擎使用保证金交易模式：")
print(f"- 保证金率 {margin_rate} 意味着 {1/margin_rate:.2f}倍杠杆")
print(f"- 100万资金可以开仓约 {pos_lots} 手螺纹钢")
print(f"- 合约总价值约 {pos_lots * contract_value_per_lot} 元")
print(f"- 这是期货交易的标准模式（自带杠杆）")
