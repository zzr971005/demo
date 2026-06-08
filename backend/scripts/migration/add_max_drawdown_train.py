"""手动添加 max_drawdown_train 字段到 candidates 表"""
import sys
sys.path.insert(0, '.')

from app.db import get_session
from sqlalchemy import text

def add_max_drawdown_train_column():
    """添加 max_drawdown_train 列到 candidates 表"""
    try:
        with get_session() as session:
            # 检查列是否已存在
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidates' 
                AND column_name = 'max_drawdown_train'
            """)
            result = session.execute(check_sql).fetchone()
            
            if result:
                print("列 max_drawdown_train 已存在，跳过添加")
                return
            
            # 添加列
            alter_sql = text("""
                ALTER TABLE candidates 
                ADD COLUMN max_drawdown_train FLOAT
            """)
            session.execute(alter_sql)
            print("成功添加 max_drawdown_train 列到 candidates 表")
            
    except Exception as e:
        print(f"添加列失败: {e}")
        raise

if __name__ == "__main__":
    add_max_drawdown_train_column()
