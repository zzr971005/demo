"""
进化线程池管理器

职责：
- 管理 ThreadPoolExecutor，最多 N 个并发进化任务（默认 12）
- GPU 信号量调度（共享单 GPU 的多任务）
- 任务提交、查询、取消
- 与 evolution_tasks 表保持状态一致
- 后台心跳监控任务（标记僵尸任务）

为什么用线程不用进程：
- Windows上Numba C扩展在进程池中会导致0xc0000005访问冲突
- 虽然GP是CPU密集型，但线程池更稳定，避免多进程内存问题
- 可通过增加线程数来提升并发度
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EvolutionThreadPool:
    """
    进化线程池单例

    使用 ThreadPoolExecutor 替代 ProcessPoolExecutor，避免 Windows 上 Numba C 扩展导致的 0xc0000005 访问冲突问题。
    虽然 GP 是 CPU 密集型，但线程池更稳定，避免多进程内存问题。
    """

    _instance: Optional["EvolutionThreadPool"] = None

    def __init__(
        self,
        max_workers: int = 12,
        gpu_max_concurrency: int = 2,
    ):
        """
        初始化进化线程池

        参数：
            max_workers: 最大并发任务数
            gpu_max_concurrency: 同时使用 GPU 的最大任务数
        """
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
        )
        self._max_workers = max_workers

        # GPU 信号量：线程间协调（用线程安全的 threading.Semaphore）
        self._gpu_semaphore = threading.Semaphore(gpu_max_concurrency)

        # 任务追踪：task_id -> Future
        self._futures: Dict[str, Future] = {}

        # 心跳监控线程
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_stop = asyncio.Event()

        logger.info(
            f"EvolutionThreadPool 已初始化 max_workers={max_workers}, "
            f"gpu_max_concurrency={gpu_max_concurrency}"
        )

    @classmethod
    def get_instance(cls) -> "EvolutionThreadPool":
        """获取全局单例"""
        if cls._instance is None:
            # 默认 12 并发，GPU 同时 2 个
            max_workers = int(os.getenv("EVOLUTION_MAX_WORKERS", "12"))
            gpu_max = int(os.getenv("EVOLUTION_GPU_MAX_CONCURRENCY", "2"))
            cls._instance = cls(
                max_workers=max_workers,
                gpu_max_concurrency=gpu_max,
            )
        return cls._instance

    def submit_task(
        self,
        task_config_dict: Dict[str, Any],
        use_gpu: bool = False,
    ) -> Future:
        """
        提交进化任务到线程池

        参数：
            task_config_dict: EvolutionTaskConfig 字典形式
            use_gpu: 是否启用 GPU 加速

        返回：
            Future 对象
        """
        from quant_engine.ops.evolution_worker import run_evolution_in_worker

        task_id = task_config_dict["task_id"]

        # 1. 先在数据库创建 PENDING 任务记录
        self._create_task_record(task_config_dict, use_gpu)

        # 2. 提交到线程池
        future = self._executor.submit(
            run_evolution_in_worker,
            task_config_dict,
            use_gpu,
            self._gpu_semaphore if use_gpu else None,
        )

        self._futures[task_id] = future

        # 3. 完成回调（清理 Future 引用）
        def _on_done(fut: Future):
            try:
                result = fut.result()
                logger.info(f"任务完成 task_id={task_id} result={result}")
            except Exception as e:
                logger.error(f"任务异常 task_id={task_id}: {e}", exc_info=True)
            finally:
                self._futures.pop(task_id, None)

        future.add_done_callback(_on_done)

        logger.info(f"任务已提交线程池 task_id={task_id} use_gpu={use_gpu}")
        return future

    def _create_task_record(
        self,
        task_config_dict: Dict[str, Any],
        use_gpu: bool,
    ) -> None:
        """在 evolution_tasks 表创建 PENDING 记录"""
        try:
            from app.models import EvolutionTask, EvolutionTaskStatus
            from app.db import get_session

            with get_session() as session:
                task_id = task_config_dict["task_id"]
                existing = session.get(EvolutionTask, task_id)
                if existing:
                    # 已存在：重置为 PENDING
                    existing.status = EvolutionTaskStatus.PENDING
                    existing.use_gpu = use_gpu
                    existing.config_json = json.dumps(task_config_dict, default=str)
                    existing.error_message = None
                    existing.last_heartbeat = datetime.utcnow()
                else:
                    task = EvolutionTask(
                        task_id=task_id,
                        symbol=task_config_dict.get("symbol", "RB"),
                        status=EvolutionTaskStatus.PENDING,
                        population_size=task_config_dict.get("population_size", 100),
                        max_generations=task_config_dict.get("max_generations", 99999999),
                        use_gpu=use_gpu,
                        config_json=json.dumps(task_config_dict, default=str),
                    )
                    session.add(task)
        except Exception as e:
            logger.error(f"创建任务记录失败: {e}", exc_info=True)

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        注意：ProcessPoolExecutor.cancel() 仅能取消未启动的任务，
        已启动的任务需要发送 SIGTERM 给子进程
        """
        from app.models import EvolutionTask, EvolutionTaskStatus
        from app.db import get_session

        future = self._futures.get(task_id)
        cancelled = False

        if future and not future.done():
            cancelled = future.cancel()
            if not cancelled:
                # 已运行：尝试通过 PID 终止
                try:
                    with get_session() as session:
                        task = session.get(EvolutionTask, task_id)
                        if task and task.pid:
                            try:
                                os.kill(task.pid, signal.SIGTERM)
                                cancelled = True
                                logger.info(f"已发送 SIGTERM 至 PID={task.pid}")
                            except ProcessLookupError:
                                pass
                except Exception as e:
                    logger.error(f"终止进程失败: {e}")

        # 更新数据库状态
        try:
            with get_session() as session:
                task = session.get(EvolutionTask, task_id)
                if task and task.status == EvolutionTaskStatus.RUNNING:
                    task.status = EvolutionTaskStatus.CANCELLED
                    task.finished_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"更新取消状态失败: {e}")

        return cancelled

    def get_running_count(self) -> int:
        """当前运行中任务数"""
        return sum(1 for f in self._futures.values() if not f.done())

    def shutdown(self, wait: bool = False) -> None:
        """关闭线程池"""
        logger.info("关闭 EvolutionThreadPool")
        self._executor.shutdown(wait=wait, cancel_futures=True)


# ---------------------------------------------------------------------------
# 心跳监控（在主进程的 asyncio 事件循环中运行）
# ---------------------------------------------------------------------------

# 全局变量存储 EvolutionThreadPool 实例
_evolution_pool_instance: Optional['EvolutionThreadPool'] = None


def set_evolution_pool_instance(pool: 'EvolutionThreadPool') -> None:
    """设置 EvolutionThreadPool 实例，供心跳监控使用"""
    global _evolution_pool_instance
    _evolution_pool_instance = pool


async def heartbeat_monitor_loop(
    interval_seconds: int = 30,
    timeout_seconds: int = 90,
) -> None:
    """
    心跳监控循环：标记心跳超时的任务为 ZOMBIE，并推送进化状态更新给前端

    参数：
        interval_seconds: 检查间隔
        timeout_seconds: 心跳超时阈值（>这个时间没心跳的视为僵尸）
    """
    from app.models import EvolutionTask, EvolutionTaskStatus
    from app.db import get_session
    from sqlalchemy import select
    from quant_engine.ops.websocket_manager import get_ws_manager, MessageType, WebSocketMessage

    logger.info(
        f"心跳监控已启动 interval={interval_seconds}s timeout={timeout_seconds}s"
    )

    ws_manager = get_ws_manager()

    loop_count = 0
    while True:
        try:
            loop_count += 1
            logger.info(f"心跳监控第{loop_count}次检查开始")
            
            await asyncio.sleep(interval_seconds)

            now = datetime.utcnow()
            threshold = now - timedelta(seconds=timeout_seconds)

            with get_session() as session:
                # 1. 检测僵尸任务
                stmt = select(EvolutionTask).where(
                    EvolutionTask.status == EvolutionTaskStatus.RUNNING,
                    EvolutionTask.last_heartbeat < threshold,
                )
                zombie_tasks = session.execute(stmt).scalars().all()

                for task in zombie_tasks:
                    logger.warning(
                        f"检测到僵尸任务 task_id={task.task_id} pid={task.pid} "
                        f"最后心跳={task.last_heartbeat}"
                    )
                    
                    # 自动杀掉僵尸进程
                    if task.pid:
                        try:
                            os.kill(task.pid, signal.SIGTERM)
                            logger.info(f"已发送 SIGTERM 终止僵尸进程 PID={task.pid}")
                        except ProcessLookupError:
                            logger.warning(f"僵尸进程 PID={task.pid} 已不存在")
                        except Exception as e:
                            logger.error(f"终止僵尸进程失败 PID={task.pid}: {e}")
                    
                    # 取消对应的 Future（使用全局实例）
                    if _evolution_pool_instance is not None:
                        future = _evolution_pool_instance._futures.get(task.task_id)
                        if future and not future.done():
                            future.cancel()
                            logger.info(f"已取消僵尸任务 Future task_id={task.task_id}")
                    else:
                        logger.warning(f"无法取消任务 Future，EvolutionThreadPool 实例未设置")
                    
                    task.status = EvolutionTaskStatus.ZOMBIE
                    task.error_message = (
                        f"心跳超时（>{timeout_seconds}s），已被系统自动清理"
                    )
                    task.finished_at = now

                if zombie_tasks:
                    logger.info(f"已自动清理 {len(zombie_tasks)} 个僵尸任务")

                # 2. 获取所有运行中的任务状态，推送给前端
                stmt = select(EvolutionTask).where(
                    EvolutionTask.status == EvolutionTaskStatus.RUNNING
                )
                running_tasks = session.execute(stmt).scalars().all()

                logger.info(f"心跳监控检查: 发现 {len(running_tasks)} 个运行中任务")

                if running_tasks:
                    # 构建进度消息
                    progress_data = []
                    for task in running_tasks:
                        progress_data.append({
                            "task_id": task.task_id,
                            "symbol": task.symbol,
                            "status": task.status.value,
                            "current_generation": task.current_generation or 0,
                            "max_generations": task.max_generations or 99999999,
                            "best_fitness": float(task.best_fitness or 0.0),
                            "best_sharpe": float(task.best_sharpe or 0.0),
                            "avg_sharpe": float(task.avg_sharpe or 0.0),
                            "diversity_score": float(task.diversity_score or 0.0),
                            "unique_expressions": task.unique_expressions or 0,
                            "total_factors": task.total_factors or 0,
                            "passed_factors": task.passed_factors or 0,
                            "started_at": task.started_at.isoformat() if task.started_at else None,
                            "last_heartbeat": task.last_heartbeat.isoformat() if task.last_heartbeat else None,
                        })

                    logger.info(f"准备推送进化进度: {progress_data}")
                    
                    # 发送 WebSocket 消息
                    ws_message = WebSocketMessage(
                        message_type=MessageType.EVOLUTION_PROGRESS,
                        payload={
                            "tasks": progress_data,
                            "timestamp": now.isoformat(),
                        },
                        broadcast=True
                    )
                    
                    try:
                        await ws_manager.broadcast(ws_message)
                        logger.info(f"已推送 {len(running_tasks)} 个进化任务状态到 WebSocket")
                    except Exception as e:
                        logger.error(f"WebSocket 推送失败: {e}", exc_info=True)
                else:
                    logger.info("当前没有运行中的进化任务")

        except asyncio.CancelledError:
            logger.info("心跳监控被取消")
            break
        except Exception as e:
            logger.error(f"心跳监控异常: {e}", exc_info=True)
            # 不退出循环，等下一周期


# 全局快捷访问
def get_evolution_pool() -> EvolutionThreadPool:
    """获取全局进化线程池"""
    return EvolutionThreadPool.get_instance()
