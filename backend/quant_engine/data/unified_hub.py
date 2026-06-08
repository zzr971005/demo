"""
统一数据访问中心 - 整合所有数据库访问

职责：
- 时序数据（OHLCV、因子值）→ TimescaleDB
- 业务数据（策略、交易记录、风控事件）→ PostgreSQL
- 缓存 → Redis（可选）

替代分散的数据库连接，提供统一API
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataHub:
    """统一数据访问中心"""

    def __init__(
        self,
        db_url: Optional[str] = None,
        redis_url: Optional[str] = None
    ):
        self._db_url = db_url or os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/quant_db")
        
        # 初始化时序数据库
        from .hub import TimescaleHub
        self.timescale = TimescaleHub(db_url=self._db_url)
        
        # 初始化业务数据库（PostgreSQL）
        try:
            from .postgres_hub import PostgresHub
            self.postgres = PostgresHub(db_url=self._db_url)
        except ImportError as e:
            logger.warning(f"无法导入PostgresHub: {e}")
            self.postgres = None
        
        # 初始化Redis缓存（可选）
        self.redis = None
        if redis_url or os.getenv("REDIS_URL"):
            try:
                import redis
                redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
            except (ImportError, Exception) as e:
                logger.warning(f"无法连接Redis: {e}")

    # ========== 时序数据操作（委托给TimescaleHub） ==========
    
    def get_ohlcv(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "1H",
        **kwargs
    ) -> pd.DataFrame:
        """获取OHLCV数据"""
        return self.timescale.get_ohlcv(symbol, start_date, end_date, frequency, **kwargs)

    def save_ohlcv(self, symbol: str, df: pd.DataFrame, frequency: str = "1H") -> int:
        """保存OHLCV数据"""
        return self.timescale.save_ohlcv(symbol, df, frequency)

    def get_factor_values(
        self,
        symbol: str,
        factor_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取因子值"""
        return self.timescale.get_factor_values(symbol, factor_name, start_date, end_date)

    def save_factor_values(
        self,
        symbol: str,
        factor_name: str,
        df: pd.DataFrame,
        overwrite: bool = False,
    ) -> int:
        """保存因子值"""
        return self.timescale.save_factor_values(symbol, factor_name, df, overwrite)

    def get_available_range(self, symbol: str, duration_seconds: int) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
        """获取可用数据范围"""
        return self.timescale.get_available_range(symbol, duration_seconds)

    def get_multi_symbol_ohlcv(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "1H",
        normalize: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        获取多品种OHLCV数据
        
        Args:
            symbols: 品种列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            normalize: 是否标准化为收益率
            
        Returns:
            {symbol: DataFrame} 字典，每个DataFrame包含OHLCV数据和收益率
        """
        result = {}
        for symbol in symbols:
            df = self.get_ohlcv(symbol, start_date, end_date, frequency)
            if not df.empty:
                if normalize:
                    df = self._normalize_to_log_returns(df)
                result[symbol] = df
        return result

    def _normalize_to_log_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将OHLCV数据转换为对数收益率
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            包含收益率的DataFrame
        """
        df = df.copy()
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        df['symbol'] = df.index.name if hasattr(df.index, 'name') else 'unknown'
        return df

    # ========== 业务数据操作（委托给PostgresHub） ==========
    
    def save_candidate(self, data: Dict[str, Any]) -> None:
        """保存候选策略"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.save_candidate(data)

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """获取候选策略"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        return self.postgres.get_candidate(candidate_id)

    def query_candidates(self, **kwargs) -> List[Dict[str, Any]]:
        """查询候选策略列表"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        return self.postgres.query_candidates(**kwargs)

    def update_candidate(self, candidate_id: str, updates: Dict[str, Any]) -> None:
        """更新候选策略"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.update_candidate(candidate_id, updates)

    def delete_candidate(self, candidate_id: str) -> None:
        """删除候选策略"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.delete_candidate(candidate_id)

    def save_trade(self, data: Dict[str, Any]) -> None:
        """保存交易记录"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.save_trade(data)

    def query_trades(self, **kwargs) -> List[Dict[str, Any]]:
        """查询交易记录"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        return self.postgres.query_trades(**kwargs)

    def update_trade(self, trade_id: str, updates: Dict[str, Any]) -> None:
        """更新交易记录"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.update_trade(trade_id, updates)

    def save_evolution_generation(self, data: Dict[str, Any]) -> None:
        """保存进化世代记录"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.save_evolution_generation(data)

    def get_latest_generation(self, symbol: str, stage: int) -> Optional[int]:
        """获取最新进化世代"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        return self.postgres.get_latest_generation(symbol, stage)

    def save_risk_event(self, data: Dict[str, Any]) -> None:
        """保存风控事件"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.save_risk_event(data)

    def query_risk_events(self, **kwargs) -> List[Dict[str, Any]]:
        """查询风控事件"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        return self.postgres.query_risk_events(**kwargs)

    def get_symbol_switch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取品种开关状态"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        return self.postgres.get_symbol_switch(symbol)

    def set_symbol_switch(self, symbol: str, mode: str, config: Optional[str] = None) -> None:
        """设置品种开关状态"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        self.postgres.set_symbol_switch(symbol, mode, config)

    def get_all_symbol_switches(self) -> List[Dict[str, Any]]:
        """获取所有品种开关状态"""
        if not self.postgres:
            raise RuntimeError("PostgresHub未初始化")
        return self.postgres.get_all_symbol_switches()

    # ========== 缓存操作（委托给Redis） ==========
    
    def cache_set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> None:
        """设置缓存"""
        if not self.redis:
            return
        if expire_seconds:
            self.redis.setex(key, expire_seconds, value)
        else:
            self.redis.set(key, value)

    def cache_get(self, key: str) -> Optional[str]:
        """获取缓存"""
        if not self.redis:
            return None
        return self.redis.get(key)

    def cache_delete(self, key: str) -> None:
        """删除缓存"""
        if not self.redis:
            return
        self.redis.delete(key)

    def close(self) -> None:
        """关闭所有连接"""
        self.timescale.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# 设置导出
__all__ = ["DataHub"]
