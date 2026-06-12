"""检查evolution_tasks表的结构"""
from db_utils import get_db_connection

def check_evolution_tasks_structure():
    """检查evolution_tasks表的结构"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查表结构
        print("=== 检查evolution_tasks表结构 ===")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'evolution_tasks'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f"{col[0]}: {col[1]}")
        
    except Exception as e:
        print(f"检查失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_evolution_tasks_structure()
