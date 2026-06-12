"""
端到端进化测试

测试完整的遗传编程进化流程：
1. 创建进化任务配置
2. 初始化进化中心
3. 运行完整进化流程
4. 检查过拟合检验结果
5. 验证输出因子
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import tempfile
import time
from datetime import datetime

import numpy as np
import pandas as pd

from quant_engine.ops.evolution_center import (
    EvolutionCenter,
    EvolutionTaskConfig,
    EvolutionScheduler,
    FactorRecord,
)
from quant_engine.ops.gp_evolution import GenerationStats

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def test_task_config():
    """测试任务配置"""
    print("=" * 70)
    print("测试1: 任务配置创建")
    print("=" * 70)
    
    config = EvolutionTaskConfig(
        task_id="test_evolution_001",
        symbol="RB",
        description="螺纹钢因子进化测试",
        population_size=20,  # 小种群用于测试
        max_generations=3,    # 少代数用于测试
        max_stagnation=5,
        enable_overfitting_check=True,
        pbo_threshold=0.3,
        dsr_threshold=0.6,
        wfe_threshold=0.7,
        save_top_n=10,
        save_path=tempfile.gettempdir(),
    )
    
    print(f"任务ID: {config.task_id}")
    print(f"品种: {config.symbol}")
    print(f"种群大小: {config.population_size}")
    print(f"最大代数: {config.max_generations}")
    print(f"启用过拟合检查: {config.enable_overfitting_check}")
    print(f"PBO阈值: {config.pbo_threshold}")
    print(f"DSR阈值: {config.dsr_threshold}")
    print(f"WFE阈值: {config.wfe_threshold}")
    
    config_dict = config.to_dict()
    assert "task_id" in config_dict
    assert "population_size" in config_dict
    assert "max_generations" in config_dict
    
    print("✓ 通过!")
    return True


def test_evolution_center_init():
    """测试进化中心初始化"""
    print("\n" + "=" * 70)
    print("测试2: 进化中心初始化")
    print("=" * 70)
    
    config = EvolutionTaskConfig(
        task_id="test_evolution_002",
        symbol="RB",
        population_size=20,
        max_generations=3,
    )
    
    center = EvolutionCenter(config)
    
    assert center.task_config.task_id == "test_evolution_002"
    assert center.evolution_config.population_size == 20
    assert center.evolution_config.max_generations == 3
    assert center.overfitting_checker is not None
    assert not center.is_running
    
    print(f"✓ 进化中心创建成功")
    print(f"✓ 种群大小: {center.evolution_config.population_size}")
    print(f"✓ 过拟合检查器: {center.overfitting_checker}")
    print("✓ 通过!")
    return True


def test_evolution_process():
    """测试完整进化流程"""
    print("\n" + "=" * 70)
    print("测试3: 完整进化流程")
    print("=" * 70)
    
    config = EvolutionTaskConfig(
        task_id="test_evolution_003",
        symbol="RB",
        population_size=20,
        max_generations=3,
        enable_overfitting_check=True,
        save_top_n=5,
        save_path=tempfile.gettempdir(),
    )
    
    center = EvolutionCenter(config)
    
    # 注册回调
    generations_completed = []
    
    def on_generation(gen: int, stats: GenerationStats):
        generations_completed.append(gen)
        print(f"  第{gen}代完成 | 最佳夏普: {stats.max_sharpe:.4f} | "
              f"有效个体: {stats.valid_count}/{stats.population_size}")
    
    center.on_generation_complete = on_generation
    
    # 运行进化
    start_time = time.time()
    result = center.run_evolution()
    elapsed = time.time() - start_time
    
    print(f"\n进化完成! 耗时: {elapsed:.2f}秒")
    print(f"总代数: {result.total_generations}")
    print(f"最佳适应度: {result.best_fitness:.4f}")
    print(f"最佳夏普: {result.best_sharpe:.4f}")
    print(f"最终种群大小: {len(result.final_population)}")
    print(f"最佳个体数量: {len(result.best_individuals)}")
    
    # 验证结果
    assert result.total_generations == 3
    assert len(result.history) == 3
    
    # 验证进化历史
    history_df = pd.DataFrame([s.to_dict() for s in result.history])
    print(f"\n进化历史:")
    print(history_df[["generation", "max_sharpe", "mean_sharpe", "valid_count"]])
    
    # 验证最佳个体
    unique_best = result.get_unique_best(n=5)
    print(f"\n唯一最佳个体数量: {len(unique_best)}")
    for i, ind in enumerate(unique_best[:3]):
        print(f"  #{i+1}: 夏普={ind.fitness.get('sharpe', 0):.4f}, "
              f"节点数={ind.get_node_count()}, 表达式={ind.to_expression()[:60]}...")
    
    # 验证最终因子
    print(f"\n生成因子总数: {len(center.final_factors)}")
    passed_factors = [f for f in center.final_factors if f.overfitting_passed]
    print(f"通过过拟合检验的因子: {len(passed_factors)}")
    
    for factor in center.final_factors[:3]:
        print(f"  {factor.factor_id}: 夏普={factor.sharpe:.4f}, "
              f"DSR={factor.dsr:.4f}, 通过={factor.overfitting_passed}")
    
    print("\n✓ 通过!")
    return True


def test_scheduler():
    """测试任务调度器"""
    print("\n" + "=" * 70)
    print("测试4: 任务调度器")
    print("=" * 70)
    
    scheduler = EvolutionScheduler()
    
    # 创建多个任务
    config1 = EvolutionTaskConfig(
        task_id="test_sched_001",
        symbol="RB",
        population_size=10,
        max_generations=2,
        save_path=tempfile.gettempdir(),
    )
    
    config2 = EvolutionTaskConfig(
        task_id="test_sched_002",
        symbol="MA",
        population_size=10,
        max_generations=2,
        save_path=tempfile.gettempdir(),
    )
    
    task_id1 = scheduler.create_task(config1)
    task_id2 = scheduler.create_task(config2)
    
    print(f"创建任务: {task_id1}, {task_id2}")
    print(f"待执行任务: {scheduler.get_all_tasks()}")
    
    assert len(scheduler.get_all_tasks()) == 2
    
    # 运行第一个任务
    print(f"\n运行任务: {task_id1}")
    result1 = scheduler.run_task(task_id1)
    assert result1 is not None
    
    print(f"任务1完成, 最佳夏普: {result1.best_sharpe:.4f}")
    
    # 检查任务状态
    status = scheduler.get_task_status(task_id1)
    print(f"任务1状态: {status}")
    assert status is not None
    assert not status["is_running"]
    
    # 检查已完成任务
    assert task_id1 in scheduler.completed_tasks
    assert task_id2 in scheduler.tasks
    
    print(f"\n待执行任务: {list(scheduler.tasks.keys())}")
    print(f"已完成任务: {list(scheduler.completed_tasks.keys())}")
    
    print("\n✓ 通过!")
    return True


def test_factor_record():
    """测试因子记录"""
    print("\n" + "=" * 70)
    print("测试5: 因子记录")
    print("=" * 70)
    
    record = FactorRecord(
        factor_id="factor_001",
        expression="ts_mean(close, 20) - ts_std(close, 20)",
        symbol="RB",
        generation=10,
        origin="crossover",
        sharpe=1.85,
        calmar=2.34,
        max_drawdown=0.15,
        total_return=0.45,
        win_rate=0.55,
        total_trades=120,
        avg_trade_pnl=2500.0,
        turnover_rate=0.05,
        pbo=0.2,
        dsr=0.75,
        wfe=0.85,
        overfitting_passed=True,
        node_count=8,
        tree_depth=4,
    )
    
    print(f"因子ID: {record.factor_id}")
    print(f"表达式: {record.expression}")
    print(f"夏普比率: {record.sharpe:.4f}")
    print(f"Calmar: {record.calmar:.4f}")
    print(f"最大回撤: {record.max_drawdown:.4f}")
    print(f"PBO: {record.pbo}")
    print(f"DSR: {record.dsr}")
    print(f"WFE: {record.wfe}")
    print(f"过拟合检验通过: {record.overfitting_passed}")
    
    record_dict = record.to_dict()
    assert record_dict["factor_id"] == "factor_001"
    assert record_dict["sharpe"] == 1.85
    assert record_dict["overfitting_passed"] == True
    
    print("\n✓ 通过!")
    return True


def test_evolution_progress():
    """测试进化进度跟踪"""
    print("\n" + "=" * 70)
    print("测试6: 进化进度跟踪")
    print("=" * 70)
    
    config = EvolutionTaskConfig(
        task_id="test_progress_001",
        symbol="RB",
        population_size=15,
        max_generations=3,
        save_path=tempfile.gettempdir(),
    )
    
    center = EvolutionCenter(config)
    
    # 初始进度
    progress = center.get_progress()
    print(f"初始进度: {progress['progress_pct']:.1f}%")
    print(f"当前代数: {progress['current_generation']}")
    print(f"运行中: {progress['is_running']}")
    
    assert progress["is_running"] == False
    assert progress["current_generation"] == 0
    
    # 运行进化
    center.run_evolution()
    
    # 最终进度
    progress = center.get_progress()
    print(f"\n最终进度: {progress['progress_pct']:.1f}%")
    print(f"当前代数: {progress['current_generation']}")
    print(f"最佳适应度: {progress['best_fitness']:.4f}")
    
    assert progress["is_running"] == False
    assert progress["current_generation"] == 2  # 0-based
    
    # 获取摘要
    summary = center.get_evolution_summary()
    print(f"\n进化摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    assert summary["total_generations"] == 3
    assert "total_factors" in summary
    assert "passed_factors" in summary
    
    print("\n✓ 通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("遗传编程进化系统 - 端到端测试")
    print("=" * 70)
    
    tests = [
        ("任务配置创建", test_task_config),
        ("进化中心初始化", test_evolution_center_init),
        ("完整进化流程", test_evolution_process),
        ("任务调度器", test_scheduler),
        ("因子记录", test_factor_record),
        ("进化进度跟踪", test_evolution_progress),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ 测试失败: {name}")
        except Exception as e:
            failed += 1
            print(f"❌ 测试异常: {name}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
