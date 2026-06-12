"""检查evolution_tasks表的数据"""
from db_utils import get_db_connection

def check_evolution_tasks():
    """检查evolution_tasks表的数据"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查最新任务
        print("=== 检查最新进化任务 (RB品种) ===")
        cursor.execute("""
            SELECT task_id, symbol, status, current_generation, max_generations,
                   total_factors, passed_factors, unique_expressions,
                   started_at, finished_at, last_heartbeat
            FROM evolution_tasks
            WHERE symbol = 'RB'
            ORDER BY created_at DESC
            LIMIT 3
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"找到 {len(rows)} 条记录")
            for row in rows:
                print(f"\n任务ID: {row[0]}")
                print(f"品种: {row[1]}")
                print(f"状态: {row[2]}")
                print(f"当前代数: {row[3]}")
                print(f"最大代数: {row[4]}")
                print(f"总因子数: {row[5]}")
                print(f"通过因子数: {row[6]}")
                print(f"唯一表达式: {row[7]}")
                print(f"开始时间: {row[8]}")
                print(f"结束时间: {row[9]}")
                print(f"最后心跳: {row[10]}")
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
    check_evolution_tasks()
