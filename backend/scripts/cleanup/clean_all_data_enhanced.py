"""增强版数据库清理脚本
清理所有相关数据表，确保数据完整性
"""

from app.db import get_session
from app.models import (
    ValidationPipelineData,      # 验证流程数据
    Candidate,                   # 候选因子
    EvolutionTask,               # 进化任务
    EvolutionGeneration,         # 进化代数据
    GenerationStats,             # 代统计
    FactorValue,                 # 因子值
    Trade,                       # 交易记录
    BaselineComparisonResult,    # 基线对比结果
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
            # 核心业务数据（最后清理）
            (FactorValue, "因子值数据"),
            (Trade, "交易记录"),
            (Candidate, "候选因子"),
            
            # 验证和统计数据（中间清理）
            (ValidationPipelineData, "验证流程数据"),
            (GenerationStats, "代统计数据"),
            (EvolutionGeneration, "进化代数据"),
            (BaselineComparisonResult, "基线对比结果"),
            
            # 任务数据（最先清理）
            (EvolutionTask, "进化任务"),
        ]
        
        total_deleted = 0
        
        for table, table_name in tables_to_clean:
            try:
                # 先检查有多少数据
                count_result = session.execute(select(table)).scalars().all()
                count = len(count_result)
                
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
        
        # 清理因子值数据
        try:
            result = session.execute(
                delete(FactorValue).where(
                    FactorValue.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除因子值数据: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除因子值数据时出错: {e}")
        
        # 清理交易记录
        try:
            result = session.execute(
                delete(Trade).where(
                    Trade.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除交易记录: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除交易记录时出错: {e}")
        
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
        
        # 清理进化代数据
        try:
            result = session.execute(
                delete(EvolutionGeneration).where(
                    EvolutionGeneration.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除进化代数据: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除进化代数据时出错: {e}")
        
        # 清理代统计数据
        try:
            result = session.execute(
                delete(GenerationStats).where(
                    GenerationStats.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除代统计数据: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除代统计数据时出错: {e}")
        
        # 清理基线对比结果
        try:
            result = session.execute(
                delete(BaselineComparisonResult).where(
                    BaselineComparisonResult.symbol == symbol
                )
            )
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"✓ 删除基线对比结果: {deleted_count} 条记录")
        except Exception as e:
            print(f"✗ 删除基线对比结果时出错: {e}")
        
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
            (EvolutionGeneration, "进化代数据"),
            (GenerationStats, "代统计数据"),
            (FactorValue, "因子值数据"),
            (Trade, "交易记录"),
            (BaselineComparisonResult, "基线对比结果"),
        ]
        
        for table, table_name in tables:
            try:
                result = session.execute(select(table)).scalars().all()
                count = len(result)
                print(f"✓ {table_name}: {count} 条记录")
                
                # 检查是否有孤立数据
                if hasattr(table, 'symbol') and result:
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
            generation_symbols = set(
                item.symbol for item in session.execute(select(EvolutionGeneration)).scalars().all()
            )
            factor_symbols = set(
                item.symbol for item in session.execute(select(FactorValue)).scalars().all()
            )
            trade_symbols = set(
                item.symbol for item in session.execute(select(Trade)).scalars().all()
            )
            
            all_symbols = (pipeline_symbols | candidate_symbols | task_symbols | 
                          generation_symbols | factor_symbols | trade_symbols)
            
            print(f"\n所有涉及的品种: {', '.join(sorted(all_symbols))}")
            
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
                generation_count = len([
                    item for item in session.execute(select(EvolutionGeneration)).scalars().all()
                    if item.symbol == symbol
                ])
                factor_count = len([
                    item for item in session.execute(select(FactorValue)).scalars().all()
                    if item.symbol == symbol
                ])
                trade_count = len([
                    item for item in session.execute(select(Trade)).scalars().all()
                    if item.symbol == symbol
                ])
                
                print(f"品种 {symbol}: 验证流程={pipeline_count}, 候选因子={candidate_count}, "
                      f"进化任务={task_count}, 进化代={generation_count}, "
                      f"因子值={factor_count}, 交易={trade_count}")
                
                # 检查是否有不一致的情况
                if candidate_count > 0 and pipeline_count == 0:
                    issues.append(f"品种 {symbol}: 有候选因子但无验证流程数据")
                if task_count > 0 and candidate_count == 0:
                    issues.append(f"品种 {symbol}: 有进化任务但无候选因子")
                if factor_count > 0 and candidate_count == 0:
                    issues.append(f"品种 {symbol}: 有因子值但无候选因子")
                if trade_count > 0 and candidate_count == 0:
                    issues.append(f"品种 {symbol}: 有交易记录但无候选因子")
                    
        except Exception as e:
            issues.append(f"检查品种一致性时出错: {e}")
        
        # 检查数据逻辑一致性
        try:
            # 检查验证流程数据的逻辑性
            pipeline_data = session.execute(select(ValidationPipelineData)).scalars().all()
            for data in pipeline_data:
                if data.search_output > data.search_input:
                    issues.append(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                f"search_output({data.search_output}) > search_input({data.search_input})")
                
                if data.replay_output > data.replay_input:
                    issues.append(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                f"replay_output({data.replay_output}) > replay_input({data.replay_input})")
                
                if data.validation_output > data.validation_input:
                    issues.append(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                f"validation_output({data.validation_output}) > validation_input({data.validation_input})")
                
                if data.demo_output > data.demo_input:
                    issues.append(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                f"demo_output({data.demo_output}) > demo_input({data.demo_input})")
                    
        except Exception as e:
            issues.append(f"检查数据逻辑一致性时出错: {e}")
        
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
        tables = [ValidationPipelineData, Candidate, EvolutionTask, 
                 EvolutionGeneration, FactorValue, Trade]
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


def get_data_summary():
    """获取数据概览"""
    print("=== 数据概览 ===")
    
    with get_session() as session:
        tables = [
            (ValidationPipelineData, "验证流程数据"),
            (Candidate, "候选因子"),
            (EvolutionTask, "进化任务"),
            (EvolutionGeneration, "进化代数据"),
            (GenerationStats, "代统计数据"),
            (FactorValue, "因子值数据"),
            (Trade, "交易记录"),
            (BaselineComparisonResult, "基线对比结果"),
        ]
        
        total_records = 0
        
        for table, table_name in tables:
            try:
                result = session.execute(select(table)).scalars().all()
                count = len(result)
                total_records += count
                
                if hasattr(table, 'symbol') and result:
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
        elif command == "clean-symbol" and len(sys.argv) > 2:
            symbol = sys.argv[2]
            clean_symbol_data(symbol)
        elif command == "validate":
            validate_data_integrity()
        elif command == "list":
            list_all_symbols()
        elif command == "summary":
            get_data_summary()
        else:
            print("用法:")
            print("  python clean_all_data_enhanced.py clean          # 清理所有数据")
            print("  python clean_all_data_enhanced.py clean-symbol <品种>  # 清理指定品种")
            print("  python clean_all_data_enhanced.py validate       # 验证数据完整性")
            print("  python clean_all_data_enhanced.py list          # 列出所有品种")
            print("  python clean_all_data_enhanced.py summary       # 数据概览")
    else:
        print("用法:")
        print("  python clean_all_data_enhanced.py clean          # 清理所有数据")
        print("  python clean_all_data_enhanced.py clean-symbol <品种>  # 清理指定品种")
        print("  python clean_all_data_enhanced.py validate       # 验证数据完整性")
        print("  python clean_all_data_enhanced.py list          # 列出所有品种")
        print("  python clean_all_data_enhanced.py summary       # 数据概览")
