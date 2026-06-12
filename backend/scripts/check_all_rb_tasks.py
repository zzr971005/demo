"""检查所有RB任务的数据"""
from db_utils import get_db_connection

def check_all_rb_tasks():
    """检查所有RB任务的数据"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询所有RB任务
        cursor.execute("""
            SELECT task_id, symbol, status, current_generation,
                   total_factors, unique_expressions, passed_factors,
                   cumulative_replay_input, cumulative_validation_input, cumulative_demo_input,
                   created_at, started_at, finished_at
            FROM evolution_tasks
            WHERE symbol = 'RB'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"找到 {len(rows)} 个RB任务:")
            for i, row in enumerate(rows, 1):
                print(f"\n任务 {i}:")
                print(f"  任务ID: {row[0]}")
                print(f"  品种: {row[1]}")
                print(f"  状态: {row[2]}")
                print(f"  当前代数: {row[3]}")
                print(f"  总因子数: {row[4]}")
                print(f"  唯一表达式: {row[5]}")
                print(f"  通过因子数: {row[6]}")
                print(f"  累计Replay输入: {row[7]}")
                print(f"  累计Validation输入: {row[8]}")
                print(f"  累计Demo输入: {row[9]}")
                print(f"  创建时间: {row[10]}")
                print(f"  开始时间: {row[11]}")
                print(f"  结束时间: {row[12]}")
        else:
            print("没有找到RB任务")
        
    except Exception as e:
        print(f"检查失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_all_rb_tasks()
