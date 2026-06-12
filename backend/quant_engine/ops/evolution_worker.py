"""
进化任务 Worker —— 独立进程入口

职责：
- 在独立 Python 进程中运行单品种进化任务
- 完全独立的资源（数据库连接、TQSDK、GP状态机）
- 通过 evolution_tasks 表与主进程同步状态
- 心跳机制：每代结束时更新 last_heartbeat 字段
- GPU 信号量协调（multiprocessing.Semaphore）
- 异常自动捕获并写入数据库

设计原则：
- 不依赖 FastAPI app 实例（避免 pickle 失败）
- 重新初始化日志、数据库连接（子进程不继承父进程连接）
- 优雅退出：SIGTERM/SIGINT 处理
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _setup_worker_logging(task_id: str) -> None:
    """
    在子进程中重新初始化日志
    
    子进程不继承父进程的 logging handler，必须重新设置
    """
    log_dir = Path(__file__).parent.parent.parent.parent / "logs" / "evolution_workers"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{task_id}.log"
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除已有 handler（防止重复）
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 写文件
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(fmt)
    root_logger.addHandler(fh)
    
    # 同时输出到 stdout，便于调试
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root_logger.addHandler(sh)


def _update_task_status(
    task_id: str,
    status: Optional[str] = None,
    pid: Optional[int] = None,
    error: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
) -> None:
    """更新 evolution_tasks 表的状态字段"""
    try:
        from app.models import EvolutionTask, EvolutionTaskStatus
        from app.db import get_session
        
        with get_session() as session:
            task = session.get(EvolutionTask, task_id)
            if task is None:
                return
            
            if status is not None:
                task.status = EvolutionTaskStatus(status)
            if pid is not None:
                task.pid = pid
            if error is not None:
                task.error_message = error
            if started_at is not None:
                task.started_at = started_at
            if finished_at is not None:
                task.finished_at = finished_at
            
            task.last_heartbeat = datetime.utcnow()
    except Exception as e:
        # 子进程中数据库不可用时，不阻塞主流程
        logger.debug(f"更新任务状态失败: {e}", exc_info=True)


def _update_heartbeat(
    task_id: str,
    *,
    current_generation: Optional[int] = None,
    best_fitness: Optional[float] = None,
    best_sharpe: Optional[float] = None,
    avg_sharpe: Optional[float] = None,
    diversity_score: Optional[float] = None,
    unique_expressions: Optional[int] = None,
    total_factors: Optional[int] = None,
    passed_factors: Optional[int] = None,
) -> None:
    """更新心跳与进度字段（每代调用）"""
    try:
        from app.models import EvolutionTask
        from app.db import get_session
        
        with get_session() as session:
            task = session.get(EvolutionTask, task_id)
            if task is None:
                return
            
            if current_generation is not None:
                task.current_generation = current_generation
            if best_fitness is not None:
                task.best_fitness = float(best_fitness)
            if best_sharpe is not None:
                task.best_sharpe = float(best_sharpe)
            if avg_sharpe is not None:
                task.avg_sharpe = float(avg_sharpe)
            if diversity_score is not None:
                task.diversity_score = float(diversity_score)
            if unique_expressions is not None:
                task.unique_expressions = int(unique_expressions)
            if total_factors is not None:
                task.total_factors = int(total_factors)
            if passed_factors is not None:
                old_value = task.passed_factors
                task.passed_factors = int(passed_factors)
                import logging
                logger = logging.getLogger("heartbeat_debug")
                logger.info(
                    f"[HEARTBEAT] task_id={task_id} "
                    f"passed_factors: {old_value} -> {task.passed_factors}"
                )
            
            task.last_heartbeat = datetime.utcnow()
    except Exception as e:
        # 心跳失败不能拖垮进化任务
        logger.debug(f"心跳更新失败: {e}")


def run_evolution_in_worker(
    task_config_dict: Dict[str, Any],
    use_gpu: bool = False,
    gpu_semaphore: Any = None,
) -> Dict[str, Any]:
    """
    Worker 进程主入口（pickleable）
    
    参数：
        task_config_dict: EvolutionTaskConfig 的字典形式
        use_gpu: 是否启用 GPU 加速
        gpu_semaphore: 跨进程 GPU 信号量（multiprocessing.Semaphore）
    
    返回：
        {"status": "success/failed", "task_id": ..., "message": ...}
    
    注意：此函数必须是顶层函数，不能是闭包或类方法（pickle 限制）
    """
    task_id = task_config_dict.get("task_id", "unknown")
    pid = os.getpid()
    
    # 1. 初始化子进程的日志
    _setup_worker_logging(task_id)
    logger = logging.getLogger(f"evolution_worker.{task_id}")
    
    logger.info(f"Worker 进程启动 PID={pid} task_id={task_id}")
    
    # 2. 注册信号处理（优雅退出）
    def _signal_handler(signum, frame):
        logger.warning(f"收到信号 {signum}，准备退出")
        _update_task_status(
            task_id,
            status="CANCELLED",
            finished_at=datetime.utcnow(),
            error=f"收到信号 {signum} 终止",
        )
        sys.exit(1)
    
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
    except (ValueError, AttributeError):
        # Windows 上某些信号可能不可用
        pass
    
    # 3. 标记任务为 RUNNING
    started_at = datetime.utcnow()
    _update_task_status(
        task_id,
        status="RUNNING",
        pid=pid,
        started_at=started_at,
    )
    
    # 4. GPU 资源调度
    gpu_acquired = False
    try:
        if use_gpu and gpu_semaphore is not None:
            logger.info(f"等待 GPU 资源 task_id={task_id}")
            gpu_semaphore.acquire()
            gpu_acquired = True
            logger.info(f"获得 GPU 资源 task_id={task_id}")
        
        # 5. 导入并运行进化（子进程内重新导入，避免 pickle 整个 app）
        from quant_engine.ops.evolution_center import (
            EvolutionCenter,
            EvolutionTaskConfig,
        )
        from quant_engine.data.hub import TimescaleHub
        
        # 重建配置对象
        config = EvolutionTaskConfig(**task_config_dict)
        
        # 重新创建 DataHub（子进程不能继承数据库连接）
        data_hub = TimescaleHub()
        
        # 创建并运行进化中心
        center = EvolutionCenter(config, data_hub)
        
        # 把 task_id 传给 center 用于心跳
        center._worker_task_id = task_id
        
        result = center.run_evolution()
        
        # 6. 完成 - 记录停止原因
        stop_reason = "正常完成"
        if hasattr(center, 'gp') and center.gp:
            stagnation = center.gp.stagnation_count
            if stagnation > 0:
                stop_reason = f"停滞{stagnation}代后完成"
        
        logger.info(
            f"进化任务完成 task_id={task_id} "
            f"代数={getattr(result, 'total_generations', 'N/A')} "
            f"最佳夏普={getattr(result, 'best_sharpe', 'N/A')} "
            f"停止原因: {stop_reason}"
        )
        
        _update_task_status(
            task_id,
            status="COMPLETED",
            finished_at=datetime.utcnow(),
            stop_reason=stop_reason,
        )
        
        return {
            "status": "success",
            "task_id": task_id,
            "total_generations": getattr(result, "total_generations", 0),
            "best_sharpe": float(getattr(result, "best_sharpe", 0.0) or 0.0),
            "best_fitness": float(getattr(result, "best_fitness", 0.0) or 0.0),
        }
    
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        full_trace = traceback.format_exc()
        logger.error(
            f"Worker 进程异常 task_id={task_id}\n{full_trace}",
            exc_info=False,
        )
        
        # 记录异常停止原因
        stop_reason = f"异常: {err_msg}"
        
        _update_task_status(
            task_id,
            status="FAILED",
            finished_at=datetime.utcnow(),
            error=err_msg,
            stop_reason=stop_reason,
        )
        
        return {
            "status": "failed",
            "task_id": task_id,
            "error": err_msg,
            "stop_reason": stop_reason,
        }
    
    finally:
        # 最终检查：如果任务既不是COMPLETED也不是FAILED，记录为未知停止
        if gpu_acquired and gpu_semaphore is not None:
            gpu_semaphore.release()
            logger.info(f"释放 GPU 资源 task_id={task_id}")
        
        # 检查任务状态，如果未设置则记录未知停止
        try:
            from app.db import get_session
            from app.models import EvolutionTask
            from sqlalchemy import select
            
            with get_session() as session:
                stmt = select(EvolutionTask).where(EvolutionTask.task_id == task_id)
                task = session.execute(stmt).scalars().first()
                
                if task and task.status not in ["COMPLETED", "FAILED", "CANCELLED"]:
                    stop_reason = "未知原因停止（可能是进程被杀或系统异常）"
                    logger.error(f"进化任务异常终止 task_id={task_id} {stop_reason}")
                    task.status = "FAILED"
                    task.error = stop_reason
                    task.finished_at = datetime.utcnow()
        except Exception as e:
            logger.debug(f"检查任务状态失败: {e}")


# 子进程内被 evolution_center 调用的辅助函数
def heartbeat(
    task_id: str,
    **fields,
) -> None:
    """供 EvolutionCenter 在每代结束时调用的心跳接口"""
    _update_heartbeat(task_id, **fields)
