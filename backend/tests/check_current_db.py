"""检查当前数据库中的因子表现"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查当前数据库中的因子表现 ===")

# 查询最近的因子
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
ORDER BY created_at DESC
LIMIT 30
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录")
print("\n因子表现数据：")
print(df[['id', 'generation', 'formula', 'sharpe_train', 'total_return', 'total_trades', 'win_rate', 'max_drawdown']])

# 检查指标是否完全相同
print("\n=== 指标差异分析 ===")
metrics = ['sharpe_train', 'total_return', 'total_trades', 'avg_trade_return', 'win_rate', 'max_drawdown', 'calmar']

for metric in metrics:
    if metric in df.columns:
        unique_values = df[metric].nunique()
        if unique_values == 1:
            print(f"❌ {metric}: 所有值相同 = {df[metric].iloc[0]}")
        else:
            print(f"✅ {metric}: 有 {unique_values} 个不同值")
            print(f"   范围: [{df[metric].min():.4f}, {df[metric].max():.4f}]")

# 检查表达式是否相同
unique_formulas = df['formula'].nunique()
print(f"\n公式唯一性: {unique_formulas} 个不同公式")

if unique_formulas > 1:
    print("\n不同公式示例：")
    for formula in df['formula'].unique()[:5]:
        print(f"  - {formula}")

print("\n=== 检查完成 ===")
