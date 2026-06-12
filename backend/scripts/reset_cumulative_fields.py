"""清空evolution_tasks表的累计字段"""
from db_utils import get_db_connection

def reset_cumulative_fields():
    """清空evolution_tasks表的累计字段"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询当前累计字段值
        cursor.execute("""
            SELECT task_id, symbol, cumulative_replay_input, cumulative_validation_input, cumulative_demo_input
            FROM evolution_tasks
            WHERE cumulative_replay_input > 0 OR cumulative_validation_input > 0 OR cumulative_demo_input > 0
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"找到 {len(rows)} 个任务有累计数据:")
            for row in rows:
                print(f"  - {row[0]}: {row[1]} (Replay={row[2]}, Validation={row[3]}, Demo={row[4]})")
            
            # 清空累计字段
            cursor.execute("""
                UPDATE evolution_tasks
                SET cumulative_replay_input = 0,
                    cumulative_validation_input = 0,
                    cumulative_demo_input = 0
                WHERE cumulative_replay_input > 0 OR cumulative_validation_input > 0 OR cumulative_demo_input > 0
            """)
            
            conn.commit()
            print(f"已清空 {len(rows)} 个任务的累计字段")
        else:
            print("没有需要清空的累计数据")
        
    except Exception as e:
        print(f"清空累计字段失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    reset_cumulative_fields()
