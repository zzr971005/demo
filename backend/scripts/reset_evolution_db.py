"""
重置进化相关数据库表
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quant_engine.core.models.evolution import (
    Base,
    sqlite_engine,
)


def reset_database():
    """重置数据库表"""
    print("正在删除旧表...")
    
    # 删除所有表
    Base.metadata.drop_all(bind=sqlite_engine)
    
    print("正在创建新表...")
    
    # 创建所有表
    Base.metadata.create_all(bind=sqlite_engine)
    
    print("数据库表重置完成！")
    
    # 验证表是否创建成功
    from sqlalchemy import inspect
    inspector = inspect(sqlite_engine)
    tables = inspector.get_table_names()
    
    print(f"\n已创建的表: {tables}")


if __name__ == "__main__":
    reset_database()
