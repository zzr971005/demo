"""详细检查数据库中重复因子的公式"""
import sys
sys.path.insert(0, '.')

from app.db import get_session
from app.models import Candidate
from sqlalchemy import select
import pandas as pd

with get_session() as session:
    # 获取所有RB因子
    stmt = select(Candidate).where(Candidate.symbol == 'RB')
    results = session.execute(stmt).scalars().all()

    print(f"总因子数: {len(results)}")

    # 按性能指标分组
    from collections import defaultdict
    groups = defaultdict(list)
    for c in results:
        key = (round(c.sharpe_train, 4), round(c.calmar, 4), c.total_trades)
        groups[key].append(c)

    print(f"\n重复组数: {len([g for g in groups.values() if len(g) > 1])}")

    # 找出最大的重复组
    max_group = max(groups.values(), key=len)
    print(f"\n最大重复组: {len(max_group)} 个因子")
    print(f"性能指标: Sharpe={max_group[0].sharpe_train:.4f}, Calmar={max_group[0].calmar:.4f}, TotalTrades={max_group[0].total_trades}")

    # 检查公式是否真的不同
    formulas = [c.formula for c in max_group]
    unique_formulas = set(formulas)
    print(f"\n唯一公式数: {len(unique_formulas)}")

    if len(unique_formulas) < len(formulas):
        print(f"有 {len(formulas) - len(unique_formulas)} 个完全重复的公式")
        # 找出重复的公式
        from collections import Counter
        formula_counts = Counter(formulas)
        duplicates = {f: c for f, c in formula_counts.items() if c > 1}
        print(f"\n重复的公式:")
        for f, c in duplicates.items():
            print(f"  {f} (重复{c}次)")
    else:
        print(f"所有公式都不同，但产生相同性能指标")

    # 分析共同特征
    print(f"\n=== 分析共同特征 ===")
    has_division = sum(1 for f in formulas if '/' in f)
    has_oi_price_corr = sum(1 for f in formulas if 'oi_price_corr' in f)
    has_ts_min = sum(1 for f in formulas if 'ts_min' in f)
    print(f"包含除法: {has_division}/{len(formulas)}")
    print(f"包含oi_price_corr: {has_oi_price_corr}/{len(formulas)}")
    print(f"包含ts_min: {has_ts_min}/{len(formulas)}")
