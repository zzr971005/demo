"""检查G160代因子详情"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查G160代因子详情 ===")

# 查询G160代的因子
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
WHERE generation = 160
ORDER BY created_at DESC
LIMIT 20
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录")
if len(df) == 0:
    print("G160代没有因子")
else:
    print("\n因子详情：")
    print(df[['id', 'formula', 'sharpe_train', 'total_return', 'total_trades', 'win_rate', 'max_drawdown']])

    # 检查公式是否相同
    unique_formulas = df['formula'].nunique()
    print(f"\n公式唯一性: {unique_formulas} 个不同公式")

    if unique_formulas > 1:
        print("\n不同公式：")
        for formula in df['formula'].unique():
            print(f"  - {formula}")
    else:
        print(f"\n所有公式相同: {df['formula'].iloc[0]}")

print("\n=== 检查完成 ===")
