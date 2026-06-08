"""
检查 generation_stats 表的所有记录（不限制 task_id）
"""

import sys
import os

# 确保 backend 目录在 sys.path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from app.db import get_session
from app.models import GenerationStats
from sqlalchemy import select

def check_all_generation_stats():
    """检查 generation_stats 表的所有记录"""
    try:
        with get_session() as session:
            stmt = select(GenerationStats)
            all_stats = session.execute(stmt).scalars().all()
            
            if not all_stats:
                print("generation_stats 表中没有记录")
                return
            
            print(f"generation_stats 表中共有 {len(all_stats)} 条记录:")
            for stat in all_stats:
                print(f"  - 代数: {stat.generation}, task_id: {stat.task_id}, "
                      f"avg_sharpe: {stat.avg_sharpe:.4f}, max_sharpe: {stat.max_sharpe:.4f}, "
                      f"unique_expressions: {stat.unique_expressions}, "
                      f"created_at: {stat.created_at}")
                
    except Exception as e:
        print(f"检查失败: {e}")
        raise

if __name__ == "__main__":
    check_all_generation_stats()
