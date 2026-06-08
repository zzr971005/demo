"""
持续进化中心 — 永不停止的因子挖掘系统

基于EvoGP (2025) 和最新学术研究

特点：
- GPU加速进化
- 永不停止的持续进化
- 多品种并行
- 实时因子库更新
- 过拟合检验
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from ..data.hub import TimescaleHub as DataHub
from .gpu_evolution import ContinuousEvolutionEngine, GPUEvolutionConfig
from .multi_symbol_evolution import (
    MultiSymbolEvolutionScheduler,
    SymbolEvolutionConfig,
)
from .gp_fitness import FitnessConfig
from .gp_overfitting import OverfittingCheckResult, OverfittingConfig, OverfittingChecker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 因子库记录
# ---------------------------------------------------------------------------

@dataclass
class LibraryFactor:
    """因子库中的因子记录"""
    
    factor_id: str
    symbol: str
    expression: str
    
    # 性能
    sharpe: float
    fitness: float
    total_return: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    
    # 来源
    generation: int
    origin: str = "unknown"
    
    # 检验
    overfitting_passed: bool = False
    pbo: Optional[float] = None
    dsr: Optional[float] = None
    wfe: Optional[float] = None
    
    # 元数据
    added_at: datetime = field(default_factory=datetime.now)
    last_checked: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "symbol": self.symbol,
            "expression": self.expression,
            "sharpe": self.sharpe,
            "fitness": self.fitness,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "generation": self.generation,
            "origin": self.origin,
            "overfitting_passed": self.overfitting_passed,
            "pbo": self.pbo,
            "dsr": self.dsr,
            "wfe": self.wfe,
            "added_at": self.added_at.isoformat(),
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# 持续进化中心
# ---------------------------------------------------------------------------

class ContinuousEvolutionCenter:
    """持续进化中心"""
    
    def __init__(
        self,
        data_hub: Optional[DataHub] = None,
        max_concurrent_evolution: int = 4,
        use_gpu: bool = False,
        output_dir: str = "./output/continuous_evolution",
    ):
        self.data_hub = data_hub
        self.output_dir = output_dir
        self.use_gpu = use_gpu
        
        # 创建目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 调度器
        self.scheduler = MultiSymbolEvolutionScheduler(
            max_concurrent=max_concurrent_evolution,
            use_gpu=use_gpu,
        )
        
        # 过拟合检验器
        self.overfitting_config = OverfittingConfig(
            pbo_threshold=0.3,
            dsr_threshold=0.6,
            wfe_threshold=0.7,
        )
        self.fitness_config = FitnessConfig()
        self.overfitting_checker = OverfittingChecker(
            self.overfitting_config,
            self.fitness_config,
        )
        
        # 因子库
        self.factor_library: Dict[str, LibraryFactor] = {}
        self.library_lock = threading.RLock()
        
        # 符号数据缓存
        self.symbol_data_cache: Dict[str, pd.DataFrame] = {}
        
        # 状态
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        logger.info("持续进化中心初始化完成")
        logger.info(f"GPU加速: {'启用' if use_gpu else '禁用'}")
        logger.info(f"最大并发: {max_concurrent_evolution}")
        logger.info(f"输出目录: {output_dir}")
    
    def register_symbol(
        self,
        symbol: str,
        mode: str = "paper",
        priority: int = 5,
        population_size: int = 500,
        min_sharpe: float = 0.8,
        data: Optional[pd.DataFrame] = None,
    ) -> None:
        """注册品种"""
        # 加载数据（如果没有提供）
        if data is None:
            data = self._load_symbol_data(symbol)
        
        if data is None or len(data) == 0:
            logger.error(f"无法加载品种 {symbol} 的数据")
            return
        
        # 缓存数据
        self.symbol_data_cache[symbol] = data
        
        # 创建配置
        config = SymbolEvolutionConfig(
            symbol=symbol,
            mode=mode,
            priority=priority,
            population_size=population_size,
            min_sharpe=min_sharpe,
            use_gpu=self.use_gpu,
            data=data,
        )
        
        # 设置回调
        config.on_new_factor = self._on_new_factor
        config.on_checkpoint = self._on_checkpoint
        
        # 注册
        self.scheduler.register_symbol(config)
        
        logger.info(f"品种 {symbol} 注册完成，数据量: {len(data)}")
    
    def _load_symbol_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """加载品种数据"""
        if self.data_hub is None:
            logger.error("DataHub未配置")
            return None
        
        # 计算日期范围（2年）
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=730)
        
        try:
            data = self.data_hub.get_ohlcv(
                symbol=symbol,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                frequency="1H",
            )
            logger.info(f"从DataHub加载品种 {symbol} 数据: {len(data)} 条")
            return data
        except Exception as e:
            logger.error(f"加载品种 {symbol} 数据失败: {e}")
            return None
    
    def start_evolution(self, symbol: str) -> bool:
        """启动品种进化"""
        # 确保数据已加载
        if symbol not in self.symbol_data_cache:
            self._load_symbol_data(symbol)
        
        return self.scheduler.start_evolution(symbol)
    
    def stop_evolution(self, symbol: str) -> bool:
        """停止品种进化"""
        return self.scheduler.stop_evolution(symbol)
    
    def stop_all_evolutions(self) -> None:
        """停止所有进化"""
        self.scheduler.stop_all()
    
    def _on_new_factor(
        self,
        symbol: str,
        individual: Any,
        generation: int,
    ) -> None:
        """新因子回调"""
        try:
            expr = individual.to_expression()
            sharpe = individual.fitness.get("sharpe", 0.0)
            fitness = individual.fitness.get("penalized", 0.0)
            
            # 生成因子ID
            factor_id = f"{symbol}_{int(time.time())}_{generation}"
            
            # 创建因子记录
            factor = LibraryFactor(
                factor_id=factor_id,
                symbol=symbol,
                expression=expr,
                sharpe=sharpe,
                fitness=fitness,
                total_return=individual.metrics.get("total_return", 0.0),
                max_drawdown=individual.metrics.get("max_drawdown", 0.0),
                total_trades=individual.metrics.get("total_trades", 0),
                win_rate=individual.metrics.get("win_rate", 0.0),
                generation=generation,
                origin=individual.origin,
            )
            
            # 异步过拟合检验
            # 这里我们先添加到库，后续在后台检验
            with self.library_lock:
                self.factor_library[factor_id] = factor
            
            logger.debug(
                f"新因子: {symbol} 代{generation} "
                f"夏普={sharpe:.4f} "
                f"表达式={expr}"
            )
            
        except Exception as e:
            logger.error(f"处理新因子失败: {e}", exc_info=True)
    
    def _on_checkpoint(self, symbol: str, checkpoint: Dict[str, Any]) -> None:
        """检查点回调"""
        logger.info(
            f"品种 {symbol} 检查点: "
            f"代={checkpoint.get('generation')} "
            f"最佳适应度={checkpoint.get('best_fitness', 0):.4f} "
            f"因子库={checkpoint.get('factor_library_size', 0)}"
        )
        
        # 保存因子库快照
        self._save_factor_library()
    
    def _save_factor_library(self) -> None:
        """保存因子库"""
        try:
            with self.library_lock:
                if not self.factor_library:
                    return
                
                # 转换为DataFrame
                factors = list(self.factor_library.values())
                df = pd.DataFrame([f.to_dict() for f in factors])
                
                # 保存
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(
                    self.output_dir,
                    f"factor_library_{timestamp}.csv",
                )
                df.to_csv(file_path, index=False, encoding="utf-8")
                
                # 同时保存最新版本
                latest_path = os.path.join(
                    self.output_dir,
                    "factor_library_latest.csv",
                )
                df.to_csv(latest_path, index=False, encoding="utf-8")
                
                logger.info(f"因子库已保存: {len(df)} 个因子")
                
        except Exception as e:
            logger.error(f"保存因子库失败: {e}", exc_info=True)
    
    def get_status(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取状态"""
        scheduler_status = self.scheduler.get_status(symbol)
        
        if symbol is None:
            # 全局状态
            with self.library_lock:
                library_count = len(self.factor_library)
                active_factors = sum(1 for f in self.factor_library.values() if f.is_active)
                passed_factors = sum(1 for f in self.factor_library.values() if f.overfitting_passed)
            
            return {
                **scheduler_status,
                "factor_library": {
                    "total": library_count,
                    "active": active_factors,
                    "passed": passed_factors,
                },
            }
        else:
            return scheduler_status
    
    def get_best_factors(
        self,
        n: int = 100,
        symbol: Optional[str] = None,
        only_passed: bool = True,
    ) -> List[LibraryFactor]:
        """获取最佳因子"""
        with self.library_lock:
            factors = list(self.factor_library.values())
            
            if symbol is not None:
                factors = [f for f in factors if f.symbol == symbol]
            
            if only_passed:
                factors = [f for f in factors if f.overfitting_passed]
            
            # 按夏普排序
            factors.sort(key=lambda x: x.sharpe, reverse=True)
            
            return factors[:n]
    
    def get_factor(self, factor_id: str) -> Optional[LibraryFactor]:
        """获取指定因子"""
        with self.library_lock:
            return self.factor_library.get(factor_id)
    
    def load_factor_library(self, file_path: Optional[str] = None) -> int:
        """加载因子库"""
        if file_path is None:
            file_path = os.path.join(self.output_dir, "factor_library_latest.csv")
        
        if not os.path.exists(file_path):
            logger.warning(f"因子库文件不存在: {file_path}")
            return 0
        
        try:
            df = pd.read_csv(file_path)
            count = 0
            
            with self.library_lock:
                for _, row in df.iterrows():
                    factor = LibraryFactor(
                        factor_id=row["factor_id"],
                        symbol=row["symbol"],
                        expression=row["expression"],
                        sharpe=row["sharpe"],
                        fitness=row["fitness"],
                        total_return=row.get("total_return", 0.0),
                        max_drawdown=row.get("max_drawdown", 0.0),
                        total_trades=row.get("total_trades", 0),
                        win_rate=row.get("win_rate", 0.0),
                        generation=row.get("generation", 0),
                        origin=row.get("origin", "unknown"),
                        overfitting_passed=row.get("overfitting_passed", False),
                        pbo=row.get("pbo"),
                        dsr=row.get("dsr"),
                        wfe=row.get("wfe"),
                        is_active=row.get("is_active", True),
                    )
                    
                    if row.get("added_at"):
                        factor.added_at = datetime.fromisoformat(row["added_at"])
                    if row.get("last_checked"):
                        factor.last_checked = datetime.fromisoformat(row["last_checked"])
                    
                    self.factor_library[factor.factor_id] = factor
                    count += 1
            
            logger.info(f"加载因子库完成: {count} 个因子")
            return count
            
        except Exception as e:
            logger.error(f"加载因子库失败: {e}", exc_info=True)
            return 0
    
    def shutdown(self) -> None:
        """关闭"""
        logger.info("正在关闭持续进化中心...")
        self.shutdown_event.set()
        self.scheduler.shutdown()
        self._save_factor_library()
        logger.info("持续进化中心已关闭")
