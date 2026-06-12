"""停用RB品种"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.models import SymbolSwitch, SymbolMode
from app.db import get_session
from sqlalchemy import select

print("=== 停用RB品种 ===")

with get_session() as session:
    # 查询RB的symbol_switch
    stmt = select(SymbolSwitch).where(SymbolSwitch.symbol == "RB")
    switch = session.execute(stmt).scalars().first()
    
    if switch:
        print(f"当前RB模式: {switch.mode}")
        switch.mode = SymbolMode.OFF
        session.commit()
        print(f"已将RB模式设置为: {switch.mode}")
    else:
        print("RB品种不存在于symbol_switches表中")

print("\n等待进化引擎停止...")
