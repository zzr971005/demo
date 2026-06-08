"""检查数据库当前状态"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查数据库当前状态 ===")

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
    calmar,
    created_at
FROM candidates
ORDER BY created_at DESC
"""

df = pd.read_sql(query, engine)

print(f"\n数据库中共有 {len(df)} 个因子")

if len(df) > 0:
    print("\n最近的因子：")
    print(df[['id', 'generation', 'sharpe_train', 'total_return', 'created_at']].head(20))
    
    # 检查G285和G286代
    gen285 = df[df['generation'] == 285]
    gen286 = df[df['generation'] == 286]
    
    print(f"\nG285代因子数量: {len(gen285)}")
    print(f"G286代因子数量: {len(gen286)}")
    
    if len(gen285) > 0:
        print("\nG285代因子示例：")
        print(gen285[['id', 'formula', 'sharpe_train', 'total_return']].head(5))
    
    if len(gen286) > 0:
        print("\nG286代因子示例：")
        print(gen286[['id', 'formula', 'sharpe_train', 'total_return']].head(5))
else:
    print("数据库为空")

print("\n=== 检查完成 ===")
