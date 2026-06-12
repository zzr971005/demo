"""检查 generation_stats 表的数据"""
import sys
sys.path.insert(0, '.')

from app.db import get_session
from app.models import GenerationStats
from sqlalchemy import select, desc

def check_generation_stats():
    """检查 generation_stats 表的数据"""
    try:
        with get_session() as session:
            # 查询所有世代统计
            stmt = select(GenerationStats).order_by(desc(GenerationStats.generation))
            results = session.execute(stmt).scalars().all()
            
            print(f"generation_stats 表中共有 {len(results)} 条记录")
            print("\n世代统计详情:")
            for row in results:
                print(f"  代数: {row.generation}, task_id: {row.task_id}, "
                      f"avg_sharpe: {row.avg_sharpe:.4f}, max_sharpe: {row.max_sharpe:.4f}, "
                      f"unique_expressions: {row.unique_expressions}, created_at: {row.created_at}")
            
    except Exception as e:
        print(f"查询失败: {e}")
        raise

if __name__ == "__main__":
    check_generation_stats()
