"""检查数据库中的种子数据"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.models import Candidate
from app.db import get_session
from sqlalchemy import select, desc

print("=== 检查数据库中的种子数据 ===")

with get_session() as session:
    # 查询RB的所有因子
    stmt = select(Candidate).where(Candidate.symbol == "RB").order_by(desc(Candidate.sharpe_train))
    candidates = session.execute(stmt).scalars().all()
    
    print(f"RB因子总数: {len(candidates)}")
    
    if candidates:
        # 检查公式唯一性
        formulas = [c.formula for c in candidates]
        unique_formulas = set(formulas)
        print(f"唯一公式数量: {len(unique_formulas)}")
        
        # 检查性能指标唯一性
        performance_signatures = []
        for c in candidates:
            sig = (c.sharpe_train, c.calmar, c.max_drawdown, c.total_return, c.total_trades, c.win_rate)
            performance_signatures.append(sig)
        
        unique_performances = set(performance_signatures)
        print(f"唯一性能指标数量: {len(unique_performances)}")
        
        # 找出重复的性能指标
        from collections import Counter
        perf_counter = Counter(performance_signatures)
        duplicates = [(sig, count) for sig, count in perf_counter.items() if count > 1]
        
        if duplicates:
            print(f"\n发现 {len(duplicates)} 组重复的性能指标:")
            for sig, count in duplicates[:5]:
                print(f"  Sharpe={sig[0]:.4f}, Calmar={sig[1]:.4f}, 重复次数={count}")
        
        # 检查状态分布
        from collections import Counter
        status_counter = Counter([c.status for c in candidates])
        print(f"\n状态分布: {dict(status_counter)}")
        
        # 显示前10个因子
        print("\n前10个因子:")
        for i, c in enumerate(candidates[:10]):
            print(f"{i+1}. {c.formula[:50]}... Sharpe={c.sharpe_train:.4f}, Status={c.status}")
    else:
        print("数据库中没有RB因子")

print("\n=== 完成 ===")
