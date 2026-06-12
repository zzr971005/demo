"""
检查运行中的进化任务
"""

import sys
import os

# 确保 backend 目录在 sys.path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from app.db import get_session
from app.models import EvolutionTask, EvolutionTaskStatus
from sqlalchemy import select

def check_running_tasks():
    """检查运行中的进化任务"""
    try:
        with get_session() as session:
            stmt = select(EvolutionTask).where(
                EvolutionTask.status == EvolutionTaskStatus.RUNNING
            )
            running_tasks = session.execute(stmt).scalars().all()
            
            if not running_tasks:
                print("当前没有运行中的进化任务")
                return
            
            print(f"当前有 {len(running_tasks)} 个运行中的进化任务:")
            for task in running_tasks:
                print(f"  - task_id: {task.task_id}")
                print(f"    symbol: {task.symbol}")
                print(f"    current_generation: {task.current_generation}")
                print(f"    max_generations: {task.max_generations}")
                print(f"    started_at: {task.started_at}")
                print(f"    last_heartbeat: {task.last_heartbeat}")
                print()
                
    except Exception as e:
        print(f"检查失败: {e}")
        raise

if __name__ == "__main__":
    check_running_tasks()
