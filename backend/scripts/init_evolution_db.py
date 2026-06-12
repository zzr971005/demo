"""
初始化进化相关数据库表
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quant_engine.core.models.evolution import (
    Base,
    sqlite_engine,
    EvolutionTask,
    EvolutionGeneration,
    EvolutionFactor,
    FactorLiveStat,
)


def init_database():
    """初始化数据库表"""
    print("正在创建数据库表...")
    
    # 创建所有表
    Base.metadata.create_all(bind=sqlite_engine)
    
    print("数据库表创建完成！")
    
    # 验证表是否创建成功
    from sqlalchemy import inspect
    inspector = inspect(sqlite_engine)
    tables = inspector.get_table_names()
    
    print(f"\n已创建的表: {tables}")
    
    expected_tables = [
        'evolution_tasks',
        'evolution_generations', 
        'evolution_factors',
        'factor_live_stats'
    ]
    
    for table in expected_tables:
        if table in tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} (缺失)")


if __name__ == "__main__":
    init_database()
