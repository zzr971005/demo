"""
清理数据库中因回测引擎溢出产生的脏数据。

清理范围：
1. candidates: 异常的 total_return, calmar, sharpe, max_drawdown, win_rate, pbo, dsr, wfe
2. evolution_tasks: 异常的 best_fitness, best_sharpe, avg_sharpe
3. baseline_comparison_results: 异常的 strategy_return, strategy_calmar 等
4. generation_stats: 异常的 avg_fitness, best_fitness, max_sharpe
"""

import os
import sys

# 确保 backend 目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, delete
from app.db import engine, get_session
from app.models import (
    Candidate,
    EvolutionTask,
    BaselineComparisonResult,
    GenerationStats,
)


def clean_candidates():
    """清理 candidates 表异常数据"""
    print("\n[1/4] 清理 candidates 表...")

    with get_session() as session:
        # total_return 超出 [-100, 100] 的设为 NULL（与 engine.py cap 一致）
        result = session.execute(
            text("""
                UPDATE candidates
                SET total_return = NULL
                WHERE total_return IS NOT NULL
                  AND (total_return < -100 OR total_return > 100)
            """)
        )
        total_return_count = result.rowcount

        # calmar 超出 [-100, 100] 的设为 NULL（与 engine.py cap 一致）
        result = session.execute(
            text("""
                UPDATE candidates
                SET calmar = NULL
                WHERE calmar IS NOT NULL
                  AND (calmar < -100 OR calmar > 100)
            """)
        )
        calmar_count = result.rowcount

        # sharpe_test 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE candidates
                SET sharpe_test = NULL
                WHERE sharpe_test IS NOT NULL
                  AND (sharpe_test < -100 OR sharpe_test > 100)
            """)
        )
        sharpe_test_count = result.rowcount

        # sharpe_val 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE candidates
                SET sharpe_val = NULL
                WHERE sharpe_val IS NOT NULL
                  AND (sharpe_val < -100 OR sharpe_val > 100)
            """)
        )
        sharpe_val_count = result.rowcount

        # sharpe_train 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE candidates
                SET sharpe_train = NULL
                WHERE sharpe_train IS NOT NULL
                  AND (sharpe_train < -100 OR sharpe_train > 100)
            """)
        )
        sharpe_train_count = result.rowcount

        # max_drawdown 超出 [0, 1] 的设为 NULL（正常最大回撤应在0-1之间）
        result = session.execute(
            text("""
                UPDATE candidates
                SET max_drawdown = NULL
                WHERE max_drawdown IS NOT NULL
                  AND (max_drawdown < 0 OR max_drawdown > 1)
            """)
        )
        max_dd_count = result.rowcount

        # win_rate 超出 [0, 1] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE candidates
                SET win_rate = NULL
                WHERE win_rate IS NOT NULL
                  AND (win_rate < 0 OR win_rate > 1)
            """)
        )
        win_rate_count = result.rowcount

        # pbo 超出 [0, 1] 的设为 NULL（概率值）
        result = session.execute(
            text("""
                UPDATE candidates
                SET pbo = NULL
                WHERE pbo IS NOT NULL
                  AND (pbo < 0 OR pbo > 1)
            """)
        )
        pbo_count = result.rowcount

        # dsr 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE candidates
                SET dsr = NULL
                WHERE dsr IS NOT NULL
                  AND (dsr < -100 OR dsr > 100)
            """)
        )
        dsr_count = result.rowcount

        # wfe 超出 [0, 10] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE candidates
                SET wfe = NULL
                WHERE wfe IS NOT NULL
                  AND (wfe < 0 OR wfe > 10)
            """)
        )
        wfe_count = result.rowcount

    print(f"  total_return 异常 -> NULL: {total_return_count} 条")
    print(f"  calmar 异常 -> NULL: {calmar_count} 条")
    print(f"  sharpe_test 异常 -> NULL: {sharpe_test_count} 条")
    print(f"  sharpe_val 异常 -> NULL: {sharpe_val_count} 条")
    print(f"  sharpe_train 异常 -> NULL: {sharpe_train_count} 条")
    print(f"  max_drawdown 异常 -> NULL: {max_dd_count} 条")
    print(f"  win_rate 异常 -> NULL: {win_rate_count} 条")
    print(f"  pbo 异常 -> NULL: {pbo_count} 条")
    print(f"  dsr 异常 -> NULL: {dsr_count} 条")
    print(f"  wfe 异常 -> NULL: {wfe_count} 条")


def clean_evolution_tasks():
    """清理 evolution_tasks 表异常数据"""
    print("\n[2/4] 清理 evolution_tasks 表...")

    with get_session() as session:
        # best_fitness 超出 [-1e6, 1e6] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE evolution_tasks
                SET best_fitness = NULL
                WHERE best_fitness IS NOT NULL
                  AND (best_fitness < -1000000 OR best_fitness > 1000000)
            """)
        )
        best_fitness_count = result.rowcount

        # best_sharpe 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE evolution_tasks
                SET best_sharpe = NULL
                WHERE best_sharpe IS NOT NULL
                  AND (best_sharpe < -100 OR best_sharpe > 100)
            """)
        )
        best_sharpe_count = result.rowcount

        # avg_sharpe 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE evolution_tasks
                SET avg_sharpe = NULL
                WHERE avg_sharpe IS NOT NULL
                  AND (avg_sharpe < -100 OR avg_sharpe > 100)
            """)
        )
        avg_sharpe_count = result.rowcount

    print(f"  best_fitness 异常 -> NULL: {best_fitness_count} 条")
    print(f"  best_sharpe 异常 -> NULL: {best_sharpe_count} 条")
    print(f"  avg_sharpe 异常 -> NULL: {avg_sharpe_count} 条")


def clean_baseline_comparison():
    """清理 baseline_comparison_results 表异常数据"""
    print("\n[3/4] 清理 baseline_comparison_results 表...")

    with get_session() as session:
        # strategy_return 超出 [-1e6, 1e6] 的删除（此表数据可以重新计算）
        result = session.execute(
            text("""
                DELETE FROM baseline_comparison_results
                WHERE strategy_return < -1000000
                   OR strategy_return > 1000000
                   OR strategy_calmar < -1000
                   OR strategy_calmar > 1000
                   OR strategy_sharpe < -100
                   OR strategy_sharpe > 100
            """)
        )
        delete_count = result.rowcount

    print(f"  删除异常记录: {delete_count} 条")


def clean_generation_stats():
    """清理 generation_stats 表异常数据"""
    print("\n[4/4] 清理 generation_stats 表...")

    with get_session() as session:
        # avg_fitness 超出 [-1e6, 1e6] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET avg_fitness = NULL
                WHERE avg_fitness IS NOT NULL
                  AND (avg_fitness < -1000000 OR avg_fitness > 1000000)
            """)
        )
        avg_fitness_count = result.rowcount

        # best_fitness 超出 [-1e6, 1e6] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET best_fitness = NULL
                WHERE best_fitness IS NOT NULL
                  AND (best_fitness < -1000000 OR best_fitness > 1000000)
            """)
        )
        best_fitness_count = result.rowcount

        # max_sharpe 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET max_sharpe = NULL
                WHERE max_sharpe IS NOT NULL
                  AND (max_sharpe < -100 OR max_sharpe > 100)
            """)
        )
        max_sharpe_count = result.rowcount

        # avg_sharpe 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET avg_sharpe = NULL
                WHERE avg_sharpe IS NOT NULL
                  AND (avg_sharpe < -100 OR avg_sharpe > 100)
            """)
        )
        avg_sharpe_count = result.rowcount

        # min_sharpe 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET min_sharpe = NULL
                WHERE min_sharpe IS NOT NULL
                  AND (min_sharpe < -100 OR min_sharpe > 100)
            """)
        )
        min_sharpe_count = result.rowcount

        # top_10_avg_sharpe 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET top_10_avg_sharpe = NULL
                WHERE top_10_avg_sharpe IS NOT NULL
                  AND (top_10_avg_sharpe < -100 OR top_10_avg_sharpe > 100)
            """)
        )
        top10_count = result.rowcount

        # pbo 超出 [0, 1] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET pbo = NULL
                WHERE pbo IS NOT NULL
                  AND (pbo < 0 OR pbo > 1)
            """)
        )
        pbo_count = result.rowcount

        # dsr 超出 [-100, 100] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET dsr = NULL
                WHERE dsr IS NOT NULL
                  AND (dsr < -100 OR dsr > 100)
            """)
        )
        dsr_count = result.rowcount

        # wfe 超出 [0, 10] 的设为 NULL
        result = session.execute(
            text("""
                UPDATE generation_stats
                SET wfe = NULL
                WHERE wfe IS NOT NULL
                  AND (wfe < 0 OR wfe > 10)
            """)
        )
        wfe_count = result.rowcount

    print(f"  avg_fitness 异常 -> NULL: {avg_fitness_count} 条")
    print(f"  best_fitness 异常 -> NULL: {best_fitness_count} 条")
    print(f"  max_sharpe 异常 -> NULL: {max_sharpe_count} 条")
    print(f"  avg_sharpe 异常 -> NULL: {avg_sharpe_count} 条")
    print(f"  min_sharpe 异常 -> NULL: {min_sharpe_count} 条")
    print(f"  top_10_avg_sharpe 异常 -> NULL: {top10_count} 条")
    print(f"  pbo 异常 -> NULL: {pbo_count} 条")
    print(f"  dsr 异常 -> NULL: {dsr_count} 条")
    print(f"  wfe 异常 -> NULL: {wfe_count} 条")


def show_summary():
    """显示清理后摘要"""
    print("\n" + "=" * 50)
    print("清理完成！数据库异常数据已处理。")
    print("=" * 50)
    print("\n下一步操作：")
    print("  1. 重启后端服务（start_panel.bat）")
    print("  2. 重启进化引擎（start_evolution.bat）")
    print("  3. 刷新前端页面（Ctrl+F5）")
    print("\n注意：")
    print("  - candidates 表中异常记录保留了 formula 和基本信息")
    print("  - 只有异常指标字段被设为 NULL，不会丢失因子公式")
    print("  - baseline_comparison_results 的异常记录已删除（可重新计算）")


if __name__ == "__main__":
    print("=" * 50)
    print("  期货自动进化因子挖掘系统 - 数据库脏数据清理")
    print("=" * 50)

    clean_candidates()
    clean_evolution_tasks()
    clean_baseline_comparison()
    clean_generation_stats()
    show_summary()
