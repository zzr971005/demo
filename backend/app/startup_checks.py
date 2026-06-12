"""项目启动时的自动检查模块

在项目启动时自动执行完整性检查，确保系统状态正常
"""

import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_session
from app.models import (
    ValidationPipelineData,
    Candidate, 
    EvolutionTask,
    GenerationStats,
)
from sqlalchemy import select, text

logger = logging.getLogger(__name__)


class StartupCheckResult:
    """启动检查结果"""
    def __init__(self):
        self.passed = True
        self.warnings = []
        self.errors = []
        self.info = []
    
    def add_error(self, message: str):
        self.errors.append(message)
        self.passed = False
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def add_info(self, message: str):
        self.info.append(message)
    
    def print_summary(self):
        """打印检查结果摘要"""
        print("=" * 60)
        print("🚀 项目启动完整性检查")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if self.info:
            print("📊 系统信息:")
            for info in self.info:
                print(f"  ✓ {info}")
            print()
        
        if self.warnings:
            print("⚠️  警告:")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
            print()
        
        if self.errors:
            print("❌ 错误:")
            for error in self.errors:
                print(f"  ❌ {error}")
            print()
        
        if self.passed:
            if self.warnings:
                print("🟡 检查通过，但有警告项需要注意")
            else:
                print("🟢 所有检查通过，系统状态正常")
        else:
            print("🔴 检查失败，请修复错误后重新启动")
        
        print("=" * 60)
        
        return self.passed


class StartupChecker:
    """启动检查器"""
    
    def __init__(self):
        self.result = StartupCheckResult()
    
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with get_session() as session:
                # 执行简单查询测试连接
                session.execute(text("SELECT 1"))
                self.result.add_info("数据库连接正常")
                return True
        except Exception as e:
            self.result.add_error(f"数据库连接失败: {e}")
            return False
    
    def check_table_structure(self) -> bool:
        """检查表结构"""
        try:
            with get_session() as session:
                # 检查主要表是否存在
                tables_to_check = [
                    'validation_pipeline_data',
                    'candidates', 
                    'evolution_tasks',
                    'generation_stats'
                ]
                
                for table in tables_to_check:
                    try:
                        session.execute(text(f"SELECT COUNT(*) FROM {table} LIMIT 1"))
                        self.result.add_info(f"表 {table} 结构正常")
                    except Exception as e:
                        self.result.add_error(f"表 {table} 结构异常: {e}")
                        return False
                
                return True
        except Exception as e:
            self.result.add_error(f"表结构检查失败: {e}")
            return False
    
    def check_data_integrity(self) -> bool:
        """检查数据完整性"""
        try:
            with get_session() as session:
                issues = []
                
                # 检查各表数据量
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
                            self.result.add_info(f"{table_name}: {count} 条记录 (品种: {len(symbols)})")
                        else:
                            self.result.add_info(f"{table_name}: {count} 条记录")
                            
                    except Exception as e:
                        issues.append(f"检查 {table_name} 时出错: {e}")
                
                if issues:
                    for issue in issues:
                        self.result.add_warning(issue)
                
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
                    
                    if candidate_symbols and not pipeline_symbols:
                        self.result.add_warning("有候选因子但无验证流程数据")
                    
                    if task_symbols and not candidate_symbols:
                        self.result.add_warning("有进化任务但无候选因子")
                    
                    all_symbols = pipeline_symbols | candidate_symbols | task_symbols
                    if all_symbols:
                        self.result.add_info(f"系统涉及品种: {', '.join(sorted(all_symbols))}")
                    
                except Exception as e:
                    self.result.add_warning(f"检查品种一致性时出错: {e}")
                
                # 检查数据逻辑一致性
                try:
                    pipeline_data = session.execute(select(ValidationPipelineData)).scalars().all()
                    for data in pipeline_data:
                        if data.search_output > data.search_input:
                            self.result.add_error(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                               f"search_output({data.search_output}) > search_input({data.search_input})")
                        
                        if data.replay_output > data.replay_input:
                            self.result.add_error(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                               f"replay_output({data.replay_output}) > replay_input({data.replay_input})")
                        
                        if data.validation_output > data.validation_input:
                            self.result.add_error(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                               f"validation_output({data.validation_output}) > validation_input({data.validation_input})")
                        
                        if data.demo_output > data.demo_input:
                            self.result.add_error(f"验证流程数据错误: {data.symbol} 第{data.generation}代 "
                                               f"demo_output({data.demo_output}) > demo_input({data.demo_input})")
                            
                except Exception as e:
                    self.result.add_warning(f"检查数据逻辑一致性时出错: {e}")
                
                self.result.add_info(f"数据完整性检查完成，总记录数: {total_records}")
                return len(self.result.errors) == 0
                
        except Exception as e:
            self.result.add_error(f"数据完整性检查失败: {e}")
            return False
    
    def check_system_resources(self) -> bool:
        """检查系统资源"""
        try:
            import psutil
            
            # 检查内存使用
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.result.add_warning(f"内存使用率过高: {memory.percent:.1f}%")
            else:
                self.result.add_info(f"内存使用率: {memory.percent:.1f}%")
            
            # 检查磁盘空间
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                self.result.add_warning(f"磁盘使用率过高: {disk.percent:.1f}%")
            else:
                self.result.add_info(f"磁盘使用率: {disk.percent:.1f}%")
            
            return True
            
        except ImportError:
            self.result.add_info("未安装 psutil，跳过系统资源检查")
            return True
        except Exception as e:
            self.result.add_warning(f"系统资源检查失败: {e}")
            return True
    
    def check_required_services(self) -> bool:
        """检查必需的服务"""
        # 这里可以添加对外部服务的检查
        # 比如Redis、消息队列等
        self.result.add_info("必需服务检查通过")
        return True
    
    def run_all_checks(self) -> bool:
        """运行所有检查"""
        print("🔍 开始执行启动检查...")
        
        checks = [
            ("数据库连接", self.check_database_connection),
            ("表结构", self.check_table_structure),
            ("数据完整性", self.check_data_integrity),
            ("系统资源", self.check_system_resources),
            ("必需服务", self.check_required_services),
        ]
        
        for check_name, check_func in checks:
            try:
                print(f"  检查 {check_name}...")
                check_func()
            except Exception as e:
                self.result.add_error(f"{check_name}检查异常: {e}")
        
        return self.result.print_summary()


def run_startup_checks() -> bool:
    """运行启动检查的入口函数"""
    checker = StartupChecker()
    return checker.run_all_checks()


def run_startup_checks_with_fallback() -> bool:
    """运行启动检查，失败时提供选项"""
    passed = run_startup_checks()
    
    if not passed:
        print("\n🔧 检查失败，您可以选择:")
        print("1. 继续启动（可能存在风险）")
        print("2. 退出并修复问题")
        print("3. 运行数据清理工具")
        
        try:
            choice = input("\n请选择 (1/2/3): ").strip()
            if choice == "1":
                print("⚠️  继续启动，请注意潜在风险")
                return True
            elif choice == "2":
                print("👋 退出程序，请修复问题后重新启动")
                sys.exit(1)
            elif choice == "3":
                print("🧹 启动数据清理工具...")
                from scripts.cleanup.clean_data_simple import clean_all_data
                clean_all_data()
                print("✅ 数据清理完成，请重新启动程序")
                sys.exit(0)
            else:
                print("❌ 无效选择，默认退出")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 用户取消，退出程序")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 处理选择时出错: {e}")
            sys.exit(1)
    
    return passed


if __name__ == "__main__":
    # 直接运行此脚本时执行检查
    success = run_startup_checks_with_fallback()
    sys.exit(0 if success else 1)
