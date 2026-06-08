"""
快速开始：遗传编程因子挖掘

使用进化中心进行因子挖掘的完整示例
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from datetime import datetime

from quant_engine.ops.evolution_center import (
    EvolutionCenter,
    EvolutionTaskConfig,
    EvolutionScheduler,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def example_single_task():
    """单任务进化示例"""
    print("=" * 70)
    print("示例1: 单任务进化")
    print("=" * 70)
    
    # 创建任务配置
    config = EvolutionTaskConfig(
        task_id=f"RB_factor_{datetime.now().strftime('%Y%m%d')}",
        symbol="RB",
        description="螺纹钢Alpha因子挖掘",
        
        # 进化参数
        population_size=50,      # 种群大小
        max_generations=10,      # 最大代数
        max_stagnation=5,         # 停滞代数
        
        # 过拟合检验
        enable_overfitting_check=True,
        pbo_threshold=0.3,
        dsr_threshold=0.6,
        wfe_threshold=0.7,
        
        # 回测参数
        init_capital=1_000_000,
        position_size_pct=0.95,
        contract_value_per_lot=50000,
        
        # 输出
        save_top_n=20,
        save_path="./output/factors",
    )
    
    print(f"任务ID: {config.task_id}")
    print(f"品种: {config.symbol}")
    print(f"种群大小: {config.population_size}")
    print(f"最大代数: {config.max_generations}")
    print()
    
    # 创建进化中心
    center = EvolutionCenter(config)
    
    # 注册回调
    def on_generation(gen, stats):
        progress = (gen + 1) / config.max_generations * 100
        print(f"  [{progress:5.1f}%] 第{gen:2d}代 | "
              f"最佳夏普: {stats.max_sharpe:.4f} | "
              f"平均夏普: {stats.mean_sharpe:.4f} | "
              f"有效个体: {stats.valid_count}/{stats.population_size}")
    
    center.on_generation_complete = on_generation
    
    # 运行进化
    print("开始进化...\n")
    result = center.run_evolution()
    
    # 输出结果
    print("\n" + "=" * 70)
    print("进化完成!")
    print("=" * 70)
    print(f"总耗时: {result.total_time:.2f}秒")
    print(f"总代数: {result.total_generations}")
    print(f"最佳适应度: {result.best_fitness:.4f}")
    print(f"最佳夏普: {result.best_sharpe:.4f}")
    
    # 展示最佳因子
    print("\n" + "=" * 70)
    print("最佳因子 (Top 5)")
    print("=" * 70)
    
    best_factors = center.get_best_factors(n=5, only_passed=False)
    
    for i, factor in enumerate(best_factors, 1):
        status = "✓ 通过" if factor.overfitting_passed else "✗ 未通过"
        print(f"\n#{i}: {factor.factor_id} [{status}]")
        print(f"   表达式: {factor.expression}")
        print(f"   夏普比率: {factor.sharpe:.4f} | Calmar: {factor.calmar:.4f}")
        print(f"   总收益: {factor.total_return:.2%} | 最大回撤: {factor.max_drawdown:.2%}")
        print(f"   胜率: {factor.win_rate:.2%} | 交易次数: {factor.total_trades}")
        print(f"   复杂度: {factor.node_count}节点 | 深度: {factor.tree_depth}")
        if factor.pbo is not None:
            print(f"   PBO: {factor.pbo:.4f} | DSR: {factor.dsr:.4f} | WFE: {factor.wfe:.4f}")
    
    # 展示进化历史
    print("\n" + "=" * 70)
    print("进化历史")
    print("=" * 70)
    
    import pandas as pd
    history_df = pd.DataFrame([s.to_dict() for s in result.history])
    print(history_df[["generation", "max_sharpe", "mean_sharpe", "valid_count", 
                       "unique_expressions", "total_time"]])
    
    print("\n" + "=" * 70)
    print(f"结果已保存到: {config.save_path}")
    print("=" * 70)


def example_multi_task():
    """多任务调度示例"""
    print("\n" + "=" * 70)
    print("示例2: 多任务调度")
    print("=" * 70)
    
    scheduler = EvolutionScheduler()
    
    # 创建多个品种的任务
    symbols = ["RB", "MA", "AG"]
    for symbol in symbols:
        config = EvolutionTaskConfig(
            task_id=f"{symbol}_factor_{datetime.now().strftime('%Y%m%d')}",
            symbol=symbol,
            population_size=30,
            max_generations=5,
            save_path="./output/factors",
            description=f"{symbol}因子挖掘",
        )
        scheduler.create_task(config)
        print(f"✓ 创建任务: {config.task_id} ({symbol})")
    
    print(f"\n待执行任务: {len(scheduler.get_all_tasks())}")
    
    # 运行所有任务
    print("\n开始执行任务...\n")
    results = scheduler.run_all_tasks()
    
    # 输出结果
    print("\n" + "=" * 70)
    print("任务执行汇总")
    print("=" * 70)
    
    for task_id, result in results.items():
        if result is not None:
            print(f"✓ {task_id}: 最佳夏普={result.best_sharpe:.4f}, "
                  f"耗时={result.total_time:.1f}秒")
        else:
            print(f"✗ {task_id}: 执行失败")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("期货自动进化因子挖掘系统 - 遗传编程示例")
    print("=" * 70)
    print()
    
    # 示例1: 单任务进化
    example_single_task()
    
    # 示例2: 多任务调度 (可选)
    # example_multi_task()
    
    print("\n示例运行完成!")


if __name__ == "__main__":
    main()
