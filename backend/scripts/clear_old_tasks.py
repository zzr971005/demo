"""清理旧的进化任务"""
from db_utils import get_db_connection

def clear_old_tasks():
    """清理旧的进化任务"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除所有RB品种的进化任务
        print("=== 清理RB品种的进化任务 ===")
        cursor.execute("""
            DELETE FROM evolution_tasks
            WHERE symbol = 'RB'
        """)
        deleted = cursor.rowcount
        print(f"删除了 {deleted} 条进化任务记录")
        
        conn.commit()
        print("清理完成")
        
    except Exception as e:
        print(f"清理失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    clear_old_tasks()
