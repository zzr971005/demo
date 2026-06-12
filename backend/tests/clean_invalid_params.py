"""清理数据库中包含浮点数参数的因子"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from sqlalchemy import text
from app.db import get_session
import re

print("=== 清理数据库中包含浮点数参数的因子 ===")

with get_session() as session:
    # 查询所有因子
    query = text("""
        SELECT id, formula, generation
        FROM candidates
        ORDER BY created_at DESC
    """)
    result = session.execute(query)
    all_factors = result.fetchall()

    print(f"查询到 {len(all_factors)} 条记录")

    # 找出包含浮点数参数的因子
    invalid_ids = []
    for row in all_factors:
        formula = row[1]
        # 检查是否包含浮点数（如 -2.7697, 1.3424, 2.68等）
        if re.search(r'\d+\.\d+', formula):
            invalid_ids.append(row[0])

    print(f"发现 {len(invalid_ids)} 个包含浮点数参数的因子")

    if len(invalid_ids) > 0:
        # 删除这些因子
        delete_query = text(f"""
            DELETE FROM candidates
            WHERE id IN ({','.join([f"'{id}'" for id in invalid_ids])})
        """)
        result = session.execute(delete_query)
        deleted_count = result.rowcount
        print(f"删除了 {deleted_count} 个因子")

        session.commit()
    else:
        print("没有需要删除的因子")

print("=== 清理完成 ===")
