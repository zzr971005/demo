"""
检查 symbol_switches 表状态
"""

import sys
import os

# 确保 backend 目录在 sys.path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from app.db import get_session
from app.models import SymbolSwitch, SymbolMode
from sqlalchemy import select

def check_symbol_switches():
    """检查 symbol_switches 表状态"""
    try:
        with get_session() as session:
            stmt = select(SymbolSwitch)
            switches = session.execute(stmt).scalars().all()
            
            if not switches:
                print("symbol_switches 表中没有记录")
                return
            
            print(f"symbol_switches 表中共有 {len(switches)} 条记录:")
            for switch in switches:
                print(f"  - symbol: {switch.symbol}")
                print(f"    mode: {switch.mode}")
                print(f"    last_switch_at: {switch.last_switch_at}")
                print()
                
    except Exception as e:
        print(f"检查失败: {e}")
        raise

if __name__ == "__main__":
    check_symbol_switches()
