"""
进化引擎API

提供遗传编程进化任务的启动、停止、状态查询、历史数据等功能
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.api.deps import get_config
from app.config import Settings
from quant_engine.ops.evolution_center import (
    EvolutionCenter,
    EvolutionTaskConfig,
    EvolutionScheduler,
)
from quant_engine.ops.gp_evolution import GenerationStats

router = APIRouter(tags=["evolution"])

# 全局进化调度器
scheduler = EvolutionScheduler()


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class EvolutionStatusResponse(BaseModel):
    """进化状态响应"""
    status: str = "IDLE"  # IDLE | RUNNING | STOPPED | ERROR
    current_generation: int = 0
    total_generations: int = 60
    population_size: int = 0
    elite_count: int = 0
    current_symbol: Optional[str] = None
    start_time: Optional[datetime] = None
    elapsed_seconds: Optional[float] = None
    estimated_remaining_seconds: Optional[float] = None


class GenerationMetrics(BaseModel):
    """世代指标"""
    generation: int
    avg_sharpe: float
    max_sharpe: float
    min_sharpe: float
    top_10_sharpe: float
    diversity_score: float
    avg_fitness: float
    best_fitness: float
    unique_expressions: int
    pbo: Optional[float] = None
    dsr: Optional[float] = None
    wfe: Optional[float] = None
    created_at: datetime


class EvolutionTriggerRequest(BaseModel):
    """进化启动请求"""
    symbols: List[str] = Field(default_factory=list)
    generations: int = Field(default=30, ge=5, le=99999999, description="进化世代数，持续进化模式可设为极大值")
    population_size: int = Field(default=100, ge=10, le=500)
    max_stagnation: int = Field(default=0, ge=0, le=100, description="停滞阈值，0表示禁用（持续进化模式）")
    enable_overfitting_check: bool = True
    pbo_threshold: float = Field(default=0.3, ge=0, le=1)
    dsr_threshold: float = Field(default=0.6, ge=0)
    wfe_threshold: float = Field(default=0.7, ge=0)
    save_top_n: int = Field(default=20, ge=1)
    use_gpu: bool = Field(default=False, description="是否启用 GPU 加速（5070Ti），多任务共享1个GPU时由信号量限流")


class EvolutionTaskResponse(BaseModel):
    """进化任务响应"""
    task_id: str
    symbol: str
    status: str
    message: str
    created_at: datetime


class EvolutionFactorResult(BaseModel):
    """进化结果因子"""
    factor_id: str
    expression: str
    generation: int
    origin: str
    sharpe_ratio: float
    calmar_ratio: float
    max_drawdown: float
    total_return: float
    win_rate: float
    total_trades: int
    avg_trade_return: float
    pbo: Optional[float] = None
    dsr: Optional[float] = None
    wfe: Optional[float] = None
    overfitting_passed: bool
    node_count: int
    tree_depth: int
    created_at: datetime
    composite_score: float = 0.0  # 综合评分


class EvolutionTreeResponse(BaseModel):
    """进化树响应"""
    id: str
    factor_id: str
    generation: int
    sharpe_ratio: float
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    origin: str
    overfitting_passed: Optional[bool] = None
    pbo: Optional[float] = None
    dsr: Optional[float] = None
    wfe: Optional[float] = None
    created_at: datetime


class EvolutionHistoryResponse(BaseModel):
    """进化历史响应"""
    symbol: str
    generations: List[GenerationMetrics]
    best_factors: List[EvolutionFactorResult]


# ---------------------------------------------------------------------------
# API端点
# ---------------------------------------------------------------------------

@router.get(
    "/evolution/status",
    response_model=EvolutionStatusResponse,
    summary="获取进化引擎状态",
    description="获取当前进化引擎的运行状态、进度、估计剩余时间等（从数据库读取，不依赖内存scheduler）",
)
async def get_evolution_status(
    symbol: Optional[str] = Query(default=None, description="品种名称，为空则返回所有运行中任务的状态"),
    settings: Settings = Depends(get_config),
) -> EvolutionStatusResponse:
    """获取进化引擎状态（基于 evolution_tasks 表）"""
    from app.models import EvolutionTask, EvolutionTaskStatus
    from app.db import get_session
    from sqlalchemy import select

    try:
        with get_session() as session:
            # 查找最新的 RUNNING 任务
            stmt = select(EvolutionTask).where(
                EvolutionTask.status == EvolutionTaskStatus.RUNNING,
            )
            if symbol:
                stmt = stmt.where(EvolutionTask.symbol == symbol)
            stmt = stmt.order_by(EvolutionTask.started_at.desc())
            running = session.execute(stmt).scalars().first()

            if running:
                elapsed = 0
                remaining = 0
                if running.started_at:
                    elapsed = (
                        datetime.utcnow() - running.started_at.replace(tzinfo=None)
                    ).total_seconds()
                if running.current_generation > 0 and running.max_generations > 0:
                    avg = elapsed / running.current_generation
                    remaining = avg * (running.max_generations - running.current_generation)

                return EvolutionStatusResponse(
                    status="RUNNING",
                    current_generation=running.current_generation,
                    total_generations=running.max_generations,
                    population_size=running.population_size,
                    elite_count=int(running.population_size * 0.1),
                    current_symbol=running.symbol,
                    start_time=running.started_at,
                    elapsed_seconds=int(elapsed),
                    estimated_remaining_seconds=int(remaining),
                )
    except Exception as e:
        logger.error(f"读取进化状态失败: {e}", exc_info=True)

    # 没有RUNNING任务时，查找最近的一个任务（任意状态）来显示真实进度
    try:
        with get_session() as session:
            from sqlalchemy import select
            stmt = select(EvolutionTask).order_by(
                EvolutionTask.started_at.desc()
            ).limit(1)
            latest_task = session.execute(stmt).scalars().first()
            
            if latest_task:
                task_status = "STOPPED"
                if latest_task.status == EvolutionTaskStatus.COMPLETED:
                    task_status = "COMPLETED"
                elif latest_task.status == EvolutionTaskStatus.FAILED:
                    task_status = "ERROR"
                elif latest_task.status == EvolutionTaskStatus.ZOMBIE:
                    task_status = "ZOMBIE"
                
                return EvolutionStatusResponse(
                    status=task_status,
                    current_generation=latest_task.current_generation or 0,
                    total_generations=latest_task.max_generations or settings.system.evolution.generations,
                    population_size=latest_task.population_size or 100,
                    elite_count=int((latest_task.population_size or 100) * 0.1),
                    current_symbol=latest_task.symbol,
                    start_time=latest_task.started_at,
                    elapsed_seconds=0,
                    estimated_remaining_seconds=0,
                )
    except Exception as e:
        logger.error(f"读取最近任务状态失败: {e}", exc_info=True)

    return EvolutionStatusResponse(
        status="IDLE",
        total_generations=settings.system.evolution.generations,
    )


@router.get(
    "/evolution/generations",
    summary="获取世代指标历史",
    description="获取指定品种的进化世代历史指标（从 generation_stats 表读取）",
)
async def get_generation_metrics(
    symbol: Optional[str] = Query(default=None, description="品种代码，为空返回所有品种"),
    limit: int = Query(default=10000, ge=1, le=100000, description="返回条数限制，持续进化模式需要更大值"),
) -> Dict[str, Any]:
    """从 generation_stats 表读取世代历史（独立存储，完整准确）"""
    from app.models import EvolutionTask, EvolutionTaskStatus, GenerationStats
    from app.db import get_session
    from sqlalchemy import select, desc

    generations: List[GenerationMetrics] = []
    found_symbol = symbol or "RB"

    try:
        with get_session() as session:
            # 优先查找 RUNNING 状态的任务（Evolution Engine 正在执行的）
            task = None
            if symbol:
                running_stmt = select(EvolutionTask).where(
                    EvolutionTask.symbol == symbol,
                    EvolutionTask.status == EvolutionTaskStatus.RUNNING,
                ).order_by(desc(EvolutionTask.started_at)).limit(1)
                task = session.execute(running_stmt).scalars().first()

            # fallback：查找最新创建的任意状态任务
            if task is None:
                latest_stmt = select(EvolutionTask)
                if symbol:
                    latest_stmt = latest_stmt.where(EvolutionTask.symbol == symbol)
                latest_stmt = latest_stmt.order_by(desc(EvolutionTask.created_at)).limit(1)
                task = session.execute(latest_stmt).scalars().first()

            if task:
                found_symbol = task.symbol

                # 从 generation_stats 表读取统计指标（新方式，准确完整）
                stats_stmt = select(GenerationStats).where(
                    GenerationStats.task_id == task.task_id
                ).order_by(desc(GenerationStats.generation)).limit(limit)

                stats_rows = session.execute(stats_stmt).scalars().all()

                for row in reversed(stats_rows):  # 升序返回
                    generations.append(GenerationMetrics(
                        generation=row.generation,
                        avg_sharpe=float(row.avg_sharpe or 0),
                        max_sharpe=float(row.max_sharpe or 0),
                        min_sharpe=float(row.min_sharpe or 0),
                        top_10_sharpe=float(row.top_10_avg_sharpe or 0),
                        diversity_score=float(row.diversity_score or 0),
                        avg_fitness=float(row.avg_fitness or 0),
                        best_fitness=float(row.best_fitness or 0),
                        unique_expressions=int(row.unique_expressions or 0),
                        pbo=float(row.pbo) if row.pbo is not None else None,
                        dsr=float(row.dsr) if row.dsr is not None else None,
                        wfe=float(row.wfe) if row.wfe is not None else None,
                        created_at=row.created_at,
                    ))

                logger.info(f"从generation_stats表读取到 {len(generations)} 代数据 (task={task.task_id}, status={task.status.value})")

                # 注意：禁止回退到旧方式，确保数据准确性
                # 如果新表无数据，说明该任务尚未产生进化数据，返回空列表
                if not generations:
                    logger.info(f"任务 {task.task_id} 暂无进化数据，等待进化开始")
    except Exception as e:
        logger.error(f"读取世代指标失败: {e}", exc_info=True)

    return {
        "symbol": found_symbol,
        "total": len(generations),
        "generations": generations,
    }


@router.post(
    "/evolution/start",
    summary="启动进化进程",
    description="启动指定品种的遗传编程进化进程，使用独立窗口（每个品种一个窗口）",
)
async def start_evolution(
    request: EvolutionTriggerRequest,
) -> Dict[str, Any]:
    """启动进化进程 — 为每个品种启动独立的进化窗口"""
    if not request.symbols:
        request.symbols = ["RB"]

    import subprocess
    import sys
    import os

    from app.models import SymbolSwitch, SymbolMode, EvolutionTask, EvolutionTaskStatus
    from app.db import get_session
    from sqlalchemy import select

    task_ids = []
    skipped = []
    started_windows = []

    # 获取backend目录路径
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(backend_dir, "scripts", "run_continuous_evolution.py")

    for symbol in request.symbols:
        # 防止同品种重复启动
        if _is_symbol_running(symbol):
            skipped.append(symbol)
            logger.warning(f"品种 {symbol} 已有运行中任务，跳过")
            continue

        task_id = f"{symbol}_evolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 1. 在 symbol_switches 中激活品种（PAPER 模式）
        try:
            with get_session() as session:
                stmt = select(SymbolSwitch).where(SymbolSwitch.symbol == symbol)
                switch = session.execute(stmt).scalars().first()
                if switch:
                    switch.mode = SymbolMode.PAPER
                    switch.last_switch_at = datetime.utcnow()
                else:
                    switch = SymbolSwitch(
                        symbol=symbol,
                        mode=SymbolMode.PAPER,
                    )
                    session.add(switch)
                logger.info(f"品种 {symbol} 已激活为 PAPER 模式")
        except Exception as e:
            logger.error(f"激活品种 {symbol} 失败: {e}")
            continue

        # 2. 创建 EvolutionTask 记录
        try:
            with get_session() as session:
                task = EvolutionTask(
                    task_id=task_id,
                    symbol=symbol,
                    status=EvolutionTaskStatus.PENDING,
                    population_size=request.population_size,
                    max_generations=request.generations,
                    current_generation=0,
                    started_at=datetime.utcnow(),
                )
                session.add(task)
                task_ids.append(task_id)
                logger.info(f"已创建进化任务记录: {task_id}")
        except Exception as e:
            logger.error(f"创建进化任务记录失败: {e}")
            continue

        # 3. 启动独立的进化窗口
        try:
            # 设置环境变量
            env = os.environ.copy()
            env['PYTHONPATH'] = backend_dir
            env['SYMBOL'] = symbol
            env['TASK_ID'] = task_id

            # 启动新的cmd窗口运行进化脚本
            window_title = f"Evolution - {symbol}"
            cmd = f'cd /d "{backend_dir}" && set PYTHONPATH={backend_dir} && set SYMBOL={symbol} && set TASK_ID={task_id} && python scripts\\run_continuous_evolution.py'

            process = subprocess.Popen(
                ['cmd', '/k', cmd],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                env=env,
                cwd=backend_dir
            )

            started_windows.append({
                "symbol": symbol,
                "task_id": task_id,
                "pid": process.pid,
                "window_title": window_title
            })
            logger.info(f"已启动品种 {symbol} 的独立进化窗口 (PID: {process.pid})")

        except Exception as e:
            logger.error(f"启动品种 {symbol} 的独立窗口失败: {e}")
            # 回滚任务状态
            try:
                with get_session() as session:
                    stmt = select(EvolutionTask).where(EvolutionTask.task_id == task_id)
                    task = session.execute(stmt).scalars().first()
                    if task:
                        task.status = EvolutionTaskStatus.FAILED
                        task.finished_at = datetime.utcnow()
            except:
                pass
            continue

    return {
        "message": f"已启动 {len(started_windows)} 个品种的独立进化窗口",
        "task_ids": task_ids,
        "symbols": request.symbols,
        "skipped": skipped,
        "running_count": len(started_windows),
        "windows": started_windows,
    }


def _is_symbol_running(symbol: str) -> bool:
    """检查指定品种是否有运行中的任务"""
    try:
        from app.models import EvolutionTask, EvolutionTaskStatus
        from app.db import get_session
        from sqlalchemy import select
        with get_session() as session:
            stmt = select(EvolutionTask).where(
                EvolutionTask.symbol == symbol,
                EvolutionTask.status.in_([
                    EvolutionTaskStatus.PENDING,
                    EvolutionTaskStatus.RUNNING,
                ]),
            )
            existing = session.execute(stmt).scalars().first()
            return existing is not None
    except Exception:
        return False


def _run_evolution_task(task_id: str):
    """[已弃用] 旧的同进程任务执行器，保留以兼容老调用者"""
    logger.warning(f"调用了已弃用的 _run_evolution_task，task_id={task_id}")
    return None


def _handle_task_callback(task: asyncio.Task):
    """[已弃用] 旧的回调，保留以兼容老调用者"""
    try:
        if task.exception():
            logger.error(f"后台任务失败: {task.exception()}")
    except Exception as e:
        logger.error(f"任务回调处理错误: {e}")


@router.post(
    "/evolution/stop",
    summary="停止进化进程",
    description="停止指定的进化任务（向 worker 线程发送停止信号）",
)
async def stop_evolution(
    task_id: Optional[str] = Query(default=None, description="任务ID，为空则停止所有运行中任务"),
    symbol: Optional[str] = Query(default=None, description="品种名称，为空则停止所有运行中任务"),
) -> Dict[str, Any]:
    """停止进化进程 — 通过关闭 symbol_switch 让独立进化进程停止"""
    from app.models import EvolutionTask, EvolutionTaskStatus, SymbolSwitch, SymbolMode
    from app.db import get_session
    from sqlalchemy import select

    stopped: List[str] = []

    with get_session() as session:
        tasks_to_stop = []

        if task_id:
            stmt = select(EvolutionTask).where(EvolutionTask.task_id == task_id)
            task = session.execute(stmt).scalars().first()
            if task:
                tasks_to_stop.append(task)
        elif symbol:
            # 停止指定品种的所有运行中任务
            stmt = select(EvolutionTask).where(
                EvolutionTask.symbol == symbol,
                EvolutionTask.status.in_([
                    EvolutionTaskStatus.PENDING,
                    EvolutionTaskStatus.RUNNING,
                ])
            )
            tasks_to_stop = session.execute(stmt).scalars().all()
        else:
            # 停止所有运行中任务
            stmt = select(EvolutionTask).where(
                EvolutionTask.status.in_([
                    EvolutionTaskStatus.PENDING,
                    EvolutionTaskStatus.RUNNING,
                ])
            )
            tasks_to_stop = session.execute(stmt).scalars().all()

        for task in tasks_to_stop:
            # 1. 标记任务为 CANCELLED
            task.status = EvolutionTaskStatus.CANCELLED
            task.finished_at = datetime.utcnow()
            stopped.append(task.task_id)

            # 2. 关闭对应品种的 symbol_switch（mode -> OFF）
            #    这样独立进化进程 run_continuous_evolution.py 下一轮会检测到并停止
            switch_stmt = select(SymbolSwitch).where(SymbolSwitch.symbol == task.symbol)
            switch = session.execute(switch_stmt).scalars().first()
            if switch:
                switch.mode = SymbolMode.OFF
                switch.last_switch_at = datetime.utcnow()
                logger.info(f"品种 {task.symbol} 已关闭，独立进化进程将在下一轮停止")

    return {
        "message": f"已停止 {len(stopped)} 个任务",
        "stopped": stopped,
    }


@router.post(
    "/evolution/cleanup_zombies",
    summary="清理僵尸任务",
    description="将心跳超时但状态仍是 RUNNING 的任务标记为 ZOMBIE",
)
async def cleanup_zombies(
    timeout_seconds: int = Query(default=120, ge=30, le=600),
) -> Dict[str, Any]:
    """手动触发僵尸进程清理"""
    from app.models import EvolutionTask, EvolutionTaskStatus
    from app.db import get_session
    from sqlalchemy import select
    from datetime import timedelta

    now = datetime.utcnow()
    threshold = now - timedelta(seconds=timeout_seconds)
    cleaned: List[str] = []

    try:
        with get_session() as session:
            stmt = select(EvolutionTask).where(
                EvolutionTask.status == EvolutionTaskStatus.RUNNING,
                EvolutionTask.last_heartbeat < threshold,
            )
            zombies = session.execute(stmt).scalars().all()
            for t in zombies:
                t.status = EvolutionTaskStatus.ZOMBIE
                t.error_message = f"心跳超时（>{timeout_seconds}s）"
                t.finished_at = now
                cleaned.append(t.task_id)
    except Exception as e:
        logger.error(f"清理僵尸任务失败: {e}", exc_info=True)

    return {
        "message": f"已标记 {len(cleaned)} 个僵尸任务",
        "task_ids": cleaned,
    }


@router.get(
    "/evolution/results",
    summary="获取进化结果",
    description="从 candidates 表读取指定品种的进化结果（最佳因子列表）",
)
async def get_evolution_results(
    symbol: str = Query(..., description="品种代码"),
    only_passed: bool = Query(default=True, description="是否只返回通过过拟合检验的因子"),
    limit: int = Query(default=50, ge=1, le=200, description="返回条数限制"),
) -> Dict[str, Any]:
    """从数据库读取进化结果（candidates 表 + evolution_tasks 表）"""
    from app.models import Candidate, EvolutionTask
    from app.db import get_session
    from sqlalchemy import select, func, desc

    factors: List[EvolutionFactorResult] = []
    total = 0
    passed = 0

    try:
        with get_session() as session:
            # 总数 + 通过数
            total = session.execute(
                select(func.count(Candidate.id)).where(Candidate.symbol == symbol)
            ).scalar() or 0
            
            # 通过过拟合检验的标准：sharpe_train > pbo_threshold（简化）
            # 实际应该从 evolution_tasks 中读取 passed_factors
            task_stmt = select(EvolutionTask).where(
                EvolutionTask.symbol == symbol,
            ).order_by(desc(EvolutionTask.created_at)).limit(1)
            task = session.execute(task_stmt).scalars().first()
            if task:
                passed = task.passed_factors or 0
            
            # 取所有候选者，然后按综合评分排序
            cand_stmt = select(Candidate).where(
                Candidate.symbol == symbol,
                Candidate.sharpe_train.isnot(None),
            )
            
            candidates = session.execute(cand_stmt).scalars().all()
            
            # 计算综合评分（与后端evolution_center._compute_composite_score保持一致）
            # 使用配置文件的权重和归一化参数
            def compute_composite_score(c):
                sharpe = c.sharpe_train or 0
                calmar = c.calmar or 0
                max_drawdown = c.max_drawdown or 0
                win_rate = c.win_rate or 0
                total_trades = c.total_trades or 0

                # 从配置文件读取参数（与后端保持一致）
                try:
                    from quant_engine.ops.evolution_center import get_factor_pool_config
                    config = get_factor_pool_config()
                    weights = config.get("composite_score_weights", {})
                    norm_config = config.get("normalization", {})

                    # 夏普归一化
                    sharpe_min = norm_config.get("sharpe", {}).get("min", -2)
                    sharpe_max = norm_config.get("sharpe", {}).get("max", 5)
                    sharpe_norm = max(0, min(1, (sharpe - sharpe_min) / (sharpe_max - sharpe_min)))

                    # 卡玛归一化
                    calmar_min = norm_config.get("calmar", {}).get("min", 0)
                    calmar_max = norm_config.get("calmar", {}).get("max", 5)
                    calmar_norm = max(0, min(1, (calmar - calmar_min) / (calmar_max - calmar_min)))

                    # 最大回撤转换
                    drawdown_score = max(0, 1 - max_drawdown)

                    # 胜率归一化
                    win_rate_norm = win_rate

                    # 交易次数归一化
                    trades_max = norm_config.get("trades", {}).get("max", 100)
                    trades_norm = min(1, total_trades / trades_max)

                    # 综合评分
                    score = (
                        sharpe_norm * weights.get("sharpe", 0.4) +
                        calmar_norm * weights.get("calmar", 0.2) +
                        drawdown_score * weights.get("drawdown", 0.2) +
                        win_rate_norm * weights.get("win_rate", 0.1) +
                        trades_norm * weights.get("trades", 0.1)
                    )
                except Exception:
                    # 降级到硬编码值
                    sharpe_norm = max(0, min(1, (sharpe + 2) / 7))
                    calmar_norm = max(0, min(1, calmar / 5))
                    drawdown_score = max(0, 1 - max_drawdown)
                    win_rate_norm = win_rate
                    trades_norm = min(1, total_trades / 100)
                    score = (
                        sharpe_norm * 0.4 +
                        calmar_norm * 0.2 +
                        drawdown_score * 0.2 +
                        win_rate_norm * 0.1 +
                        trades_norm * 0.1
                    )
                return score
            
            # 先过滤过拟合检验，再排序和限制数量
            candidates_with_score = []
            for c in candidates:
                # 简单判定 overfitting_passed：sharpe_train > 0 且 sharpe_val > 0
                of_passed = bool(
                    (c.sharpe_train or 0) > 0
                    and (c.sharpe_val is None or (c.sharpe_val or 0) > 0)
                )

                if only_passed and not of_passed:
                    continue

                composite_score = compute_composite_score(c)
                candidates_with_score.append((c, composite_score))

            # 按综合评分降序排序
            candidates_with_score.sort(key=lambda x: x[1], reverse=True)
            candidates_with_score = candidates_with_score[:limit]

            for c, composite_score in candidates_with_score:
                
                factors.append(EvolutionFactorResult(
                    factor_id=c.id,
                    expression=c.formula,
                    generation=c.generation or 0,
                    origin="db",
                    sharpe_ratio=float(c.sharpe_train or 0),
                    calmar_ratio=float(c.calmar or 0),
                    max_drawdown=float(c.max_drawdown or 0),
                    total_return=float(c.total_return or 0),
                    win_rate=float(c.win_rate or 0),
                    total_trades=int(c.total_trades or 0),
                    avg_trade_return=float(c.avg_trade_return or 0),
                    pbo=float(c.pbo) if c.pbo is not None else None,
                    dsr=float(c.dsr) if c.dsr is not None else None,
                    wfe=float(c.wfe) if c.wfe is not None else None,
                    overfitting_passed=of_passed,
                    node_count=int(c.node_count or 0),
                    tree_depth=int(c.tree_depth or 0),
                    created_at=c.created_at,
                    composite_score=composite_score,  # 添加综合评分
                ))
    except Exception as e:
        logger.error(f"读取进化结果失败: {e}", exc_info=True)

    return {
        "symbol": symbol,
        "total": total,
        "passed": passed,
        "factors": factors,
    }


@router.get(
    "/factors/evolution",
    summary="获取因子进化树",
    description="从 candidates 表读取指定品种的因子进化树（基于 parent_id 血缘关系）",
)
async def get_factor_evolution_tree(
    symbol: str = Query(..., description="品种代码"),
    limit: int = Query(default=200, ge=10, le=500, description="返回节点数量限制"),
) -> Dict[str, Any]:
    """从数据库读取因子进化树"""
    from app.models import Candidate
    from app.db import get_session
    from sqlalchemy import select, desc

    tree: List[Dict[str, Any]] = []
    found_symbol = symbol

    try:
        with get_session() as session:
            stmt = select(Candidate).where(
                Candidate.symbol == symbol,
            ).order_by(desc(Candidate.sharpe_train)).limit(limit)
            
            candidates = session.execute(stmt).scalars().all()
            
            # 构建 id 集合，用于过滤无效 parent_id
            id_set = {c.id for c in candidates}
            
            # 构建 parent -> children 反向映射
            children_map: Dict[str, List[str]] = {}
            for c in candidates:
                if c.parent_id and c.parent_id in id_set:
                    children_map.setdefault(c.parent_id, []).append(c.id)
            
            for c in candidates:
                of_passed = bool(
                    (c.sharpe_train or 0) > 0
                    and (c.sharpe_val is None or (c.sharpe_val or 0) > 0)
                )
                tree.append({
                    "id": c.id,
                    "factor_id": c.id,
                    "generation": c.generation or 0,
                    "sharpe_ratio": float(c.sharpe_train or 0),
                    "parent_id": c.parent_id if c.parent_id in id_set else None,
                    "children": children_map.get(c.id, []),
                    "origin": "db",
                    "overfitting_passed": of_passed,
                    "pbo": None,
                    "dsr": None,
                    "wfe": None,
                    "created_at": (c.created_at.isoformat() if c.created_at else None),
                })
    except Exception as e:
        logger.error(f"读取进化树失败: {e}", exc_info=True)

    return {
        "symbol": found_symbol,
        "total_nodes": len(tree),
        "tree": tree,
    }


@router.get(
    "/evolution/tasks",
    summary="获取进化任务列表",
    description="从 evolution_tasks 表读取所有进化任务的状态",
)
async def get_evolution_tasks(
    status: Optional[str] = Query(default=None, description="按状态过滤"),
) -> Dict[str, Any]:
    """从数据库读取进化任务列表"""
    from app.models import EvolutionTask, EvolutionTaskStatus
    from app.db import get_session
    from sqlalchemy import select, desc

    tasks: List[Dict[str, Any]] = []

    try:
        with get_session() as session:
            stmt = select(EvolutionTask).order_by(desc(EvolutionTask.created_at))
            if status:
                try:
                    stmt = stmt.where(EvolutionTask.status == EvolutionTaskStatus(status.upper()))
                except ValueError:
                    pass

            for t in session.execute(stmt).scalars().all():
                tasks.append({
                    "task_id": t.task_id,
                    "symbol": t.symbol,
                    "status": t.status.value.lower() if t.status else "unknown",
                    "pid": t.pid,
                    "current_generation": t.current_generation,
                    "total_generations": t.max_generations,
                    "is_running": t.status == EvolutionTaskStatus.RUNNING,
                    "best_sharpe": t.best_sharpe,
                    "best_fitness": t.best_fitness,
                    "use_gpu": t.use_gpu,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "finished_at": t.finished_at.isoformat() if t.finished_at else None,
                    "last_heartbeat": t.last_heartbeat.isoformat() if t.last_heartbeat else None,
                })
    except Exception as e:
        logger.error(f"读取任务列表失败: {e}", exc_info=True)

    return {
        "total": len(tasks),
        "tasks": tasks,
    }


@router.get(
    "/evolution/factors",
    summary="获取进化出来的因子列表",
    description="从 candidates 表读取指定品种进化出来的所有因子",
)
async def get_evolution_factors(
    symbol: str = Query(..., description="品种代码"),
    only_passed: bool = Query(default=False, description="是否只返回通过过拟合检验的因子"),
    limit: int = Query(default=100, ge=1, le=200, description="返回条数限制"),
) -> Dict[str, Any]:
    """从数据库读取进化因子列表"""
    from app.models import Candidate, CandidateStatus
    from app.db import get_session
    from sqlalchemy import select, desc

    try:
        with get_session() as session:
            # 构建查询条件
            conditions = [Candidate.symbol == symbol]
            if only_passed:
                conditions.append(Candidate.status == CandidateStatus.VALIDATED)

            # 查询因子
            query = select(Candidate).where(*conditions).order_by(
                desc(Candidate.sharpe_test)
            ).limit(limit)
            result = session.execute(query)
            candidates = result.scalars().all()

            # 转换为返回格式
            factors = []
            for c in candidates:
                factors.append({
                    "factor_id": c.id,
                    "expression": c.formula,  # Candidate模型使用formula字段
                    "generation": c.generation,
                    "sharpe_ratio": float(c.sharpe_test) if c.sharpe_test else 0.0,
                    "ic_mean_24h": float(c.ic_mean_24h) if c.ic_mean_24h else 0.0,
                    "ic_ir": float(c.ic_ir) if c.ic_ir else 0.0,
                    "status": c.status.value if c.status else "unknown",
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })

            return {
                "symbol": symbol,
                "total": len(candidates),
                "factors": factors,
                "only_passed": only_passed,
                "limit": limit,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/evolution/diversity-analysis",
    summary="获取多样性分析",
    description="分析指定品种的因子多样性，包括重复表达式统计",
)
async def get_diversity_analysis(
    symbol: str = Query(..., description="品种代码"),
    generation: Optional[int] = Query(default=None, description="代数，为空则分析所有代数"),
) -> Dict[str, Any]:
    """分析因子多样性"""
    from app.models import Candidate, GenerationStats
    from app.db import get_session
    from sqlalchemy import select, func, and_
    from collections import Counter

    try:
        with get_session() as session:
            # 构建查询条件
            conditions = [Candidate.symbol == symbol]
            if generation is not None:
                conditions.append(Candidate.generation == generation)

            # 获取所有因子
            result = session.execute(
                select(Candidate).where(and_(*conditions))
            )
            candidates = result.scalars().all()

            if not candidates:
                return {
                    "symbol": symbol,
                    "generation": generation,
                    "total_factors": 0,
                    "unique_expressions": 0,
                    "duplicate_rate": 0.0,
                    "duplicate_expressions": [],
                    "diversity_score": 0.0,
                }

            # 统计表达式重复
            expressions = [c.formula for c in candidates if c.formula]
            expression_counts = Counter(expressions)
            total_factors = len(candidates)
            unique_expressions = len(expression_counts)
            duplicate_rate = (total_factors - unique_expressions) / total_factors if total_factors > 0 else 0.0

            # 获取重复表达式列表（重复次数>1）
            duplicate_expressions = [
                {"expression": expr, "count": count}
                for expr, count in expression_counts.items()
                if count > 1
            ]
            duplicate_expressions.sort(key=lambda x: x["count"], reverse=True)

            # 计算多样性得分（基于香农熵）
            import math
            if total_factors > 0:
                probs = [count / total_factors for count in expression_counts.values()]
                entropy = -sum(p * math.log(p) if p > 0 else 0 for p in probs)
                max_entropy = math.log(unique_expressions) if unique_expressions > 1 else 1
                diversity_score = entropy / max_entropy if max_entropy > 0 else 0.0
            else:
                diversity_score = 0.0

            # 获取代数统计
            generation_stats = {}
            if generation is None:
                for gen in set(c.generation for c in candidates):
                    gen_candidates = [c for c in candidates if c.generation == gen]
                    gen_exprs = [c.formula for c in gen_candidates if c.formula]
                    gen_unique = len(set(gen_exprs))
                    generation_stats[gen] = {
                        "total": len(gen_candidates),
                        "unique": gen_unique,
                        "duplicate_rate": (len(gen_candidates) - gen_unique) / len(gen_candidates) if len(gen_candidates) > 0 else 0.0,
                    }

            return {
                "symbol": symbol,
                "generation": generation,
                "total_factors": total_factors,
                "unique_expressions": unique_expressions,
                "duplicate_rate": duplicate_rate,
                "duplicate_expressions": duplicate_expressions[:50],  # 最多返回50个
                "diversity_score": diversity_score,
                "generation_stats": generation_stats,
            }

    except Exception as e:
        logger.error(f"多样性分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"多样性分析失败: {str(e)}")


@router.get(
    "/evolution/factors",
    summary="获取进化出来的因子列表",
    description="从 candidates 表读取指定品种进化出来的所有因子",
)
async def get_evolution_factors_list(
    symbol: str = Query(..., description="品种代码"),
    only_passed: bool = Query(default=False, description="是否只返回通过过拟合检验的因子"),
    limit: int = Query(default=100, ge=1, le=200, description="返回条数限制"),
) -> Dict[str, Any]:
    """从数据库读取进化因子列表"""
    from app.models import Candidate
    from app.db import get_session
    from sqlalchemy import select, desc

    factors: List[Dict[str, Any]] = []

    try:
        with get_session() as session:
            stmt = select(Candidate).where(
                Candidate.symbol == symbol,
            ).order_by(desc(Candidate.sharpe_train)).limit(limit)

            candidates = session.execute(stmt).scalars().all()

            for c in candidates:
                of_passed = bool(
                    (c.sharpe_train or 0) > 0
                    and (c.sharpe_val is None or (c.sharpe_val or 0) > 0)
                )
                if only_passed and not of_passed:
                    continue

                factors.append({
                    "id": c.id,
                    "symbol": c.symbol,
                    "expression": c.formula,
                    "sharpe_ratio": float(c.sharpe_train or 0),
                    "calmar_ratio": float(c.calmar or 0),
                    "max_drawdown": float(c.max_drawdown or 0),
                    "total_return": float(c.total_return or 0),
                    "win_rate": float(c.win_rate or 0),
                    "total_trades": int(c.total_trades or 0),
                    "avg_trade_return": float(c.avg_trade_return or 0),
                    "node_count": int(c.node_count or 0),
                    "tree_depth": int(c.tree_depth or 0),
                    "generation": c.generation or 0,
                    "origin": "db",
                    "is_running": False,
                    "is_candidate": True,
                    "overfitting_passed": of_passed,
                    "created_at": c.created_at,
                })
    except Exception as e:
        logger.error(f"读取因子列表失败: {e}", exc_info=True)

    return {
        "symbol": symbol,
        "total": len(factors),
        "factors": factors,
    }


# ---------------------------------------------------------------------------
# 验证监控API（Validation Monitor）
# ---------------------------------------------------------------------------
# 注：/evolution/cycles, /evolution/stats, /evolution/current 三个端点
# 已迁移到 app/api/evolution_cycles.py，使用真实 scheduler 数据。


# ---------------------------------------------------------------------------
# WebSocket 实时进化进度推送
# ---------------------------------------------------------------------------

@router.websocket("/ws/evolution")
async def evolution_websocket(websocket: WebSocket):
    """进化进度WebSocket"""
    await websocket.accept()

    try:
        # 发送初始状态
        await websocket.send_json({
            "type": "status",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
        })

        # 持续监听消息并推送进度
        while True:
            data = await websocket.receive_json()
            # 处理客户端请求
            if data.get("type") == "subscribe":
                # 订阅指定品种的进化进度
                symbol = data.get("symbol")
                await websocket.send_json({
                    "type": "subscription",
                    "symbol": symbol,
                    "status": "subscribed",
                })

    except WebSocketDisconnect:
        pass
