"""激活品种的进化模式"""
import sys
import os
from datetime import datetime

# 确保 backend 目录在 sys.path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from app.db import get_session
from app.models import SymbolSwitch, SymbolMode
from sqlalchemy import select, update

def activate_symbol(symbol: str, mode: str = "PAPER"):
    """激活品种的进化模式"""
    try:
        with get_session() as session:
            # 查找记录
            stmt = select(SymbolSwitch).where(SymbolSwitch.symbol == symbol)
            switch = session.execute(stmt).scalars().first()
            
            if switch:
                # 更新模式
                switch.mode = SymbolMode[mode.upper()]
                switch.last_switch_at = datetime.utcnow()
                session.commit()
                print(f"已激活品种 {symbol} 为 {mode} 模式")
            else:
                # 创建新记录
                new_switch = SymbolSwitch(
                    symbol=symbol,
                    mode=SymbolMode[mode.upper()],
                    last_switch_at=datetime.utcnow(),
                )
                session.add(new_switch)
                session.commit()
                print(f"已创建并激活品种 {symbol} 为 {mode} 模式")
                
    except Exception as e:
        print(f"激活失败: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/activate_symbol.py <symbol> [mode]")
        print("示例: python scripts/activate_symbol.py RB PAPER")
        sys.exit(1)
    
    symbol = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "PAPER"
    activate_symbol(symbol, mode)
