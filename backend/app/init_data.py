"""
数据初始化脚本 — 下载历史K线数据并初始化数据库

功能：
- 下载指定品种的历史K线数据
- 支持增量更新（从上次下载结束时间开始
- 数据写入 TimescaleDB
- 支持全量初始化/增量更新两种模式

使用方法：
    # 全量初始化（所有品种，最近2年）
    python -m app.init_data --full

    # 增量更新（所有品种，从上次结束时间开始
    python -m app.init_data --incremental

    # 指定品种和时间范围
    python -m app.init_data --symbols RB,MA,M --start 2024-01-01 --end 2025-01-01

    # 查看数据检查
    python -m app.init_data --check
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("data_init")

# 确保项目根目录在路径中
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from quant_engine.data.hub import TimescaleHub
from quant_engine.data.source import TqDataSource, TermStructureData
from quant_engine.data.data_backup import DataBackup


# ============================================================================
# 默认配置
# ============================================================================

# 首批实盘交易品种（保证金均低于1.5万，适合10-20万资金起步测试
DEFAULT_SYMBOLS = [
    "RB",  # 螺纹钢
    "MA",  # 甲醇
    "M",   # 豆粕
    "TA",  # PTA
    "FG",  # 玻璃
    "SR",  # 白糖
    "SA",  # 纯碱
    "PP",  # 聚丙烯
]

# 扩展品种（资金充足后使用）
EXTENDED_SYMBOLS = [
    "AU",  # 黄金
    "CU",  # 铜
    "SC",  # 原油
    "IF",  # 沪深300股指
]

# 支持的K线周期（秒）
SUPPORTED_DURATIONS = [
    3600,  # 1小时
    86400,  # 日线
]


# ============================================================================
# 交易时间工具函数
# ============================================================================

def is_market_open(now: datetime = None) -> bool:
    """判断当前是否在期货交易时间内"""
    now = now or datetime.now()
    hour = now.hour
    minute = now.minute
    
    # 周末不交易（周六=5，周日=6）
    if now.weekday() >= 5:
        return False
    
    # 日盘时间
    # 09:00 - 10:15
    if 9 <= hour < 10 or (hour == 10 and minute <= 15):
        return True
    # 10:30 - 11:30
    if (hour == 10 and minute >= 30) or (11 <= hour < 12):
        return True
    # 13:30 - 15:00
    if 13 <= hour < 15 or (hour == 15 and minute == 0):
        return True
    # 夜盘时间 21:00 - 23:00
    if 21 <= hour < 23:
        return True
    
    return False

def get_last_trading_time(now: datetime = None) -> datetime:
    """获取上一根K线应该结束的时间（考虑交易时间）"""
    now = now or datetime.now()
    hour = now.hour
    
    # 如果是周末，返回上周五的交易结束时间
    if now.weekday() >= 5:
        # 找到上一个周五
        days_since_friday = now.weekday() - 4  # Saturday=5, Sunday=6
        last_friday = now - pd.Timedelta(days=days_since_friday)
        # 返回上周五夜盘结束时间 23:00
        return last_friday.replace(hour=23, minute=0, second=0, microsecond=0)
    
    # 如果现在在交易时间内，返回当前周期的结束时间
    if is_market_open(now):
        # 1小时K线，返回当前小时的结束时间
        return now.replace(minute=0, second=0, microsecond=0)
    
    # 如果不在交易时间内，返回上一个交易时段的结束时间
    # 夜盘结束时间 23:00
    if hour < 9:
        # 上午9点前，返回前一天夜盘结束时间23:00
        return (now - pd.Timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
    # 10:15-10:30 休盘
    elif 10 <= hour < 11:
        if (hour == 10 and minute < 15):
            return now.replace(hour=10, minute=0, second=0, microsecond=0)
        else:
            return (now - pd.Timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    # 11:30-13:30 午休
    elif 11 <= hour < 14:
        return now.replace(hour=11, minute=0, second=0, microsecond=0)
    # 15:00-21:00 休盘
    elif 15 <= hour < 21:
        return now.replace(hour=15, minute=0, second=0, microsecond=0)
    # 23:00之后
    else:  # hour >= 23
        return now.replace(hour=23, minute=0, second=0, microsecond=0)

# ============================================================================
# 数据初始化类
# ============================================================================

class DataInitializer:
    """数据初始化器"""

    def __init__(
        self,
        tq_account: Optional[str] = None, tq_password: Optional[str] = None):
        settings = get_settings()
        self.tq_account = tq_account or settings.tqsdk_account
        self.tq_password = tq_password or settings.tqsdk_password
        self.timescale = TimescaleHub()
        self.backup = DataBackup()
        self._tq_ds: Optional[TqDataSource] = None
        self._term_ds: Optional[TermStructureData] = None

    def _get_tq(self) -> TqDataSource:
        """获取或创建TqDataSource实例"""
        if self._tq_ds is None:
            if not self.tq_account or self.tq_account == "your_tqsdk_account":
                logger.warning("未配置天勤账号，使用模拟模式，数据可能受限")

            self._tq_ds = TqDataSource(
                account=self.tq_account,
                password=self.tq_password,
                sim=True,
            )
        return self._tq_ds

    def _get_term_ds(self) -> TermStructureData:
        """获取或创建TermStructureData实例"""
        if self._term_ds is None:
            self._term_ds = TermStructureData(self._get_tq())
        return self._term_ds

    def _get_available_range(
        self, symbol: str, duration: int
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取数据库中已有的数据时间范围"""
        try:
            min_ts, max_ts = self.timescale.get_available_range(symbol, duration)
            return min_ts, max_ts
        except Exception as e:
            logger.debug(f"[{symbol}] 获取数据范围失败: {e}")
            return None, None

    def download_symbol(
        self,
        symbol: str,
        start_dt: datetime,
        end_dt: datetime,
        duration: int = 3600,
        force: bool = False,
    ) -> Dict[str, any]:
        """
        下载单个品种数据

        Parameters
        ----------
        symbol : str
            品种代码
        start_dt : datetime
            开始时间
        end_dt : datetime
            结束时间
        duration : int
            K线周期（秒）
        force : bool
            是否强制覆盖已有数据
        """
        logger.info(f"[{symbol}] 开始下载 {duration//3600}小时 K线...")
        logger.info(f"[{symbol}] 时间范围: {start_dt.date()} 到 {end_dt.date()}")

        tq = self._get_tq()

        try:
            ohlcv = tq.download_klines(
                symbol=symbol,
                start_dt=start_dt,
                end_dt=end_dt,
                duration_seconds=duration,
                use_cache=True,
                main_contract=True,
            )

            df = ohlcv.to_dataframe()

            if df.empty:
                logger.warning(f"[{symbol}] 下载数据为空")
                return {"symbol": symbol, "duration": duration, "rows": 0, "success": False, "reason": "empty_data"}

            # 插入数据库
            inserted = self.timescale.insert_ohlcv(
                symbol=symbol,
                df=df,
                duration_seconds=duration,
                if_exists="replace" if force else "append",
            )

            logger.info(f"[{symbol}] 成功插入 {inserted} 条记录")
            
            # 自动备份到CSV
            freq_map = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 86400: "1d"}
            freq = freq_map.get(duration, "1h")
            
            # 确保DataFrame有需要的列
            df_backup = df.copy()
            df_backup.reset_index(inplace=True)  # 确保索引转成列
            if 'ts' not in df_backup.columns and 'datetime' in df_backup.columns:
                df_backup['ts'] = df_backup['datetime']
            elif 'ts' not in df_backup.columns:
                df_backup['ts'] = df_backup.index
            
            self.backup.backup_ohlcv(symbol, freq, df_backup)
            return {
                "symbol": symbol,
                "duration": duration,
                "rows": inserted,
                "success": True,
                "start": str(df.index[0]) if not df.empty else None,
                "end": str(df.index[-1]) if not df.empty else None,
            }

        except Exception as e:
            logger.exception(f"[{symbol}] 下载失败: {e}")
            return {"symbol": symbol, "duration": duration, "rows": 0, "success": False, "reason": str(e)}

    def download_term_structure(
        self,
        symbol: str,
        start_dt: datetime,
        end_dt: datetime,
        duration: int = 3600,
        force: bool = False,
        skip_contract_download: bool = False,
    ) -> Dict[str, any]:
        """
        下载单个品种的期限结构数据

        Parameters
        ----------
        symbol : str
            品种代码
        start_dt : datetime
            开始时间
        end_dt : datetime
            结束时间
        duration : int
            K线周期（秒）
        force : bool
            是否强制覆盖已有数据
        skip_contract_download : bool
            是否跳过合约数据下载（复用前一次频率的数据）
        """
        logger.info(f"[{symbol}] 开始下载期限结构数据 {duration//3600}小时...")
        logger.info(f"[{symbol}] 时间范围: {start_dt.date()} 到 {end_dt.date()}")

        term_ds = self._get_term_ds()

        try:
            # 下载期限结构数据
            df, contract_mapping = term_ds.download_term_structure_data(
                symbol=symbol,
                start_dt=start_dt,
                end_dt=end_dt,
                duration_seconds=duration,
                skip_contract_download=skip_contract_download,
            )

            if df.empty:
                logger.warning(f"[{symbol}] 期限结构数据为空")
                return {"symbol": symbol, "duration": duration, "rows": 0, "success": False, "reason": "empty_data"}

            # 插入数据库
            inserted = self.timescale.insert_term_structure(
                symbol=symbol,
                df=df,
                duration_seconds=duration,
                if_exists="replace" if force else "append",
            )

            logger.info(f"[{symbol}] 期限结构数据成功插入 {inserted} 条记录")
            
            # 自动备份到CSV
            freq_map = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 86400: "1d"}
            freq = freq_map.get(duration, "1h")
            
            # 确保DataFrame有需要的列
            df_backup = df.copy()
            df_backup.reset_index(inplace=True)
            if 'ts' not in df_backup.columns and 'datetime' in df_backup.columns:
                df_backup['ts'] = df_backup['datetime']
            elif 'ts' not in df_backup.columns:
                df_backup['ts'] = df_backup.index
            
            self.backup.backup_term_structure(symbol, freq, df_backup)
            return {
                "symbol": symbol,
                "duration": duration,
                "rows": inserted,
                "success": True,
                "start": str(df.index[0]) if not df.empty else None,
                "end": str(df.index[-1]) if not df.empty else None,
                "contracts_used": len(contract_mapping),
            }

        except Exception as e:
            logger.exception(f"[{symbol}] 期限结构数据下载失败: {e}")
            return {"symbol": symbol, "duration": duration, "rows": 0, "success": False, "reason": str(e)}

    def download_all_symbols(
        self,
        symbols: List[str],
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
        durations: Optional[List[int]] = None,
        incremental: bool = False,
        force: bool = False,
    ) -> Dict[str, any]:
        """
        下载所有品种数据

        Parameters
        ----------
        symbols : List[str]
            品种列表
        start_dt : datetime, optional
            开始时间，默认2年前
        end_dt : datetime, optional
            结束时间，默认昨天
        durations : List[int], optional
            K线周期列表
        incremental : bool
            是否增量更新
        force : bool
            是否强制覆盖
        """
        durations = durations or SUPPORTED_DURATIONS

        end_dt = end_dt or datetime.now()
        start_dt = start_dt or (end_dt - pd.Timedelta(days=730))

        logger.info("="*60)
        logger.info("开始批量下载历史数据")
        logger.info(f"品种数量: {len(symbols)}")
        logger.info(f"时间范围: {start_dt.date()} 到 {end_dt.date()}")
        logger.info(f"K线周期: {' ,'.join([str(d//3600) + '小时' for d in durations])}")
        logger.info(f"增量模式: {incremental}")
        logger.info("="*60)

        results = []
        total_rows = 0

        freq_map = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 86400: "1d"}
        
        for symbol in symbols:
            for duration in durations:
                freq = freq_map.get(duration, "1h")
                symbol_start = start_dt
                action = "download"
                reason = ""

                if incremental and not force:
                    # 获取数据库和CSV的最新时间
                    db_min_ts, db_max_ts = self._get_available_range(symbol, duration)
                    csv_max_ts = self.backup.get_latest_timestamp(symbol, freq)
                    
                    # 处理时区问题
                    if db_max_ts and db_max_ts.tzinfo is not None:
                        db_max_ts = db_max_ts.replace(tzinfo=None)
                    if csv_max_ts and csv_max_ts.tzinfo is not None:
                        csv_max_ts = csv_max_ts.replace(tzinfo=None)
                    
                    # 获取当前应该有的最新K线时间
                    last_trading_time = get_last_trading_time(end_dt)
                    logger.info(f"[{symbol}] {freq} 检查数据状态...")
                    logger.info(f"[{symbol}] {freq} 数据库最新: {db_max_ts}")
                    logger.info(f"[{symbol}] {freq} CSV备份最新: {csv_max_ts}")
                    logger.info(f"[{symbol}] {freq} 当前时间: {end_dt} ({'交易中' if is_market_open(end_dt) else '非交易时间'})")
                    logger.info(f"[{symbol}] {freq} 应有的最新时间: {last_trading_time}")

                    # 情况1: 数据库为空
                    if not db_max_ts:
                        if csv_max_ts:
                            logger.info(f"[{symbol}] {freq} 数据库为空，从CSV恢复")
                            df = self.backup.restore_ohlcv(symbol, freq)
                            if df is not None and not df.empty:
                                if 'ts' in df.columns:
                                    df = df.set_index('ts')
                                elif 'datetime' in df.columns:
                                    df = df.set_index('datetime')
                                inserted = self.timescale.insert_ohlcv(
                                    symbol=symbol, df=df, duration_seconds=duration, if_exists="replace"
                                )
                                logger.info(f"[{symbol}] {freq} 从CSV恢复 {inserted} 条")
                                results.append({"symbol": symbol, "duration": duration, "rows": inserted, "success": True, "skipped": False, "action": "restore_from_csv"})
                                total_rows += inserted
                                continue
                            else:
                                logger.info(f"[{symbol}] {freq} CSV也为空，开始下载")
                        else:
                            logger.info(f"[{symbol}] {freq} 数据库和CSV都为空，开始下载")
                    
                    # 情况2: 数据库有数据，检查是否需要更新
                    else:
                        # 检查数据库和CSV是否同步
                        if csv_max_ts:
                            if db_max_ts < csv_max_ts:
                                # CSV有更多数据，从CSV补全数据库
                                logger.info(f"[{symbol}] {freq} 数据库落后于CSV，从CSV补全")
                                df = self.backup.restore_ohlcv(symbol, freq)
                                if df is not None and not df.empty:
                                    # 只取数据库没有的部分
                                    if 'ts' in df.columns:
                                        df = df[df['ts'] > db_max_ts]
                                        df = df.set_index('ts')
                                    elif 'datetime' in df.columns:
                                        df = df[df['datetime'] > db_max_ts]
                                        df = df.set_index('datetime')
                                    if not df.empty:
                                        inserted = self.timescale.insert_ohlcv(
                                            symbol=symbol, df=df, duration_seconds=duration, if_exists="append"
                                        )
                                        logger.info(f"[{symbol}] {freq} 从CSV补全 {inserted} 条")
                                        results.append({"symbol": symbol, "duration": duration, "rows": inserted, "success": True, "skipped": False, "action": "sync_from_csv"})
                                        total_rows += inserted
                                        # 更新db_max_ts
                                        db_max_ts = self._get_available_range(symbol, duration)[1]
                                        if db_max_ts and db_max_ts.tzinfo is not None:
                                            db_max_ts = db_max_ts.replace(tzinfo=None)
                                    else:
                                        logger.info(f"[{symbol}] {freq} CSV没有新数据")
                            elif db_max_ts > csv_max_ts:
                                # 数据库有更多数据，备份到CSV
                                logger.info(f"[{symbol}] {freq} 数据库领先于CSV，备份到CSV")
                                min_ts, max_ts = self._get_available_range(symbol, duration)
                                if max_ts:
                                    # 确保时区一致性
                                    if max_ts.tzinfo is not None:
                                        max_ts = max_ts.replace(tzinfo=None)
                                    if csv_max_ts and csv_max_ts.tzinfo is not None:
                                        csv_max_ts = csv_max_ts.replace(tzinfo=None)
                                    if min_ts and min_ts.tzinfo is not None:
                                        min_ts = min_ts.replace(tzinfo=None)
                                    
                                    backup_start = csv_max_ts + pd.Timedelta(seconds=duration) if csv_max_ts else min_ts
                                    
                                    logger.info(f"[{symbol}] {freq} 正在从数据库读取 {symbol} 的 {freq} 数据...")
                                    try:
                                        df_backup = self.timescale.query_ohlcv(
                                            symbol=symbol,
                                            start_dt=backup_start,
                                            end_dt=max_ts,
                                            duration_seconds=duration,
                                        )
                                        if not df_backup.empty:
                                            df_backup = df_backup.reset_index()
                                            if 'ts' not in df_backup.columns and 'datetime' in df_backup.columns:
                                                df_backup['ts'] = df_backup['datetime']
                                            self.backup.backup_ohlcv(symbol, freq, df_backup)
                                            logger.info(f"[{symbol}] {freq} 已备份到CSV ({len(df_backup)}条)")
                                    except Exception as e:
                                        logger.warning(f"[{symbol}] {freq} 备份失败: {e}, 跳过备份")
                        else:
                            # CSV为空，需要备份数据库数据
                            logger.info(f"[{symbol}] {freq} CSV为空，备份数据库数据")
                            min_ts, max_ts = self._get_available_range(symbol, duration)
                            if max_ts:
                                # 直接从数据库读取数据（不从天勤下载）
                                logger.info(f"[{symbol}] {freq} 正在从数据库读取 {symbol} 的 {freq} 数据...")
                                try:
                                    df_backup = self.timescale.query_ohlcv(
                                        symbol=symbol,
                                        start_dt=min_ts,
                                        end_dt=max_ts,
                                        duration_seconds=duration,
                                    )
                                    if not df_backup.empty:
                                        df_backup = df_backup.reset_index()
                                        if 'ts' not in df_backup.columns and 'datetime' in df_backup.columns:
                                            df_backup['ts'] = df_backup['datetime']
                                        self.backup.backup_ohlcv(symbol, freq, df_backup)
                                        logger.info(f"[{symbol}] {freq} 已备份到CSV ({len(df_backup)}条)")
                                    else:
                                        logger.warning(f"[{symbol}] {freq} 数据库数据为空，无法备份")
                                except Exception as e:
                                    logger.warning(f"[{symbol}] {freq} 备份失败: {e}, 跳过备份")

                        # 现在检查是否需要从交易所下载新数据
                        # 1. 检查数据最早时间是否足够（增量模式下，检查是否需要补充早期数据）
                        if incremental and db_min_ts:
                            if db_min_ts.tzinfo is not None:
                                db_min_ts_check = db_min_ts.replace(tzinfo=None)
                            else:
                                db_min_ts_check = db_min_ts
                            
                            # 期望的开始时间应该早于数据库最早时间，说明缺少早期数据
                            if start_dt < db_min_ts_check:
                                logger.info(f"[{symbol}] {freq} 数据库缺少早期数据（期望从 {start_dt.date()} 开始，但数据库最早是 {db_min_ts_check.date()}）")
                                logger.info(f"[{symbol}] {freq} 需要补充早期数据，从 {start_dt} 到 {db_min_ts_check - pd.Timedelta(seconds=duration)}")
                                result = self.download_symbol(
                                    symbol=symbol,
                                    start_dt=start_dt,
                                    end_dt=db_min_ts_check - pd.Timedelta(seconds=duration),
                                    duration=duration,
                                    force=force,
                                )
                                results.append(result)
                                if result["success"]:
                                    total_rows += result["rows"]
                                    # 重新获取最新的db_min_ts和db_max_ts
                                    db_min_ts, db_max_ts = self._get_available_range(symbol, duration)
                                    if db_max_ts and db_max_ts.tzinfo is not None:
                                        db_max_ts = db_max_ts.replace(tzinfo=None)
                        
                        # 2. 检查数据最新时间是否需要更新
                        symbol_start = db_max_ts + pd.Timedelta(seconds=duration) if db_max_ts else start_dt
                        
                        # 判断是否已是最新
                        if symbol_start >= last_trading_time:
                            logger.info(f"[{symbol}] {freq} 数据已是最新，跳过")
                            results.append({"symbol": symbol, "duration": duration, "rows": 0, "success": True, "skipped": True, "action": "up_to_date"})
                            continue
                        else:
                            logger.info(f"[{symbol}] {freq} 需要下载新数据，从 {symbol_start} 到 {last_trading_time}")

                # 移除end_dt的时区信息（如果有）
                end_dt_compare = end_dt
                if hasattr(end_dt_compare, 'tzinfo') and end_dt_compare.tzinfo is not None:
                    end_dt_compare = end_dt_compare.replace(tzinfo=None)

                if symbol_start >= end_dt_compare and not incremental:
                    logger.info(f"[{symbol}] {freq} 数据已是最新，跳过")
                    results.append({"symbol": symbol, "duration": duration, "rows": 0, "success": True, "skipped": True})
                    continue

                result = self.download_symbol(
                    symbol=symbol,
                    start_dt=symbol_start,
                    end_dt=end_dt,
                    duration=duration,
                    force=force,
                )
                results.append(result)
                if result["success"]:
                    total_rows += result["rows"]

        logger.info("="*60)
        logger.info(f"下载完成！总记录数: {total_rows}")
        logger.info("="*60)

        return {
            "total_rows": total_rows,
            "results": results,
        }

    def download_term_structure_all(
        self,
        symbols: List[str],
        start_dt: Optional[datetime] = None,
        end_dt: Optional[datetime] = None,
        durations: Optional[List[int]] = None,
        incremental: bool = False,
        force: bool = False,
    ) -> Dict[str, any]:
        """
        下载所有品种的期限结构数据

        Parameters
        ----------
        symbols : List[str]
            品种列表
        start_dt : datetime, optional
            开始时间，默认2年前
        end_dt : datetime, optional
            结束时间，默认昨天
        durations : List[int], optional
            K线周期列表
        incremental : bool
            是否增量更新
        force : bool
            是否强制覆盖
        """
        durations = durations or SUPPORTED_DURATIONS

        end_dt = end_dt or datetime.now()
        start_dt = start_dt or (end_dt - pd.Timedelta(days=730))

        logger.info("="*60)
        logger.info("开始批量下载期限结构数据")
        logger.info(f"品种数量: {len(symbols)}")
        logger.info(f"时间范围: {start_dt.date()} 到 {end_dt.date()}")
        logger.info(f"K线周期: {' ,'.join([str(d//3600) + '小时' for d in durations])}")
        logger.info(f"增量模式: {incremental}")
        logger.info("="*60)

        results = []
        total_rows = 0

        for symbol in symbols:
            first_duration = True
            for duration in durations:
                freq_map = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 86400: "1d"}
                freq = freq_map.get(duration, "1h")
                symbol_start = start_dt

                if incremental and not force:
                    # 检查是否已有期限结构数据
                    try:
                        df_existing = self.timescale.query_term_structure(
                            symbol=symbol,
                            start_dt=start_dt,
                            end_dt=end_dt,
                            duration_seconds=duration,
                        )
                        if not df_existing.empty:
                            max_ts = df_existing.index.max()
                            if max_ts >= end_dt - pd.Timedelta(days=1):
                                logger.info(f"[{symbol}] {freq} 期限结构数据已是最新，跳过")
                                results.append({
                                    "symbol": symbol,
                                    "duration": duration,
                                    "rows": 0,
                                    "success": True,
                                    "skipped": True,
                                    "action": "up_to_date",
                                })
                                continue
                            else:
                                symbol_start = max_ts + pd.Timedelta(seconds=duration)
                    except Exception as e:
                        logger.debug(f"[{symbol}] {freq} 检查期限结构数据失败: {e}")

                # 第一个频率下载合约数据，后续频率复用
                result = self.download_term_structure(
                    symbol=symbol,
                    start_dt=symbol_start,
                    end_dt=end_dt,
                    duration=duration,
                    force=force,
                    skip_contract_download=not first_duration,
                )
                first_duration = False
                results.append(result)
                if result["success"]:
                    total_rows += result["rows"]

        logger.info("="*60)
        logger.info(f"期限结构数据下载完成！总记录数: {total_rows}")
        logger.info("="*60)

        return {
            "total_rows": total_rows,
            "results": results,
        }

    def check_backup_status(self, symbols: List[str]) -> Dict[str, any]:
        """
        检查备份状态（数据库 vs CSV）

        Parameters
        ----------
        symbols : List[str]
            品种列表
        """
        logger.info("="*60)
        logger.info("检查备份状态")
        logger.info("="*60)
        
        freq_map = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 86400: "1d"}
        
        # 获取数据库记录数
        db_counts = {}
        for symbol in symbols:
            for duration in SUPPORTED_DURATIONS:
                freq = freq_map.get(duration, "1h")
                try:
                    count = self.timescale.get_record_count(symbol, duration)
                    db_counts[(symbol, freq)] = count
                except Exception:
                    db_counts[(symbol, freq)] = 0
        
        # 检查备份状态
        status = self.backup.check_backup_status(db_counts)
        
        # 输出信息
        metadata = status["metadata"]
        logger.info(f"备份最后更新: {metadata.get('last_backup_time', '从未')}")
        logger.info(f"总备份记录: {metadata.get('total_records', 0)}")
        
        if status["all_ok"]:
            logger.info("✅ 数据库与备份同步，状态正常")
        else:
            logger.warning("⚠️ 发现问题:")
            for issue in status["issues"]:
                if issue["issue"] == "database_empty":
                    logger.warning(f"   - {issue['symbol']} {issue['freq']}: 数据库为空，备份有 {issue['csv_count']} 条")
                elif issue["issue"] == "database_outdated":
                    logger.warning(f"   - {issue['symbol']} {issue['freq']}: 数据库 {issue['db_count']} 条 < 备份 {issue['csv_count']} 条")
        
        return status

    def restore_from_backup(self, symbols: List[str]) -> Dict[str, any]:
        """
        从CSV备份恢复数据

        Parameters
        ----------
        symbols : List[str]
            品种列表
        """
        logger.info("="*60)
        logger.info("从CSV备份恢复数据")
        logger.info("="*60)
        
        freq_map = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 86400: "1d"}
        # 反向映射
        duration_map = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "1d": 86400}
        
        results = []
        total_restored = 0
        
        for symbol in symbols:
            for freq in ["1h", "1d"]:
                df = self.backup.restore_ohlcv(symbol, freq)
                if df is not None and not df.empty:
                    duration = duration_map.get(freq, 3600)
                    
                    # 确保ts列是datetime类型并设为索引
                    if 'ts' in df.columns:
                        df = df.set_index('ts')
                    elif 'datetime' in df.columns:
                        df = df.set_index('datetime')
                    
                    # 插入数据库
                    inserted = self.timescale.insert_ohlcv(
                        symbol=symbol,
                        df=df,
                        duration_seconds=duration,
                        if_exists="replace",
                    )
                    
                    total_restored += inserted
                    logger.info(f"[{symbol}] {freq}: 恢复 {inserted} 条")
                    results.append({
                        "symbol": symbol,
                        "freq": freq,
                        "rows": inserted,
                        "success": True
                    })
                else:
                    logger.info(f"[{symbol}] {freq}: 无备份")
                    results.append({
                        "symbol": symbol,
                        "freq": freq,
                        "rows": 0,
                        "success": False,
                        "reason": "no_backup"
                    })
        
        logger.info(f"恢复完成！总记录数: {total_restored}")
        logger.info("="*60)
        
        return {
            "total_rows": total_restored,
            "results": results
        }

    def check_data_status(self, symbols: List[str]) -> Dict[str, any]:
        """
        检查数据状态

        Parameters
        ----------
        symbols : List[str]
            品种列表
        """
        logger.info("="*60)
        logger.info("检查数据状态")
        logger.info("="*60)

        status = []

        for symbol in symbols:
            for duration in SUPPORTED_DURATIONS:
                min_ts, max_ts = self._get_available_range(symbol, duration)
                if min_ts and max_ts:
                    days_range = (max_ts - min_ts).days
                    status.append({
                        "symbol": symbol,
                        "duration": duration,
                        "has_data": True,
                        "min_ts": min_ts.isoformat(),
                        "max_ts": max_ts.isoformat(),
                        "days": days_range,
                    })
                    logger.info(f"[{symbol}] {duration//3600}小时: {min_ts.date()} 到 {max_ts.date()} ({days_range} 天)")
                else:
                    status.append({
                        "symbol": symbol,
                        "duration": duration,
                        "has_data": False,
                    })
                    logger.info(f"[{symbol}] {duration//3600}小时: 无数据")

        return {"status": status}

    def close(self):
        """关闭资源"""
        if self._tq_ds:
            self._tq_ds.close()
        self.timescale.close()


# ============================================================================
# 主程序
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="期货数据初始化工具")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full", action="store_true", help="全量初始化（下载所有品种最近2年数据）")
    group.add_argument("--incremental", action="store_true", help="增量更新（从上次结束时间开始）")
    group.add_argument("--check", action="store_true", help="检查数据状态")
    group.add_argument("--check-backup", action="store_true", help="检查备份状态（数据库 vs CSV）")
    group.add_argument("--restore", action="store_true", help="从CSV备份恢复数据")
    group.add_argument("--term-structure", action="store_true", help="下载期限结构数据（近月/远月合约）")
    group.add_argument("--term-structure-incremental", action="store_true", help="增量更新期限结构数据")

    parser.add_argument("--symbols", type=str, help="指定品种，用逗号分隔（如 RB,MA,M）")
    parser.add_argument("--start", type=str, help="开始日期，如 2024-01-01")
    parser.add_argument("--end", type=str, help="结束日期，如 2025-01-01")
    parser.add_argument("--extended", action="store_true", help="包含扩展品种(AU,CU,SC,IF)")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有数据")

    args = parser.parse_args()

    # 确定品种列表
    symbols = DEFAULT_SYMBOLS.copy()
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    elif args.extended:
        symbols += EXTENDED_SYMBOLS

    # 确定时间范围
    start_dt = pd.to_datetime(args.start) if args.start else None
    end_dt = pd.to_datetime(args.end) if args.end else None

    # 初始化
    initializer = DataInitializer()

    try:
        if args.check:
            initializer.check_data_status(symbols)
        elif args.check_backup:
            initializer.check_backup_status(symbols)
        elif args.restore:
            initializer.restore_from_backup(symbols)
        elif args.full:
            initializer.download_all_symbols(
                symbols=symbols,
                start_dt=start_dt,
                end_dt=end_dt,
                incremental=False,
                force=args.force,
            )
        elif args.incremental:
            initializer.download_all_symbols(
                symbols=symbols,
                start_dt=start_dt,
                end_dt=end_dt,
                incremental=True,
                force=args.force,
            )
        elif args.term_structure:
            initializer.download_term_structure_all(
                symbols=symbols,
                start_dt=start_dt,
                end_dt=end_dt,
                incremental=False,
                force=args.force,
            )
        elif args.term_structure_incremental:
            initializer.download_term_structure_all(
                symbols=symbols,
                start_dt=start_dt,
                end_dt=end_dt,
                incremental=True,
                force=args.force,
            )

    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"数据初始化失败: {e}")
        sys.exit(1)
    finally:
        initializer.close()


if __name__ == "__main__":
    main()
