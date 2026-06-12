"""检查G124代因子的公式是否相同"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查G124代因子公式 ===")

# 查询G124代因子
query = """
SELECT
    id,
    formula,
    sharpe_train,
    max_drawdown,
    calmar
FROM candidates
WHERE generation = 124
ORDER BY created_at DESC
LIMIT 20
"""

df = pd.read_sql(query, engine)

print(f"\nG124代因子数量: {len(df)}")
print("\n因子公式和性能:")

for idx, row in df.iterrows():
    print(f"\n因子 {idx+1}:")
    print(f"  ID: {row['id']}")
    print(f"  公式: {row['formula']}")
    print(f"  夏普: {row['sharpe_train']}")
    print(f"  Calmar: {row['calmar']}")
    print(f"  最大回撤: {row['max_drawdown']}")

# 检查公式唯一性
unique_expressions = df['formula'].nunique()
print(f"\n唯一公式数量: {unique_expressions}")
print(f"总因子数量: {len(df)}")

if unique_expressions == 1:
    print("\n警告: 所有因子公式相同！")
elif unique_expressions < len(df):
    print(f"\n警告: 存在重复公式，重复率: {(len(df) - unique_expressions) / len(df) * 100:.1f}%")
else:
    print("\n正常: 所有因子公式不同")

print("\n=== 检查完成 ===")
