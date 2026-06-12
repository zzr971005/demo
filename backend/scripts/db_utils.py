"""数据库连接工具

提供scripts目录中脚本使用的通用数据库连接函数。
"""

import os
import psycopg2
from typing import Optional


def get_db_connection():
    """获取数据库连接
    
    从环境变量DATABASE_URL读取数据库连接信息，
    如果未设置则使用默认值。
    
    Returns:
        psycopg2.connection: 数据库连接对象
    """
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/quant_db')
    
    # psycopg2需要postgres://前缀
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')
    
    return psycopg2.connect(db_url)


def execute_query(query: str, params: Optional[tuple] = None, fetch: bool = True):
    """执行SQL查询
    
    Args:
        query: SQL查询语句
        params: 查询参数
        fetch: 是否获取结果
        
    Returns:
        如果fetch=True，返回查询结果；否则返回None
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
