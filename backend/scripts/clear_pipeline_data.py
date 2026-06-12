"""清空validation_pipeline_data表的数据"""
from db_utils import get_db_connection

def clear_pipeline_data():
    """清空validation_pipeline_data表的数据"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询当前数据量
        cursor.execute("SELECT COUNT(*) FROM validation_pipeline_data")
        count = cursor.fetchone()[0]
        print(f"当前validation_pipeline_data表有 {count} 条记录")
        
        if count > 0:
            # 清空表
            cursor.execute("DELETE FROM validation_pipeline_data")
            conn.commit()
            print(f"已清空validation_pipeline_data表")
        else:
            print("validation_pipeline_data表为空，无需清空")
        
    except Exception as e:
        print(f"清空失败: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    clear_pipeline_data()
