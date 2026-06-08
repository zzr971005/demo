"""添加累计字段到validation_pipeline_data表"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_utils import get_db_connection

def add_cumulative_fields():
    """添加累计字段到validation_pipeline_data表"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'validation_pipeline_data' 
            AND column_name = 'cumulative_search_input'
        """
        cursor.execute(check_sql)
        result = cursor.fetchone()
        
        if result:
            print("字段已存在，跳过迁移")
            return
        
        # 添加累计字段
        alter_sqls = [
            "ALTER TABLE validation_pipeline_data ADD COLUMN cumulative_search_input INTEGER DEFAULT 0",
            "ALTER TABLE validation_pipeline_data ADD COLUMN cumulative_replay_input INTEGER DEFAULT 0",
            "ALTER TABLE validation_pipeline_data ADD COLUMN cumulative_validation_input INTEGER DEFAULT 0",
            "ALTER TABLE validation_pipeline_data ADD COLUMN cumulative_demo_input INTEGER DEFAULT 0",
        ]
        
        for sql in alter_sqls:
            print(f"执行: {sql}")
            cursor.execute(sql)
        
        conn.commit()
        print("累计字段添加成功")
        
    except Exception as e:
        print(f"添加字段失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_cumulative_fields()
