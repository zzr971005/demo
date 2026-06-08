"""检查当前进化任务状态"""

import sys
sys.path.insert(0, r'd:\期货自动进化因子挖掘系统\backend')

from app.models import EvolutionTask, EvolutionTaskStatus
from app.db import get_session
from sqlalchemy import select, desc

print("=== 检查当前进化任务状态 ===")

with get_session() as session:
    # 查询RB的进化任务
    stmt = select(EvolutionTask).where(EvolutionTask.symbol == "RB").order_by(desc(EvolutionTask.created_at))
    tasks = session.execute(stmt).scalars().all()
    
    print(f"RB进化任务总数: {len(tasks)}")
    
    if tasks:
        print("\n最新的任务:")
        for i, task in enumerate(tasks[:3]):
            print(f"\n{i+1}. Task ID: {task.task_id}")
            print(f"   状态: {task.status}")
            print(f"   当前世代: {task.current_generation}")
            print(f"   通过因子数: {task.passed_factors}")
            print(f"   创建时间: {task.created_at}")
            print(f"   开始时间: {task.started_at}")
            print(f"   最后心跳: {task.last_heartbeat}")
    else:
        print("没有RB进化任务")

print("\n=== 完成 ===")
