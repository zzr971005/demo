"""清理所有旧因子数据"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import get_session

print("=== 清理所有旧因子数据 ===")

with get_session() as session:
    # 删除所有因子
    result = session.execute(text("DELETE FROM candidates"))
    deleted_count = result.rowcount
    print(f"删除了 {deleted_count} 个因子")

    session.commit()

print("=== 清理完成 ===")
