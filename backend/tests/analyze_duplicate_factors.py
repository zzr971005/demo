"""分析重复性能指标的因子"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.models import Candidate
from app.db import get_session
from sqlalchemy import select, desc
from collections import Counter, defaultdict

print("=== 分析重复性能指标的因子 ===")

with get_session() as session:
    # 查询所有RB因子
    stmt = select(Candidate).where(Candidate.symbol == "RB").order_by(desc(Candidate.sharpe_train))
    candidates = session.execute(stmt).scalars().all()
    
    # 按性能指标分组
    perf_groups = defaultdict(list)
    for c in candidates:
        sig = (c.sharpe_train, c.calmar, c.max_drawdown, c.total_return, c.total_trades, c.win_rate)
        perf_groups[sig].append(c)
    
    # 找出重复的组
    duplicates = [(sig, factors) for sig, factors in perf_groups.items() if len(factors) > 1]
    
    print(f"总因子数: {len(candidates)}")
    print(f"重复组数: {len(duplicates)}")
    
    # 分析最大的重复组
    if duplicates:
        duplicates.sort(key=lambda x: len(x[1]), reverse=True)
        sig, factors = duplicates[0]
        print(f"\n最大重复组: {len(factors)} 个因子")
        print(f"性能指标: Sharpe={sig[0]:.4f}, Calmar={sig[1]:.4f}, TotalTrades={sig[4]}")
        
        # 检查公式唯一性
        formulas = [f.formula for f in factors]
        unique_formulas = set(formulas)
        print(f"唯一公式数: {len(unique_formulas)}")
        
        # 显示前10个公式
        print("\n前10个公式:")
        for i, f in enumerate(factors[:10]):
            print(f"{i+1}. {f.formula}")
        
        # 如果公式不同但性能相同，说明因子值相同
        if len(unique_formulas) > 1:
            print(f"\n*** 警告: {len(unique_formulas)} 个不同公式产生相同性能指标 ***")
            print("可能原因: 浮点参数被截断导致因子值相同")
