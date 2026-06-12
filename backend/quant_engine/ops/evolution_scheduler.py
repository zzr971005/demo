"""
进化调度器
定时触发进化任务的调度系统
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    name: str
    symbol: str
    cron_expression: str
    task_type: str
    next_run_time: datetime
    last_run_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    enabled: bool = True
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskExecution:
    """任务执行记录"""
    execution_id: str
    task_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.RUNNING
    result: Optional[Dict] = None
    error_message: Optional[str] = None


class EvolutionScheduler:
    """进化调度器"""
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._executions: List[TaskExecution] = []
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._task_callbacks: Dict[str, Callable] = {}
        
    def register_task(self, task: ScheduledTask, callback: Callable) -> None:
        """注册调度任务"""
        self._tasks[task.task_id] = task
        self._task_callbacks[task.task_id] = callback
        logger.info(f"Registered task: {task.name} ({task.task_id})")
    
    def unregister_task(self, task_id: str) -> None:
        """取消注册任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            if task_id in self._task_callbacks:
                del self._task_callbacks[task_id]
            logger.info(f"Unregistered task: {task_id}")
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            logger.info(f"Enabled task: {task_id}")
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            logger.info(f"Disabled task: {task_id}")
            return True
        return False
    
    def get_tasks(self) -> List[ScheduledTask]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取指定任务"""
        return self._tasks.get(task_id)
    
    def get_executions(self, task_id: Optional[str] = None, limit: int = 50) -> List[TaskExecution]:
        """获取执行记录"""
        if task_id:
            return [e for e in self._executions if e.task_id == task_id][-limit:]
        return self._executions[-limit:]
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """执行任务"""
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}_{task.task_id}"
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task.task_id,
            start_time=datetime.now()
        )
        self._executions.append(execution)
        
        logger.info(f"Executing task: {task.name} ({task.task_id})")
        task.status = TaskStatus.RUNNING
        task.last_run_time = datetime.now()
        
        try:
            callback = self._task_callbacks.get(task.task_id)
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(task)
                else:
                    result = callback(task)
                
                execution.result = result
                execution.status = TaskStatus.COMPLETED
                task.status = TaskStatus.COMPLETED
                logger.info(f"Task completed: {task.name} ({task.task_id})")
            else:
                raise ValueError(f"No callback found for task: {task.task_id}")
                
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            task.status = TaskStatus.FAILED
            task.retry_count += 1
            logger.error(f"Task failed: {task.name} ({task.task_id}): {e}")
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                logger.info(f"Retrying task {task.name} (attempt {task.retry_count}/{task.max_retries})")
                asyncio.create_task(self._execute_task(task))
        
        finally:
            execution.end_time = datetime.now()
    
    def _should_run_task(self, task: ScheduledTask, now: datetime) -> bool:
        """判断任务是否应该运行"""
        if not task.enabled:
            return False
        
        if task.next_run_time is None:
            return False
        
        # 简单的时间比较
        return now >= task.next_run_time
    
    def _update_next_run_time(self, task: ScheduledTask) -> None:
        """更新下一次运行时间"""
        # 简化的cron解析 - 每天晚上20:30运行
        now = datetime.now()
        next_run = datetime.combine(now.date(), time(20, 30))
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        task.next_run_time = next_run
    
    async def _scheduler_loop(self) -> None:
        """调度主循环"""
        logger.info("Evolution scheduler started")
        
        while self._running:
            try:
                now = datetime.now()
                
                # 检查所有任务
                for task in self._tasks.values():
                    if self._should_run_task(task, now):
                        asyncio.create_task(self._execute_task(task))
                        self._update_next_run_time(task)
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Evolution scheduler stopped")
    
    async def start(self) -> None:
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        # 初始化所有任务的下一次运行时间
        for task in self._tasks.values():
            self._update_next_run_time(task)
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
    
    async def stop(self) -> None:
        """停止调度器"""
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Evolution scheduler stopped")
    
    async def trigger_task(self, task_id: str) -> bool:
        """手动触发任务"""
        task = self._tasks.get(task_id)
        if task:
            await self._execute_task(task)
            self._update_next_run_time(task)
            return True
        return False
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        running_tasks = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
        enabled_tasks = sum(1 for t in self._tasks.values() if t.enabled)
        
        return {
            "running": self._running,
            "total_tasks": len(self._tasks),
            "enabled_tasks": enabled_tasks,
            "running_tasks": running_tasks,
            "total_executions": len(self._executions),
            "last_execution_time": max([e.start_time for e in self._executions], default=None)
        }


# 全局调度器实例
scheduler = EvolutionScheduler()


def get_scheduler() -> EvolutionScheduler:
    """获取全局调度器实例"""
    return scheduler
