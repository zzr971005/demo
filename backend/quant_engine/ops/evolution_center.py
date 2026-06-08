"""
进化中心服务 — 因子挖掘系统编排层

负责：
- 定时进化任务调度
- 进化流程编排
- 因子库管理
- 进化历史记录
- 过拟合监控
- 优质因子选拔与上报
- 数据库持久化
- WebSocket实时推送
"""

from __future__ import annotations

import json
import logging
import os
import time
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ..data.hub import TimescaleHub as DataHub
from .gp_evolution import (
    EvolutionConfig,
    EvolutionResult,
    GenerationStats,
    GeneticProgramming,
)
from .gp_fitness import FitnessConfig
from .gp_individual import GPNode, GPIndividual, create_individual_from_expr
from .gp_overfitting import (
    OverfittingCheckResult,
    OverfittingConfig,
    OverfittingChecker,
)
from .websocket_manager import WebSocketManager, WebSocketMessage, MessageType, MessagePriority

logger = logging.getLogger(__name__)

# 全局WebSocket管理器
_ws_manager = None


def classify_factor_by_half_life(half_life: Optional[int]) -> Optional[str]:
    """按IC半衰期分类因子"""
    if half_life is None:
        return None
    if half_life <= 2:
        return "fast"  # 快速衰减（动量、情绪）
    elif half_life <= 3:
        return "medium"  # 中等衰减（价值、技术）
    else:
        return "slow"  # 慢速衰减（成长、质量）

def set_websocket_manager(manager: WebSocketManager):
    """设置全局WebSocket管理器"""
    global _ws_manager
    _ws_manager = manager

def get_websocket_manager() -> WebSocketManager:
    """获取WebSocket管理器"""
    return _ws_manager


# ---------------------------------------------------------------------------
# 因子池管理配置
# ---------------------------------------------------------------------------

def load_factor_pool_config() -> Dict[str, Any]:
    """加载因子池管理配置"""
    config_path = Path(__file__).parent.parent.parent / "config" / "factor_pool_config.yaml"
    
    default_config = {
        "factor_pool_size": 20,
        "rolling_window": {"enabled": True, "size": 50},
        "decay_evaluation": {"enabled": True, "threshold": 0.3},
        "rebalancing": {"enabled": True, "period": 10},
        "niche_mechanism": {"enabled": False},
        "composite_score_weights": {
            "sharpe": 0.4,
            "calmar": 0.2,
            "drawdown": 0.2,
            "win_rate": 0.1,
            "trades": 0.1
        },
        "normalization": {
            "sharpe": {"min": -2, "max": 5},
            "calmar": {"min": 0, "max": 5},
            "trades": {"max": 100}
        }
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                # 合并配置
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in default_config:
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
                logger.info(f"加载因子池配置: {config_path}")
        except Exception as e:
            logger.warning(f"加载因子池配置失败，使用默认配置: {e}")
    else:
        logger.warning(f"因子池配置文件不存在: {config_path}，使用默认配置")
    
    return default_config


# 全局配置缓存
_factor_pool_config = None

def get_factor_pool_config() -> Dict[str, Any]:
    """获取因子池配置（单例模式）"""
    global _factor_pool_config
    if _factor_pool_config is None:
        _factor_pool_config = load_factor_pool_config()
    return _factor_pool_config


# ---------------------------------------------------------------------------
# 进化任务配置
# ---------------------------------------------------------------------------

@dataclass
class EvolutionTaskConfig:
    """进化任务配置"""
    
    task_id: str
    symbol: str = "RB"
    description: str = ""
    
    # 进化模式: single, joint, hybrid
    evolution_mode: str = "single"
    symbols: List[str] = field(default_factory=list)  # For joint/hybrid mode
    
    # 进化参数
    population_size: int = 100
    max_generations: int = 50
    max_stagnation: int = 0
    target_fitness: Optional[float] = None
    
    # 过拟合检验
    enable_overfitting_check: bool = True
    pbo_threshold: float = 0.3
    dsr_threshold: float = 0.6
    wfe_threshold: float = 0.7
    
    # 数据配置
    data_start_date: Optional[str] = None
    data_end_date: Optional[str] = None
    data_frequency: str = "1H"
    
    # 结果保存
    save_top_n: int = 20
    save_path: str = "./output/factors"
    
    # 回测参数
    init_capital: float = 1_000_000.0
    position_size_pct: float = 0.95
    contract_value_per_lot: float = 50000.0
    contract_multiplier: float = 10.0  # 每手吨数（螺纹钢=10吨/手）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "symbol": self.symbol,
            "description": self.description,
            "evolution_mode": self.evolution_mode,
            "symbols": self.symbols,
            "population_size": self.population_size,
            "max_generations": self.max_generations,
            "max_stagnation": self.max_stagnation,
            "target_fitness": self.target_fitness,
            "enable_overfitting_check": self.enable_overfitting_check,
            "pbo_threshold": self.pbo_threshold,
            "dsr_threshold": self.dsr_threshold,
            "wfe_threshold": self.wfe_threshold,
            "data_start_date": self.data_start_date,
            "data_end_date": self.data_end_date,
            "data_frequency": self.data_frequency,
            "save_top_n": self.save_top_n,
            "save_path": self.save_path,
            "init_capital": self.init_capital,
            "position_size_pct": self.position_size_pct,
            "contract_value_per_lot": self.contract_value_per_lot,
            "contract_multiplier": self.contract_multiplier,
        }


# ---------------------------------------------------------------------------
# 因子记录
# ---------------------------------------------------------------------------

@dataclass
class FactorRecord:
    """因子记录"""
    
    factor_id: str
    expression: str
    symbol: str
    generation: int
    origin: str
    
    # 绩效指标
    sharpe: float
    calmar: float
    max_drawdown: float
    total_return: float
    win_rate: float
    total_trades: int
    avg_trade_pnl: float
    turnover_rate: float
    
    # 过拟合检验
    pbo: Optional[float]
    dsr: Optional[float]
    wfe: Optional[float]
    overfitting_passed: bool
    
    # 复杂度
    node_count: int
    tree_depth: int
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    task_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "expression": self.expression,
            "symbol": self.symbol,
            "generation": self.generation,
            "origin": self.origin,
            "sharpe": self.sharpe,
            "calmar": self.calmar,
            "max_drawdown": self.max_drawdown,
            "total_return": self.total_return,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "avg_trade_pnl": self.avg_trade_pnl,
            "turnover_rate": self.turnover_rate,
            "pbo": self.pbo,
            "dsr": self.dsr,
            "wfe": self.wfe,
            "overfitting_passed": self.overfitting_passed,
            "node_count": self.node_count,
            "tree_depth": self.tree_depth,
            "created_at": self.created_at.isoformat(),
            "task_id": self.task_id,
        }


# ---------------------------------------------------------------------------
# 进化中心
# ---------------------------------------------------------------------------

class EvolutionCenter:
    """进化中心服务"""
    
    def __init__(
        self,
        task_config: EvolutionTaskConfig,
        data_hub: Optional[DataHub] = None,
    ):
        self.task_config = task_config
        self.data_hub = data_hub
        
        # 初始化配置
        # 持续进化模式：max_stagnation=0 时禁用停滞检查，并将 max_generations 设置为很大值
        effective_max_gen = task_config.max_generations
        effective_max_stagnation = task_config.max_stagnation
        if effective_max_stagnation == 0:
            effective_max_gen = 99999999  # 持续进化模式，无最大代数限制
            logger.info("持续进化模式已启用（max_stagnation=0），max_generations 设置为 99999999")

        self.evolution_config = EvolutionConfig(
            population_size=task_config.population_size,
            max_generations=effective_max_gen,
            max_stagnation=effective_max_stagnation,
            target_fitness=task_config.target_fitness,
            fitness_config=FitnessConfig(
                init_capital=task_config.init_capital,
                position_size_pct=task_config.position_size_pct,
                contract_value_per_lot=task_config.contract_value_per_lot,
                contract_multiplier=task_config.contract_multiplier,
            ),
        )
        
        self.overfitting_config = OverfittingConfig(
            pbo_threshold=task_config.pbo_threshold,
            dsr_threshold=task_config.dsr_threshold,
            wfe_threshold=task_config.wfe_threshold,
        )
        
        self.gp = GeneticProgramming(self.evolution_config)
        self.overfitting_checker = OverfittingChecker(
            self.overfitting_config,
            self.evolution_config.fitness_config,
        )
        
        # 状态
        self.is_running = False
        self.current_generation = 0
        self.task_start_time: Optional[datetime] = None
        self.task_end_time: Optional[datetime] = None
        self.evolution_result: Optional[EvolutionResult] = None
        self.overfitting_results: List[OverfittingCheckResult] = []
        self.final_factors: List[FactorRecord] = []
        
        # 累计生成计数器（从运行开始至今生成的所有因子表达式总数，只增不减）
        self.total_generated_count: int = 0
        
        # 历史个体（用于构建进化树）
        self.historical_individuals: Dict[str, GPIndividual] = {}
        
        # 多进程心跳标识（由 evolution_worker 注入，None 表示直接调用模式）
        self._worker_task_id: Optional[str] = None
        
        # 持续进化时的 generation 偏移量（用于多轮累加）
        self._generation_offset: int = 0
        
        # 回调
        self.on_generation_complete: Optional[Callable[[int, GenerationStats], None]] = None
        self.on_evolution_complete: Optional[Callable[[EvolutionResult], None]] = None
    
    def _warn_if_degenerate_term_structure(self, data: pd.DataFrame) -> None:
        """期限结构数据健全性检查。

        若 near_close / far_close 与 close 完全相同（说明期限结构表没有真实近/远月
        数据），则期限结构类因子(spread_near_far / basis / basis_annualized)会恒为
        常数0，导致"不同因子表现完全相同"的静默错误。此处显式告警，避免无声通过。
        """
        try:
            if "near_close" not in data.columns or "far_close" not in data.columns:
                return
            near_eq_far = bool((data["near_close"].fillna(-1) == data["far_close"].fillna(-1)).all())
            near_eq_close = bool((data["near_close"].fillna(-1) == data["close"].fillna(-1)).all())
            if near_eq_far and near_eq_close:
                logger.warning(
                    "[期限结构告警] %s 的 near_close/far_close 与 close 完全相同："
                    "期限结构表无真实近/远月数据，spread_near_far/basis/basis_annualized "
                    "等期限结构因子将恒为0(不同因子表现雷同)。请先下载多合约期限结构数据。",
                    self.task_config.symbol,
                )
                self.term_structure_degenerate = True
            else:
                self.term_structure_degenerate = False
        except Exception as e:
            logger.debug(f"期限结构健全性检查失败: {e}")

    def load_data(self) -> pd.DataFrame:
        """加载历史数据（包含多合约数据用于期限结构因子）"""
        if self.data_hub is not None:
            # 尝试加载多合约数据
            try:
                data = self.data_hub.get_multi_contract_ohlcv(
                    symbol=self.task_config.symbol,
                    start_date=self.task_config.data_start_date,
                    end_date=self.task_config.data_end_date,
                    frequency=self.task_config.data_frequency,
                )
                logger.info(f"从DataHub加载多合约数据: {len(data)} 条")
                # 确保包含期限结构列
                if 'near_close' not in data.columns:
                    data['near_close'] = data.get('close', data['close'])
                if 'far_close' not in data.columns:
                    data['far_close'] = data.get('close', data['close'])
                if 'days_to_expiry' not in data.columns:
                    data['days_to_expiry'] = 30
                self._warn_if_degenerate_term_structure(data)
            except Exception as e:
                logger.warning(f"加载多合约数据失败，回退到单合约: {e}")
                data = self.data_hub.get_ohlcv(
                    symbol=self.task_config.symbol,
                    start_date=self.task_config.data_start_date,
                    end_date=self.task_config.data_end_date,
                    frequency=self.task_config.data_frequency,
                )
                # 添加期限结构所需的列（使用主力合约数据填充）
                data['near_close'] = data['close']
                data['far_close'] = data['close']
                data['days_to_expiry'] = 30
                logger.info(f"从DataHub加载单合约数据: {len(data)} 条")
                self._warn_if_degenerate_term_structure(data)
            return data
        else:
            raise RuntimeError(
                "DataHub未配置。进化引擎必须连接真实数据源才能运行。\n"
                "请检查：\n"
                "  1. run_continuous_evolution.py 中是否传入了 data_hub=_data_hub\n"
                "  2. 环境变量 DATABASE_URL 是否指向正确的 PostgreSQL 数据库\n"
                "  3. DataHub 初始化是否成功"
            )
    
    def _load_seeds_from_database(self, max_seeds: int = 20) -> List[GPIndividual]:
        """
        从数据库加载优质因子作为种子
        
        Parameters
        ----------
        max_seeds : int
            最大种子数量
            
        Returns
        -------
        List[GPIndividual]
            种子个体列表
        """
        try:
            from app.models import Candidate, CandidateStatus
            from app.db import get_session
            
            seeds = []
            
            with get_session() as session:
                # 查询当前品种的优质因子
                # 条件：夏普比率 > 0.5，按夏普比率降序排列
                candidates = session.query(Candidate).filter(
                    Candidate.symbol == self.task_config.symbol,
                    Candidate.sharpe_train > 0.5,
                ).order_by(Candidate.sharpe_train.desc()).limit(max_seeds).all()
                
                for candidate in candidates:
                    try:
                        # 从表达式创建GP个体
                        seed = create_individual_from_expr(
                            candidate.formula,
                            generation=0
                        )
                        seed.origin = 'seed'
                        seed.id = candidate.id  # 使用原有的ID

                        # 验证种子参数类型
                        from quant_engine.ops.gp_fitness import FitnessEvaluator, FitnessConfig
                        evaluator = FitnessEvaluator(FitnessConfig())
                        if not evaluator._validate_parameter_types(seed):
                            logger.warning(f"种子参数验证失败，跳过: {candidate.formula}")
                            continue

                        seeds.append(seed)
                        logger.info(f"加载种子: {candidate.id[:8]}... 夏普={candidate.sharpe_train:.4f}")
                    except Exception as e:
                        logger.warning(f"解析种子失败 {candidate.id}: {e}")
                        continue
            
            logger.info(f"从数据库加载了 {len(seeds)} 个种子")
            return seeds
            
        except Exception as e:
            logger.warning(f"加载种子失败: {e}")
            return []
    
    def run_evolution(self) -> EvolutionResult:
        """执行进化任务"""
        logger.info(f"开始进化任务: {self.task_config.task_id}")
        logger.info(f"品种: {self.task_config.symbol}")
        logger.info(f"种群大小: {self.evolution_config.population_size}")
        logger.info(f"最大代数: {self.evolution_config.max_generations}")
        logger.info(f"DEBUG: task_config.task_id = {self.task_config.task_id}")
        logger.info(f"DEBUG: _worker_task_id = {self._worker_task_id}")
        
        self.is_running = True
        self.task_start_time = datetime.now()
        
        # 发送状态更新消息（通知前端进化已启动）
        self._send_symbol_update("running")
        
        try:
            # 加载数据
            data = self.load_data()
            logger.info(f"数据加载完成: {len(data)} 条")
            
            # 加载种子（方案C：从数据库加载优质因子）
            seeds = self._load_seeds_from_database(max_seeds=20)
            
            # 对种子进行表达式去重（防止数据库中重复因子填充整个种群）
            if seeds:
                unique_seeds = []
                seen_expressions = set()
                for seed in seeds:
                    expr = seed.to_expression()
                    if expr not in seen_expressions:
                        unique_seeds.append(seed)
                        seen_expressions.add(expr)
                seeds = unique_seeds
                logger.info(f"加载种子去重后: {len(seeds)} 个唯一因子")
            
            # 累加初始种群大小到总计（第0代）
            if seeds:
                initial_count = len(seeds)
            else:
                initial_count = self.task_config.population_size
            self.total_generated_count += initial_count
            
            # 定义每代回调
            def generation_callback(generation: int, stats: GenerationStats):
                logger.info(f"generation_callback ENTRY: generation={generation}")
                try:
                    logger.info(f"generation_callback被触发: generation={generation}, current_generation={self.current_generation}")
                    self.current_generation = generation + self._generation_offset

                    # 累加本代生成的因子数量到累计计数器（只增不减）
                    # 使用实际生成的后代数量，而非种群大小
                    offspring_count = getattr(stats, "offspring_generated", 0)
                    self.total_generated_count += offspring_count

                    # 保存当前代的个体到历史记录（按适应度排序，保留优质因子）
                    max_historical = 2000  # 保留前2000个优质因子（约20代历史）
                    for ind in self.gp.manager.population:
                        self.historical_individuals[ind.id] = ind

                    # 如果历史记录过多，按适应度排序清理，保留最优个体
                    if len(self.historical_individuals) > max_historical:
                        # 按适应度（夏普比率）降序排序，保留前 max_historical 个
                        sorted_items = sorted(
                            self.historical_individuals.items(),
                            key=lambda x: x[1].fitness.get("sharpe", 0),
                            reverse=True
                        )[:max_historical]
                        self.historical_individuals = dict(sorted_items)
                        logger.debug(f"清理历史个体，保留前 {max_historical} 个优质因子")

                    # 多进程心跳：写入 evolution_tasks 表
                    if self._worker_task_id:
                        logger.info(f"worker_task_id已设置: {self._worker_task_id}, 准备写入validation_pipeline_data")
                        try:
                            from quant_engine.ops.evolution_worker import heartbeat

                            # 计算当前代的验证流程数据
                            current_gen_input = getattr(stats, "offspring_generated", 0)
                            search_output = getattr(stats, "unique_expressions", 0)

                            # Replay阶段：基于风险筛选
                            replay_candidates = [
                                ind for ind in self.gp.manager.population
                                if hasattr(ind, 'fitness') and
                                ind.fitness.get('sharpe', 0) > 1.5 and
                                ind.fitness.get('max_drawdown', 1) < 0.20 and
                                ind.fitness.get('win_rate', 0) > 0.55
                            ]
                            replay_output = len(replay_candidates)

                            # Validation阶段：基于过拟合检验
                            validation_passed = 0
                            if hasattr(self, 'overfitting_results') and self.overfitting_results:
                                latest_check = self.overfitting_results[-1] if self.overfitting_results else None
                                if latest_check and hasattr(latest_check, 'passed_count'):
                                    validation_passed = latest_check.passed_count
                            validation_output = min(validation_passed, replay_output)

                            # Demo阶段：最多保留20个
                            demo_output = min(validation_output, 20)

                            # 写入当前代数据到validation_pipeline_data表
                            from app.api.validation_pipeline import ValidationPipelineService
                            ValidationPipelineService.update_pipeline_data(
                                symbol=self.symbol,
                                generation=self.current_generation,
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
                            logger.info(f"已写入validation_pipeline_data: generation={self.current_generation}, search_input={current_gen_input}, search_output={search_output}")
                        except Exception as e:
                            logger.error(f"写入validation_pipeline_data失败: {e}", exc_info=True)

                        try:
                            from quant_engine.ops.evolution_worker import heartbeat
                            heartbeat(
                                self._worker_task_id,
                                current_generation=self.current_generation,
                                best_fitness=getattr(stats, "best_fitness", 0.0),
                                best_sharpe=getattr(stats, "max_sharpe", 0.0),
                                avg_sharpe=getattr(stats, "avg_sharpe", 0.0),
                                diversity_score=getattr(stats, "diversity_score", 0.0),
                                unique_expressions=getattr(stats, "unique_expressions", 0),
                                total_factors=self.total_generated_count,  # 累计生成的所有因子数（只增不减）
                                # 持续进化模式下 final_factors 为空，不要覆盖已有的 passed_factors
                                passed_factors=sum(
                                    1 for f in self.final_factors if f.overfitting_passed
                                ) if self.final_factors else None,
                            )
                        except Exception as e:
                            logger.debug(f"心跳更新失败（不影响进化）: {e}")

                    # 执行过拟合检验
                    if self.task_config.enable_overfitting_check:
                        check_result = self.overfitting_checker.check_population(
                            self.gp.manager.population,
                            data,
                            self.task_config.symbol,
                            generation=generation,
                        )
                        self.overfitting_results.append(check_result)
                except Exception as e:
                    logger.error(f"generation_callback执行失败: {e}", exc_info=True)

                # 每1代保存一次到数据库并推送（确保数据实时显示）
                self._save_to_database()
                self._send_websocket_update()

                # 用户回调
                if self.on_generation_complete is not None:
                    self.on_generation_complete(generation, stats)
            
            # 执行进化（注入种子）
            logger.info(f"准备调用gp.evolve, callback={generation_callback is not None}")
            result = self.gp.evolve(
                data,
                self.task_config.symbol,
                callback=generation_callback,
                seeds=seeds,
            )
            
            self.evolution_result = result
            
            # 最终过拟合检验和因子筛选
            # 始终把进化个体转换为 final_factors；过拟合检验为可选项，
            # 不应因关闭检验而出现“成功进化却 0 因子”的静默错误。
            self._process_final_results(data)
            if self.task_config.enable_overfitting_check:
                # 更新 passed_factors 到数据库（仅当从未设置过时才更新，保留定期验证的结果）
                try:
                    from app.models import EvolutionTask
                    from app.db import get_session
                    with get_session() as session:
                        task = session.get(EvolutionTask, self._worker_task_id or self.task_config.task_id)
                        should_update = task and task.passed_factors == 0
                    if should_update:
                        from quant_engine.ops.evolution_worker import heartbeat
                        heartbeat(
                            self._worker_task_id or self.task_config.task_id,
                            passed_factors=sum(
                                1 for f in self.final_factors if f.overfitting_passed
                            ),
                            total_factors=self.total_generated_count,  # 累计生成的所有因子数
                        )
                except Exception as e:
                    logger.debug(f"心跳更新失败: {e}")  # 心跳失败不影响进化结果
            
            # 保存结果
            self._save_results()
            
            # 最终保存到数据库（确保无论进化何时停止都能保存数据）
            self._save_to_database()
            
            self.task_end_time = datetime.now()
            
            logger.info(f"进化任务完成: {self.task_config.task_id}")
            logger.info(f"总代数: {result.total_generations}")
            logger.info(f"最佳适应度: {result.best_fitness:.4f}")
            logger.info(f"最佳夏普: {result.best_sharpe:.4f}")
            logger.info(f"总耗时: {result.total_time:.2f}秒")
            logger.info(f"筛选出优质因子: {len(self.final_factors)} 个")
            
            if self.on_evolution_complete is not None:
                self.on_evolution_complete(result)
            
            return result
            
        except Exception as e:
            logger.error(f"进化任务执行失败: {e}", exc_info=True)
            raise
        finally:
            self.is_running = False
    
    def _process_final_results(self, data: pd.DataFrame) -> None:
        """处理最终结果，进行过拟合检验和筛选"""
        if self.evolution_result is None:
            return
        
        # 获取最佳个体
        top_individuals = self.evolution_result.get_unique_best(
            n=self.task_config.save_top_n
        )
        
        # 过拟合检验
        if self.task_config.enable_overfitting_check:
            checked_results = self.overfitting_checker.check_final_candidates(
                top_individuals,
                data,
                self.task_config.symbol,
            )
        else:
            class _PassCheck:
                pbo = 0.0
                dsr = 0.0
                wfe = 0.0

                @staticmethod
                def overall_passed() -> bool:
                    return True

            checked_results = [(ind, _PassCheck()) for ind in top_individuals]
        
        # 转换为因子记录
        self.final_factors = []
        for i, (ind, check_result) in enumerate(checked_results):
            factor_id = f"{self.task_config.task_id}_factor_{i:03d}"
            
            record = FactorRecord(
                factor_id=factor_id,
                expression=ind.to_expression(),
                symbol=self.task_config.symbol,
                generation=ind.generation,
                origin=ind.origin,
                sharpe=ind.fitness.get("sharpe", 0.0),
                calmar=ind.fitness.get("calmar", 0.0),
                max_drawdown=ind.metrics.get("max_drawdown", 0.0),
                total_return=ind.metrics.get("total_return", 0.0),
                win_rate=ind.metrics.get("win_rate", 0.0),
                total_trades=ind.metrics.get("total_trades", 0),
                avg_trade_pnl=ind.metrics.get("avg_trade_pnl", 0.0),
                turnover_rate=0.0,  # 后续计算
                pbo=check_result.pbo,
                dsr=check_result.dsr,
                wfe=check_result.wfe,
                overfitting_passed=check_result.overall_passed(),
                node_count=ind.get_node_count(),
                tree_depth=ind.get_depth(),
                task_id=self.task_config.task_id,
            )
            
            self.final_factors.append(record)
        
        # 按夏普排序
        self.final_factors.sort(key=lambda x: x.sharpe, reverse=True)

        # 静默错误防护：不同表达式却完全相同表现 = 信号实质等价（退化）。
        # get_unique_best 仅按表达式字符串去重，无法识别“不同写法、同一信号”。
        # 这里按表现指纹再次去重，仅保留表达式最简（节点数最少）的一只，
        # 避免把实质等价的因子当成多个独立因子上报（用户核心关切）。
        self.final_factors = self._dedup_by_performance(self.final_factors)

    @staticmethod
    def _dedup_by_performance(factors):
        """按表现指纹去重，保留表达式最简者；返回去重后的列表。"""
        def fingerprint(f):
            return (
                round(f.sharpe, 8),
                round(f.total_return, 8),
                round(f.max_drawdown, 8),
                round(f.win_rate, 8),
                int(f.total_trades),
            )

        best_by_fp = {}
        collapsed = 0
        for f in factors:
            fp = fingerprint(f)
            if fp[:4] == (0.0, 0.0, 0.0, 0.0) and fp[4] == 0:
                best_by_fp[(id(f),)] = f
                continue
            existing = best_by_fp.get(fp)
            if existing is None:
                best_by_fp[fp] = f
            else:
                collapsed += 1
                if (f.node_count or 0) < (existing.node_count or 0):
                    best_by_fp[fp] = f
        if collapsed:
            logger.warning(
                "[去重] 检测到 %d 个表达式不同但表现完全相同的因子（信号实质等价），"
                "已折叠为最简表达式。这通常意味着算子忽略了某个入参或信号被符号化，"
                "请关注是否为退化因子。",
                collapsed,
            )
        return sorted(best_by_fp.values(), key=lambda x: x.sharpe, reverse=True)

    def _save_results(self) -> None:
        """保存进化结果"""
        save_path = self.task_config.save_path
        os.makedirs(save_path, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 保存任务配置
        config_file = os.path.join(
            save_path,
            f"{self.task_config.task_id}_{timestamp}_config.json",
        )
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.task_config.to_dict(), f, indent=2, ensure_ascii=False)
        
        # 2. 保存进化历史
        if self.evolution_result is not None:
            history_file = os.path.join(
                save_path,
                f"{self.task_config.task_id}_{timestamp}_history.csv",
            )
            history_df = pd.DataFrame(
                [stat.to_dict() for stat in self.evolution_result.history]
            )
            history_df.to_csv(history_file, index=False)
        
        # 3. 保存过拟合检验历史
        if self.overfitting_results:
            overfitting_file = os.path.join(
                save_path,
                f"{self.task_config.task_id}_{timestamp}_overfitting.csv",
            )
            overfitting_df = pd.DataFrame(
                [res.to_dict() for res in self.overfitting_results]
            )
            overfitting_df.to_csv(overfitting_file, index=False)
        
        # 4. 保存优质因子
        if self.final_factors:
            factors_file = os.path.join(
                save_path,
                f"{self.task_config.task_id}_{timestamp}_factors.csv",
            )
            factors_df = pd.DataFrame(
                [f.to_dict() for f in self.final_factors]
            )
            factors_df.to_csv(factors_file, index=False)
            
            # 保存表达式
            expr_file = os.path.join(
                save_path,
                f"{self.task_config.task_id}_{timestamp}_expressions.txt",
            )
            with open(expr_file, "w", encoding="utf-8") as f:
                for factor in self.final_factors:
                    if factor.overfitting_passed:
                        f.write(f"{factor.factor_id}: {factor.expression}\n")
        
        logger.info(f"结果已保存到: {save_path}")
    
    def _compute_composite_score(
        self,
        sharpe: float,
        calmar: float,
        max_drawdown: float,
        win_rate: float,
        total_trades: int,
    ) -> float:
        """计算综合评分

        评分公式从配置文件读取：
        综合评分 = sharpe_norm * sharpe_weight + calmar_norm * calmar_weight +
                   drawdown_score * drawdown_weight + win_rate_norm * win_rate_weight +
                   trades_norm * trades_weight

        注意：最大回撤是正数（如0.15表示15%），所以用 (1 - 最大回撤) 来转换

        Parameters
        ----------
        sharpe : float
            夏普比率
        calmar : float
            卡玛比率
        max_drawdown : float
            最大回撤（正数，如0.15表示15%）
        win_rate : float
            胜率（0-1）
        total_trades : int
            总交易次数
            
        Returns
        -------
        float - 综合评分（0-1范围）
        """
        config = get_factor_pool_config()
        weights = config.get("composite_score_weights", {})
        norm_config = config.get("normalization", {})

        # 夏普归一化
        sharpe_min = norm_config.get("sharpe", {}).get("min", -2)
        sharpe_max = norm_config.get("sharpe", {}).get("max", 5)
        sharpe_norm = max(0, min(1, (sharpe - sharpe_min) / (sharpe_max - sharpe_min))) if sharpe is not None else 0

        # 卡玛归一化
        calmar_min = norm_config.get("calmar", {}).get("min", 0)
        calmar_max = norm_config.get("calmar", {}).get("max", 5)
        calmar_norm = max(0, min(1, (calmar - calmar_min) / (calmar_max - calmar_min))) if calmar is not None else 0

        # 最大回撤转换（回撤越小越好，用1-回撤）
        drawdown_score = max(0, 1 - max_drawdown) if max_drawdown is not None else 0

        # 胜率归一化（假设胜率在0到1之间）
        win_rate_norm = win_rate if win_rate is not None else 0

        # 交易次数归一化
        trades_max = norm_config.get("trades", {}).get("max", 100)
        trades_norm = min(1, total_trades / trades_max) if total_trades is not None else 0

        # 综合评分（使用配置的权重）
        score = (
            sharpe_norm * weights.get("sharpe", 0.4) +
            calmar_norm * weights.get("calmar", 0.2) +
            drawdown_score * weights.get("drawdown", 0.2) +
            win_rate_norm * weights.get("win_rate", 0.1) +
            trades_norm * weights.get("trades", 0.1)
        )

        return score
    
    def _save_to_database(self) -> None:
        """将当前进化数据保存到数据库 - 竞争模式

        维护一个固定大小的最佳因子池（从配置文件读取），
        新产生的因子如果比池中的某些因子好，就替换进去。
        始终保持池中是全局最佳的因子。

        支持功能：
        - 定期重新平衡（每N代竞争一次）
        - 滚动窗口评估（使用最近N代表现）
        - 因子衰减评估（检测因子是否衰减）
        """
        try:
            from app.models import Candidate, CandidateStatus
            from app.db import get_session
            import uuid

            config = get_factor_pool_config()
            TOP_N_BEST = config.get("factor_pool_size", 20)
            rebalancing_config = config.get("rebalancing", {})
            enable_rebalancing = rebalancing_config.get("enabled", True)
            rebalance_period = rebalancing_config.get("period", 10)

            logger.info(f"开始保存第{self.current_generation}代数据到数据库（竞争模式，池大小={TOP_N_BEST}）")

            # 获取当前代的最佳个体
            sorted_inds = self.gp.manager.get_sorted_individuals(use_penalized=True)
            best_individuals = sorted_inds[:50]

            # 过滤掉无效个体（fitness为-9999的）
            valid_individuals = [ind for ind in best_individuals if ind.fitness.get("penalized", 0) > 0]
            logger.info(f"过滤前: {len(best_individuals)} 个, 过滤后: {len(valid_individuals)} 个有效个体")
            best_individuals = valid_individuals

            # 表达式去重，避免重复因子进入候选池
            unique_best = []
            seen_expr = set()
            for ind in best_individuals:
                try:
                    expr = ind.to_expression()
                except Exception:
                    expr = None
                if expr in seen_expr:
                    continue
                seen_expr.add(expr)
                unique_best.append(ind)
            best_individuals = unique_best

            logger.info(f"获取到 {len(best_individuals)} 个最佳个体（去重后）")
            
            # 调试：输出每个个体的指标
            for i, ind in enumerate(best_individuals[:10]):
                logger.info(f"个体 {ind.id} 指标: sharpe={ind.fitness.get('sharpe', 0):.4f}, "
                           f"total_return={ind.metrics.get('total_return', 0):.4f}, "
                           f"total_trades={ind.metrics.get('total_trades', 0)}, "
                           f"win_rate={ind.metrics.get('win_rate', 0):.2f}")

            if not best_individuals:
                logger.warning("没有找到最佳个体，跳过保存")
                return

            logger.info(f"准备保存第{self.current_generation}代数据到数据库")

            # 检查是否需要重新平衡
            should_rebalance = not enable_rebalancing or (self.current_generation % rebalance_period == 0)
            logger.info(f"重新平衡检查: enable={enable_rebalancing}, period={rebalance_period}, current_gen={self.current_generation}, should_rebalance={should_rebalance}")

            with get_session() as session:
                # 1. 获取当前数据库中该品种的所有候选者
                existing_candidates = session.query(Candidate).filter(
                    Candidate.symbol == self.task_config.symbol
                ).all()

                logger.info(f"数据库中已有 {len(existing_candidates)} 个候选者")

                # 2. 计算每个候选者的综合评分
                def calc_score_for_candidate(c):
                    """为现有候选者计算综合评分"""
                    base_score = self._compute_composite_score(
                        sharpe=c.sharpe_train or 0,
                        calmar=c.calmar or 0,
                        max_drawdown=c.max_drawdown or 0,
                        win_rate=c.win_rate or 0,
                        total_trades=c.total_trades or 0,
                    )

                    # 因子衰减评估
                    decay_config = config.get("decay_evaluation", {})
                    if decay_config.get("enabled", True):
                        # 简化版：如果 sharpe_val 存在且比 sharpe_train 低很多，认为衰减
                        if c.sharpe_val is not None and c.sharpe_train is not None:
                            decay_ratio = (c.sharpe_train - c.sharpe_val) / max(abs(c.sharpe_train), 0.01)
                            if decay_ratio > decay_config.get("threshold", 0.3):
                                logger.debug(f"因子 {c.id} 衰减: sharpe_train={c.sharpe_train:.4f}, sharpe_val={c.sharpe_val:.4f}, decay_ratio={decay_ratio:.4f}")
                                base_score *= 0.5  # 衰减因子评分减半

                    return base_score

                def calc_score_for_individual(ind):
                    """为新个体计算综合评分"""
                    # 获取IC指标（如果回测结果中包含）
                    ic_metrics = ind.metrics.get("ic_metrics", {})
                    ic_mean = ic_metrics.get("ic_mean_4h", 0) * 0.5 + ic_metrics.get("ic_mean_24h", 0) * 0.3 + ic_metrics.get("ic_mean_168h", 0) * 0.2
                    ic_ir = ic_metrics.get("ic_ir", 0)
                    ic_half_life = ic_metrics.get("ic_half_life", 0)
                    
                    # 计算综合评分（IC + 回测绩效）
                    performance_score = self._compute_composite_score(
                        sharpe=ind.fitness.get("sharpe", 0),
                        calmar=ind.fitness.get("calmar", 0),
                        max_drawdown=ind.metrics.get("max_drawdown", 0),
                        win_rate=ind.metrics.get("win_rate", 0),
                        total_trades=ind.metrics.get("total_trades", 0),
                    )
                    
                    # 混合评分：IC 50% + 回测绩效 50%
                    composite_score = ic_mean * 0.5 + performance_score * 0.5 if ic_mean else performance_score
                    
                    return composite_score

                # 3. 如果不重新平衡，只保存新因子
                if not should_rebalance:
                    logger.info(f"非重新平衡周期，只保存新因子")
                    saved_count = 0
                    skipped_count = 0

                    for ind in best_individuals:
                        try:
                            formula = ind.to_expression()

                            # 检查数据库中是否已存在相同公式
                            existing = session.query(Candidate).filter(
                                Candidate.symbol == self.task_config.symbol,
                                Candidate.formula == formula
                            ).first()
                            if existing:
                                logger.debug(f"数据库中公式已存在，跳过: {formula}")
                                skipped_count += 1
                                continue

                            # 生成唯一ID
                            unique_id = f"{self.task_config.task_id}_gen{ind.generation + self._generation_offset}_{uuid.uuid4().hex[:12]}"

                            # 检查父个体
                            parent_id = None
                            if ind.parent_ids and ind.parent_ids[0]:
                                parent_exists = session.query(Candidate).filter(
                                    Candidate.id == ind.parent_ids[0]
                                ).first()
                                if parent_exists:
                                    parent_id = ind.parent_ids[0]

                            # 获取IC指标
                            ic_metrics = ind.metrics.get("ic_metrics", {})
                            
                            candidate = Candidate(
                                id=unique_id,
                                symbol=self.task_config.symbol,
                                formula=formula,
                                status=CandidateStatus.SEED,
                                generation=ind.generation + self._generation_offset,
                                sharpe_train=ind.fitness.get("sharpe", 0.0),
                                max_drawdown=ind.metrics.get("max_drawdown", 0.0),
                                calmar=ind.fitness.get("calmar", 0.0),
                                total_return=ind.metrics.get("total_return", 0.0),
                                total_trades=ind.metrics.get("total_trades", 0),
                                win_rate=ind.metrics.get("win_rate", 0.0),
                                avg_trade_return=ind.metrics.get("avg_trade_return", 0.0),
                                node_count=ind.get_node_count(),
                                tree_depth=ind.get_depth(),
                                parent_id=parent_id,
                                # IC指标
                                ic_mean_4h=ic_metrics.get("ic_mean_4h"),
                                ic_mean_24h=ic_metrics.get("ic_mean_24h"),
                                ic_mean_168h=ic_metrics.get("ic_mean_168h"),
                                ic_std=ic_metrics.get("ic_std"),
                                ic_ir=ic_metrics.get("ic_ir"),
                                ic_half_life=ic_metrics.get("ic_half_life"),
                                # 因子分类
                                factor_category=classify_factor_by_half_life(ic_metrics.get("ic_half_life")),
                            )
                            session.add(candidate)
                            saved_count += 1

                        except Exception as e:
                            logger.error(f"保存个体 {ind.id} 失败: {e}", exc_info=True)

                    logger.info(f"非重新平衡周期保存完成：新增 {saved_count} 个，跳过 {skipped_count} 个重复")

                    # 保存世代统计
                    self._save_generation_stats(session, sorted_inds)
                    return

                # 4. 重新平衡：将新个体与现有候选者合并竞争
                # 创建候选者列表：(score, is_new, candidate_obj, new_ind)
                # is_new=1表示新个体，is_new=0表示现有候选者
                # 排序时先按综合评分降序，评分相同时新个体优先（增加多样性）
                all_candidates = []

                # 添加现有候选者
                for c in existing_candidates:
                    score = calc_score_for_candidate(c)
                    all_candidates.append((score, 0, c, None))

                # 添加新个体
                for ind in best_individuals:
                    score = calc_score_for_individual(ind)
                    all_candidates.append((score, 1, None, ind))

                # Fitness Sharing机制：按性能空间划分小生境
                niche_config = config.get("niche_mechanism", {})
                if niche_config.get("enabled", False):
                    logger.info("启用Fitness Sharing小生境机制")
                    niche_count = niche_config.get("niche_count", 125)

                    # 计算每个候选者的性能指标
                    def get_performance_metrics(score, is_new, db_obj, new_ind):
                        if db_obj is not None:
                            return (db_obj.sharpe_train or 0, db_obj.calmar or 0, db_obj.total_trades or 0)
                        elif new_ind is not None:
                            return (new_ind.fitness.get("sharpe", 0), new_ind.fitness.get("calmar", 0), new_ind.metrics.get("total_trades", 0))
                        return (0, 0, 0)

                    # 计算所有候选者的指标范围
                    all_metrics = [get_performance_metrics(*c) for c in all_candidates]
                    sharpe_values = [m[0] for m in all_metrics]
                    calmar_values = [m[1] for m in all_metrics]
                    trades_values = [m[2] for m in all_metrics]

                    sharpe_min, sharpe_max = min(sharpe_values), max(sharpe_values)
                    calmar_min, calmar_max = min(calmar_values), max(calmar_values)
                    trades_min, trades_max = min(trades_values), max(trades_values)

                    # 避免除零
                    sharpe_range = sharpe_max - sharpe_min if sharpe_max > sharpe_min else 1
                    calmar_range = calmar_max - calmar_min if calmar_max > calmar_min else 1
                    trades_range = trades_max - trades_min if trades_max > trades_min else 1

                    # 计算每个候选者的小生境ID
                    def get_niche_id(metrics):
                        sharpe_norm = (metrics[0] - sharpe_min) / sharpe_range
                        calmar_norm = (metrics[1] - calmar_min) / calmar_range
                        trades_norm = (metrics[2] - trades_min) / trades_range

                        # 5x5x5网格
                        sharpe_bin = int(sharpe_norm * 5)
                        calmar_bin = int(calmar_norm * 5)
                        trades_bin = int(trades_norm * 5)

                        # 限制在0-4范围内
                        sharpe_bin = min(4, max(0, sharpe_bin))
                        calmar_bin = min(4, max(0, calmar_bin))
                        trades_bin = min(4, max(0, trades_bin))

                        return sharpe_bin * 25 + calmar_bin * 5 + trades_bin

                    # 统计每个小生境的候选者数量
                    niche_counts = {}
                    for c in all_candidates:
                        metrics = get_performance_metrics(*c)
                        niche_id = get_niche_id(metrics)
                        niche_counts[niche_id] = niche_counts.get(niche_id, 0) + 1

                    # 应用Fitness Sharing：每个小生境内的候选者共享适应度
                    # 共享系数 = 1 / sqrt(小生境内候选者数量)
                    shared_scores = []
                    for c in all_candidates:
                        metrics = get_performance_metrics(*c)
                        niche_id = get_niche_id(metrics)
                        niche_size = niche_counts.get(niche_id, 1)
                        sharing_coef = 1.0 / (niche_size ** 0.5)  # 平方根共享
                        shared_score = c[0] * sharing_coef
                        shared_scores.append((shared_score, c[1], c[2], c[3]))

                    logger.info(f"Fitness Sharing: {len(niche_counts)}个小生境被占用，最大小生境大小: {max(niche_counts.values())}")
                    all_candidates = shared_scores

                # 5. 按综合评分降序排序，评分相同时新个体优先
                all_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                top_candidates = all_candidates[:TOP_N_BEST]

                # 6. 确定需要保留和删除的
                keep_ids = set()
                new_individuals = []

                for score, is_new, db_obj, new_ind in top_candidates:
                    if db_obj is not None:
                        keep_ids.add(db_obj.id)
                    elif new_ind is not None:
                        new_individuals.append(new_ind)

                # 7. 删除不在前TOP_N_BEST中的现有候选者
                deleted_count = 0
                for c in existing_candidates:
                    if c.id not in keep_ids:
                        session.delete(c)
                        deleted_count += 1

                if deleted_count > 0:
                    logger.info(f"删除了 {deleted_count} 个较差的候选者")

                # 8. 添加新的优秀个体
                saved_count = 0
                skipped_count = 0

                # 先对新个体进行去重
                seen_formulas = set()
                unique_new_individuals = []
                for ind in new_individuals:
                    try:
                        formula = ind.to_expression()
                        if formula not in seen_formulas:
                            seen_formulas.add(formula)
                            unique_new_individuals.append(ind)
                        else:
                            skipped_count += 1
                            logger.debug(f"同一代中重复公式，跳过: {formula}")
                    except Exception as e:
                        logger.error(f"获取表达式失败: {e}")

                # 保存去重后的新个体
                for ind in unique_new_individuals:
                    try:
                        formula = ind.to_expression()

                        # 检查数据库中是否已存在相同公式
                        existing = session.query(Candidate).filter(
                            Candidate.symbol == self.task_config.symbol,
                            Candidate.formula == formula
                        ).first()
                        if existing:
                            logger.debug(f"数据库中公式已存在，跳过: {formula}")
                            skipped_count += 1
                            continue

                        # 生成唯一ID
                        unique_id = f"{self.task_config.task_id}_gen{ind.generation + self._generation_offset}_{uuid.uuid4().hex[:12]}"

                        # 检查父个体
                        parent_id = None
                        if ind.parent_ids and ind.parent_ids[0]:
                            parent_exists = session.query(Candidate).filter(
                                Candidate.id == ind.parent_ids[0]
                            ).first()
                            if parent_exists:
                                parent_id = ind.parent_ids[0]

                        # 获取IC指标
                        ic_metrics = ind.metrics.get("ic_metrics", {})
                        
                        candidate = Candidate(
                            id=unique_id,
                            symbol=self.task_config.symbol,
                            formula=formula,
                            status=CandidateStatus.SEED,
                            generation=ind.generation + self._generation_offset,
                            sharpe_train=ind.fitness.get("sharpe", 0.0),
                            max_drawdown=ind.metrics.get("max_drawdown", 0.0),
                            calmar=ind.fitness.get("calmar", 0.0),
                            total_return=ind.metrics.get("total_return", 0.0),
                            total_trades=ind.metrics.get("total_trades", 0),
                            win_rate=ind.metrics.get("win_rate", 0.0),
                            avg_trade_return=ind.metrics.get("avg_trade_return", 0.0),
                            node_count=ind.get_node_count(),
                            tree_depth=ind.get_depth(),
                            parent_id=parent_id,
                            # IC指标
                            ic_mean_4h=ic_metrics.get("ic_mean_4h"),
                            ic_mean_24h=ic_metrics.get("ic_mean_24h"),
                            ic_mean_168h=ic_metrics.get("ic_mean_168h"),
                            ic_std=ic_metrics.get("ic_std"),
                            ic_ir=ic_metrics.get("ic_ir"),
                            ic_half_life=ic_metrics.get("ic_half_life"),
                            # 因子分类
                            factor_category=classify_factor_by_half_life(ic_metrics.get("ic_half_life")),
                        )
                        session.add(candidate)
                        saved_count += 1

                    except Exception as e:
                        logger.error(f"保存个体 {ind.id} 失败: {e}", exc_info=True)

                logger.info(f"第{self.current_generation}代竞争完成：新增 {saved_count} 个，跳过 {skipped_count} 个重复，删除 {deleted_count} 个，"
                           f"当前池中共有 {len(top_candidates)} 个最佳因子")

                # 10. 保存世代统计指标（用于图表展示）
                logger.info(f"准备调用 _save_generation_stats 保存第{self.current_generation}代统计")
                self._save_generation_stats(session, sorted_inds)
                logger.info(f"_save_generation_stats 调用完成")

                # 11. 触发因子值序列生成和IC计算
                self._trigger_factor_value_generation_and_ic_calculation()

        except Exception as e:
            logger.error(f"保存到数据库失败: {e}", exc_info=True)

    def _trigger_factor_value_generation_and_ic_calculation(self) -> None:
        """触发因子值序列生成和IC计算"""
        try:
            from quant_engine.ops.factor_value_generator import FactorValueGenerator
            from quant_engine.ops.ic_calculator import ICCalculator
            from quant_engine.data.hub import TimescaleHub

            logger.info(f"开始触发因子值序列生成和IC计算: {self.task_config.symbol} 第{self.current_generation}代")

            # 创建TimescaleHub实例
            timescale_hub = TimescaleHub()

            # 生成因子值序列
            factor_value_generator = FactorValueGenerator(timescale_hub)
            gen_stats = factor_value_generator.generate_factor_values(
                self.task_config.symbol,
                self.current_generation + self._generation_offset
            )
            logger.info(f"因子值序列生成完成: {gen_stats}")

            # 计算IC指标
            ic_calculator = ICCalculator(timescale_hub)
            ic_stats = ic_calculator.calculate_ic_batch(
                self.task_config.symbol,
                self.current_generation + self._generation_offset
            )
            logger.info(f"IC计算完成: {ic_stats}")

        except Exception as e:
            logger.error(f"因子值序列生成和IC计算失败: {e}", exc_info=True)

    def _save_generation_stats(self, session, sorted_inds: list) -> None:
        """保存当前世代的统计指标到 generation_stats 表"""
        try:
            from app.models import GenerationStats
            from sqlalchemy import select

            logger.info(f"开始保存第{self.current_generation}代统计指标")

            # 计算统计指标
            raw_sharpes = [ind.fitness.get("sharpe", 0) for ind in sorted_inds if ind.fitness.get("sharpe") is not None]
            fitness_values = [ind.fitness.get("penalized", 0) for ind in sorted_inds if ind.fitness.get("penalized") is not None]

            if not raw_sharpes:
                logger.warning(f"第{self.current_generation}代没有有效的夏普值，跳过统计")
                return

            # 限制夏普值范围，防止极端异常值污染统计
            sharpe_values = [max(-10.0, min(10.0, s)) for s in raw_sharpes]

            # 记录被截断的异常值
            clipped_count = sum(1 for r, c in zip(raw_sharpes, sharpe_values) if r != c)
            if clipped_count > 0:
                logger.warning(f"第{self.current_generation}代有 {clipped_count} 个夏普值超出[-10, 10]范围，已截断")

            # 计算多样性：基于表达式唯一性
            expressions = set()
            for ind in sorted_inds[:100]:  # 只检查前100个
                try:
                    expr = ind.to_expression()
                    expressions.add(expr)
                except Exception as e:
                    logger.debug(f"获取表达式失败: {e}")
            diversity_score = len(expressions) / max(len(sorted_inds[:100]), 1)

            # 计算top10平均夏普
            top_10_sharpe = sum(sharpe_values[:10]) / min(len(sharpe_values), 10) if sharpe_values else 0

            # 计算过拟合检验指标（PBO/DSR/WFE）
            pbo, dsr, wfe = self._compute_overfitting_metrics(session, sharpe_values, self.current_generation)

            # 使用 _worker_task_id 或 task_config.task_id，确保 task_id 不为 None
            effective_task_id = self._worker_task_id or self.task_config.task_id
            # 如果仍然为 None，使用 symbol 作为 fallback
            if effective_task_id is None:
                effective_task_id = f"{self.task_config.symbol}_continuous"
                logger.warning(f"task_id 为 None，使用 fallback: {effective_task_id}")
            logger.info(f"DEBUG: _worker_task_id={self._worker_task_id}, task_config.task_id={self.task_config.task_id}, effective_task_id={effective_task_id}")

            # 检查是否已存在该世代的记录
            existing = session.execute(
                select(GenerationStats).where(
                    GenerationStats.task_id == effective_task_id,
                    GenerationStats.generation == self.current_generation
                )
            ).scalar_one_or_none()

            if existing:
                # 更新已有记录
                existing.avg_sharpe = sum(sharpe_values) / len(sharpe_values)
                existing.max_sharpe = max(sharpe_values)
                existing.min_sharpe = min(sharpe_values)
                existing.top_10_avg_sharpe = top_10_sharpe
                existing.avg_fitness = sum(fitness_values) / len(fitness_values) if fitness_values else 0
                existing.best_fitness = max(fitness_values) if fitness_values else 0
                existing.diversity_score = diversity_score
                existing.unique_expressions = len(expressions)
                existing.population_size = len(sorted_inds)
                existing.elite_count = self.evolution_config.elite_size
                existing.pbo = pbo
                existing.dsr = dsr
                existing.wfe = wfe
                logger.debug(f"更新第{self.current_generation}代统计指标")
            else:
                # 创建新记录
                stats = GenerationStats(
                    task_id=effective_task_id,
                    symbol=self.task_config.symbol,
                    generation=self.current_generation,
                    avg_sharpe=sum(sharpe_values) / len(sharpe_values),
                    max_sharpe=max(sharpe_values),
                    min_sharpe=min(sharpe_values),
                    top_10_avg_sharpe=top_10_sharpe,
                    avg_fitness=sum(fitness_values) / len(fitness_values) if fitness_values else 0,
                    best_fitness=max(fitness_values) if fitness_values else 0,
                    diversity_score=diversity_score,
                    unique_expressions=len(expressions),
                    population_size=len(sorted_inds),
                    elite_count=self.evolution_config.elite_size,
                    pbo=pbo,
                    dsr=dsr,
                    wfe=wfe,
                )
                session.add(stats)
                logger.info(f"保存第{self.current_generation}代统计指标到数据库")

            logger.info(f"第{self.current_generation}代统计指标保存成功")

            # 写入validation_pipeline_data表
            try:
                from app.api.validation_pipeline import ValidationPipelineService

                # 计算当前代的验证流程数据
                current_gen_input = len(sorted_inds)
                search_output = len(expressions)

                # Replay阶段：基于风险筛选（进一步放宽条件）
                replay_candidates = [
                    ind for ind in sorted_inds
                    if hasattr(ind, 'fitness') and
                    ind.fitness.get('sharpe', 0) > 0.0
                ]
                replay_output = len(replay_candidates)

                # Validation阶段：基于过拟合检验
                validation_passed = 0
                if hasattr(self, 'overfitting_results') and self.overfitting_results:
                    latest_check = self.overfitting_results[-1] if self.overfitting_results else None
                    if latest_check and hasattr(latest_check, 'passed_count'):
                        validation_passed = latest_check.passed_count
                validation_output = min(validation_passed, replay_output)

                # Demo阶段：最多保留20个
                demo_output = min(validation_output, 20)

                # 写入当前代数据到validation_pipeline_data表
                ValidationPipelineService.update_pipeline_data(
                    symbol=self.task_config.symbol,
                    generation=self.current_generation,
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
                logger.info(f"已写入validation_pipeline_data: generation={self.current_generation}, search_input={current_gen_input}, search_output={search_output}, replay_output={replay_output}")
            except Exception as e:
                logger.error(f"写入validation_pipeline_data失败: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"保存世代统计失败: {e}", exc_info=True)
    
    def _compute_overfitting_metrics(
        self, 
        session,
        sharpe_values: list, 
        generation: int
    ) -> tuple:
        """计算过拟合检验指标（PBO/DSR/WFE）
        
        Returns
        -------
        (pbo, dsr, wfe) : tuple
            - pbo: 回测过拟合概率 (0-1)
            - dsr: 放气夏普比率 (0-1)
            - wfe: Walk-Forward效率 (0-1)
        """
        try:
            from app.models import GenerationStats
            from sqlalchemy import select, desc
            
            # 获取最近50代的平均夏普值（使用avg_sharpe更稳定）
            history_stmt = select(GenerationStats.avg_sharpe).where(
                GenerationStats.task_id == self.task_config.task_id
            ).order_by(desc(GenerationStats.generation)).limit(50)
            
            history_rows = session.execute(history_stmt).scalars().all()
            history_sharpes = list(reversed(history_rows))  # 升序
            
            logger.debug(f"过拟合检验: 获取到 {len(history_sharpes)} 代历史夏普数据")
            
            if len(history_sharpes) < 10:
                # 数据不足，返回默认值
                logger.debug(f"过拟合检验: 历史数据不足（{len(history_sharpes)} < 10），返回None")
                return None, None, None
            
            # 过滤掉None值
            history_sharpes = [s for s in history_sharpes if s is not None]
            
            if len(history_sharpes) < 10:
                logger.debug(f"过拟合检验: 过滤None后数据不足（{len(history_sharpes)} < 10），返回None")
                return None, None, None
            
            # 计算PBO（回测过拟合概率）
            pbo = self._compute_pbo_simple(history_sharpes)
            
            # 计算DSR（放气夏普比率）
            n_strategies = len(sharpe_values)
            t_periods = generation * 100  # 假设每代100个样本
            max_sharpe = max(sharpe_values) if sharpe_values else 0
            
            if t_periods > n_strategies:
                dsr_factor = max(0, 1 - (n_strategies - 1) / (t_periods - 1))
                dsr = max_sharpe * np.sqrt(dsr_factor)
                dsr_normalized = min(1.0, dsr / 2.0)
            else:
                dsr_normalized = 0.0
            
            # 计算WFE（Walk-Forward效率）
            if len(history_sharpes) >= 20:
                train_sharpes = history_sharpes[-20:-10]
                val_sharpes = history_sharpes[-10:]
                
                train_avg = np.mean(train_sharpes) if train_sharpes else 0
                val_avg = np.mean(val_sharpes) if val_sharpes else 0
                
                if train_avg > 0:
                    wfe = val_avg / train_avg
                    wfe = max(0, min(1.0, wfe))
                else:
                    wfe = 0.0
            else:
                wfe = None
            
            logger.debug(f"过拟合检验: PBO={pbo:.4f}, DSR={dsr_normalized:.4f}, WFE={wfe}")
            
            return pbo, dsr_normalized, wfe
            
        except Exception as e:
            logger.error(f"计算过拟合指标失败: {e}", exc_info=True)
            return None, None, None
    
    def _compute_pbo_simple(self, sharpe_values: list) -> float:
        """简化版PBO计算（基于夏普值序列）
        
        使用组合对称交叉验证（CSCV）的简化版本：
        1. 将夏普值序列分成两半
        2. 比较两半的最大值
        3. 如果后半部分最大值 < 前半部分，则认为过拟合
        """
        if len(sharpe_values) < 10:
            return None
        
        # 分成两半
        mid = len(sharpe_values) // 2
        first_half = sharpe_values[:mid]
        second_half = sharpe_values[mid:]
        
        # 计算两半的最大值
        max_first = max(first_half) if first_half else 0
        max_second = max(second_half) if second_half else 0
        
        # 如果后半部分最大值显著低于前半部分，说明过拟合
        if max_first > 0:
            degradation = (max_first - max_second) / max_first
            # 退化程度 > 0.3 认为过拟合
            pbo = min(1.0, max(0.0, degradation / 0.3))
        else:
            pbo = 0.0
        
        return pbo
    
    def _send_websocket_update(self) -> None:
        """发送WebSocket更新消息"""
        # 子进程无法直接访问主进程的WebSocket连接，跳过
        # 进化进度由主进程的心跳监控循环通过数据库轮询推送
        pass
    
    def _send_symbol_update(self, status: str) -> None:
        """发送品种状态更新消息"""
        # 子进程无法直接访问主进程的WebSocket连接，跳过
        # 品种状态更新由主进程的心跳监控循环通过数据库轮询推送
        pass
    
    def get_progress(self) -> Dict[str, Any]:
        """获取进化进度"""
        return {
            "task_id": self.task_config.task_id,
            "is_running": self.is_running,
            "current_generation": self.current_generation,
            "max_generations": self.evolution_config.max_generations,
            "progress_pct": (
                (self.current_generation + 1) / self.evolution_config.max_generations * 100
                if self.evolution_config.max_generations > 0
                else 0
            ),
            "start_time": self.task_start_time.isoformat() if self.task_start_time else None,
            "best_fitness": self.gp.best_fitness,
        }
    
    def get_best_factors(self, n: int = 10, only_passed: bool = True) -> List[FactorRecord]:
        """获取最佳因子"""
        factors = self.final_factors
        if only_passed:
            factors = [f for f in factors if f.overfitting_passed]
        return factors[:n]
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取进化摘要"""
        summary = {
            "task_id": self.task_config.task_id,
            "symbol": self.task_config.symbol,
            "start_time": self.task_start_time.isoformat() if self.task_start_time else None,
            "end_time": self.task_end_time.isoformat() if self.task_end_time else None,
            "total_generations": self.current_generation + 1,
            "total_factors": len(self.final_factors),
            "passed_factors": sum(1 for f in self.final_factors if f.overfitting_passed),
        }
        
        if self.final_factors:
            passed = [f for f in self.final_factors if f.overfitting_passed]
            if passed:
                summary["best_sharpe"] = passed[0].sharpe
                summary["best_calmar"] = passed[0].calmar
                summary["best_return"] = passed[0].total_return
                summary["best_drawdown"] = passed[0].max_drawdown
        
        if self.evolution_result:
            summary["total_time"] = self.evolution_result.total_time
            summary["best_fitness"] = self.evolution_result.best_fitness
        
        return summary
    
    def get_evolution_tree_data(self, limit: int = 200) -> List[Dict[str, Any]]:
        """获取进化树数据"""
        tree_nodes = []
        
        # 获取所有历史个体
        all_individuals = list(self.historical_individuals.values())
        
        # 按夏普排序，取最好的
        all_individuals.sort(key=lambda x: x.fitness.get("sharpe", 0), reverse=True)
        
        for ind in all_individuals[:limit]:
            tree_nodes.append({
                "id": ind.id,
                "factor_id": ind.id,
                "generation": ind.generation,
                "sharpe_ratio": ind.fitness.get("sharpe", 0),
                "parent_id": ind.parent_ids[0] if ind.parent_ids else None,
                "children": [],
                "origin": ind.origin,
                "overfitting_passed": None,
                "pbo": None,
                "dsr": None,
                "wfe": None,
                "created_at": datetime.now(),
            })
        
        # 构建子节点关系
        id_to_node = {node["id"]: node for node in tree_nodes}
        for node in tree_nodes:
            if node["parent_id"] and node["parent_id"] in id_to_node:
                id_to_node[node["parent_id"]]["children"].append(node["id"])
        
        return tree_nodes


# ---------------------------------------------------------------------------
# 进化任务调度器
# ---------------------------------------------------------------------------

class EvolutionScheduler:
    """进化任务调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, EvolutionCenter] = {}
        self.completed_tasks: Dict[str, EvolutionCenter] = {}
    
    def create_task(
        self,
        config: EvolutionTaskConfig,
        data_hub: Optional[DataHub] = None,
    ) -> str:
        """创建进化任务"""
        if config.task_id in self.tasks:
            logger.warning(f"任务已存在: {config.task_id}")
        
        center = EvolutionCenter(config, data_hub)
        self.tasks[config.task_id] = center
        logger.info(f"创建进化任务: {config.task_id}")
        return config.task_id
    
    def run_task(self, task_id: str) -> Optional[EvolutionResult]:
        """运行指定任务"""
        if task_id not in self.tasks:
            logger.error(f"任务不存在: {task_id}")
            return None
        
        center = self.tasks[task_id]
        
        try:
            result = center.run_evolution()
            
            # 移至已完成
            self.completed_tasks[task_id] = center
            del self.tasks[task_id]
            
            return result
        except Exception as e:
            logger.error(f"任务执行失败 {task_id}: {e}", exc_info=True)
            return None
    
    def run_all_tasks(self) -> Dict[str, Optional[EvolutionResult]]:
        """运行所有任务"""
        results = {}
        task_ids = list(self.tasks.keys())
        
        for task_id in task_ids:
            logger.info(f"开始执行任务: {task_id}")
            results[task_id] = self.run_task(task_id)
        
        return results
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id in self.tasks:
            return self.tasks[task_id].get_progress()
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id].get_progress()
        return None
    
    def get_all_tasks(self) -> List[str]:
        """获取所有任务ID"""
        return list(self.tasks.keys()) + list(self.completed_tasks.keys())
