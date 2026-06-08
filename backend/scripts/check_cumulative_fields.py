"""检查evolution_tasks表的累计字段"""
from db_utils import get_db_connection

def check_cumulative_fields():
    """检查evolution_tasks表的累计字段"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查最新任务的累计字段
        print("=== 检查最新进化任务的累计字段 (RB品种) ===")
        cursor.execute("""
            SELECT task_id, symbol, status, current_generation,
                   total_factors, unique_expressions, passed_factors,
                   cumulative_replay_input, cumulative_validation_input, cumulative_demo_input
            FROM evolution_tasks
            WHERE symbol = 'RB'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if row:
            print(f"任务ID: {row[0]}")
            print(f"品种: {row[1]}")
            print(f"状态: {row[2]}")
            print(f"当前代数: {row[3]}")
            print(f"总因子数: {row[4]}")
            print(f"唯一表达式: {row[5]}")
            print(f"通过因子数: {row[6]}")
            print(f"累计Replay输入: {row[7]}")
            print(f"累计Validation输入: {row[8]}")
            print(f"累计Demo输入: {row[9]}")
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
    check_cumulative_fields()
