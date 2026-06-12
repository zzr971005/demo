"""
持续进化引擎 - 独立进程运行

用途：与主后端 API 分离部署，避免进化日志淹没 API 日志窗口。
启动方式：
    # 多品种模式（从数据库读取活跃品种）
    cd backend && set PYTHONPATH=%CD% && python scripts/run_continuous_evolution.py

    # 单品种模式（从环境变量读取）
    set SYMBOL=RB && set TASK_ID=RB_evolution_20260601_224700 && python scripts/run_continuous_evolution.py

功能：
- 从数据库读取活跃品种列表（多品种模式）或从环境变量读取指定品种（单品种模式）
- 对每个品种循环执行因子进化
- 结果持久化到数据库（与主后端共享数据库）
- 支持 Ctrl+C 优雅退出
- 停止信号后窗口保持打开，显示停止信息
"""

import sys
import os
import time
import signal
import logging
from datetime import datetime

# 确保 backend 目录在 sys.path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from sqlalchemy import select, update
from app.db import get_session
from app.models import SymbolSwitch
from quant_engine.data.unified_hub import DataHub
from quant_engine.ops.evolution_center import (
    EvolutionCenter,
    EvolutionTaskConfig,
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("continuous_evolution")

# 全局退出标志
_stop_requested = False

# 全局 DataHub 实例（延迟初始化）
_data_hub: DataHub | None = None

# 从环境变量读取单品种配置
_SINGLE_SYMBOL = os.environ.get('SYMBOL')
_SINGLE_TASK_ID = os.environ.get('TASK_ID')


class EvolutionStopped(Exception):
    """用于从回调中优雅停止进化"""
    pass


def _signal_handler(signum, frame):
    global _stop_requested
    logger.info("收到退出信号，正在优雅关闭...")
    _stop_requested = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def get_active_symbols():
    """从数据库获取当前活跃的品种列表"""
    try:
        with get_session() as session:
            rows = session.execute(
                select(SymbolSwitch.symbol).where(
                    SymbolSwitch.mode.in_(["PAPER", "LIVE"])
                )
            ).scalars().all()
            if rows:
                return list(rows)
    except Exception as e:
        logger.warning(f"读取品种列表失败: {e}")

    # 默认品种 — 空列表表示不自动开始，等待前端激活
    return []


def run_single_symbol(symbol: str):
    """对单个品种执行持续进化（真正连续，非分轮次）"""
    global _data_hub

    # 优先复用前端创建的 PENDING 任务（保持 task_id 一致，前端才能查到数据）
    from app.models import EvolutionTask, EvolutionTaskStatus
    from app.db import get_session
    from sqlalchemy import select, desc

    task_id = None
    max_gens = 99999999  # 默认无限进化
    try:
        with get_session() as session:
            # 使用枚举成员查询（SQLAlchemy Enum 列需匹配枚举值）
            pending = EvolutionTaskStatus.PENDING
            running = EvolutionTaskStatus.RUNNING
            stmt = select(EvolutionTask).where(
                EvolutionTask.symbol == symbol,
                EvolutionTask.status.in_([pending, running]),
            ).order_by(desc(EvolutionTask.created_at)).limit(1)
            existing = session.execute(stmt).scalars().first()
            if existing:
                task_id = existing.task_id
                max_gens = existing.max_generations or 99999999
                # 标记为 RUNNING
                existing.status = EvolutionTaskStatus.RUNNING
                existing.started_at = datetime.utcnow()
                logger.info(
                    f"复用前端创建的任务: {task_id} "
                    f"(原状态={existing.status.value}, max_generations={max_gens})"
                )
            else:
                logger.info(f"未找到品种 {symbol} 的 PENDING/RUNNING 任务，将创建新任务")
                # 创建新的EvolutionTask记录
                from app.models import EvolutionTask, EvolutionTaskStatus
                new_task = EvolutionTask(
                    task_id=f"{symbol}_continuous",
                    symbol=symbol,
                    status=EvolutionTaskStatus.RUNNING,
                    population_size=100,
                    max_generations=99999999,
                    started_at=datetime.utcnow(),
                    last_heartbeat=datetime.utcnow(),
                )
                session.add(new_task)
                task_id = new_task.task_id
                logger.info(f"创建新任务: {task_id}")
    except Exception as e:
        logger.warning(f"查询现有任务失败: {e}", exc_info=True)

    # 查询数据库中该任务的最大 generation（用于累加偏移）
    generation_offset = 0
    try:
        with get_session() as session:
            from app.models import GenerationStats
            from sqlalchemy import func
            max_gen = session.execute(
                select(func.max(GenerationStats.generation))
                .where(GenerationStats.task_id == task_id)
            ).scalar()
            if max_gen is not None:
                generation_offset = max_gen + 1
                logger.info(f"[{symbol}] 历史最大 generation={max_gen}，偏移={generation_offset}")
    except Exception as e:
        logger.warning(f"查询历史 generation 失败: {e}")

    config = EvolutionTaskConfig(
        task_id=task_id,
        symbol=symbol,
        description=f"{symbol} 持续进化",
        population_size=100,
        max_generations=max_gens,
        max_stagnation=10,
        enable_overfitting_check=True,
        pbo_threshold=0.3,
        dsr_threshold=0.6,
        wfe_threshold=0.7,
        init_capital=1_000_000,
        position_size_pct=0.95,
        contract_value_per_lot=50000,
        contract_multiplier=10,  # 每手10吨（螺纹钢等商品期货）
        save_top_n=20,
        save_path="./output/factors",
    )
    logger.info(f"DEBUG: Created EvolutionTaskConfig with task_id={config.task_id}")

    logger.info(
        f"[{symbol}] 启动持续进化任务: {task_id} "
        f"(offset={generation_offset}, max_generations={max_gens})"
    )

    # 初始化 DataHub（如尚未初始化）
    if _data_hub is None:
        try:
            _data_hub = DataHub()
            logger.info("DataHub 初始化成功")
        except Exception as e:
            logger.error(f"DataHub 初始化失败，进化将回退到模拟数据: {e}")

    center = EvolutionCenter(config, data_hub=_data_hub)
    logger.info(f"DEBUG: Created EvolutionCenter, center.task_config.task_id={center.task_config.task_id}")
    logger.info(f"DEBUG: task_id variable before setting _worker_task_id={task_id}")
    # 设置 worker_task_id，让 evolution_center 在每代结束时自动更新心跳
    center._worker_task_id = task_id
    logger.info(f"DEBUG: Set center._worker_task_id={center._worker_task_id}")
    # 设置 generation 偏移量，实现持续累加
    center._generation_offset = generation_offset

    # 缓存数据，用于定期过拟合检验
    _cached_data = None

    def on_generation(gen, stats):
        nonlocal _cached_data
        logger.info(f"[{symbol}] on_generation回调被触发: gen={gen}, stats.max_sharpe={stats.max_sharpe}")

        # 检查是否收到停止请求（用户点击停止按钮）
        if _stop_requested:
            raise EvolutionStopped(f"[{symbol}] 收到停止请求，中断进化")

        actual_gen = gen + generation_offset
        progress = (actual_gen + 1) / max_gens * 100
        logger.info(
            f"[{symbol}] [{progress:5.1f}%] 第{actual_gen:3d}代 | "
            f"最佳夏普: {stats.max_sharpe:.4f} | "
            f"平均夏普: {stats.mean_sharpe:.4f} | "
            f"有效个体: {stats.valid_count}/{stats.population_size}"
        )

        # 写入validation_pipeline_data表
        try:
            from app.api.validation_pipeline import ValidationPipelineService

            # 计算当前代的验证流程数据
            current_gen_input = getattr(stats, "offspring_generated", 0)
            search_output = getattr(stats, "unique_expressions", 0)

            # Replay阶段：基于风险筛选（放宽条件）
            replay_candidates = [
                ind for ind in center.gp.manager.population
                if hasattr(ind, 'fitness') and
                ind.fitness.get('sharpe', 0) > 0.5 and
                ind.fitness.get('max_drawdown', 1) < 0.50 and
                ind.fitness.get('win_rate', 0) > 0.40
            ]
            replay_output = len(replay_candidates)

            # Validation阶段：基于过拟合检验
            validation_passed = 0
            if hasattr(center, 'overfitting_results') and center.overfitting_results:
                latest_check = center.overfitting_results[-1] if center.overfitting_results else None
                if latest_check and hasattr(latest_check, 'passed_count'):
                    validation_passed = latest_check.passed_count
            validation_output = min(validation_passed, replay_output)

            # Demo阶段：最多保留20个
            demo_output = min(validation_output, 20)

            # 写入当前代数据到validation_pipeline_data表
            ValidationPipelineService.update_pipeline_data(
                symbol=symbol,
                generation=actual_gen,
                search_input=current_gen_input,
                search_output=search_output,
                search_drop=max(0, current_gen_input - search_output),
                replay_input=search_output,
                replay_output=replay_output,
                replay_drop=max(0, search_output - replay_output),
                validation_input=replay_output,
                validation_output=validation_output,
                validation_drop=max(0, replay_output - validation_output),
                demo_input=validation_output,
                demo_output=demo_output,
                demo_drop=max(0, validation_output - demo_output),
            )
            logger.info(f"[{symbol}] 已写入validation_pipeline_data: generation={actual_gen}, search_input={current_gen_input}, search_output={search_output}")
        except Exception as e:
            logger.error(f"[{symbol}] 写入validation_pipeline_data失败: {e}", exc_info=True)

        # 保存世代统计到数据库
        logger.info(f"[{symbol}] 准备调用 center._save_to_database()")
        try:
            center._save_to_database()
            logger.info(f"[{symbol}] center._save_to_database() 调用成功")
        except Exception as e:
            logger.warning(f"[{symbol}] 保存世代统计失败: {e}", exc_info=True)

        # 每 100 代做一次临时过拟合检验，更新 passed_factors（避免持续进化永远等不到 Validation 输出）
        if actual_gen > 0 and actual_gen % 100 == 0:
            try:
                if _cached_data is None:
                    _cached_data = center.load_data()
                top = center.gp.manager.get_sorted_individuals(use_penalized=True)[
                    : center.task_config.save_top_n
                ]
                checked = center.overfitting_checker.check_final_candidates(
                    top, _cached_data, symbol
                )
                passed_count = sum(1 for _, res in checked if res.overall_passed())
                total_count = len(checked)
                logger.info(
                    f"[{symbol}] 第{actual_gen}代临时验证: {passed_count}/{total_count} 通过过拟合检验"
                )
                from quant_engine.ops.evolution_worker import heartbeat
                # 只更新 passed_factors，不覆盖 total_factors（保持累计生成数）
                heartbeat(
                    task_id,
                    passed_factors=passed_count,
                )
            except Exception as e:
                logger.warning(f"[{symbol}] 临时过拟合检验失败: {e}")

        # 手动更新心跳（确保 API 僵尸检测不会误标为 ZOMBIE）
        try:
            from quant_engine.ops.evolution_worker import heartbeat
            heartbeat(
                task_id,
                current_generation=actual_gen,
                best_fitness=getattr(stats, "best_fitness", 0.0),
                best_sharpe=getattr(stats, "max_sharpe", 0.0),
                avg_sharpe=getattr(stats, "avg_sharpe", 0.0),
                diversity_score=getattr(stats, "diversity_score", 0.0),
                unique_expressions=getattr(stats, "unique_expressions", 0),
            )
        except Exception:
            pass  # 心跳失败不能拖垮进化

    center.on_generation_complete = on_generation

    try:
        result = center.run_evolution()
        actual_total = result.total_generations + generation_offset
        logger.info(
            f"[{symbol}] 进化完成 | "
            f"执行代数: {result.total_generations} | "
            f"累计代数: {actual_total} | "
            f"最佳夏普: {result.best_sharpe:.4f} | "
            f"耗时: {result.total_time:.1f}s"
        )
        return True
    except EvolutionStopped as e:
        logger.info(str(e))
        return True
    except Exception as e:
        logger.error(f"[{symbol}] 进化失败: {e}", exc_info=True)
        return False


def main():
    global _data_hub

    # 单品种模式（从环境变量读取）
    if _SINGLE_SYMBOL:
        logger.info("=" * 60)
        logger.info(f" 单品种进化模式 - {_SINGLE_SYMBOL}")
        logger.info(f" 任务ID: {_SINGLE_TASK_ID}")
        logger.info(" 提示: 进化停止后窗口将保持打开")
        logger.info("=" * 60)

        # 预初始化 DataHub
        try:
            _data_hub = DataHub()
            rb_count = _data_hub.timescale.get_record_count(_SINGLE_SYMBOL, duration_seconds=3600)
            logger.info(f"DataHub 初始化成功，{_SINGLE_SYMBOL} 历史数据: {rb_count} 条")
        except Exception as e:
            logger.error(f"DataHub 初始化失败: {e}")
            logger.warning("进化将回退到模拟随机数据（结果不可信）")

        # 检查品种是否被停止
        def is_symbol_stopped():
            try:
                with get_session() as session:
                    from app.models import SymbolSwitch, SymbolMode
                    stmt = select(SymbolSwitch).where(SymbolSwitch.symbol == _SINGLE_SYMBOL)
                    switch = session.execute(stmt).scalars().first()
                    if not switch or switch.mode == SymbolMode.OFF:
                        return True
                return False
            except:
                return False

        # 执行单品种进化
        while not _stop_requested and not is_symbol_stopped():
            logger.info(f"开始执行品种 {_SINGLE_SYMBOL} 的进化...")
            run_single_symbol(_SINGLE_SYMBOL)

            if _stop_requested or is_symbol_stopped():
                break

            # 短暂休息
            for _ in range(1):
                if _stop_requested or is_symbol_stopped():
                    break
                time.sleep(1)

        logger.info("=" * 60)
        logger.info(f" 品种 {_SINGLE_SYMBOL} 进化已停止")
        logger.info(" 窗口保持打开，可按 Ctrl+C 关闭")
        logger.info("=" * 60)

        # 保持窗口打开，等待用户手动关闭
        while True:
            time.sleep(60)

    # 多品种模式（从数据库读取）
    else:
        logger.info("=" * 60)
        logger.info(" 持续进化引擎启动（多品种模式）")
        logger.info(" 提示: 按 Ctrl+C 优雅退出")
        logger.info("=" * 60)

        # 预初始化 DataHub
        try:
            _data_hub = DataHub()
            rb_count = _data_hub.timescale.get_record_count("RB", duration_seconds=3600)
            logger.info(f"DataHub 初始化成功，RB 历史数据: {rb_count} 条")
        except Exception as e:
            logger.error(f"DataHub 初始化失败: {e}")
            logger.warning("进化将回退到模拟随机数据（结果不可信）")

        while not _stop_requested:
            symbols = get_active_symbols()

            if not symbols:
                logger.info("无活跃品种（symbol_switches 中无 PAPER/LIVE），等待前端激活...")
                for _ in range(5):
                    if _stop_requested:
                        break
                    time.sleep(1)
                continue

            logger.info(f"持续进化中，品种: {symbols}")

            for symbol in symbols:
                if _stop_requested:
                    break
                run_single_symbol(symbol)

            if _stop_requested:
                break

            # 短暂休息后继续监控
            for _ in range(1):
                if _stop_requested:
                    break
                time.sleep(1)

        logger.info("=" * 60)
        logger.info(" 持续进化引擎已停止")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
