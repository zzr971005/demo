"""完整清理数据库脚本
清理所有相关数据表，确保数据一致性
"""

from app.db import get_session
from app.models import (
    ValidationPipelineData,  # 验证流程数据
    Candidate,               # 候选因子
    EvolutionTask,           # 进化任务
)
from sqlalchemy import select, delete
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_all_data():
    """完整清理所有相关数据"""
    print("=== 完整清理数据库 ===")
    
    with get_session() as session:
        # 按依赖关系顺序清除数据
        tables_to_clean = [
            (ValidationPipelineData, "验证流程数据"),
            (Candidate, "候选因子"),
            (EvolutionTask, "进化任务"),
        ]
        
        total_deleted = 0
        
        for table, table_name in tables_to_clean:
            try:
                # 先检查有多少数据
                count_result = session.execute(select(table)).scalar()
                count = len(count_result) if hasattr(count_result, '__len__') else (1 if count_result else 0)
                
                if count > 0:
                    # 删除数据
                    result = session.execute(delete(table))
                    deleted_count = result.rowcount
                    total_deleted += deleted_count
                    
                    print(f"✓ 删除 {table_name}: {deleted_count} 条记录")
                    logger.info(f"删除 {table_name}: {deleted_count} 条记录")
                else:
                    print(f"- {table_name}: 无数据需要删除")
                    
            except Exception as e:
                print(f"✗ 删除 {table_name} 时出错: {e}")
                logger.error(f"删除 {table_name} 失败: {e}")
                raise
        
        # 提交所有删除操作
        try:
            session.commit()
            print(f"\n✓ 数据库清理完成，共删除 {total_deleted} 条记录")
            logger.info(f"数据库清理完成，共删除 {total_deleted} 条记录")
        except Exception as e:
            print(f"✗ 提交删除操作时出错: {e}")
            logger.error(f"提交删除操作失败: {e}")
            raise


def clean_symbol_data(symbol: str):
    """清理指定品种的所有数据"""
    print(f"=== 清理品种 {symbol} 的数据 ===")
    
    with get_session() as session:
        total_deleted = 0
        
        # 清理验证流程数据
        try:
            result = session.execute(
                delete(ValidationPipelineData).where(
                    ValidationPipelineData.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除验证流程数据: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除验证流程数据时出错: {e}")
        
        # 清理候选因子
        try:
            result = session.execute(
                delete(Candidate).where(
                    Candidate.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除候选因子: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除候选因子时出错: {e}")
        
        # 清理进化任务
        try:
            result = session.execute(
                delete(EvolutionTask).where(
                    EvolutionTask.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除进化任务: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除进化任务时出错: {e}")
        
        # 提交所有删除操作
        try:
            session.commit()
            print(f"\n✓ 品种 {symbol} 数据清理完成，共删除 {total_deleted} 条记录")
        except Exception as e:
            print(f"✗ 提交删除操作时出错: {e}")
            raise


def validate_data_integrity():
    """验证数据完整性"""
    print("=== 验证数据完整性 ===")
    
    with get_session() as session:
        issues = []
        
        # 检查各表数据量
        tables = [
            (ValidationPipelineData, "验证流程数据"),
            (Candidate, "候选因子"),
            (EvolutionTask, "进化任务"),
        ]
        
        for table, table_name in tables:
            try:
                result = session.execute(select(table)).scalars().all()
                count = len(result)
                print(f"✓ {table_name}: {count} 条记录")
                
                # 检查是否有孤立数据
                if table == ValidationPipelineData:
                    symbols = set(item.symbol for item in result)
                    print(f"  - 涉及品种: {', '.join(sorted(symbols))}")
                    
                elif table == Candidate:
                    symbols = set(item.symbol for item in result)
                    print(f"  - 涉及品种: {', '.join(sorted(symbols))}")
                    
            except Exception as e:
                issues.append(f"检查 {table_name} 时出错: {e}")
                print(f"✗ 检查 {table_name} 时出错: {e}")
        
        # 检查品种一致性
        try:
            pipeline_symbols = set(
                item.symbol for item in session.execute(select(ValidationPipelineData)).scalars().all()
            )
            candidate_symbols = set(
                item.symbol for item in session.execute(select(Candidate)).scalars().all()
            )
            task_symbols = set(
                item.symbol for item in session.execute(select(EvolutionTask)).scalars().all()
            )
            
            all_symbols = pipeline_symbols | candidate_symbols | task_symbols
            
            for symbol in all_symbols:
                pipeline_count = len([
                    item for item in session.execute(select(ValidationPipelineData)).scalars().all()
                    if item.symbol == symbol
                ])
                candidate_count = len([
                    item for item in session.execute(select(Candidate)).scalars().all()
                    if item.symbol == symbol
                ])
                task_count = len([
                    item for item in session.execute(select(EvolutionTask)).scalars().all()
                    if item.symbol == symbol
                ])
                
                print(f"品种 {symbol}: 验证流程={pipeline_count}, 候选因子={candidate_count}, 进化任务={task_count}")
                
                # 检查是否有不一致的情况
                if candidate_count > 0 and pipeline_count == 0:
                    issues.append(f"品种 {symbol}: 有候选因子但无验证流程数据")
                if task_count > 0 and candidate_count == 0:
                    issues.append(f"品种 {symbol}: 有进化任务但无候选因子")
                    
        except Exception as e:
            issues.append(f"检查品种一致性时出错: {e}")
        
        if issues:
            print("\n⚠️  发现数据完整性问题:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("\n✓ 数据完整性检查通过")
            return True


def list_all_symbols():
    """列出所有品种"""
    print("=== 所有品种列表 ===")
    
    with get_session() as session:
        symbols = set()
        
        # 从各个表收集品种
        tables = [ValidationPipelineData, Candidate, EvolutionTask]
        for table in tables:
            try:
                table_symbols = set(
                    item.symbol for item in session.execute(select(table)).scalars().all()
                )
                symbols.update(table_symbols)
            except Exception as e:
                print(f"从 {table.__name__} 获取品种失败: {e}")
        
        if symbols:
            print(f"共 {len(symbols)} 个品种:")
            for symbol in sorted(symbols):
                print(f"  - {symbol}")
        else:
            print("无品种数据")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "clean":
            clean_all_data()
        elif command == "clean-symbol" and len(sys.argv) > 2:
            symbol = sys.argv[2]
            clean_symbol_data(symbol)
        elif command == "validate":
            validate_data_integrity()
        elif command == "list":
            list_all_symbols()
        else:
            print("用法:")
            print("  python clean_all_data_complete.py clean          # 清理所有数据")
            print("  python clean_all_data_complete.py clean-symbol <品种>  # 清理指定品种")
            print("  python clean_all_data_complete.py validate       # 验证数据完整性")
            print("  python clean_all_data_complete.py list          # 列出所有品种")
    else:
        print("用法:")
        print("  python clean_all_data_complete.py clean          # 清理所有数据")
        print("  python clean_all_data_complete.py clean-symbol <品种>  # 清理指定品种")
        print("  python clean_all_data_complete.py validate       # 验证数据完整性")
        print("  python clean_all_data_complete.py list          # 列出所有品种")
