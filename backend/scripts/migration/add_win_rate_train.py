"""
手动迁移脚本：添加 win_rate_train 列到 candidates 表
"""

import sys
import os

# 确保 backend 目录在 sys.path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from app.db import get_session
from sqlalchemy import text

def add_win_rate_train_column():
    """添加 win_rate_train 列到 candidates 表"""
    try:
        with get_session() as session:
            # 检查列是否已存在
            check_sql = text("""
                SELECT COUNT(*) as count
                FROM information_schema.columns
                WHERE table_name = 'candidates'
                AND column_name = 'win_rate_train'
            """)
            result = session.execute(check_sql).fetchone()
            
            if result.count > 0:
                print("win_rate_train 列已存在，跳过添加")
                return
            
            # 添加列
            alter_sql = text("""
                ALTER TABLE candidates
                ADD COLUMN win_rate_train FLOAT
            """)
            session.execute(alter_sql)
            print("成功添加 win_rate_train 列到 candidates 表")
            
    except Exception as e:
        print(f"添加列失败: {e}")
        raise

if __name__ == "__main__":
    add_win_rate_train_column()
