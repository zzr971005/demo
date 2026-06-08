"""检查ID重复问题"""
from app.db import get_session
from app.models import Candidate, EvolutionTask
from sqlalchemy import select, func, desc

with get_session() as session:
    # 检查是否有重复的ID
    print("=== 检查ID重复情况 ===")
    dup_stmt = select(
        Candidate.id,
        func.count(Candidate.id).label('count')
    ).group_by(Candidate.id).having(func.count(Candidate.id) > 1).limit(10)

    dups = session.execute(dup_stmt).all()
    if dups:
        print(f"发现 {len(dups)} 个重复ID:")
        for d in dups:
            print(f"  ID: {d.id}, 重复次数: {d.count}")
    else:
        print("没有发现重复ID")

    # 检查gen5096的个体
    print("\n=== 检查gen5096的个体 ===")
    gen5096_stmt = select(Candidate).where(Candidate.generation == 5096).order_by(Candidate.id)
    gen5096 = session.execute(gen5096_stmt).scalars().all()
    print(f"gen5096共有 {len(gen5096)} 个个体:")
    for c in gen5096:
        print(f"  ID: {c.id}, 夏普: {c.sharpe_train}, 更新时间: {c.updated_at}")

    # 检查gen0的个体
    print("\n=== 检查gen0的个体 ===")
    gen0_stmt = select(Candidate).where(Candidate.generation == 0).order_by(Candidate.sharpe_train.desc()).limit(10)
    gen0 = session.execute(gen0_stmt).scalars().all()
    print(f"gen0前10个个体:")
    for c in gen0:
        print(f"  ID: {c.id}, 夏普: {c.sharpe_train}")
