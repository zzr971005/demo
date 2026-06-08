"""
调度器API
管理进化任务调度
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from quant_engine.ops.evolution_scheduler import (
    get_scheduler,
    ScheduledTask,
    TaskStatus
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
scheduler = get_scheduler()


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    name: str
    symbol: str
    cron_expression: str
    task_type: str = "evolution"
    priority: int = 0
    enabled: bool = True


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    name: str
    symbol: str
    cron_expression: str
    task_type: str
    next_run_time: Optional[datetime]
    last_run_time: Optional[datetime]
    status: str
    enabled: bool
    priority: int
    retry_count: int
    max_retries: int


class ExecutionResponse(BaseModel):
    """执行记录响应"""
    execution_id: str
    task_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    result: Optional[dict] = None
    error_message: Optional[str] = None


def task_to_response(task: ScheduledTask) -> TaskResponse:
    """转换任务为响应"""
    return TaskResponse(
        task_id=task.task_id,
        name=task.name,
        symbol=task.symbol,
        cron_expression=task.cron_expression,
        task_type=task.task_type,
        next_run_time=task.next_run_time,
        last_run_time=task.last_run_time,
        status=task.status.value,
        enabled=task.enabled,
        priority=task.priority,
        retry_count=task.retry_count,
        max_retries=task.max_retries
    )


# 初始化默认任务
def init_default_tasks():
    """初始化默认任务"""
    from quant_engine.ops.evolution_scheduler import ScheduledTask
    
    symbols = ["KQ.m@SHFE.rb", "KQ.m@DCE.i", "KQ.m@SHFE.ag"]
    
    for i, symbol in enumerate(symbols):
        task = ScheduledTask(
            task_id=f"task_evolution_{i:03d}",
            name=f"{symbol} 进化任务",
            symbol=symbol,
            cron_expression="0 30 20 * * *",
            task_type="evolution",
            next_run_time=datetime.now(),
            priority=i
        )
        
        # 模拟回调函数
        async def mock_callback(t):
            return {"symbol": t.symbol, "status": "completed", "timestamp": datetime.now().isoformat()}
        
        scheduler.register_task(task, mock_callback)


init_default_tasks()


@router.get("/status")
async def get_scheduler_status():
    """获取调度器状态"""
    return scheduler.get_status()


@router.post("/start")
async def start_scheduler(background_tasks: BackgroundTasks):
    """启动调度器"""
    background_tasks.add_task(scheduler.start)
    return {"success": True, "message": "Scheduler starting"}


@router.post("/stop")
async def stop_scheduler():
    """停止调度器"""
    await scheduler.stop()
    return {"success": True, "message": "Scheduler stopped"}


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(symbol: Optional[str] = None):
    """获取任务列表"""
    tasks = scheduler.get_tasks()
    if symbol:
        tasks = [t for t in tasks if t.symbol == symbol]
    return [task_to_response(t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取指定任务"""
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_response(task)


@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """创建新任务"""
    from quant_engine.ops.evolution_scheduler import ScheduledTask
    
    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    task = ScheduledTask(
        task_id=task_id,
        name=request.name,
        symbol=request.symbol,
        cron_expression=request.cron_expression,
        task_type=request.task_type,
        next_run_time=datetime.now(),
        priority=request.priority,
        enabled=request.enabled
    )
    
    # 模拟回调函数
    async def mock_callback(t):
        return {"symbol": t.symbol, "status": "completed", "timestamp": datetime.now().isoformat()}
    
    scheduler.register_task(task, mock_callback)
    return task_to_response(task)


@router.post("/tasks/{task_id}/enable")
async def enable_task(task_id: str):
    """启用任务"""
    if scheduler.enable_task(task_id):
        return {"success": True, "task_id": task_id, "enabled": True}
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/disable")
async def disable_task(task_id: str):
    """禁用任务"""
    if scheduler.disable_task(task_id):
        return {"success": True, "task_id": task_id, "enabled": False}
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/trigger")
async def trigger_task(task_id: str):
    """手动触发任务"""
    if await scheduler.trigger_task(task_id):
        return {"success": True, "task_id": task_id, "message": "Task triggered"}
    raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    scheduler.unregister_task(task_id)
    return {"success": True, "task_id": task_id}


@router.get("/executions", response_model=List[ExecutionResponse])
async def get_executions(task_id: Optional[str] = None, limit: int = 50):
    """获取执行记录"""
    executions = scheduler.get_executions(task_id=task_id, limit=limit)
    return [
        ExecutionResponse(
            execution_id=e.execution_id,
            task_id=e.task_id,
            start_time=e.start_time,
            end_time=e.end_time,
            status=e.status.value,
            result=e.result,
            error_message=e.error_message
        )
        for e in executions
    ]
