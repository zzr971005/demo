#!/usr/bin/env python3
"""检查数据库中candidates表的数量"""
import sys
import os

# 确保 backend 目录在 sys.path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from app.db import get_session
from app.models import Candidate
from sqlalchemy import select, func

def main():
    with get_session() as session:
        # 总数
        total = session.execute(select(func.count()).select_from(Candidate)).scalar()
        print(f'Total candidates: {total}')
        
        # 按品种统计
        rb_count = session.execute(
            select(func.count()).select_from(Candidate).where(Candidate.symbol == 'RB')
        ).scalar()
        print(f'RB candidates: {rb_count}')
        
        # 查看最近的几个因子
        recent = session.execute(
            select(Candidate).order_by(Candidate.created_at.desc()).limit(10)
        ).scalars().all()
        
        print('\nRecent candidates:')
        for c in recent:
            print(f'  - ID: {c.id}, symbol: {c.symbol}, sharpe_train: {c.sharpe_train}, calmar: {c.calmar}, sharpe_val: {c.sharpe_val}, created_at: {c.created_at}')

if __name__ == '__main__':
    main()
