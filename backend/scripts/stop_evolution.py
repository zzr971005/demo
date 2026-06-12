"""停止进化进程"""
from db_utils import get_db_connection

def stop_evolution():
    """停止所有运行中的进化任务"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询运行中的任务
        cursor.execute("""
            SELECT task_id, symbol, status, current_generation
            FROM evolution_tasks
            WHERE status = 'RUNNING'
        """)
        running_tasks = cursor.fetchall()
        
        if not running_tasks:
            print("没有运行中的进化任务")
            return
        
        print(f"找到 {len(running_tasks)} 个运行中的任务:")
        for task in running_tasks:
            print(f"  - {task[0]}: {task[1]} (代数: {task[2]})")
        
        # 停止所有运行中的任务
        cursor.execute("""
            UPDATE evolution_tasks
            SET status = 'CANCELLED',
                finished_at = NOW()
            WHERE status = 'RUNNING'
        """)
        
        conn.commit()
        print(f"已停止 {len(running_tasks)} 个进化任务")
        
    except Exception as e:
        print(f"停止进化任务失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    stop_evolution()
