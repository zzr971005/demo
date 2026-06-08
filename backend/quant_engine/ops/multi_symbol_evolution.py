"""
多品种并行进化调度器

支持：
- 每个品种独立的进化引擎
- 并行任务调度
- GPU资源分配
- 实时监控
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

import pandas as pd

from .gpu_evolution import ContinuousEvolutionEngine, GPUEvolutionConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 品种进化任务配置
# ---------------------------------------------------------------------------

@dataclass
class SymbolEvolutionConfig:
    """单个品种的进化配置"""
    
    symbol: str
    enabled: bool = True
    mode: str = "paper"  # "paper" | "live" | "off"
    
    # 进化配置
    population_size: int = 500
    max_generations: int = 0  # 0 = 无限
    use_gpu: bool = False
    
    # 优先级（影响GPU分配）
    priority: int = 5  # 1-10，越高越优先
    
    # 因子筛选阈值
    min_sharpe: float = 0.8
    min_fitness: float = 0.5
    
    # 状态
    is_running: bool = False
    engine: Optional[ContinuousEvolutionEngine] = None
    last_update: float = 0.0
    
    # 统计
    current_generation: int = 0
    best_sharpe: float = 0.0
    factor_count: int = 0
    
    # 自定义回调
    on_new_factor: Optional[Callable[[str, Any, int], None]] = None
    on_checkpoint: Optional[Callable[[str, Dict[str, Any]], None]] = None
    
    # 数据
    data: Optional[pd.DataFrame] = None


# ---------------------------------------------------------------------------
# 多品种进化调度器
# ---------------------------------------------------------------------------

class MultiSymbolEvolutionScheduler:
    """多品种并行进化调度器"""
    
    def __init__(
        self,
        max_concurrent: int = 4,  # 最多同时运行的进化任务
        use_gpu: bool = False,
    ):
        self.max_concurrent = max_concurrent
        self.use_gpu = use_gpu
        
        # 任务管理
        self.symbol_configs: Dict[str, SymbolEvolutionConfig] = {}
        self.running_symbols: Set[str] = set()
        self.task_threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent + 2)
        
        # 全局状态
        self.is_shutdown = False
        self.global_factor_library: List[Dict[str, Any]] = []
        
        # 锁
        self.lock = threading.RLock()
        
        logger.info(f"多品种进化调度器初始化完成")
        logger.info(f"最大并发任务: {max_concurrent}")
        logger.info(f"GPU加速: {'启用' if use_gpu else '禁用'}")
    
    def register_symbol(
        self,
        config: SymbolEvolutionConfig,
    ) -> None:
        """注册品种"""
        with self.lock:
            self.symbol_configs[config.symbol] = config
            logger.info(f"注册品种: {config.symbol}")
    
    def get_symbol_config(self, symbol: str) -> Optional[SymbolEvolutionConfig]:
        """获取品种配置"""
        return self.symbol_configs.get(symbol)
    
    def update_symbol_data(self, symbol: str, data: pd.DataFrame) -> None:
        """更新品种数据"""
        with self.lock:
            if symbol in self.symbol_configs:
                self.symbol_configs[symbol].data = data
                self.symbol_configs[symbol].last_update = time.time()
    
    def start_evolution(
        self,
        symbol: str,
        data: Optional[pd.DataFrame] = None,
    ) -> bool:
        """启动品种进化"""
        with self.lock:
            # 检查是否已在运行
            if symbol in self.running_symbols:
                logger.warning(f"品种 {symbol} 已在运行中")
                return False
            
            # 检查配置
            config = self.symbol_configs.get(symbol)
            if config is None:
                logger.error(f"品种 {symbol} 未注册")
                return False
            
            if not config.enabled:
                logger.warning(f"品种 {symbol} 已禁用")
                return False
            
            # 检查并发限制
            if len(self.running_symbols) >= self.max_concurrent:
                logger.error(
                    f"已达到最大并发限制 {self.max_concurrent}，"
                    f"当前运行: {sorted(self.running_symbols)}"
                )
                return False
            
            # 更新数据
            if data is not None:
                config.data = data
            elif config.data is None:
                logger.error(f"品种 {symbol} 缺少数据")
                return False
            
            # 创建停止事件
            stop_event = threading.Event()
            self.stop_events[symbol] = stop_event
            
            # 创建并启动线程
            thread = threading.Thread(
                target=self._run_evolution_task,
                args=(symbol, config, stop_event),
                daemon=True,
                name=f"evolution_{symbol}",
            )
            self.task_threads[symbol] = thread
            self.running_symbols.add(symbol)
            config.is_running = True
            
            thread.start()
            logger.info(f"启动品种 {symbol} 的进化任务")
            
            return True
    
    def stop_evolution(self, symbol: str) -> bool:
        """停止品种进化"""
        with self.lock:
            if symbol not in self.running_symbols:
                logger.warning(f"品种 {symbol} 不在运行中")
                return False
            
            config = self.symbol_configs.get(symbol)
            if config is None:
                return False
            
            # 发送停止信号
            if symbol in self.stop_events:
                self.stop_events[symbol].set()
            
            # 停止引擎
            if config.engine is not None:
                config.engine.stop()
            
            config.is_running = False
            logger.info(f"请求停止品种 {symbol} 的进化任务")
            
            return True
    
    def stop_all(self) -> None:
        """停止所有进化任务"""
        logger.info("正在停止所有进化任务...")
        
        with self.lock:
            symbols_to_stop = list(self.running_symbols)
        
        for symbol in symbols_to_stop:
            self.stop_evolution(symbol)
        
        # 等待所有线程结束
        for symbol, thread in list(self.task_threads.items()):
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        self.is_shutdown = True
        logger.info("所有进化任务已停止")
    
    def _run_evolution_task(
        self,
        symbol: str,
        config: SymbolEvolutionConfig,
        stop_event: threading.Event,
    ) -> None:
        """在独立线程中运行进化任务"""
        try:
            logger.info(f"品种 {symbol} 进化任务开始")
            
            # 创建进化配置
            gpu_config = GPUEvolutionConfig(
                population_size=config.population_size,
                max_generations=config.max_generations,
                use_gpu=config.use_gpu and self.use_gpu,
                enable_continuous_evolution=True,
                max_stagnation=0,
            )
            
            # 创建引擎
            engine = ContinuousEvolutionEngine(gpu_config)
            config.engine = engine
            
            # 包装回调
            def on_new_factor(ind: Any, gen: int):
                config.current_generation = gen
                if ind.fitness.get("sharpe", 0) > config.best_sharpe:
                    config.best_sharpe = ind.fitness.get("sharpe", 0)
                
                # 添加到全局因子库
                self._add_to_global_library(symbol, ind, gen)
                
                # 调用自定义回调
                if config.on_new_factor:
                    config.on_new_factor(symbol, ind, gen)
            
            def on_checkpoint(checkpoint: Dict[str, Any]):
                config.factor_count = checkpoint.get("factor_library_size", 0)
                config.current_generation = checkpoint.get("generation", 0)
                
                if config.on_checkpoint:
                    config.on_checkpoint(symbol, checkpoint)
            
            # 启动进化（在同一个线程中运行，不使用executor）
            # ContinuousEvolutionEngine.evolve_continuous() 是阻塞的
            engine.evolve_continuous(
                data=config.data,
                symbol=symbol,
                on_new_factor=on_new_factor,
                on_checkpoint=on_checkpoint,
            )
        
        except Exception as e:
            logger.error(f"品种 {symbol} 进化任务出错: {e}", exc_info=True)
        finally:
            # 清理
            with self.lock:
                if symbol in self.running_symbols:
                    self.running_symbols.remove(symbol)
                if symbol in self.stop_events:
                    del self.stop_events[symbol]
                config.is_running = False
                config.engine = None
            
            logger.info(f"品种 {symbol} 进化任务结束")
    
    def _add_to_global_library(
        self,
        symbol: str,
        individual: Any,
        generation: int,
    ) -> None:
        """添加因子到全局库"""
        with self.lock:
            expr = individual.to_expression()
            
            # 检查是否已存在
            exists = any(
                f["expression"] == expr and f["symbol"] == symbol
                for f in self.global_factor_library
            )
            if exists:
                return
            
            # 添加
            factor_entry = {
                "symbol": symbol,
                "expression": expr,
                "sharpe": individual.fitness.get("sharpe", 0.0),
                "fitness": individual.fitness.get("penalized", 0.0),
                "generation": generation,
                "origin": individual.origin,
                "added_at": time.time(),
            }
            self.global_factor_library.append(factor_entry)
            
            # 保持库大小
            self.global_factor_library.sort(key=lambda x: x["sharpe"], reverse=True)
            self.global_factor_library = self.global_factor_library[:10000]  # 最多10000个
    
    def get_status(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取状态"""
        with self.lock:
            if symbol is not None:
                config = self.symbol_configs.get(symbol)
                if config is None:
                    return {}
                
                engine_stats = {}
                if config.engine is not None:
                    engine_stats = config.engine.get_stats()
                
                return {
                    "symbol": symbol,
                    "enabled": config.enabled,
                    "is_running": config.is_running,
                    "mode": config.mode,
                    "priority": config.priority,
                    "current_generation": engine_stats.get("current_generation", 0),
                    "best_sharpe": engine_stats.get("best_fitness", 0),
                    "factor_count": engine_stats.get("factor_library_size", 0),
                }
            
            # 返回所有品种状态
            return {
                "total_symbols": len(self.symbol_configs),
                "running_symbols": sorted(self.running_symbols),
                "max_concurrent": self.max_concurrent,
                "global_factor_count": len(self.global_factor_library),
                "symbols": [
                    self.get_status(sym)
                    for sym in sorted(self.symbol_configs.keys())
                ],
            }
    
    def get_best_factors(
        self,
        n: int = 100,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取最佳因子"""
        with self.lock:
            factors = self.global_factor_library
            if symbol is not None:
                factors = [f for f in factors if f["symbol"] == symbol]
            return factors[:n]
    
    def shutdown(self) -> None:
        """关闭调度器"""
        self.stop_all()
        self.executor.shutdown(wait=True)
        logger.info("多品种进化调度器已关闭")
