"""检查G30代因子的公式详情"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查G30代因子的公式详情 ===")

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
    created_at
FROM candidates
WHERE generation = 30
ORDER BY created_at DESC
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录")

if len(df) == 0:
    print("G30代没有因子")
else:
    print("\n因子详情（包含创建时间）：")
    print(df[['id', 'formula', 'sharpe_train', 'total_return', 'created_at']])

    # 检查公式结构
    print("\n=== 公式结构分析 ===")
    for idx, row in df.iterrows():
        formula = row['formula']
        print(f"\n{idx+1}. {formula[:80]}..." if len(formula) > 80 else f"\n{idx+1}. {formula}")

print("\n=== 检查完成 ===")
