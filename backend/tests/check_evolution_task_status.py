"""检查当前进化任务状态"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import engine
import pandas as pd

print("=== 检查当前进化任务状态 ===")

# 查询进化任务
query = """
SELECT
    task_id,
    symbol,
    status,
    current_generation,
    pid,
    best_sharpe,
    total_factors
FROM evolution_tasks
ORDER BY task_id DESC
LIMIT 5
"""

df = pd.read_sql(query, engine)

print(f"\n共有 {len(df)} 个进化任务")
if len(df) > 0:
    print("\n任务详情：")
    print(df)
else:
    print("没有进化任务")

print("\n=== 检查完成 ===")
