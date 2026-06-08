"""检查validation_pipeline_data表的数据"""
from db_utils import get_db_connection

def check_pipeline_data():
    """检查validation_pipeline_data表的数据"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查表结构
        print("=== 检查表结构 ===")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'validation_pipeline_data'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f"{col[0]}: {col[1]}")
        
        # 检查最新数据
        print("\n=== 检查最新数据 (RB品种) ===")
        cursor.execute("""
            SELECT symbol, generation, 
                   search_input, search_output, search_drop,
                   replay_input, replay_output, replay_drop,
                   validation_input, validation_output, validation_drop,
                   demo_input, demo_output, demo_drop,
                   created_at, updated_at
            FROM validation_pipeline_data
            WHERE symbol = 'RB'
            ORDER BY generation DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        if rows:
            print(f"找到 {len(rows)} 条记录")
            for row in rows:
                print(f"\n代数: {row[1]}")
                print(f"Search: 输入={row[2]}, 输出={row[3]}, 淘汰={row[4]}")
                print(f"Replay: 输入={row[5]}, 输出={row[6]}, 淘汰={row[7]}")
                print(f"Validation: 输入={row[8]}, 输出={row[9]}, 淘汰={row[10]}")
                print(f"Demo: 输入={row[11]}, 输出={row[12]}, 淘汰={row[13]}")
                print(f"创建时间: {row[14]}, 更新时间: {row[15]}")
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
    check_pipeline_data()
