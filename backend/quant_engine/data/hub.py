"""
数据读写中心 — TimescaleDB 与 SQLite 统一读写接口

提供：
- OHLCV K线数据读写（TimescaleDB）
- 因子值读写（TimescaleDB）
- 候选策略、交易记录、系统状态读写（SQLite）
- 批量导入与查询优化
- 与系统配置对齐的品种支持
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    delete,
    func,
    insert,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError
import time
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

DEFAULT_TIMESCALE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/quant_db"
)
# 如果URL使用asyncpg，替换为psycopg2用于同步连接
if DEFAULT_TIMESCALE_URL.startswith("postgresql+asyncpg"):
    DEFAULT_TIMESCALE_URL = DEFAULT_TIMESCALE_URL.replace(
        "postgresql+asyncpg",
        "postgresql+psycopg2"
    )

DEFAULT_SQLITE_PATH = os.getenv(
    "SQLITE_PATH",
    str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "runtime.db")
)

# 支持的K线周期（秒）
SUPPORTED_DURATIONS = {
    60: "1m",
    300: "5m",
    900: "15m",
    1800: "30m",
    3600: "1h",
    86400: "1d",
}


# 表名白名单，防止SQL注入
VALID_TABLE_NAMES = {'ohlcv_1m', 'ohlcv_5m', 'ohlcv_15m', 'ohlcv_30m', 'ohlcv_1h', 'ohlcv_1d', 'factor_values', 'ohlcv_term_1h', 'ohlcv_term_1d'}

def validate_table_name(table_name: str) -> str:
    """验证表名是否在白名单中，防止SQL注入"""
    if table_name not in VALID_TABLE_NAMES:
        raise ValueError(f'非法表名: {table_name}')
    return table_name

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class OHLCVRecord:
    """单条K线记录"""
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_interest: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "ts": self.ts,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "open_interest": self.open_interest,
        }


@dataclass
class FactorRecord:
    """单条因子值记录"""
    symbol: str
    ts: datetime
    factor_name: str
    value: float
    generation: Optional[int] = None
    candidate_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "ts": self.ts,
            "factor_name": self.factor_name,
            "value": self.value,
            "generation": self.generation,
            "candidate_id": self.candidate_id,
        }


# ---------------------------------------------------------------------------
# TimescaleDB 读写中心
# ---------------------------------------------------------------------------

class TimescaleHub:
    """
    TimescaleDB 数据读写中心

    负责：
    - OHLCV K线数据的读写
    - 因子值的读写
    - 超表管理与查询优化
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or DEFAULT_TIMESCALE_URL
        self.engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._connect()

    def _connect(self, max_retries: int = 5, base_delay: float = 1.0) -> None:
        """
        建立数据库连接（带重试机制）
        
        参数:
            max_retries: 最大重试次数，默认5次
            base_delay: 基础延迟秒数，默认1秒（指数退避）
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                self.engine = create_engine(
                    self.db_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    echo=False,
                    connect_args={
                        "connect_timeout": 10,
                    }
                )
                
                # 测试连接
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                self._session_factory = sessionmaker(bind=self.engine)
                self._ensure_hypertables()
                
                if attempt > 0:
                    logger.info(f"数据库连接成功（第 {attempt + 1} 次尝试）")
                return
                
            except OperationalError as e:
                last_error = e
                delay = base_delay * (2 ** attempt)  # 指数退避
                
                if attempt < max_retries - 1:
                    logger.warning(
                        f"数据库连接失败（第 {attempt + 1}/{max_retries} 次）: {e}\n"
                        f"将在 {delay:.1f} 秒后重试..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"数据库连接失败，已达到最大重试次数 ({max_retries})")
                    raise RuntimeError(
                        f"无法连接到数据库: {self.db_url}\n"
                        f"错误: {e}\n"
                        f"请检查:\n"
                        f"  1. PostgreSQL 服务是否运行: sc query postgresql-x64-17\n"
                        f"  2. 数据库端口是否监听: netstat -an | findstr 5432\n"
                        f"  3. 用户名密码是否正确: qmt/qmt_secret\n"
                        f"  4. 运行诊断脚本: bat启动文件夹\\检查数据库状态.bat"
                    ) from e
                    
            except Exception as e:
                last_error = e
                logger.error(f"数据库连接发生未知错误: {e}")
                raise

    def _ensure_hypertables(self) -> None:
        """确保超表已创建"""
        with self.engine.begin() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                logger.info("TimescaleDB 扩展已创建")
            else:
                logger.info("TimescaleDB 扩展已存在")

            tables_to_hypertable = [
                ("ohlcv_1h", "ohlcv_1h"),
                ("ohlcv_1d", "ohlcv_1d"),
                ("factor_values", "factor_values"),
            ]

            # 先创建期限结构表（如果不存在）
            self._create_term_structure_tables(conn)
            
            # 添加期限结构表到超表列表
            tables_to_hypertable.extend([
                ("ohlcv_term_1h", "ohlcv_term_1h"),
                ("ohlcv_term_1d", "ohlcv_term_1d"),
            ])

            for table_name, hypertable_name in tables_to_hypertable:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM timescaledb_information.hypertables
                        WHERE hypertable_name = :ht_name
                    ) as exists_hypertable
                """), {"ht_name": hypertable_name}).fetchone()

                if not result or not result[0]:
                    try:
                        conn.execute(text(f"""
                            SELECT create_hypertable('{hypertable_name}', 'ts',
                                if_not_exists => TRUE,
                                migrate_data => TRUE)
                        """))
                        logger.info(f"超表 {hypertable_name} 已创建")
                    except Exception as e:
                        logger.debug(f"创建超表 {hypertable_name} 时出现问题: {e}")

                idx_name = f"idx_{table_name}_symbol_ts"
                try:
                    conn.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} (symbol, ts DESC)
                    """))
                except Exception as e:
                    logger.debug(f"创建索引 {idx_name} 时出现问题: {e}")

    def _create_term_structure_tables(self, conn) -> None:
        """创建期限结构数据表（如果不存在）"""
        for suffix in ["1h", "1d"]:
            table_name = f"ohlcv_term_{suffix}"
            try:
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        symbol VARCHAR(16) NOT NULL,
                        ts TIMESTAMP NOT NULL,
                        open DOUBLE PRECISION,
                        high DOUBLE PRECISION,
                        low DOUBLE PRECISION,
                        close DOUBLE PRECISION,
                        volume DOUBLE PRECISION,
                        open_interest DOUBLE PRECISION,
                        near_close DOUBLE PRECISION,
                        far_close DOUBLE PRECISION,
                        main_contract VARCHAR(32),
                        near_contract VARCHAR(32),
                        far_contract VARCHAR(32),
                        days_to_expiry INTEGER,
                        PRIMARY KEY (symbol, ts)
                    )
                """))
                logger.debug(f"期限结构表 {table_name} 已确保存在")
            except Exception as e:
                logger.debug(f"创建期限结构表 {table_name} 时出现问题: {e}")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """获取数据库会话"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    # ------------------------------------------------------------------
    # OHLCV 操作
    # ------------------------------------------------------------------

    def insert_ohlcv(
        self,
        symbol: str,
        df: pd.DataFrame,
        duration_seconds: int = 3600,
        if_exists: str = "replace",
    ) -> int:
        """
        插入 OHLCV K线数据

        Parameters
        ----------
        symbol : str
            品种代码
        df : pd.DataFrame
            K线数据，index为datetime，包含open/high/low/close/volume
        duration_seconds : int
            K线周期（秒）
        if_exists : str
            'fail' | 'replace' | 'append'

        Returns
        -------
        int — 插入的行数
        """
        if duration_seconds not in SUPPORTED_DURATIONS:
            raise ValueError(f"不支持的周期: {duration_seconds}，支持: {SUPPORTED_DURATIONS.keys()}")

        table_name = f"ohlcv_{SUPPORTED_DURATIONS[duration_seconds]}"
        validate_table_name(table_name)

        if df.empty:
            logger.warning(f"空数据，跳过插入: {symbol} {duration_seconds}s")
            return 0

        df = df.copy()
        df["symbol"] = symbol
        if "ts" not in df.columns:
            df["ts"] = df.index
        if "open_interest" not in df.columns:
            df["open_interest"] = None

        # 确保时间戳时区正确
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        records = df[
            ["symbol", "ts", "open", "high", "low", "close", "volume", "open_interest"]
        ].to_dict("records")

        with self.session() as session:
            if if_exists == "replace":
                session.execute(text(f"""
                    DELETE FROM {table_name} WHERE symbol = :symbol
                """), {"symbol": symbol})

            inserted = 0
            try:
                # 使用批量插入优化性能
                session.execute(
                    text(f"""
                        INSERT INTO {table_name} (symbol, ts, open, high, low, close, volume, open_interest)
                        VALUES (:symbol, :ts, :open, :high, :low, :close, :volume, :open_interest)
                        ON CONFLICT (symbol, ts) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            open_interest = EXCLUDED.open_interest
                    """),
                    records
                )
                inserted = len(records)
            except IntegrityError:
                if if_exists == "fail":
                    raise
                elif if_exists == "append":
                    # 逐行插入作为fallback
                    for record in records:
                        try:
                            session.execute(text(f"""
                                INSERT INTO {table_name} (symbol, ts, open, high, low, close, volume, open_interest)
                                VALUES (:symbol, :ts, :open, :high, :low, :close, :volume, :open_interest)
                                ON CONFLICT (symbol, ts) DO NOTHING
                            """), record)
                            inserted += 1
                        except Exception:
                            pass

            logger.info(f"插入 {inserted} 条 {symbol} {duration_seconds}s K线数据")
            return inserted

    def insert_term_structure(
        self,
        symbol: str,
        df: pd.DataFrame,
        duration_seconds: int = 3600,
        if_exists: str = "replace",
    ) -> int:
        """
        插入期限结构数据

        Parameters
        ----------
        symbol : str
            品种代码
        df : pd.DataFrame
            期限结构数据，index为datetime，包含：
            - open, high, low, close, volume, open_interest: 主连数据
            - near_close: 近月合约收盘价
            - far_close: 远月合约收盘价
            - main_contract: 当前主力合约
            - near_contract: 近月合约代码
            - far_contract: 远月合约代码
            - days_to_expiry: 近月合约到期天数
        duration_seconds : int
            K线周期（秒）
        if_exists : str
            'fail' | 'replace' | 'append'

        Returns
        -------
        int — 插入的行数
        """
        if duration_seconds not in SUPPORTED_DURATIONS:
            raise ValueError(f"不支持的周期: {duration_seconds}，支持: {SUPPORTED_DURATIONS.keys()}")

        table_name = f"ohlcv_term_{SUPPORTED_DURATIONS[duration_seconds]}"
        validate_table_name(table_name)

        if df.empty:
            logger.warning(f"空数据，跳过插入期限结构: {symbol} {duration_seconds}s")
            return 0

        df = df.copy()
        df["symbol"] = symbol
        if "ts" not in df.columns:
            df["ts"] = df.index

        # 确保时间戳时区正确
        if df["ts"].dtype == "datetime64[ns, UTC]":
            df["ts"] = df["ts"].dt.tz_convert(None)
        elif df["ts"].dtype == "datetime64[ns]":
            pass
        else:
            df["ts"] = pd.to_datetime(df["ts"])

        # 选择需要的列
        required_columns = [
            "symbol", "ts", "open", "high", "low", "close", "volume", "open_interest",
            "near_close", "far_close", "main_contract", "near_contract",
            "far_contract", "days_to_expiry"
        ]
        df = df[required_columns]

        # 转换为记录列表
        records = df.to_dict("records")

        inserted = 0
        with self.session() as session:
            try:
                if if_exists == "replace":
                    # 先删除现有数据
                    session.execute(text(f"""
                        DELETE FROM {table_name} WHERE symbol = :symbol
                    """), {"symbol": symbol})
                
                session.execute(text(f"""
                    INSERT INTO {table_name} (
                        symbol, ts, open, high, low, close, volume, open_interest,
                        near_close, far_close, main_contract, near_contract,
                        far_contract, days_to_expiry
                    ) VALUES (
                        :symbol, :ts, :open, :high, :low, :close, :volume, :open_interest,
                        :near_close, :far_close, :main_contract, :near_contract,
                        :far_contract, :days_to_expiry
                    )
                    ON CONFLICT (symbol, ts) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        open_interest = EXCLUDED.open_interest,
                        near_close = EXCLUDED.near_close,
                        far_close = EXCLUDED.far_close,
                        main_contract = EXCLUDED.main_contract,
                        near_contract = EXCLUDED.near_contract,
                        far_contract = EXCLUDED.far_contract,
                        days_to_expiry = EXCLUDED.days_to_expiry
                """), records)
                inserted = len(records)
            except IntegrityError:
                if if_exists == "fail":
                    raise
                elif if_exists == "append":
                    # 逐行插入作为fallback
                    for record in records:
                        try:
                            session.execute(text(f"""
                                INSERT INTO {table_name} (
                                    symbol, ts, open, high, low, close, volume, open_interest,
                                    near_close, far_close, main_contract, near_contract,
                                    far_contract, days_to_expiry
                                ) VALUES (
                                    :symbol, :ts, :open, :high, :low, :close, :volume, :open_interest,
                                    :near_close, :far_close, :main_contract, :near_contract,
                                    :far_contract, :days_to_expiry
                                )
                                ON CONFLICT (symbol, ts) DO NOTHING
                            """), record)
                            inserted += 1
                        except Exception:
                            pass

            logger.info(f"插入 {inserted} 条 {symbol} {duration_seconds}s 期限结构数据")
            return inserted

    def query_term_structure(
        self,
        symbol: str,
        start_dt: Optional[Union[str, datetime]] = None,
        end_dt: Optional[Union[str, datetime]] = None,
        duration_seconds: int = 3600,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        查询期限结构数据

        Parameters
        ----------
        symbol : str
            品种代码
        start_dt : str or datetime
            开始时间（包含）
        end_dt : str or datetime
            结束时间（包含）
        duration_seconds : int
            K线周期（秒）
        limit : int, optional
            最大返回条数

        Returns
        -------
        pd.DataFrame — index为datetime，包含期限结构数据
        """
        if duration_seconds not in SUPPORTED_DURATIONS:
            raise ValueError(f"不支持的周期: {duration_seconds}，支持: {SUPPORTED_DURATIONS.keys()}")

        table_name = f"ohlcv_term_{SUPPORTED_DURATIONS[duration_seconds]}"
        validate_table_name(table_name)

        conditions = ["symbol = :symbol"]
        params = {"symbol": symbol}

        if start_dt:
            conditions.append("ts >= :start_dt")
            ts = pd.Timestamp(start_dt)
            params["start_dt"] = ts.tz_localize(None) if ts.tzinfo is None else ts.tz_convert(None).to_pydatetime()
        if end_dt:
            conditions.append("ts <= :end_dt")
            ts = pd.Timestamp(end_dt)
            params["end_dt"] = ts.tz_localize(None) if ts.tzinfo is None else ts.tz_convert(None).to_pydatetime()

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT ts, open, high, low, close, volume, open_interest,
                   near_close, far_close, main_contract, near_contract,
                   far_contract, days_to_expiry
            FROM {table_name}
            WHERE {where_clause}
            ORDER BY ts ASC
        """
        if limit:
            sql += " LIMIT :limit"
            params["limit"] = limit

        with self.session() as session:
            result = session.execute(text(sql), params)
            df = pd.DataFrame(result.fetchall(), columns=[
                "ts", "open", "high", "low", "close", "volume", "open_interest",
                "near_close", "far_close", "main_contract", "near_contract",
                "far_contract", "days_to_expiry"
            ])
            
            if not df.empty:
                df["ts"] = pd.to_datetime(df["ts"])
                df.set_index("ts", inplace=True)
            
            return df

    def query_ohlcv(
        self,
        symbol: str,
        start_dt: Optional[Union[str, datetime]] = None,
        end_dt: Optional[Union[str, datetime]] = None,
        duration_seconds: int = 3600,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        查询 OHLCV K线数据

        Parameters
        ----------
        symbol : str
            品种代码
        start_dt : str or datetime
            开始时间（包含）
        end_dt : str or datetime
            结束时间（包含）
        duration_seconds : int
            K线周期（秒）
        limit : int, optional
            最大返回条数

        Returns
        -------
        pd.DataFrame — index为datetime，包含open/high/low/close/volume
        """
        if duration_seconds not in SUPPORTED_DURATIONS:
            raise ValueError(f"不支持的周期: {duration_seconds}，支持: {SUPPORTED_DURATIONS.keys()}")

        table_name = f"ohlcv_{SUPPORTED_DURATIONS[duration_seconds]}"
        validate_table_name(table_name)

        conditions = ["symbol = :symbol"]
        params = {"symbol": symbol}

        if start_dt:
            conditions.append("ts >= :start_dt")
            ts = pd.Timestamp(start_dt)
            params["start_dt"] = ts.tz_localize(None) if ts.tzinfo is None else ts.tz_convert(None).to_pydatetime()
        if end_dt:
            conditions.append("ts <= :end_dt")
            ts = pd.Timestamp(end_dt)
            params["end_dt"] = ts.tz_localize(None) if ts.tzinfo is None else ts.tz_convert(None).to_pydatetime()

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT ts, open, high, low, close, volume, open_interest
            FROM {table_name}
            WHERE {where_clause}
            ORDER BY ts ASC
        """
        if limit:
            params["limit_val"] = limit
            sql += " LIMIT :limit_val"

        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            df = pd.read_sql(text(sql), conn, params=params, index_col="ts")

        return df

    def get_record_count(
        self,
        symbol: str,
        duration_seconds: int = 3600,
    ) -> int:
        """获取某品种K线数据的记录数"""
        if duration_seconds not in SUPPORTED_DURATIONS:
            raise ValueError(f"不支持的周期: {duration_seconds}")

        table_name = f"ohlcv_{SUPPORTED_DURATIONS[duration_seconds]}"
        validate_table_name(table_name)

        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT COUNT(*) as count
                FROM {table_name}
                WHERE symbol = :symbol
            """), {"symbol": symbol}).fetchone()

        return result[0] if result else 0

    def get_available_range(
        self,
        symbol: str,
        duration_seconds: int = 3600,
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取某品种K线数据的可用时间范围"""
        if duration_seconds not in SUPPORTED_DURATIONS:
            raise ValueError(f"不支持的周期: {duration_seconds}")

        table_name = f"ohlcv_{SUPPORTED_DURATIONS[duration_seconds]}"
        validate_table_name(table_name)

        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            result = conn.execute(text(f"""
                SELECT MIN(ts) as min_ts, MAX(ts) as max_ts
                FROM {table_name}
                WHERE symbol = :symbol
            """), {"symbol": symbol}).fetchone()

        if result is None or result.min_ts is None:
            return None, None
        return result[0], result[1]

    def get_all_symbols(self, duration_seconds: int = 3600) -> List[str]:
        """获取数据库中已有数据的品种列表"""
        table_name = f"ohlcv_{SUPPORTED_DURATIONS[duration_seconds]}"
        validate_table_name(table_name)

        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            result = conn.execute(text(f"""
                SELECT DISTINCT symbol FROM {table_name} ORDER BY symbol
            """)).fetchall()

        return [row[0] for row in result]

    def get_ohlcv(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "1H",
    ) -> pd.DataFrame:
        """
        获取 OHLCV K线数据（供进化引擎使用）

        Parameters
        ----------
        symbol : str
            品种代码
        start_date : str, optional
            开始日期，格式 YYYY-MM-DD
        end_date : str, optional
            结束日期，格式 YYYY-MM-DD
        frequency : str
            频率，支持 '1H', '1D'

        Returns
        -------
        pd.DataFrame — index为datetime，包含open/high/low/close/volume/open_interest
        """
        frequency_map = {
            "1H": 3600,
            "1D": 86400,
        }

        if frequency not in frequency_map:
            raise ValueError(f"不支持的频率: {frequency}，支持: {list(frequency_map.keys())}")

        duration_seconds = frequency_map[frequency]

        df = self.query_ohlcv(
            symbol=symbol,
            start_dt=start_date,
            end_dt=end_date,
            duration_seconds=duration_seconds,
        )

        # 确保列名符合进化引擎期望
        df = df.rename(columns={"open_interest": "open_interest"})

        return df

    def get_multi_contract_ohlcv(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "1H",
    ) -> pd.DataFrame:
        """
        获取多合约OHLCV数据（主力、近月、远月）
        
        用于期限结构因子计算。优先从期限结构表读取，如果没有则回退到主连数据。
        
        Parameters
        ----------
        symbol : str
            品种代码（如 'RB'）
        start_date : str, optional
            开始日期
        end_date : str, optional
            结束日期
        frequency : str
            频率
            
        Returns
        -------
        pd.DataFrame
            包含主力、近月、远月合约数据的DataFrame
            列: open, high, low, close, volume, open_interest,
                near_close, far_close, days_to_expiry
        """
        frequency_map = {
            "1H": 3600,
            "1D": 86400,
        }
        
        duration_seconds = frequency_map.get(frequency, 3600)
        
        # 优先从期限结构表读取数据
        try:
            term_df = self.query_term_structure(
                symbol=symbol,
                start_dt=start_date,
                end_dt=end_date,
                duration_seconds=duration_seconds,
            )
            
            if not term_df.empty:
                logger.debug(f"从期限结构表获取 {symbol} 数据，共 {len(term_df)} 条")
                return term_df
        except Exception as e:
            logger.debug(f"从期限结构表读取数据失败: {e}")
        
        # 如果期限结构表没有数据，使用主连数据作为回退
        logger.debug(f"期限结构表无数据，使用主连数据回退: {symbol}")
        main_df = self.get_ohlcv(symbol, start_date, end_date, frequency)
        
        # 如果没有期限结构数据，用主连数据填充
        main_df['near_close'] = main_df['close']
        main_df['far_close'] = main_df['close']
        main_df['main_contract'] = None
        main_df['near_contract'] = None
        main_df['far_contract'] = None
        main_df['days_to_expiry'] = 30
        
        return main_df

    # ------------------------------------------------------------------
    # 因子值操作
    # ------------------------------------------------------------------

    def insert_factors(
        self,
        symbol: str,
        factor_name: str,
        values: pd.Series,
        generation: Optional[int] = None,
        candidate_id: Optional[str] = None,
        if_exists: str = "replace",
    ) -> int:
        """
        插入因子值序列

        Parameters
        ----------
        symbol : str
            品种代码
        factor_name : str
            因子名称
        values : pd.Series
            因子值，index为datetime
        generation : int, optional
            进化代数
        candidate_id : str, optional
            候选策略ID
        if_exists : str
            'fail' | 'replace' | 'append'

        Returns
        -------
        int — 插入的行数
        """
        if values.empty:
            return 0

        records = [
            FactorRecord(
                symbol=symbol,
                ts=ts,
                factor_name=factor_name,
                value=value,
                generation=generation,
                candidate_id=candidate_id,
            ).to_dict()
            for ts, value in values.items()
        ]

        with self.session() as session:
            if if_exists == "replace":
                session.execute(text("""
                    DELETE FROM factor_values
                    WHERE symbol = :symbol AND factor_name = :factor_name
                """), {"symbol": symbol, "factor_name": factor_name})

            inserted = 0
            try:
                # 批量插入优化
                session.execute(
                    text("""
                        INSERT INTO factor_values (symbol, ts, factor_name, value, generation, candidate_id)
                        VALUES (:symbol, :ts, :factor_name, :value, :generation, :candidate_id)
                        ON CONFLICT (symbol, ts, factor_name) DO UPDATE SET
                            value = EXCLUDED.value,
                            generation = EXCLUDED.generation,
                            candidate_id = EXCLUDED.candidate_id
                    """),
                    records
                )
                inserted = len(records)
            except IntegrityError:
                if if_exists == "fail":
                    raise

            logger.info(f"插入 {inserted} 条 {symbol} {factor_name} 因子值")
            return inserted

    def query_factors(
        self,
        symbol: str,
        factor_name: Union[str, List[str]],
        start_dt: Optional[Union[str, datetime]] = None,
        end_dt: Optional[Union[str, datetime]] = None,
    ) -> pd.DataFrame:
        """
        查询因子值

        Parameters
        ----------
        symbol : str
            品种代码
        factor_name : str or list[str]
            因子名称（单个或多个）
        start_dt : str or datetime, optional
            开始时间
        end_dt : str or datetime, optional
            结束时间

        Returns
        -------
        pd.DataFrame — columns为因子名，index为datetime
        """
        if isinstance(factor_name, str):
            factor_names = [factor_name]
        else:
            factor_names = factor_name

        conditions = ["symbol = :symbol"]
        params = {"symbol": symbol}

        if len(factor_names) == 1:
            conditions.append("factor_name = :factor_name")
            params["factor_name"] = factor_names[0]
        else:
            placeholders = ", ".join([f":fn{i}" for i in range(len(factor_names))])
            conditions.append(f"factor_name IN ({placeholders})")
            for i, fn in enumerate(factor_names):
                params[f"fn{i}"] = fn

        if start_dt:
            conditions.append("ts >= :start_dt")
            ts = pd.Timestamp(start_dt)
            params["start_dt"] = ts.tz_localize(None) if ts.tzinfo is None else ts.tz_convert(None).to_pydatetime()
        if end_dt:
            conditions.append("ts <= :end_dt")
            ts = pd.Timestamp(end_dt)
            params["end_dt"] = ts.tz_localize(None) if ts.tzinfo is None else ts.tz_convert(None).to_pydatetime()

        where_clause = " AND ".join(conditions)

        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            df = pd.read_sql(text(f"""
                SELECT ts, factor_name, value
                FROM factor_values
                WHERE {where_clause}
                ORDER BY ts ASC
            """), conn, params=params)

        if df.empty:
            return pd.DataFrame()

        result = df.pivot(index="ts", columns="factor_name", values="value")
        return result

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self) -> None:
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self._session_factory = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# SQLite 运行时数据读写
# ---------------------------------------------------------------------------

class SQLiteHub:
    """
    SQLite 运行时数据读写中心

    负责：
    - 候选策略状态管理
    - 交易记录读写
    - 品种开关状态
    - 进化世代记录
    - 风控事件记录
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_SQLITE_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._connect()
        self._ensure_tables()

    def _connect(self) -> None:
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        self._session_factory = sessionmaker(bind=self.engine)

    def _ensure_tables(self) -> None:
        """确保所有表已创建"""
        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            # 候选策略表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS candidates (
                    id VARCHAR(64) PRIMARY KEY,
                    symbol VARCHAR(16) NOT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'SEED',
                    regime VARCHAR(16) DEFAULT 'ALL',
                    formula TEXT NOT NULL,
                    params TEXT,
                    parent_id VARCHAR(64),
                    generation INTEGER DEFAULT 0,
                    sharpe_train REAL,
                    sharpe_val REAL,
                    sharpe_test REAL,
                    sharpe_paper_5d REAL,
                    max_drawdown REAL,
                    calmar REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    total_trades INTEGER,
                    avg_holding_bars REAL,
                    is_seed BOOLEAN DEFAULT 0,
                    seed_code VARCHAR(16),
                    deployed_at TIMESTAMP,
                    degraded_at TIMESTAMP,
                    retired_at TIMESTAMP,
                    retire_reason TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_candidates_symbol ON candidates (symbol)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates (status)
            """))

            # 交易记录表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trades (
                    id VARCHAR(64) PRIMARY KEY,
                    symbol VARCHAR(16) NOT NULL,
                    candidate_id VARCHAR(64),
                    side VARCHAR(8) NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    entry_at TIMESTAMP NOT NULL,
                    exit_at TIMESTAMP,
                    status VARCHAR(16) DEFAULT 'PENDING',
                    pnl REAL,
                    pnl_pct REAL,
                    commission REAL,
                    slippage REAL,
                    is_paper BOOLEAN DEFAULT 1,
                    order_id VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trades_candidate ON trades (candidate_id)
            """))

            # 品种开关表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS symbol_switches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(16) UNIQUE NOT NULL,
                    mode VARCHAR(8) DEFAULT 'OFF',
                    current_candidate_id VARCHAR(64),
                    paper_candidate_id VARCHAR(64),
                    group_name VARCHAR(8),
                    margin_per_lot REAL,
                    max_lots INTEGER DEFAULT 1,
                    is_priority BOOLEAN DEFAULT 0,
                    live_enabled_at TIMESTAMP,
                    last_switch_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    switch_reason TEXT,
                    operator VARCHAR(32),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # 进化世代记录表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS evolution_generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(16) NOT NULL,
                    generation INTEGER NOT NULL,
                    stage INTEGER DEFAULT 1,
                    population_size INTEGER DEFAULT 300,
                    elite_count INTEGER DEFAULT 30,
                    mutation_rate REAL DEFAULT 0.2,
                    crossover_rate REAL DEFAULT 0.7,
                    best_fitness REAL,
                    avg_fitness REAL,
                    diversity_score REAL,
                    new_candidates INTEGER DEFAULT 0,
                    pruned_candidates INTEGER DEFAULT 0,
                    runtime_seconds REAL,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP,
                    log_path VARCHAR(256),
                    notes TEXT
                )
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_evol_gen_symbol_gen ON evolution_generations (symbol, generation, stage)
            """))

            # 风控事件表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type VARCHAR(32) NOT NULL,
                    symbol VARCHAR(16),
                    level VARCHAR(16) NOT NULL,
                    message TEXT NOT NULL,
                    metric_value REAL,
                    metric_threshold REAL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    action_taken TEXT,
                    is_resolved BOOLEAN DEFAULT 0,
                    operator VARCHAR(32),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_risk_events_triggered ON risk_events (triggered_at DESC)
            """))
            conn.commit()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    # ------------------------------------------------------------------
    # 候选策略操作
    # ------------------------------------------------------------------

    def insert_candidate(self, candidate: Dict[str, Any]) -> str:
        """插入新的候选策略"""
        with self.session() as session:
            session.execute(text("""
                INSERT INTO candidates (
                    id, symbol, status, regime, formula, params,
                    parent_id, generation, is_seed, seed_code, notes
                ) VALUES (
                    :id, :symbol, :status, :regime, :formula, :params,
                    :parent_id, :generation, :is_seed, :seed_code, :notes
                )
            """), candidate)
            return candidate["id"]

    def update_candidate_metrics(self, candidate_id: str, metrics: Dict[str, Any]) -> None:
        """更新候选策略的绩效指标"""
        metrics["id"] = candidate_id
        with self.session() as session:
            session.execute(text("""
                UPDATE candidates SET
                    sharpe_train = :sharpe_train,
                    sharpe_val = :sharpe_val,
                    sharpe_test = :sharpe_test,
                    max_drawdown = :max_drawdown,
                    calmar = :calmar,
                    win_rate = :win_rate,
                    profit_factor = :profit_factor,
                    total_trades = :total_trades,
                    avg_holding_bars = :avg_holding_bars,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), metrics)

    def update_candidate_status(self, candidate_id: str, status: str, reason: Optional[str] = None) -> None:
        """更新候选策略状态"""
        params = {
            "id": candidate_id,
            "status": status,
            "reason": reason,
        }
        sql_parts = ["status = :status"]

        if status == "DEPLOYED":
            sql_parts.append("deployed_at = CURRENT_TIMESTAMP")
        elif status == "DEGRADED":
            sql_parts.append("degraded_at = CURRENT_TIMESTAMP")
            params["retire_reason"] = reason
            sql_parts.append("retire_reason = :retire_reason")
        elif status == "RETIRED":
            sql_parts.append("retired_at = CURRENT_TIMESTAMP")
            params["retire_reason"] = reason
            sql_parts.append("retire_reason = :retire_reason")

        set_clause = ", ".join(sql_parts)

        with self.session() as session:
            session.execute(text(f"""
                UPDATE candidates SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), params)

    def query_candidates(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        regime: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询候选策略"""
        conditions = ["1=1"]
        params = {}

        if symbol:
            conditions.append("symbol = :symbol")
            params["symbol"] = symbol
        if status:
            conditions.append("status = :status")
            params["status"] = status
        if regime:
            conditions.append("regime = :regime")
            params["regime"] = regime

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT * FROM candidates
            WHERE {where_clause}
            ORDER BY created_at DESC
        """
        if limit:
            params["limit_val"] = limit
            sql += " LIMIT :limit_val"

        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            result = conn.execute(text(sql), params).mappings().fetchall()

        return [dict(row) for row in result]

    # ------------------------------------------------------------------
    # 交易记录操作
    # ------------------------------------------------------------------

    def insert_trade(self, trade: Dict[str, Any]) -> str:
        """插入交易记录"""
        with self.session() as session:
            session.execute(text("""
                INSERT INTO trades (
                    id, symbol, candidate_id, side, quantity,
                    entry_price, exit_price, entry_at, exit_at,
                    status, pnl, pnl_pct, commission, slippage,
                    is_paper, order_id, notes
                ) VALUES (
                    :id, :symbol, :candidate_id, :side, :quantity,
                    :entry_price, :exit_price, :entry_at, :exit_at,
                    :status, :pnl, :pnl_pct, :commission, :slippage,
                    :is_paper, :order_id, :notes
                )
            """), trade)
            return trade["id"]

    def update_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_at: datetime,
        pnl: float,
        pnl_pct: float,
        status: str = "FILLED",
    ) -> None:
        """更新交易的平仓信息"""
        with self.session() as session:
            session.execute(text("""
                UPDATE trades SET
                    exit_price = :exit_price,
                    exit_at = :exit_at,
                    pnl = :pnl,
                    pnl_pct = :pnl_pct,
                    status = :status
                WHERE id = :id
            """), {
                "id": trade_id,
                "exit_price": exit_price,
                "exit_at": exit_at,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "status": status,
            })

    # ------------------------------------------------------------------
    # 品种开关操作
    # ------------------------------------------------------------------

    def set_symbol_mode(self, symbol: str, mode: str, reason: Optional[str] = None, operator: Optional[str] = None) -> None:
        """设置品种运行模式：OFF / PAPER / LIVE"""
        with self.session() as session:
            session.execute(text("""
                INSERT INTO symbol_switches (symbol, mode, switch_reason, operator, last_switch_at)
                VALUES (:symbol, :mode, :reason, :operator, CURRENT_TIMESTAMP)
                ON CONFLICT (symbol) DO UPDATE SET
                    mode = :mode,
                    switch_reason = :reason,
                    operator = :operator,
                    last_switch_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "symbol": symbol,
                "mode": mode,
                "reason": reason,
                "operator": operator,
            })

    def get_symbol_mode(self, symbol: str) -> Optional[str]:
        """获取品种当前运行模式"""
        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            result = conn.execute(text("""
                SELECT mode FROM symbol_switches WHERE symbol = :symbol
            """), {"symbol": symbol}).fetchone()
        return result[0] if result else None

    def get_all_symbol_modes(self) -> Dict[str, str]:
        """获取所有品种的运行模式"""
        with self.engine.connect() as conn:
            # 检查并创建TimescaleDB扩展
            conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """))
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                ) as has_timescaledb
            """)).fetchone()
            if not result or not result[0]:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                conn.commit()

            result = conn.execute(text("""
                SELECT symbol, mode FROM symbol_switches
            """)).fetchall()
        return {row[0]: row[1] for row in result}

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self._session_factory = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# 数据管道：天勤 → 数据库
# ---------------------------------------------------------------------------

class DataPipeline:
    """
    数据管道：天勤行情 → TimescaleDB

    负责：
    - 从TqDataSource下载历史数据
    - 写入TimescaleDB
    - 增量更新检查
    """

    def __init__(
        self,
        timescale_hub: Optional[TimescaleHub] = None,
        tq_data_source=None,
    ):
        self.timescale = timescale_hub or TimescaleHub()
        self._tq_data_source = tq_data_source

    @property
    def tq(self):
        """惰性初始化天勤数据源"""
        if self._tq_data_source is None:
            from .source import TqDataSource
            self._tq_data_source = TqDataSource()
        return self._tq_data_source

    def download_and_save(
        self,
        symbol: str,
        start_dt: Union[str, datetime],
        end_dt: Union[str, datetime],
        duration_seconds: int = 3600,
        use_cache: bool = True,
    ) -> int:
        """
        从TqSdk下载K线数据并保存到TimescaleDB

        Parameters
        ----------
        symbol : str
            品种代码
        start_dt : str or datetime
            开始时间
        end_dt : str or datetime
            结束时间
        duration_seconds : int
            K线周期（秒）
        use_cache : bool
            是否使用本地文件缓存

        Returns
        -------
        int — 插入的行数
        """
        ohlcv = self.tq.download_klines(
            symbol=symbol,
            start_dt=start_dt,
            end_dt=end_dt,
            duration_seconds=duration_seconds,
            use_cache=use_cache,
        )

        df = ohlcv.to_dataframe()
        inserted = self.timescale.insert_ohlcv(
            symbol=symbol,
            df=df,
            duration_seconds=duration_seconds,
            if_exists="append",
        )

        logger.info(f"{symbol}: 下载并保存 {inserted} 条K线数据")
        return inserted

    def incremental_update(
        self,
        symbol: str,
        duration_seconds: int = 3600,
        days_back: int = 7,
    ) -> int:
        """
        增量更新K线数据：从数据库中最新时间点下载到当前

        Parameters
        ----------
        symbol : str
            品种代码
        duration_seconds : int
            K线周期
        days_back : int
            如果数据库为空，默认回溯的天数

        Returns
        -------
        int — 插入的行数
        """
        min_ts, max_ts = self.timescale.get_available_range(symbol, duration_seconds)

        if max_ts is None:
            start_dt = pd.Timestamp.now() - pd.Timedelta(days=days_back)
        else:
            start_dt = max_ts

        end_dt = pd.Timestamp.now()

        if start_dt >= end_dt:
            logger.info(f"{symbol}: 数据已是最新，无需更新")
            return 0

        return self.download_and_save(
            symbol=symbol,
            start_dt=start_dt,
            end_dt=end_dt,
            duration_seconds=duration_seconds,
        )

    def batch_update(
        self,
        symbols: List[str],
        duration_seconds: int = 3600,
        days_back: int = 7,
    ) -> Dict[str, int]:
        """批量更新多个品种的数据"""
        results = {}
        for symbol in symbols:
            try:
                inserted = self.incremental_update(symbol, duration_seconds, days_back)
                results[symbol] = inserted
            except Exception as exc:
                logger.error(f"{symbol}: 更新失败 - {exc}")
                results[symbol] = -1
        return results

    def close(self) -> None:
        self.timescale.close()
        if self._tq_data_source:
            self._tq_data_source.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
