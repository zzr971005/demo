"""检查G30代因子的参数"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd
import re

print("=== 检查G30代因子的参数 ===")

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
    max_drawdown
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

    # 检查公式中是否包含浮点数参数
    invalid_factors = []
    for idx, row in df.iterrows():
        formula = row['formula']
        # 检查是否包含浮点数（如 -8.6408, -3.1628, 7.6913等）
        if re.search(r'\d+\.\d+', formula):
            invalid_factors.append(row)

    print(f"\n发现 {len(invalid_factors)} 个包含浮点数参数的因子")

    if len(invalid_factors) > 0:
        print("\n包含浮点数参数的因子：")
        invalid_df = pd.DataFrame(invalid_factors)
        print(invalid_df[['id', 'formula', 'sharpe_train', 'total_return']])

print("\n=== 检查完成 ===")
