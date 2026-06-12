"""
验证期限结构数据完整性
"""
from quant_engine.data.hub import TimescaleHub
from datetime import datetime
import pandas as pd
import os

hub = TimescaleHub()

# 验证1h数据
df_1h = hub.query_term_structure("MA", datetime(2024,5,26), datetime(2026,5,26), 3600)
print(f"1h 数据: {len(df_1h)} 条")
print(f"1h 时间范围: {df_1h.index.min()} ~ {df_1h.index.max()}")
if not df_1h.empty:
    print(f"1h 主力合约(前5): {df_1h['main_contract'].dropna().unique()[:5]}")
    print(f"1h 近月合约(前5): {df_1h['near_contract'].dropna().unique()[:5]}")
    print(f"1h 远月合约(前5): {df_1h['far_contract'].dropna().unique()[:5]}")

print()

# 验证24h数据
df_1d = hub.query_term_structure("MA", datetime(2024,5,26), datetime(2026,5,26), 86400)
print(f"24h 数据: {len(df_1d)} 条")
print(f"24h 时间范围: {df_1d.index.min()} ~ {df_1d.index.max()}")
if not df_1d.empty:
    print(f"24h 主力合约(前5): {df_1d['main_contract'].dropna().unique()[:5]}")

print()

# 检查CSV备份
csv_1h = "D:/期货自动进化因子挖掘系统/data_backup/term_structure/1h/MA.csv"
csv_1d = "D:/期货自动进化因子挖掘系统/data_backup/term_structure/1d/MA.csv"
if os.path.exists(csv_1h):
    df_csv = pd.read_csv(csv_1h)
    print(f"CSV 1h 备份: {len(df_csv)} 条")
else:
    print("CSV 1h 备份: 不存在")
if os.path.exists(csv_1d):
    df_csv = pd.read_csv(csv_1d)
    print(f"CSV 1d 备份: {len(df_csv)} 条")
else:
    print("CSV 1d 备份: 不存在")

print()
print("="*60)
print("验证完成！")
print("="*60)