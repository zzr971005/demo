"""检查前端显示的因子"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查前端显示的因子 ===")

# 查询这些因子的详细信息
factor_ids = [
    "RB_evolution_20260531_002136_gen212_290194b93bdb",
    "RB_evolution_20260531_002136_gen224_85fdccbfb21a",
    "RB_evolution_20260531_002136_gen236_265e4b65109e",
    "RB_evolution_20260531_002136_gen248_28b4c330e42e",
    "RB_evolution_20260531_002136_gen270_fb36852106a7",
]

query = f"""
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
WHERE id IN ({','.join([f"'{id}'" for id in factor_ids])})
"""

df = pd.read_sql(query, engine)

print(f"\n查询到 {len(df)} 条记录")
print("\n因子详情：")
print(df[['id', 'generation', 'formula', 'sharpe_train', 'total_return', 'total_trades', 'win_rate', 'max_drawdown']])

# 检查公式是否相同
unique_formulas = df['formula'].nunique()
print(f"\n公式唯一性: {unique_formulas} 个不同公式")

if unique_formulas > 1:
    print("\n不同公式：")
    for formula in df['formula'].unique():
        print(f"  - {formula}")

print("\n=== 检查完成 ===")
