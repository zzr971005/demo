"""检查G30代因子指标是否相同"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查G30代因子指标是否相同 ===")

# 查询G30代的因子
query = """
SELECT
    id,
    formula,
    generation,
    sharpe_train,
    total_return,
    total_trades,
    win_rate,
    max_drawdown,
    calmar
FROM candidates
WHERE generation = 30
ORDER BY created_at DESC
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录")

if len(df) == 0:
    print("G30代没有因子")
else:
    print("\n因子详情：")
    print(df[['id', 'formula', 'sharpe_train', 'total_return', 'total_trades', 'win_rate', 'max_drawdown']])

    # 检查指标是否相同
    print("\n=== 指标差异分析 ===")
    metrics = ['sharpe_train', 'total_return', 'total_trades', 'win_rate', 'max_drawdown', 'calmar']

    for metric in metrics:
        if metric in df.columns:
            unique_values = df[metric].nunique()
            if unique_values == 1:
                print(f"❌ {metric}: 所有值相同 = {df[metric].iloc[0]}")
            else:
                print(f"✅ {metric}: 有 {unique_values} 个不同值")

print("\n=== 检查完成 ===")
