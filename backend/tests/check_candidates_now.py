"""再次检查candidates表内容"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.models import Candidate
from app.db import get_session
from sqlalchemy import select, desc

print("=== 再次检查candidates表内容 ===")

with get_session() as session:
    # 查询RB的所有因子
    stmt = select(Candidate).where(Candidate.symbol == "RB").order_by(desc(Candidate.created_at))
    candidates = session.execute(stmt).scalars().all()
    
    print(f"RB因子总数: {len(candidates)}")
    
    if candidates:
        print("\n最新的5个因子:")
        for i, c in enumerate(candidates[:5]):
            print(f"\n{i+1}. ID: {c.id}")
            print(f"   公式: {c.formula}")
            print(f"   状态: {c.status}")
            print(f"   世代: {c.generation}")
            print(f"   Sharpe: {c.sharpe_train}")
            print(f"   Calmar: {c.calmar}")
            print(f"   Max Drawdown: {c.max_drawdown}")
            print(f"   Total Return: {c.total_return}")
            print(f"   Total Trades: {c.total_trades}")
            print(f"   Win Rate: {c.win_rate}")
            print(f"   创建时间: {c.created_at}")
    else:
        print("candidates表中没有RB因子")

print("\n=== 完成 ===")
