"""
插入测试数据用于验证实盘交易功能
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quant_engine.core.models.evolution import (
    get_db_session,
    EvolutionTask,
    EvolutionGeneration,
    EvolutionFactor,
)


def seed_test_data():
    """插入测试数据"""
    print("正在插入测试数据...")
    
    with get_db_session() as session:
        # 创建进化任务
        task = EvolutionTask(
            task_id="TASK_20250101_001",
            symbol="RB",
            description="螺纹钢因子进化测试",
            generations=10,
            population_size=50,
            status="COMPLETED",
            started_at=datetime.now() - timedelta(days=5),
            completed_at=datetime.now() - timedelta(days=4),
        )
        session.add(task)
        session.flush()
        
        # 创建世代记录
        for gen in range(1, 6):
            generation = EvolutionGeneration(
                task_id=task.task_id,
                generation=gen,
                avg_sharpe=0.5 + gen * 0.05,
                max_sharpe=0.8 + gen * 0.03,
                min_sharpe=0.2 + gen * 0.01,
                top_10_sharpe=0.7 + gen * 0.04,
                avg_fitness=0.5 + gen * 0.05,
                best_fitness=0.8 + gen * 0.03,
                diversity_score=0.7 - gen * 0.05,
                unique_expressions=40,
                generation_time_seconds=120,
            )
            session.add(generation)
        
        # 创建候选因子（已通过过拟合检验）
        candidate_factors = [
            {
                "factor_id": "FACTOR_RB_001",
                "expression": "add(mul(close, volume), sma(high, 5))",
                "sharpe_ratio": 1.8,
                "pbo": 0.25,
                "dsr": 0.65,
                "wfe": 0.75,
            },
            {
                "factor_id": "FACTOR_RB_002", 
                "expression": "sub(div(close, open), rsi(close, 14))",
                "sharpe_ratio": 1.5,
                "pbo": 0.28,
                "dsr": 0.62,
                "wfe": 0.72,
            },
            {
                "factor_id": "FACTOR_RB_003",
                "expression": "mul(returns(close, 1), volume)",
                "sharpe_ratio": 1.2,
                "pbo": 0.20,
                "dsr": 0.70,
                "wfe": 0.78,
            },
        ]
        
        for i, factor_data in enumerate(candidate_factors):
            factor = EvolutionFactor(
                factor_id=factor_data["factor_id"],
                task_id=task.task_id,
                symbol="RB",
                expression=factor_data["expression"],
                generation=i + 1,
                origin="crossover",
                node_count=8,
                tree_depth=3,
                sharpe_ratio=factor_data["sharpe_ratio"],
                calmar_ratio=1.2,
                max_drawdown=0.15,
                total_return=0.25,
                win_rate=0.55,
                total_trades=100,
                avg_trade_pnl=100.0,
                turnover_rate=0.3,
                pbo_value=factor_data["pbo"],
                dsr_value=factor_data["dsr"],
                wfe_value=factor_data["wfe"],
                overfitting_passed=True,
                rank_in_generation=1,
                overall_rank=i + 1,
                is_live=False,
                is_candidate=True,
            )
            session.add(factor)
        
        # 创建一个实盘因子
        live_factor = EvolutionFactor(
            factor_id="FACTOR_RB_LIVE_001",
            task_id=task.task_id,
            symbol="RB",
            expression="sma(close, 10)",
            generation=3,
            origin="mutation",
            node_count=3,
            tree_depth=2,
            sharpe_ratio=2.0,
            calmar_ratio=1.5,
            max_drawdown=0.12,
            total_return=0.30,
            win_rate=0.58,
            total_trades=150,
            avg_trade_pnl=120.0,
            turnover_rate=0.25,
            pbo_value=0.22,
            dsr_value=0.68,
            wfe_value=0.80,
            overfitting_passed=True,
            rank_in_generation=1,
            overall_rank=1,
            is_live=True,
            is_candidate=False,
            live_since=datetime.now() - timedelta(days=7),
            last_deployed_at=datetime.now() - timedelta(days=7),
        )
        session.add(live_factor)
        
        print("测试数据插入完成！")
        
        # 统计
        task_count = session.query(EvolutionTask).count()
        factor_count = session.query(EvolutionFactor).count()
        live_count = session.query(EvolutionFactor).filter_by(is_live=True).count()
        candidate_count = session.query(EvolutionFactor).filter_by(is_candidate=True).count()
        
        print(f"\n数据统计:")
        print(f"  任务数: {task_count}")
        print(f"  因子总数: {factor_count}")
        print(f"  实盘因子: {live_count}")
        print(f"  候选因子: {candidate_count}")


if __name__ == "__main__":
    seed_test_data()
