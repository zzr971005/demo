"""移除validation_pipeline_data和evolution_tasks表中的累计字段"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_utils import get_db_connection

def remove_cumulative_fields():
    """移除累计字段"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 移除validation_pipeline_data表的累计字段
        print("=== 移除validation_pipeline_data表的累计字段 ===")
        fields_to_drop = [
            'cumulative_search_input',
            'cumulative_replay_input',
            'cumulative_validation_input',
            'cumulative_demo_input'
        ]
        
        for field in fields_to_drop:
            try:
                cursor.execute(f"ALTER TABLE validation_pipeline_data DROP COLUMN IF EXISTS {field}")
                print(f"已移除字段: {field}")
            except Exception as e:
                print(f"移除字段 {field} 失败: {e}")
        
        # 移除evolution_tasks表的累计字段
        print("\n=== 移除evolution_tasks表的累计字段 ===")
        fields_to_drop = [
            'cumulative_replay_input',
            'cumulative_validation_input',
            'cumulative_demo_input'
        ]
        
        for field in fields_to_drop:
            try:
                cursor.execute(f"ALTER TABLE evolution_tasks DROP COLUMN IF EXISTS {field}")
                print(f"已移除字段: {field}")
            except Exception as e:
                print(f"移除字段 {field} 失败: {e}")
        
        conn.commit()
        print("\n数据库迁移完成")
        
    except Exception as e:
        print(f"数据库迁移失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    remove_cumulative_fields()
