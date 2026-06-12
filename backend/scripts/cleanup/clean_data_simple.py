"""简化版数据清理脚本
只清理能正常工作的表，避免数据库字段问题
"""

import sys
import os

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from app.db import get_session
from app.models import (
    ValidationPipelineData,      # 验证流程数据
    Candidate,                   # 候选因子
    EvolutionTask,               # 进化任务
    GenerationStats,             # 代统计数据
)
from sqlalchemy import select, delete
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_all_data():
    """清理核心数据"""
    print("=== 清理核心数据 ===")
    
    with get_session() as session:
        # 按依赖关系顺序清除数据
        tables_to_clean = [
            (GenerationStats, "代统计数据"),
            (ValidationPipelineData, "验证流程数据"),
            (Candidate, "候选因子"),
            (EvolutionTask, "进化任务"),
        ]
        
        total_deleted = 0
        
        for table, table_name in tables_to_clean:
            try:
                # 先检查有多少数据
                result = session.execute(select(table)).scalars().all()
                count = len(result)
                
                if count > 0:
                    # 删除数据
                    delete_result = session.execute(delete(table))
                    deleted_count = delete_result.rowcount
                    total_deleted += deleted_count
                    
                    print(f"✓ 删除 {table_name}: {deleted_count} 条记录")
                    logger.info(f"删除 {table_name}: {deleted_count} 条记录")
                else:
                    print(f"- {table_name}: 无数据需要删除")
                    
            except Exception as e:
                print(f"✗ 删除 {table_name} 时出错: {e}")
                logger.error(f"删除 {table_name} 失败: {e}")
                # 继续处理其他表，不中断
        
        # 提交所有删除操作
        try:
            session.commit()
            print(f"\n✓ 数据清理完成，共删除 {total_deleted} 条记录")
            logger.info(f"数据清理完成，共删除 {total_deleted} 条记录")
        except Exception as e:
            print(f"✗ 提交删除操作时出错: {e}")
            logger.error(f"提交删除操作失败: {e}")
            raise


def get_data_summary():
    """获取核心数据概览"""
    print("=== 核心数据概览 ===")
    
    with get_session() as session:
        tables = [
            (ValidationPipelineData, "验证流程数据"),
            (Candidate, "候选因子"),
            (EvolutionTask, "进化任务"),
            (GenerationStats, "代统计数据"),
        ]
        
        total_records = 0
        
        for table, table_name in tables:
            try:
                result = session.execute(select(table)).scalars().all()
                count = len(result)
                total_records += count
                
                if result and hasattr(result[0], 'symbol'):
                    symbols = set(item.symbol for item in result)
                    print(f"  {table_name}: {count} 条记录 (品种: {len(symbols)})")
                else:
                    print(f"  {table_name}: {count} 条记录")
                    
            except Exception as e:
                print(f"  {table_name}: 查询失败 - {e}")
        
        print(f"\n总计: {total_records} 条记录")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "clean":
            clean_all_data()
        elif command == "summary":
            get_data_summary()
        else:
            print("用法:")
            print("  python clean_data_simple.py clean     # 清理数据")
            print("  python clean_data_simple.py summary   # 数据概览")
    else:
        print("用法:")
        print("  python clean_data_simple.py clean     # 清理数据")
        print("  python clean_data_simple.py summary   # 数据概览")
