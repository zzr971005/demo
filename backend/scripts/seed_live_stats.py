"""
插入实盘统计数据
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quant_engine.core.models.evolution import (
    get_db_session,
    FactorLiveStat,
)


def seed_live_stats():
    """插入实盘统计数据"""
    print("正在插入实盘统计数据...")
    
    with get_db_session() as session:
        # 为实盘因子创建统计记录
        live_stat = FactorLiveStat(
            factor_id="FACTOR_RB_LIVE_001",
            symbol="RB",
            live_sharpe_ratio=1.9,  # 略低于回测，模拟衰减
            live_total_return=0.28,
            live_max_drawdown=0.13,
            live_win_rate=0.56,
            live_total_trades=80,
            bt_sharpe_ratio=2.0,  # 回测夏普
            bt_total_return=0.30,
            bt_max_drawdown=0.12,
            performance_decay=0.05,  # 5%衰减
            days_running=7,
            is_active=True,
        )
        session.add(live_stat)
        
        print("实盘统计数据插入完成！")
        
        # 统计
        stat_count = session.query(FactorLiveStat).count()
        print(f"\n实盘统计记录数: {stat_count}")


if __name__ == "__main__":
    seed_live_stats()
