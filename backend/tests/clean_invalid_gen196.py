"""清理G196代的无效因子"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import get_session
from app.models import Candidate

print("=== 清理G196代的无效因子 ===")

with get_session() as session:
    # 查询G196代的因子
    gen196_factors = session.query(Candidate).filter(
        Candidate.generation == 196
    ).all()

    print(f"找到 {len(gen196_factors)} 个G196代因子")

    # 删除G196代的所有因子
    deleted_count = 0
    for factor in gen196_factors:
        session.delete(factor)
        deleted_count += 1

    print(f"删除了 {deleted_count} 个G196代因子")

    # 提交
    session.commit()

print("=== 清理完成 ===")
