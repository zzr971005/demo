#!/usr/bin/env python3
"""
修复脚本：重新计算 avg_trade_return

问题：之前的回测引擎 bug 导致 avg_trade_return 保存为 0
修复：根据 total_return / total_trades 重新计算
"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.db import get_session
from app.models import Candidate
from sqlalchemy import select, func

def fix_avg_trade_return():
    """重新计算 avg_trade_return"""
    with get_session() as session:
        # 查找 avg_trade_return = 0 但 total_trades > 0 的记录
        candidates = session.execute(
            select(Candidate).where(
                Candidate.avg_trade_return == 0,
                Candidate.total_trades > 0
            )
        ).scalars().all()
        
        print(f"找到 {len(candidates)} 条需要修复的记录")
        
        fixed_count = 0
        for c in candidates:
            # 重新计算 avg_trade_return
            if c.total_trades > 0:
                new_avg = c.total_return / c.total_trades
                print(f"修复: {c.id[:40]}...")
                print(f"  total_return={c.total_return}, total_trades={c.total_trades}")
                print(f"  avg_trade_return: {c.avg_trade_return} -> {new_avg}")
                c.avg_trade_return = new_avg
                fixed_count += 1
        
        print(f"\n成功修复 {fixed_count} 条记录")

if __name__ == "__main__":
    fix_avg_trade_return()
