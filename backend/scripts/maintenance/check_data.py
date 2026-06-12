"""检查数据库中的进化数据"""
from app.db import get_session
from app.models import Candidate, EvolutionTask
from sqlalchemy import select, func, desc

with get_session() as session:
    # 检查最新的进化任务
    task_stmt = select(EvolutionTask).order_by(desc(EvolutionTask.created_at)).limit(1)
    task = session.execute(task_stmt).scalars().first()
    if task:
        print(f'最新任务: {task.task_id}')
        print(f'品种: {task.symbol}')
        print(f'当前代数: {task.current_generation}')
        print(f'状态: {task.status}')
    else:
        print('没有找到任务')

    # 检查候选者数据
    cand_count = session.execute(select(func.count(Candidate.id))).scalar()
    print(f'\n候选者总数: {cand_count}')

    # 按世代分组查看
    gen_stmt = select(
        Candidate.generation,
        func.count(Candidate.id).label('count'),
        func.avg(Candidate.sharpe_train).label('avg_sharpe'),
        func.max(Candidate.sharpe_train).label('max_sharpe'),
        func.min(Candidate.sharpe_train).label('min_sharpe'),
    ).group_by(Candidate.generation).order_by(Candidate.generation.desc()).limit(10)

    rows = session.execute(gen_stmt).all()
    print('\n最近10代统计:')
    for row in rows:
        print(f'  世代 {row.generation}: 数量={row.count}, 平均夏普={row.avg_sharpe:.4f}, 最大夏普={row.max_sharpe:.4f}, 最小夏普={row.min_sharpe:.4f}')

    # 查看收益率数据
    return_stmt = select(
        Candidate.generation,
        Candidate.total_return,
        Candidate.sharpe_train,
        Candidate.formula,
    ).order_by(desc(Candidate.sharpe_train)).limit(5)

    returns = session.execute(return_stmt).all()
    print('\n夏普最高的5个候选者:')
    for r in returns:
        print(f'  世代 {r.generation}: 夏普={r.sharpe_train:.4f}, 收益率={r.total_return}, 公式={r.formula[:50]}...')
