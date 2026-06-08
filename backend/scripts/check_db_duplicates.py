import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_session
from app.models import Candidate
from sqlalchemy import select, func
from collections import Counter

with get_session() as session:
    result = session.execute(select(Candidate.formula))
    formulas = [r[0] for r in result if r[0]]
    counts = Counter(formulas)

    print(f'总因子数: {len(formulas)}')
    print(f'唯一表达式数: {len(counts)}')
    if len(formulas) > 0:
        print(f'重复率: {(len(formulas) - len(counts)) / len(formulas) * 100:.2f}%')
    else:
        print('重复率: N/A (无数据)')

    print('\n重复最多的表达式:')
    for expr, count in counts.most_common(10):
        if count > 1:
            print(f'  {expr} ({count}次)')
