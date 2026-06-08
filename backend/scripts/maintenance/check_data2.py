"""更详细地检查数据库中的进化数据"""
from app.db import get_session
from app.models import Candidate, EvolutionTask
from sqlalchemy import select, func, desc

with get_session() as session:
    # 检查不同世代的夏普分布
    print("=== 检查不同世代的夏普分布 ===")
    gen_stmt = select(
        Candidate.generation,
        func.count(Candidate.id).label('count'),
        func.avg(Candidate.sharpe_train).label('avg_sharpe'),
        func.max(Candidate.sharpe_train).label('max_sharpe'),
        func.min(Candidate.sharpe_train).label('min_sharpe'),
        func.avg(Candidate.total_return).label('avg_return'),
        func.max(Candidate.total_return).label('max_return'),
    ).group_by(Candidate.generation).order_by(Candidate.generation.desc()).limit(20)

    rows = session.execute(gen_stmt).all()
    for row in rows:
        print(f'世代 {row.generation}: 数量={row.count}, 平均夏普={row.avg_sharpe:.4f}, 最大夏普={row.max_sharpe:.4f}, 平均收益率={row.avg_return}')

    # 检查是否有不同的夏普值
    print("\n=== 检查所有不同的夏普值 ===")
    sharpe_stmt = select(Candidate.sharpe_train).distinct().order_by(desc(Candidate.sharpe_train)).limit(10)
    sharpes = session.execute(sharpe_stmt).scalars().all()
    print(f"不同的夏普值数量: {len(list(session.execute(select(Candidate.sharpe_train).distinct()).scalars().all()))}")
    print(f"前10个夏普值: {sharpes}")

    # 检查世代0的数据
    print("\n=== 检查世代0的数据 ===")
    gen0_stmt = select(Candidate).where(Candidate.generation == 0).limit(5)
    gen0 = session.execute(gen0_stmt).scalars().all()
    for c in gen0:
        print(f"ID: {c.id[:20]}..., 夏普: {c.sharpe_train}, 收益率: {c.total_return}, 公式: {c.formula[:60]}...")

    # 检查最近一代的数据
    print("\n=== 检查最近一代(5096)的数据 ===")
    latest_stmt = select(Candidate).where(Candidate.generation == 5096).limit(5)
    latest = session.execute(latest_stmt).scalars().all()
    for c in latest:
        print(f"ID: {c.id[:20]}..., 夏普: {c.sharpe_train}, 收益率: {c.total_return}, 公式: {c.formula[:60]}...")

    # 检查是否有更新时间的差异
    print("\n=== 检查更新时间差异 ===")
    time_stmt = select(
        Candidate.generation,
        func.min(Candidate.updated_at).label('min_time'),
        func.max(Candidate.updated_at).label('max_time'),
    ).group_by(Candidate.generation).order_by(Candidate.generation.desc()).limit(5)
    times = session.execute(time_stmt).all()
    for t in times:
        print(f"世代 {t.generation}: 最早={t.min_time}, 最晚={t.max_time}")
