"""检查evolution_tasks表的数据"""
from db_utils import get_db_connection

def check_evolution_task():
    """检查evolution_tasks表的数据"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查最新数据
        print("=== 检查evolution_tasks表 (RB品种) ===")
        cursor.execute("""
            SELECT task_id, symbol, status, current_generation, 
                   total_factors, passed_factors, 
                   started_at, last_heartbeat
            FROM evolution_tasks
            WHERE symbol = 'RB'
            ORDER BY started_at DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"找到 {len(rows)} 条记录")
            for row in rows:
                print(f"\n任务ID: {row[0]}")
                print(f"品种: {row[1]}")
                print(f"状态: {row[2]}")
                print(f"当前代数: {row[3]}")
                print(f"总因子数: {row[4]}")
                print(f"通过因子数: {row[5]}")
                print(f"开始时间: {row[6]}")
                print(f"最后心跳: {row[7]}")
        else:
            print("没有找到数据")
        
    except Exception as e:
        print(f"检查失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_evolution_task()
