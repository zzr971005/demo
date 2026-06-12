"""检查同一代因子的表现差异"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查同一代因子的表现差异 ===")

# 查询G196和G198代的因子
query = """
SELECT
    id,
    formula,
    generation,
    sharpe_train,
    total_return,
    total_trades,
    avg_trade_return,
    win_rate,
    max_drawdown,
    calmar,
    created_at
FROM candidates
WHERE generation IN (196, 198)
ORDER BY generation, created_at DESC
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录")
print("\n按世代分组统计：")
for gen in [196, 198]:
    gen_df = df[df['generation'] == gen]
    print(f"\n世代 {gen}: {len(gen_df)} 个因子")
    if len(gen_df) > 0:
        print(f"  年化收益率范围: [{gen_df['total_return'].min():.2f}%, {gen_df['total_return'].max():.2f}%]")
        print(f"  夏普范围: [{gen_df['sharpe_train'].min():.4f}, {gen_df['sharpe_train'].max():.4f}]")
        print(f"  交易次数范围: [{gen_df['total_trades'].min()}, {gen_df['total_trades'].max()}]")

        # 检查是否有完全相同的指标
        unique_returns = gen_df['total_return'].nunique()
        unique_sharpes = gen_df['sharpe_train'].nunique()
        print(f"  年化收益率唯一值数量: {unique_returns}")
        print(f"  夏普唯一值数量: {unique_sharpes}")

        if unique_returns == 1:
            print(f"  ⚠️ 所有因子的年化收益率相同: {gen_df['total_return'].iloc[0]:.2f}%")

print("\n=== 详细数据 ===")
print(df[['id', 'generation', 'formula', 'total_return', 'sharpe_train', 'total_trades']])

# 检查表达式是否相同
print("\n=== 表达式唯一性分析 ===")
for gen in [196, 198]:
    gen_df = df[df['generation'] == gen]
    unique_formulas = gen_df['formula'].nunique()
    print(f"世代 {gen}: {unique_formulas} 个不同公式")
    if unique_formulas < len(gen_df):
        print(f"  ⚠️ 存在重复公式")

print("\n=== 检查完成 ===")
