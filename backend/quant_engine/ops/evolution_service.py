"""
进化服务 - 完整的进化流程编排与数据持久化

负责：
- 完整进化流程管理（启动/停止/监控）
- 数据持久化到数据库
- 实盘因子上线/下线流程
- 实盘性能监控与统计
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from quant_engine.core.models.evolution import (
    EvolutionFactor,
    EvolutionGeneration,
    EvolutionTask,
    FactorLiveStat,
    get_db_session,
)
from quant_engine.ops.gp_evolution import (
    EvolutionConfig,
    EvolutionResult,
    GenerationStats,
    GeneticProgramming,
)
from quant_engine.ops.gp_fitness import FitnessConfig
from quant_engine.ops.gp_individual import GPIndividual
from quant_engine.ops.gp_overfitting import OverfittingChecker, OverfittingConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 进化服务
# ---------------------------------------------------------------------------

class EvolutionService:
    """
    进化服务 - 完整的进化流程管理
    """

    def __init__(self, data_hub=None):
        self.data_hub = data_hub
        self._running_tasks: Dict[str, "RunningEvolution"] = {}
        self._stop_flags: Dict[str, bool] = {}

    # -----------------------------------------------------------------------
    # 任务管理
    # -----------------------------------------------------------------------

    def create_task(self, config: dict) -> dict:
        """
        创建进化任务

        Args:
            config: 任务配置字典

        Returns:
            任务信息字典
        """
        with get_db_session() as db:
            task = EvolutionTask.create(
                db,
                task_id=config["task_id"],
                symbol=config["symbol"],
                description=config.get("description", ""),
                generations=config.get("generations", 30),
                population_size=config.get("population_size", 100),
                enable_overfitting_check=config.get("enable_overfitting_check", True),
                pbo_threshold=config.get("pbo_threshold", 0.3),
                dsr_threshold=config.get("dsr_threshold", 0.6),
                wfe_threshold=config.get("wfe_threshold", 0.7),
            )
            return task.to_dict()

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务信息"""
        with get_db_session() as db:
            task = EvolutionTask.get_by_id(db, task_id)
            return task.to_dict() if task else None

    def list_tasks(self, symbol: Optional[str] = None, limit: int = 20) -> List[dict]:
        """列出任务"""
        with get_db_session() as db:
            if symbol:
                tasks = EvolutionTask.list_by_symbol(db, symbol, limit)
            else:
                from sqlalchemy import desc

                tasks = (
                    db.query(EvolutionTask)
                    .order_by(desc(EvolutionTask.created_at))
                    .limit(limit)
                    .all()
                )
            return [t.to_dict() for t in tasks]

    def get_running_tasks(self) -> List[dict]:
        """获取正在运行的任务"""
        with get_db_session() as db:
            tasks = EvolutionTask.get_running_tasks(db)
            return [t.to_dict() for t in tasks]

    # -----------------------------------------------------------------------
    # 进化执行
    # -----------------------------------------------------------------------

    def start_evolution(self, task_id: str) -> dict:
        """
        启动进化任务

        Args:
            task_id: 任务ID

        Returns:
            启动结果
        """
        with get_db_session() as db:
            task = EvolutionTask.get_by_id(db, task_id)
            if not task:
                return {"success": False, "error": f"任务 {task_id} 不存在"}

            if task.status == "RUNNING":
                return {"success": False, "error": f"任务 {task_id} 已在运行"}

            task.mark_running(db)

        # 启动异步进化
        self._stop_flags[task_id] = False
        self._run_evolution_async(task_id)

        return {"success": True, "task_id": task_id, "message": "进化任务已启动"}

    def _run_evolution_async(self, task_id: str):
        """异步执行进化"""
        # 注意：在生产环境中应该使用Celery等任务队列
        # 这里简化处理，实际应用需要改成真正的异步
        pass

    def run_evolution_sync(self, task_id: str, data: pd.DataFrame, callback: Optional[Callable] = None) -> dict:
        """
        同步执行进化（用于测试或脚本）

        Args:
            task_id: 任务ID
            data: 历史数据
            callback: 每代完成回调

        Returns:
            进化结果
        """
        try:
            with get_db_session() as db:
                task = EvolutionTask.get_by_id(db, task_id)
                if not task:
                    return {"success": False, "error": f"任务 {task_id} 不存在"}

                # 创建GP配置
                gp_config = EvolutionConfig(
                    population_size=task.population_size,
                    max_generations=task.generations,
                    max_stagnation=10,
                    pbo_threshold=task.pbo_threshold,
                    dsr_threshold=task.dsr_threshold,
                    wfe_threshold=task.wfe_threshold,
                )

                gp = GeneticProgramming(gp_config)
                overfitting_checker = OverfittingChecker(
                    OverfittingConfig(
                        pbo_threshold=task.pbo_threshold,
                        dsr_threshold=task.dsr_threshold,
                        wfe_threshold=task.wfe_threshold,
                    ),
                    FitnessConfig(),
                )

                # 每代完成回调
                generation_times = []

                def generation_callback(gen: int, stats: GenerationStats):
                    gen_start_time = time.time()

                    # 保存世代记录
                    generation_data = {
                        "task_id": task_id,
                        "generation": gen,
                        "avg_sharpe": float(stats.avg_sharpe),
                        "max_sharpe": float(stats.max_sharpe),
                        "min_sharpe": float(stats.min_sharpe),
                        "top_10_sharpe": float(stats.mean_sharpe),
                        "avg_fitness": float(stats.avg_sharpe),
                        "best_fitness": float(stats.max_sharpe),
                        "diversity_score": float(stats.diversity_score),
                        "unique_expressions": int(stats.unique_expressions),
                    }

                    if gen % 5 == 0 and task.enable_overfitting_check:
                        # 每5代执行过拟合检验
                        check_result = overfitting_checker.check_population(
                            gp.manager.population, data, task.symbol, gen
                        )
                        generation_data["pbo_value"] = check_result.pbo
                        generation_data["dsr_value"] = check_result.dsr
                        generation_data["wfe_value"] = check_result.wfe

                    with get_db_session() as db:
                        EvolutionGeneration.add_generation(db, **generation_data)
                        task.update_progress(db, gen, generation_data["max_sharpe"], generation_data["best_fitness"])

                    generation_times.append(time.time() - gen_start_time)

                    if callback:
                        callback(gen, stats)

                # 执行进化
                result = gp.evolve(data, task.symbol, callback=generation_callback)

                # 保存最佳因子
                self._save_best_factors(task_id, task.symbol, result.best_individuals, task.generations)

                # 标记任务完成
                with get_db_session() as db:
                    final_task = EvolutionTask.get_by_id(db, task_id)
                    passed_count = sum(
                        1 for f in result.best_individuals if f.overfitting_passed
                    ) if task.enable_overfitting_check else len(result.best_individuals)
                    final_task.mark_completed(db, len(result.best_individuals), passed_count)

                return {
                    "success": True,
                    "task_id": task_id,
                    "total_generations": result.total_generations,
                    "best_sharpe": result.best_sharpe,
                    "best_fitness": result.best_fitness,
                    "total_time": result.total_time,
                    "factors_count": len(result.best_individuals),
                }

        except Exception as e:
            logger.exception(f"进化任务失败: {task_id}")
            with get_db_session() as db:
                task = EvolutionTask.get_by_id(db, task_id)
                if task:
                    task.mark_failed(db, str(e))
            return {"success": False, "error": str(e)}

    def _save_best_factors(self, task_id: str, symbol: str, individuals: List[GPIndividual], generation: int):
        """保存最佳因子"""
        factors_data = []

        for i, ind in enumerate(individuals):
            factor_data = {
                "factor_id": f"{task_id}_factor_{i:04d}",
                "task_id": task_id,
                "symbol": symbol,
                "expression": ind.to_expression(),
                "generation": ind.generation,
                "origin": ind.origin,
                "node_count": ind.node_count,
                "tree_depth": ind.tree_depth,
                "sharpe_ratio": ind.fitness.get("sharpe", 0.0),
                "calmar_ratio": ind.fitness.get("calmar", 0.0),
                "max_drawdown": ind.fitness.get("max_drawdown", 0.0),
                "total_return": ind.fitness.get("total_return", 0.0),
                "win_rate": ind.fitness.get("win_rate", 0.0),
                "total_trades": int(ind.fitness.get("total_trades", 0)),
                "avg_trade_pnl": ind.fitness.get("avg_trade_pnl", 0.0),
                "turnover_rate": ind.fitness.get("turnover_rate", 0.0),
                "pbo_value": 0.0,
                "dsr_value": 0.0,
                "wfe_value": 0.0,
                "overfitting_passed": getattr(ind, "overfitting_passed", False),
                "rank_in_generation": i + 1,
                "overall_rank": i + 1,
            }
            factors_data.append(factor_data)

        with get_db_session() as db:
            EvolutionFactor.add_factors_batch(db, factors_data)

    def stop_evolution(self, task_id: str) -> dict:
        """
        停止进化任务

        Args:
            task_id: 任务ID

        Returns:
            停止结果
        """
        self._stop_flags[task_id] = True

        with get_db_session() as db:
            task = EvolutionTask.get_by_id(db, task_id)
            if task and task.status == "RUNNING":
                task.mark_stopped(db)
                return {"success": True, "message": "进化任务已停止"}

        return {"success": False, "error": "没有正在运行的任务"}

    # -----------------------------------------------------------------------
    # 世代与因子数据
    # -----------------------------------------------------------------------

    def get_generations(self, task_id: str) -> List[dict]:
        """获取任务的世代记录"""
        with get_db_session() as db:
            generations = EvolutionGeneration.get_by_task(db, task_id)
            return [g.to_dict() for g in generations]

    def get_best_factors(self, symbol: str, only_passed: bool = True, limit: int = 20) -> List[dict]:
        """获取最佳因子"""
        with get_db_session() as db:
            factors = EvolutionFactor.get_best_factors(db, symbol, only_passed, limit)
            return [f.to_dict() for f in factors]

    def get_factor(self, factor_id: str) -> Optional[dict]:
        """获取因子详情"""
        with get_db_session() as db:
            factor = db.query(EvolutionFactor).filter(EvolutionFactor.factor_id == factor_id).first()
            return factor.to_dict() if factor else None

    # -----------------------------------------------------------------------
    # 实盘集成 - 因子上线/下线
    # -----------------------------------------------------------------------

    def get_live_factors(self, symbol: Optional[str] = None) -> List[dict]:
        """获取实盘因子"""
        with get_db_session() as db:
            factors = EvolutionFactor.get_live_factors(db, symbol)
            result = []
            for f in factors:
                factor_dict = f.to_dict()
                stat = FactorLiveStat.get_by_factor(db, f.factor_id)
                if stat:
                    factor_dict["live_stats"] = stat.to_dict()
                result.append(factor_dict)
            return result

    def get_candidate_factors(self, symbol: Optional[str] = None) -> List[dict]:
        """获取候选因子"""
        with get_db_session() as db:
            factors = EvolutionFactor.get_candidate_factors(db, symbol)
            return [f.to_dict() for f in factors]

    def mark_as_candidate(self, factor_id: str) -> dict:
        """标记为候选因子"""
        with get_db_session() as db:
            factor = db.query(EvolutionFactor).filter(EvolutionFactor.factor_id == factor_id).first()
            if not factor:
                return {"success": False, "error": "因子不存在"}

            factor.mark_as_candidate(db)
            return {"success": True, "factor_id": factor_id}

    def deploy_to_live(self, factor_id: str) -> dict:
        """
        部署因子到实盘

        流程：
        1. 验证因子存在
        2. 检查是否通过过拟合检验
        3. 更新因子状态
        4. 初始化实盘统计记录
        """
        with get_db_session() as db:
            factor = db.query(EvolutionFactor).filter(EvolutionFactor.factor_id == factor_id).first()
            if not factor:
                return {"success": False, "error": "因子不存在"}

            if not factor.overfitting_passed:
                return {"success": False, "error": "因子未通过过拟合检验，无法部署"}

            factor.deploy_to_live(db)

            # 初始化实盘统计
            FactorLiveStat.update_or_create(
                db,
                factor_id=factor_id,
                symbol=factor.symbol,
                bt_sharpe_ratio=factor.sharpe_ratio,
                bt_total_return=factor.total_return,
                bt_max_drawdown=factor.max_drawdown,
            )

            logger.info(f"因子 {factor_id} 已部署到实盘")
            return {"success": True, "factor_id": factor_id, "symbol": factor.symbol}

    def remove_from_live(self, factor_id: str) -> dict:
        """
        从实盘移除因子
        """
        with get_db_session() as db:
            factor = db.query(EvolutionFactor).filter(EvolutionFactor.factor_id == factor_id).first()
            if not factor:
                return {"success": False, "error": "因子不存在"}

            factor.remove_from_live(db)

            # 更新实盘统计状态
            stat = FactorLiveStat.get_by_factor(db, factor_id)
            if stat:
                stat.is_active = False
                db.commit()

            logger.info(f"因子 {factor_id} 已从实盘移除")
            return {"success": True, "factor_id": factor_id}

    # -----------------------------------------------------------------------
    # 实盘性能监控
    # -----------------------------------------------------------------------

    def update_live_stats(self, factor_id: str, stats_data: dict) -> dict:
        """
        更新因子实盘统计

        Args:
            factor_id: 因子ID
            stats_data: 统计数据
                - live_sharpe_ratio: 实盘夏普比率
                - live_total_return: 实盘总收益
                - live_max_drawdown: 实盘最大回撤
                - live_win_rate: 胜率
                - live_total_trades: 交易次数
                - live_pnl_total: 总盈亏
                - live_pnl_daily: 当日盈亏
                - days_running: 运行天数
        """
        with get_db_session() as db:
            factor = db.query(EvolutionFactor).filter(EvolutionFactor.factor_id == factor_id).first()
            if not factor:
                return {"success": False, "error": "因子不存在"}

            # 计算性能衰减
            if factor.sharpe_ratio != 0:
                performance_decay = (stats_data.get("live_sharpe_ratio", 0) - factor.sharpe_ratio) / abs(
                    factor.sharpe_ratio
                )
                stats_data["performance_decay"] = max(-1.0, min(1.0, performance_decay))

            stat = FactorLiveStat.update_or_create(db, factor_id=factor_id, symbol=factor.symbol, **stats_data)
            return {"success": True, "data": stat.to_dict()}

    def get_live_stats(self, factor_id: str) -> Optional[dict]:
        """获取因子实盘统计"""
        with get_db_session() as db:
            stat = FactorLiveStat.get_by_factor(db, factor_id)
            return stat.to_dict() if stat else None

    def get_all_live_stats(self, symbol: Optional[str] = None) -> List[dict]:
        """获取所有实盘因子的统计"""
        with get_db_session() as db:
            query = db.query(FactorLiveStat).filter(FactorLiveStat.is_active == True)
            if symbol:
                query = query.filter(FactorLiveStat.symbol == symbol)
            stats = query.all()
            return [s.to_dict() for s in stats]

    def get_live_performance_summary(self, symbol: Optional[str] = None) -> dict:
        """获取实盘性能汇总"""
        with get_db_session() as db:
            query = db.query(FactorLiveStat).filter(FactorLiveStat.is_active == True)
            if symbol:
                query = query.filter(FactorLiveStat.symbol == symbol)
            stats = query.all()

            if not stats:
                return {"count": 0, "message": "没有实盘因子"}

            sharpe_values = [s.live_sharpe_ratio for s in stats if s.live_sharpe_ratio > 0]
            return_values = [s.live_total_return for s in stats if s.live_total_return > 0]
            decay_values = [s.performance_decay for s in stats]

            return {
                "count": len(stats),
                "avg_live_sharpe": float(np.mean(sharpe_values)) if sharpe_values else 0,
                "avg_live_return": float(np.mean(return_values)) if return_values else 0,
                "avg_performance_decay": float(np.mean(decay_values)) if decay_values else 0,
                "positive_sharpe_ratio": len(sharpe_values) / len(stats) if stats else 0,
                "factors": [s.to_dict() for s in stats],
            }

    def get_factor_evolution_history(self, symbol: str) -> dict:
        """获取因子进化历史（用于可视化）"""
        with get_db_session() as db:
            # 获取最近的任务
            task = (
                db.query(EvolutionTask)
                .filter(EvolutionTask.symbol == symbol)
                .order_by(EvolutionTask.created_at.desc())
                .first()
            )

            if not task:
                return {"success": False, "error": "没有找到进化任务"}

            # 获取世代记录
            generations = EvolutionGeneration.get_by_task(db, task.task_id)

            # 获取最佳因子
            factors = EvolutionFactor.get_best_factors(db, symbol, only_passed=False, limit=50)

            return {
                "success": True,
                "task": task.to_dict(),
                "generations": [g.to_dict() for g in generations],
                "factors": [f.to_dict() for f in factors],
            }


# ---------------------------------------------------------------------------
# 单例实例
# ---------------------------------------------------------------------------

_evolution_service: Optional[EvolutionService] = None


def get_evolution_service(data_hub=None) -> EvolutionService:
    """获取进化服务单例"""
    global _evolution_service
    if _evolution_service is None:
        _evolution_service = EvolutionService(data_hub=data_hub)
    return _evolution_service
