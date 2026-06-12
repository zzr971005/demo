"""检查数据库中包含无效参数的因子"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd
import re

print("=== 检查数据库中包含无效参数的因子 ===")

# 查询所有因子
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
ORDER BY created_at DESC
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录")

if len(df) == 0:
    print("数据库为空")
else:
    # 检查公式中是否包含浮点数参数
    invalid_factors = []
    for idx, row in df.iterrows():
        formula = row['formula']

        # 检查是否包含浮点数（如 -2.7697, 1.3424, 2.68等）
        # 匹配模式：数字后面有小数点
        if re.search(r'\d+\.\d+', formula):
            invalid_factors.append(row)

    print(f"\n发现 {len(invalid_factors)} 个包含浮点数参数的因子")

    if len(invalid_factors) > 0:
        print("\n无效因子详情：")
        invalid_df = pd.DataFrame(invalid_factors)
        print(invalid_df[['id', 'generation', 'formula', 'sharpe_train', 'total_return']])

        # 按代数统计
        print("\n按代数统计：")
        gen_counts = invalid_df['generation'].value_counts().sort_index()
        for gen, count in gen_counts.items():
            print(f"  G{gen}: {count} 个")

print("\n=== 检查完成 ===")
