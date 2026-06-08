"""
quant_engine.data — 数据接入层

包含：
- source: 天勤行情接入（历史数据、实时订阅、主力合约映射）
- hub: 数据读写中心（TimescaleDB + SQLite）
- unified_hub: 统一数据访问中心（整合所有数据库）
- postgres_hub: PostgreSQL业务数据访问中心
"""

from .source import TqDataSource, KlineCache, get_main_contract, OHLCV
from .hub import (
    TimescaleHub,
    SQLiteHub,
    DataPipeline,
    OHLCVRecord,
    FactorRecord,
)
from .unified_hub import DataHub
from .postgres_hub import PostgresHub

__all__ = [
    "TqDataSource",
    "KlineCache",
    "OHLCV",
    "get_main_contract",
    "TimescaleHub",
    "SQLiteHub",
    "PostgresHub",
    "DataPipeline",
    "DataHub",
    "OHLCVRecord",
    "FactorRecord",
]
