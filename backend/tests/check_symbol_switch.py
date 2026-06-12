"""检查symbol_switches表状态"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.models import SymbolSwitch, SymbolMode
from app.db import get_session
from sqlalchemy import select

print("=== 检查symbol_switches表状态 ===")

with get_session() as session:
    # 查询所有symbol_switch
    stmt = select(SymbolSwitch)
    switches = session.execute(stmt).scalars().all()
    
    print(f"总品种数: {len(switches)}")
    
    for switch in switches:
        print(f"品种: {switch.symbol}, 模式: {switch.mode}")
