"""清理所有数据（因子和进化任务）"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import get_session

print("=== 清理所有数据 ===")

with get_session() as session:
    # 删除所有因子
    result = session.execute(text("DELETE FROM candidates"))
    deleted_factors = result.rowcount
    print(f"删除了 {deleted_factors} 个因子")

    # 删除所有进化任务
    result = session.execute(text("DELETE FROM evolution_tasks"))
    deleted_tasks = result.rowcount
    print(f"删除了 {deleted_tasks} 个进化任务")

    # 删除所有generation_stats
    result = session.execute(text("DELETE FROM generation_stats"))
    deleted_stats = result.rowcount
    print(f"删除了 {deleted_stats} 条generation_stats记录")

    session.commit()

print("=== 清理完成 ===")
