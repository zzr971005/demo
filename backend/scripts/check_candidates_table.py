"""检查 candidates 表的列结构"""
import sys
sys.path.insert(0, '.')

from app.db import get_session
from sqlalchemy import text

def check_candidates_columns():
    """检查 candidates 表的列"""
    try:
        with get_session() as session:
            # 查询candidates表的所有列
            check_sql = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'candidates' 
                ORDER BY ordinal_position
            """)
            results = session.execute(check_sql).fetchall()
            
            print("candidates 表的列结构:")
            for row in results:
                print(f"  {row.column_name}: {row.data_type}")
            
    except Exception as e:
        print(f"查询失败: {e}")
        raise

if __name__ == "__main__":
    check_candidates_columns()
