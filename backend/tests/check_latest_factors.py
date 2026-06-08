"""检查最新产生的因子（重启后）"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查最新产生的因子（重启后） ===")

# 查询最新的因子
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
    calmar,
    created_at
FROM candidates
WHERE created_at > '2026-05-31 00:30:00'
ORDER BY created_at DESC
LIMIT 30
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录（重启后产生的）")
if len(df) == 0:
    print("重启后没有产生新因子")
else:
    print("\n因子详情：")
    print(df[['id', 'generation', 'formula', 'sharpe_train', 'total_return', 'total_trades', 'win_rate', 'max_drawdown', 'created_at']])

    # 检查指标是否相同
    print("\n=== 指标差异分析 ===")
    metrics = ['sharpe_train', 'total_return', 'total_trades', 'avg_trade_return', 'win_rate', 'max_drawdown', 'calmar']

    for metric in metrics:
        if metric in df.columns:
            unique_values = df[metric].nunique()
            if unique_values == 1:
                print(f"❌ {metric}: 所有值相同 = {df[metric].iloc[0]}")
            else:
                print(f"✅ {metric}: 有 {unique_values} 个不同值")

print("\n=== 检查完成 ===")
