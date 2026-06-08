"""
天勤行情接入 — 历史数据下载、实时订阅、主力合约映射、K线缓存

支持：
- 1小时K线数据获取
- 主力合约自动映射（KQ.m@{交易所}.{品种}）
- 本地K线数据缓存（parquet格式）
- 实时行情订阅（模拟盘/实盘）
- 与 system.yaml 品种配置对齐
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except Exception:  # pragma: no cover - 极端环境缺少 tzdata 时回退
    _BEIJING_TZ = None
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _is_market_open(now: Optional[datetime] = None) -> bool:
    """
    判断当前是否在期货交易时段内（简单版本，覆盖大部分品种的日盘+夜盘）
    
    日盘：09:00-10:15, 10:30-11:30, 13:30-15:00
    夜盘：21:00-23:00（部分品种更长，但用23:00作为保守判断）
    """
    # 中国期货交易时段以北京时间（UTC+8）为准。务必把时间换算到北京时区，
    # 否则在 UTC 等非北京时区的服务器（如云端）上判断会整体错位，
    # 导致真实开盘时段被误判为休市、静默跳过真实合约下载并回退到退化数据。
    if now is None:
        if _BEIJING_TZ is not None:
            now = datetime.now(_BEIJING_TZ)
        else:
            now = datetime.now()
    elif now.tzinfo is not None and _BEIJING_TZ is not None:
        now = now.astimezone(_BEIJING_TZ)
    if now.weekday() >= 5:
        return False
    hour = now.hour
    minute = now.minute
    if 9 <= hour < 10 or (hour == 10 and minute <= 15):
        return True
    if (hour == 10 and minute >= 30) or hour == 11:
        return True
    if 13 <= hour < 15:
        return True
    if hour == 15 and minute == 0:
        return True
    if 21 <= hour < 23:
        return True
    return False

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

EXCHANGE_MAP = {
    "SHFE": "SHFE",
    "DCE": "DCE",
    "CZCE": "CZCE",
    "CFFEX": "CFFEX",
    "INE": "INE",
    "GFEX": "GFEX",
}

SYMBOL_TO_EXCHANGE = {
    "RB": "SHFE",
    "MA": "CZCE",
    "M": "DCE",
    "TA": "CZCE",
    "FG": "CZCE",
    "SR": "CZCE",
    "SA": "CZCE",
    "PP": "DCE",
    "AU": "SHFE",
    "CU": "SHFE",
    "SC": "INE",
    "IF": "CFFEX",
    "IC": "CFFEX",
    "IH": "CFFEX",
}

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "kline_cache"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class KlineCache:
    """K线缓存元数据"""

    symbol: str
    duration_seconds: int
    start_dt: pd.Timestamp
    end_dt: pd.Timestamp
    rows: int
    cache_path: Path
    md5: str = ""

    def to_dict(self) -> Dict[str, Union[str, int]]:
        return {
            "symbol": self.symbol,
            "duration_seconds": self.duration_seconds,
            "start_dt": str(self.start_dt),
            "end_dt": str(self.end_dt),
            "rows": self.rows,
            "cache_path": str(self.cache_path),
            "md5": self.md5,
        }


@dataclass
class OHLCV:
    """OHLCV 数据容器"""

    datetime: pd.DatetimeIndex
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    open_interest: np.ndarray = field(default_factory=lambda: np.array([]))

    def to_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame({
            "datetime": self.datetime,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        })
        if len(self.open_interest) == len(self.datetime):
            df["open_interest"] = self.open_interest
        df.set_index("datetime", inplace=True)
        return df

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "OHLCV":
        return cls(
            datetime=pd.DatetimeIndex(df.index),
            open=df["open"].values,
            high=df["high"].values,
            low=df["low"].values,
            close=df["close"].values,
            volume=df["volume"].values,
            open_interest=df["open_interest"].values if "open_interest" in df.columns else np.array([]),
        )


# 需要保持品种代码大写的交易所（CZCE郑商所、CFFEX中金所）
_UPPERCASE_EXCHANGES = {"CZCE", "CFFEX"}


def get_main_contract(symbol: str) -> str:
    """
    获取天勤主连合约代码

    Parameters
    ----------
    symbol : str
        品种代码，如 "RB", "MA", "M"

    Returns
    -------
    str — 天勤主连代码，如 "KQ.m@SHFE.rb"
    """
    exchange = SYMBOL_TO_EXCHANGE.get(symbol.upper())
    if exchange is None:
        raise ValueError(f"未知品种: {symbol}")
    if exchange in _UPPERCASE_EXCHANGES:
        return f"KQ.m@{exchange}.{symbol.upper()}"
    return f"KQ.m@{exchange}.{symbol.lower()}"


def get_specific_contract(symbol: str, contract_month: str) -> str:
    """
    获取具体合约代码

    Parameters
    ----------
    symbol : str
        品种代码
    contract_month : str
        合约月份，如 "2505"

    Returns
    -------
    str — 天勤合约代码，如 "SHFE.rb2505"
    """
    exchange = SYMBOL_TO_EXCHANGE.get(symbol.upper())
    if exchange is None:
        raise ValueError(f"未知品种: {symbol}")
    if exchange in _UPPERCASE_EXCHANGES:
        return f"{exchange}.{symbol.upper()}{contract_month}"
    return f"{exchange}.{symbol.lower()}{contract_month}"


# ---------------------------------------------------------------------------
# 天勤数据源
# ---------------------------------------------------------------------------

class TqDataSource:
    """
    天勤行情数据源

    支持历史数据下载、实时订阅、主力合约映射、本地缓存。
    回测时使用 TqBacktest 或 TqSim 账户。

    Parameters
    ----------
    account : str, optional
        天勤账号
    password : str, optional
        天勤密码
    sim : bool
        是否使用模拟盘（默认True）
    cache_dir : Path
        本地缓存目录
    """

    def __init__(
        self,
        account: Optional[str] = None,
        password: Optional[str] = None,
        sim: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        self.account = account
        self.password = password
        self.sim = sim
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._api = None
        self._subscribed: set = set()
        self._klines: Dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _get_api(self):
        """惰性初始化 TqApi"""
        if self._api is not None:
            return self._api
        try:
            from tqsdk import TqApi, TqAuth, TqSim, TqBacktest
        except ImportError as exc:
            raise ImportError("tqsdk 未安装，请执行: pip install tqsdk") from exc

        auth = None
        if self.account and self.password:
            auth = TqAuth(self.account, self.password)

        if self.sim:
            self._api = TqApi(TqSim(), auth=auth)
        else:
            self._api = TqApi(auth=auth)
        return self._api

    def _cache_key(
        self,
        symbol: str,
        duration_seconds: int,
        start_dt: pd.Timestamp,
        end_dt: pd.Timestamp,
    ) -> str:
        raw = f"{symbol}_{duration_seconds}_{start_dt}_{end_dt}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.parquet"

    def _load_cache(self, cache_path: Path) -> Optional[pd.DataFrame]:
        if not cache_path.exists():
            return None
        try:
            df = pd.read_parquet(cache_path)
            logger.debug(f"缓存命中: {cache_path.name}")
            return df
        except Exception as exc:
            logger.warning(f"缓存读取失败: {exc}")
            return None

    def _save_cache(self, cache_path: Path, df: pd.DataFrame) -> None:
        try:
            df.to_parquet(cache_path, compression="zstd")
            logger.debug(f"缓存写入: {cache_path.name}")
        except Exception as exc:
            logger.warning(f"缓存写入失败: {exc}")

    # ------------------------------------------------------------------
    # 历史数据下载
    # ------------------------------------------------------------------

    def download_klines(
        self,
        symbol: str,
        start_dt: Union[str, pd.Timestamp],
        end_dt: Union[str, pd.Timestamp],
        duration_seconds: int = 3600,
        use_cache: bool = True,
        main_contract: bool = True,
    ) -> OHLCV:
        """
        下载历史K线数据

        Parameters
        ----------
        symbol : str
            品种代码，如 "RB"
        start_dt : str or Timestamp
            开始时间
        end_dt : str or Timestamp
            结束时间
        duration_seconds : int
            K线周期（秒），默认3600=1小时
        use_cache : bool
            是否使用本地缓存
        main_contract : bool
            是否使用主力合约映射

        Returns
        -------
        OHLCV
        """
        start_dt = pd.Timestamp(start_dt)
        end_dt = pd.Timestamp(end_dt)
        
        # 统一时区处理，确保比较时类型一致
        if start_dt.tzinfo is not None:
            start_dt = start_dt.tz_localize(None)
        if end_dt.tzinfo is not None:
            end_dt = end_dt.tz_localize(None)

        tq_symbol = get_main_contract(symbol) if main_contract else symbol
        cache_key = self._cache_key(tq_symbol, duration_seconds, start_dt, end_dt)
        cache_path = self._cache_path(cache_key)

        if use_cache:
            cached = self._load_cache(cache_path)
            if cached is not None:
                return OHLCV.from_dataframe(cached)

        api = self._get_api()
        from tqsdk import TqApi
        import time

        # 计算需要的数据长度，确保覆盖整个时间范围
        # 1小时K线：约17520根/2年，日线：约730根/2年
        total_hours = (end_dt - start_dt).total_seconds() / duration_seconds
        data_length = max(10000, int(total_hours * 1.5))  # 1.5倍冗余
        # TQSDK 限制最大50000根
        data_length = min(data_length, 50000)
        
        klines = api.get_kline_serial(tq_symbol, duration_seconds, data_length=data_length)
        deadline = time.time() + 120
        while True:
            api.wait_update(deadline=deadline)
            if not klines.empty:
                break
            if time.time() >= deadline:
                raise TimeoutError(f"获取K线数据超时: {tq_symbol}")

        df = klines.copy()
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df[(df["datetime"] >= start_dt) & (df["datetime"] <= end_dt)].copy()
        df.set_index("datetime", inplace=True)

        # 统一列名
        rename_map = {
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }
        if "open_oi" in df.columns:
            rename_map["open_oi"] = "open_interest"
        df = df.rename(columns=rename_map)
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                df[col] = np.nan

        if use_cache and not df.empty:
            self._save_cache(cache_path, df)

        return OHLCV.from_dataframe(df)

    def download_klines_batch(
        self,
        symbols: List[str],
        start_dt: Union[str, pd.Timestamp],
        end_dt: Union[str, pd.Timestamp],
        duration_seconds: int = 3600,
        use_cache: bool = True,
    ) -> Dict[str, OHLCV]:
        """
        批量下载多个品种K线

        Returns
        -------
        dict[str, OHLCV]
        """
        results = {}
        for sym in symbols:
            try:
                ohlcv = self.download_klines(
                    sym, start_dt, end_dt, duration_seconds, use_cache
                )
                results[sym] = ohlcv
            except Exception as exc:
                logger.error(f"下载 {sym} 数据失败: {exc}")
        return results

    # ------------------------------------------------------------------
    # 实时行情订阅
    # ------------------------------------------------------------------

    def subscribe_quote(self, symbol: str, main_contract: bool = True) -> None:
        """
        订阅实时行情

        Parameters
        ----------
        symbol : str
            品种代码
        main_contract : bool
            是否订阅主力合约
        """
        tq_symbol = get_main_contract(symbol) if main_contract else symbol
        if tq_symbol in self._subscribed:
            return
        api = self._get_api()
        api.subscribe_quote(tq_symbol)
        self._subscribed.add(tq_symbol)
        logger.info(f"订阅行情: {tq_symbol}")

    def subscribe_klines(
        self,
        symbol: str,
        duration_seconds: int = 3600,
        main_contract: bool = True,
    ) -> pd.DataFrame:
        """
        订阅K线序列并返回当前数据

        Parameters
        ----------
        symbol : str
            品种代码
        duration_seconds : int
            K线周期（秒）
        main_contract : bool
            是否使用主力合约

        Returns
        -------
        pd.DataFrame
        """
        tq_symbol = get_main_contract(symbol) if main_contract else symbol
        api = self._get_api()
        klines = api.get_kline_serial(tq_symbol, duration_seconds)
        self._klines[tq_symbol] = klines
        return klines

    def get_latest_tick(self, symbol: str, main_contract: bool = True) -> Dict[str, Union[float, int, str]]:
        """
        获取最新Tick数据

        Returns
        -------
        dict
        """
        tq_symbol = get_main_contract(symbol) if main_contract else symbol
        api = self._get_api()
        quote = api.get_quote(tq_symbol)
        return {
            "symbol": tq_symbol,
            "last_price": quote.last_price,
            "bid_price1": quote.bid_price1,
            "ask_price1": quote.ask_price1,
            "bid_volume1": quote.bid_volume1,
            "ask_volume1": quote.ask_volume1,
            "volume": quote.volume,
            "datetime": quote.datetime,
        }

    def wait_update(self, deadline: Optional[pd.Timestamp] = None) -> bool:
        """
        等待行情更新

        Parameters
        ----------
        deadline : Timestamp, optional
            超时时间

        Returns
        -------
        bool — 是否有新数据
        """
        api = self._get_api()
        return api.wait_update(deadline=deadline)

    # ------------------------------------------------------------------
    # 主力合约映射
    # ------------------------------------------------------------------

    def get_current_main_contract(self, symbol: str) -> str:
        """
        查询当前主力合约具体代码

        Returns
        -------
        str — 如 "SHFE.rb2505"
        """
        tq_symbol = get_main_contract(symbol)
        api = self._get_api()
        quote = api.get_quote(tq_symbol)
        # 天勤主连的 underlying 即为当前主力合约
        underlying = getattr(quote, "underlying_symbol", tq_symbol)
        return underlying

    def get_contract_list(self, symbol: str) -> List[str]:
        """
        获取某品种的所有可交易合约列表

        尝试顺序：
        1. query_cont_quotes（需要行情，交易时间外可能失败）
        2. query_symbol_info（静态元数据，24小时可用）
        3. 程序化生成（基于CONTRACT_MONTHS_RULE，完全离线）

        Returns
        -------
        list[str]
        """
        symbol_upper = symbol.upper()
        exchange = SYMBOL_TO_EXCHANGE.get(symbol_upper)
        if exchange is None:
            return []

        api = self._get_api()
        product_code = symbol_upper if exchange in _UPPERCASE_EXCHANGES else symbol.lower()
        tq_product = f"{exchange}.{product_code}"

        # 方法1: query_cont_quotes
        try:
            cont_list = api.query_cont_quotes(tq_product)
            if cont_list and len(cont_list) > 0:
                logger.debug(f"通过 query_cont_quotes 获取 {symbol} 合约列表: {len(cont_list)} 个")
                return cont_list
        except Exception as exc:
            logger.debug(f"query_cont_quotes 获取 {symbol} 失败: {exc}")

        # 方法2: query_symbol_info（需要先拿到合约ID，尝试按产品前缀查询）
        try:
            # 构造产品前缀：如 SHFE.rb, CZCE.MA, DCE.m
            prefix = tq_product
            quote_list = list(api._quotes.keys()) if hasattr(api, '_quotes') else []
            if quote_list:
                matching = [q for q in quote_list if q.startswith(prefix + "2")]
                if matching:
                    logger.debug(f"通过 quotes 匹配 {symbol} 合约: {len(matching)} 个")
                    return matching
        except Exception as exc:
            logger.debug(f"通过 quotes 匹配 {symbol} 失败: {exc}")

        # 方法3: 程序化生成（回看3年确保覆盖历史合约）
        logger.warning(f"{symbol} 合约列表获取失败，使用程序化生成")
        generated = TermStructureData.generate_contracts_for_symbol(
            symbol_upper, exchange, lookback_years=3, lookforward_years=1
        )
        contract_codes = []
        for year, month in generated:
            if exchange in _UPPERCASE_EXCHANGES:
                code = f"{exchange}.{symbol_upper}{year}{month}"
            else:
                code = f"{exchange}.{product_code}{year}{month}"
            contract_codes.append(code)

        logger.info(f"程序化生成 {symbol} 合约列表: {len(contract_codes)} 个")
        return contract_codes

    # ------------------------------------------------------------------
    # 账户与交易（模拟盘）
    # ------------------------------------------------------------------

    def get_account(self) -> Dict[str, float]:
        """获取账户信息"""
        api = self._get_api()
        account = api.get_account()
        return {
            "balance": account.balance,
            "available": account.available,
            "float_profit": account.float_profit,
            "risk_ratio": account.risk_ratio,
            "margin": account.margin,
        }

    def get_positions(self) -> List[Dict[str, Union[str, int, float]]]:
        """获取持仓列表"""
        api = self._get_api()
        positions = api.get_position()
        result = []
        for pos in positions.values():
            result.append({
                "symbol": pos.symbol,
                "volume_long": pos.volume_long,
                "volume_short": pos.volume_short,
                "open_price_long": pos.open_price_long,
                "open_price_short": pos.open_price_short,
                "float_profit": pos.float_profit,
            })
        return result

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self) -> None:
        """关闭API连接"""
        if self._api is not None:
            try:
                self._api.close()
            except Exception as exc:
                logger.warning(f"关闭API异常: {exc}")
            finally:
                self._api = None
                self._subscribed.clear()
                self._klines.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ------------------------------------------------------------------
    # 静态工具：不依赖API的数据处理
    # ------------------------------------------------------------------

    @staticmethod
    def resample_klines(df: pd.DataFrame, target_seconds: int) -> pd.DataFrame:
        """
        K线周期转换（升/降采样）

        Parameters
        ----------
        df : pd.DataFrame
            原始K线，index为datetime，包含open/high/low/close/volume
        target_seconds : int
            目标周期（秒）

        Returns
        -------
        pd.DataFrame
        """
        if df.empty:
            return df.copy()
        freq = f"{target_seconds}S"
        resampled = df.resample(freq).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()
        return resampled

    @staticmethod
    def align_symbols(
        ohlcv_dict: Dict[str, OHLCV],
    ) -> Tuple[pd.DatetimeIndex, Dict[str, pd.DataFrame]]:
        """
        将多个品种的K线数据对齐到同一时间索引

        Returns
        -------
        (common_index, aligned_dataframes)
        """
        if not ohlcv_dict:
            return pd.DatetimeIndex([]), {}

        all_indices = [ohlcv.datetime for ohlcv in ohlcv_dict.values()]
        common_index = all_indices[0]
        for idx in all_indices[1:]:
            common_index = common_index.intersection(idx)

        aligned = {}
        for sym, ohlcv in ohlcv_dict.items():
            df = ohlcv.to_dataframe()
            aligned_df = df.loc[common_index].copy()
            aligned[sym] = aligned_df

        return common_index, aligned


# ---------------------------------------------------------------------------
# 期限结构数据获取
# ---------------------------------------------------------------------------

# 不同品种的合约月份规则
CONTRACT_MONTHS_RULE = {
    "RB": ["01", "05", "10"],      # 螺纹钢：1月、5月、10月
    "MA": ["01", "05", "09"],      # 甲醇：1月、5月、9月
    "M": ["01", "05", "09"],       # 豆粕：1月、5月、9月
    "TA": ["01", "05", "09"],      # PTA：1月、5月、9月
    "FG": ["01", "05", "09"],      # 玻璃：1月、5月、9月
    "SR": ["01", "05", "09"],      # 白糖：1月、5月、9月
    "SA": ["01", "05", "09"],      # 纯碱：1月、5月、9月
    "PP": ["01", "05", "09"],      # 聚丙烯：1月、5月、9月
    "AU": [f"{m:02d}" for m in range(1, 13)],  # 黄金：逐月
    "CU": [f"{m:02d}" for m in range(1, 13)],  # 铜：逐月
    "SC": ["01", "03", "05", "07", "09", "11"],  # 原油：单月
    "IF": ["03", "06", "09", "12"],  # 沪深300股指：季度
    "IC": ["03", "06", "09", "12"],  # 中证500：季度
    "IH": ["03", "06", "09", "12"],  # 上证50：季度
}


def parse_contract_month(contract_code: str) -> str:
    """
    从合约代码中提取到期月份
    
    Parameters
    ----------
    contract_code : str
        合约代码，如 "SHFE.rb2505"
    
    Returns
    -------
    str — 到期月份，如 "2505"
    """
    # 提取最后4位作为年月
    return contract_code[-4:]


def get_contract_expiry_date(contract_code: str) -> datetime:
    """
    获取合约到期日期

    Parameters
    ----------
    contract_code : str
        合约代码

    Returns
    -------
    datetime — 到期日期
        - CFFEX股指/国债期货：合约月份第3个周五
        - 其他：合约月份第15个自然日（遇周末提前到周五）
    """
    month_str = parse_contract_month(contract_code)
    year = 2000 + int(month_str[:2])
    month = int(month_str[2:])

    # 判断是否为CFFEX品种（股指/国债交割日为第3个周五）
    exchange_prefix = contract_code.split(".")[0] if "." in contract_code else ""
    if exchange_prefix == "CFFEX":
        # 第3个周五
        import calendar
        c = calendar.monthcalendar(year, month)
        fridays = [week[calendar.FRIDAY] for week in c if week[calendar.FRIDAY] != 0]
        if len(fridays) >= 3:
            return datetime(year, month, fridays[2])
        # 兜底
        return datetime(year, month, fridays[-1])

    # 大多数期货合约到期日为合约月份的第15日
    expiry_date = datetime(year, month, 15)

    # 如果15日是周末，调整到周五
    if expiry_date.weekday() == 5:  # Saturday
        expiry_date -= pd.Timedelta(days=1)
    elif expiry_date.weekday() == 6:  # Sunday
        expiry_date -= pd.Timedelta(days=2)

    return expiry_date


class TermStructureData:
    """
    期限结构数据类

    【核心方案】持仓量比较法确定主力合约

    核心逻辑：
    1. 获取该品种所有合约的程序化列表（含过去3年到未来1年）
    2. 下载每个合约的K线数据（含 open_interest 持仓量）
    3. 在每个时间点，比较所有活跃合约的持仓量：
       - 持仓量最大的合约 = 主力合约
       - 到期日最近（但 > 当前）的合约 = 近月合约
       - 到期日次近（但 > 当前）的合约 = 远月合约
    4. 主连K线（KQ.m@...）提供连续的价格序列

    优势：
    - 无需依赖 TQSDK 的 underlying_symbol 字段（历史数据中不存在）
    - 程序化合约生成确保24小时可用，不受非交易时间API限制
    - 持仓量比较法准确反映历史上的真实主力合约变化
    - 自动处理主力换月、近月交割、远月新增

    注意事项：
    - 已到期超过1年的合约可能没有历史数据（TQSDK限制），下载时跳过
    - 如果同时有多个合约持仓量接近，取其最大者
    - 所有数据在下载后缓存到DB并备份到CSV
    """

    def __init__(self, tq_ds: TqDataSource):
        self.tq_ds = tq_ds
        self._api = None
        self._contract_list_cache: Dict[str, List[str]] = {}
        self._contract_expiry_cache: Dict[str, datetime] = {}
        self._contract_data_cache: Dict[str, Tuple] = {}  # symbol -> (contract_data, contract_expiry_list)

    def _get_api(self):
        """获取TQSDK API实例"""
        if self._api is None:
            self._api = self.tq_ds._get_api()
        return self._api

    @staticmethod
    def generate_contracts_for_symbol(
        symbol: str,
        exchange: str,
        lookback_years: int = 3,
        lookforward_years: int = 1,
    ) -> List[Tuple[str, str]]:
        """
        程序化生成某品种所有合约的(年份,月份)列表

        根据品种的上市月份规则，在[当年-lookback_years, 当年+lookforward_years]
        范围内生成所有合约。

        Parameters
        ----------
        symbol : str
            品种代码（大写），如 RB, MA
        exchange : str
            交易所，如 SHFE, CZCE, DCE
        lookback_years : int
            回看年数
        lookforward_years : int
            展望年数

        Returns
        -------
        List[Tuple[str, str]]
            [(年份后缀, 月份)], 如 [("23", "01"), ("23", "05"), ...]
        """
        months = CONTRACT_MONTHS_RULE.get(symbol, ["01", "05", "09"])
        now = datetime.now()
        start_year = now.year - lookback_years
        end_year = now.year + lookforward_years

        result = []
        for year in range(start_year, end_year + 1):
            year_suffix = str(year)[-2:]
            for month in months:
                result.append((year_suffix, month))

        return result

    def _build_contract_list_with_expiry(
        self,
        symbol: str,
        exchange: str,
    ) -> List[Tuple[str, datetime]]:
        """
        构建合约代码及其到期日的排序列表

        返回 [(contract_code, expiry_date), ...]，按到期日升序排列
        """
        cache_key = f"{exchange}.{symbol}"
        if cache_key in self._contract_list_cache:
            cached = self._contract_list_cache[cache_key]
            return [(c, self._contract_expiry_cache[c]) for c in cached]

        contract_codes = self.tq_ds.get_contract_list(symbol)
        if not contract_codes:
            return []

        contract_expiry = []
        for code in contract_codes:
            try:
                expiry = get_contract_expiry_date(code)
                contract_expiry.append((code, expiry))
                self._contract_expiry_cache[code] = expiry
            except Exception:
                continue

        contract_expiry.sort(key=lambda x: x[1])
        self._contract_list_cache[cache_key] = [c for c, _ in contract_expiry]

        return contract_expiry

    def _contract_code_to_symbol(self, contract_code: str) -> str:
        """从完整合约代码提取品种前缀，如 CZCE.MA2401 -> MA"""
        # 格式: {exchange}.{symbol}{year}{month}
        parts = contract_code.split(".")
        if len(parts) != 2:
            return contract_code
        raw = parts[1]
        # 去掉末尾4位（年份+月份）
        symbol_part = raw[:-4]
        # 转大写（CZCE的合约代码就是大写，其他交易所是小写）
        return symbol_part.upper()

    def get_main_contract_data(
        self,
        symbol: str,
        start_dt: Union[str, pd.Timestamp],
        end_dt: Union[str, pd.Timestamp],
        duration_seconds: int = 3600,
    ) -> pd.DataFrame:
        """
        获取主连合约K线数据（KQ.m@...）

        Parameters
        ----------
        symbol : str
            品种代码
        start_dt, end_dt : str or Timestamp
            时间范围
        duration_seconds : int
            K线周期（秒）

        Returns
        -------
        pd.DataFrame
            主连K线数据，包含 datetime, open, high, low, close, volume, open_interest
        """
        start_dt = pd.Timestamp(start_dt)
        end_dt = pd.Timestamp(end_dt)
        if start_dt.tzinfo is not None:
            start_dt = start_dt.tz_localize(None)
        if end_dt.tzinfo is not None:
            end_dt = end_dt.tz_localize(None)

        tq_symbol = get_main_contract(symbol)
        api = self._get_api()

        # 计算需要的数据长度，确保覆盖整个时间范围
        total_bars = (end_dt - start_dt).total_seconds() / duration_seconds
        # 日线只需要实际所需数据量，减少请求避免超时
        data_length = max(int(total_bars * 1.5), 2000)
        data_length = min(data_length, 50000)

        # 重试机制（特别是日线数据可能需要重试）
        import time as _time
        # 日线在非交易时段几乎必定超时，不重试直接走聚合兜底
        max_retries = 1 if duration_seconds == 86400 else 3
        klines = None
        for retry in range(max_retries):
            try:
                klines = api.get_kline_serial(tq_symbol, duration_seconds, data_length=data_length)
                deadline = _time.time() + 120
                while _time.time() < deadline:
                    api.wait_update(deadline=deadline)
                    if not klines.empty:
                        break
                if not klines.empty:
                    break
            except Exception as e:
                if retry < max_retries - 1:
                    logger.warning(f"[{symbol}] {duration_seconds}s K线获取失败(重试{retry+1}): {e}")
                    _time.sleep(5)
                else:
                    # 日线兜底：从1小时K线聚合
                    if duration_seconds == 86400:
                        logger.warning(f"[{symbol}] 86400s获取失败，从1小时数据聚合")
                        try:
                            return self.get_main_contract_data(
                                symbol, start_dt, end_dt, duration_seconds=3600
                            ).resample("D").agg({
                                "open": "first",
                                "high": "max",
                                "low": "min",
                                "close": "last",
                                "volume": "sum",
                                "open_interest": "last",
                            }).dropna(how="all")
                        except Exception as e2:
                            logger.error(f"[{symbol}] 1小时聚合也失败: {e2}")
                    raise

        df = klines.copy()
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df[(df["datetime"] >= start_dt) & (df["datetime"] <= end_dt)].copy()

        if "open_oi" in df.columns:
            df = df.rename(columns={"open_oi": "open_interest"})

        df.set_index("datetime", inplace=True)
        df.index.name = "datetime"

        return df

    def download_term_structure_data(
        self,
        symbol: str,
        start_dt: Union[str, pd.Timestamp],
        end_dt: Union[str, pd.Timestamp],
        duration_seconds: int = 3600,
        skip_contract_download: bool = False,
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        下载期限结构数据

        【核心方法】持仓量比较法：
        1. 获取所有合约的程序化列表
        2. 下载每个合约的历史K线（含持仓量）
        3. 在每个时间点比较持仓量，确定主力/近月/远月合约
        4. 用主连K线提供连续OHLCV

        Parameters
        ----------
        symbol : str
            品种代码
        start_dt, end_dt : str or Timestamp
            时间范围
        duration_seconds : int
            K线周期（秒）

        Returns
        -------
        Tuple[pd.DataFrame, List[Dict]]
            (期限结构数据, 合约映射表)

        期限结构数据包含列：
        - datetime: 时间戳
        - open, high, low, close, volume, open_interest: 主连数据
        - near_close: 近月合约收盘价
        - far_close: 远月合约收盘价
        - main_contract: 当前主力合约
        - near_contract: 近月合约代码
        - far_contract: 远月合约代码
        - days_to_expiry: 近月合约到期天数
        """
        start_dt = pd.Timestamp(start_dt)
        end_dt = pd.Timestamp(end_dt)

        if start_dt.tzinfo is not None:
            start_dt = start_dt.tz_localize(None)
        if end_dt.tzinfo is not None:
            end_dt = end_dt.tz_localize(None)

        logger.info(f"[{symbol}] 开始下载期限结构: {start_dt.date()} ~ {end_dt.date()}")

        # ========== 第1步：获取主连K线 ==========
        main_df = self.get_main_contract_data(symbol, start_dt, end_dt, duration_seconds)
        if main_df.empty:
            logger.warning(f"[{symbol}] 主连数据为空")
            return main_df, []

        # ========== 第2步：构建完整合约到期列表 ==========
        exchange = SYMBOL_TO_EXCHANGE.get(symbol.upper(), "")
        all_contract_expiry = self._build_contract_list_with_expiry(symbol, exchange)

        if not all_contract_expiry:
            logger.warning(f"[{symbol}] 无可用的合约列表，返回主连数据")
            main_df["near_close"] = main_df["close"]
            main_df["far_close"] = main_df["close"]
            main_df["main_contract"] = symbol
            main_df["near_contract"] = None
            main_df["far_contract"] = None
            main_df["days_to_expiry"] = 30
            return main_df, []

        logger.info(f"[{symbol}] 合约列表: {len(all_contract_expiry)} 个")

        # ========== 第3步：下载所有合约的K线数据 ==========
        # 先检查缓存（跨频率复用）
        cache_key = f"{symbol}_{duration_seconds}"
        if cache_key in self._contract_data_cache:
            cached_data, cached_expiry = self._contract_data_cache[cache_key]
            logger.info(f"[{symbol}] 使用缓存合约数据 ({len(cached_data)} 个)")
            contract_data = cached_data
            download_ok = len(cached_data)
            download_fail = 0
        elif skip_contract_download:
            logger.info(f"[{symbol}] 跳过合约下载（复用前一次数据）")
            contract_data = self._contract_data_cache.get(symbol, ({}, []))[0] if symbol in self._contract_data_cache else {}
            download_ok = len(contract_data)
            download_fail = 0
        else:
            # 检查是否在交易时段（非交易时段 TQSDK 无法获取合约数据）
            if not _is_market_open():
                logger.warning(f"[{symbol}] 当前非交易时段，跳过合约数据下载（仅使用主连数据）")
                contract_data = {}
                download_ok = 0
                download_fail = 0
            else:
                # 只下载最可能活跃的合约（到期日在start_dt之后的）
                active_contracts = [
                    (c, e) for c, e in all_contract_expiry
                    if e >= start_dt - pd.Timedelta(days=180)
                ]

                contract_data: Dict[str, pd.DataFrame] = {}
                download_ok = 0
                download_fail = 0

                api = self._get_api()
                for contract_code, expiry in active_contracts:
                    try:
                        klines = api.get_kline_serial(contract_code, duration_seconds, data_length=200)

                        import time as _ctime
                        dl = _ctime.time() + 10
                        while _ctime.time() < dl:
                            api.wait_update(deadline=dl)
                            if not klines.empty:
                                break

                        if klines.empty:
                            download_fail += 1
                            continue

                        df_contract = klines.copy()
                        df_contract["datetime"] = pd.to_datetime(df_contract["datetime"])
                        mask = (df_contract["datetime"] >= start_dt) & (df_contract["datetime"] <= end_dt)
                        df_contract = df_contract[mask].copy()
                        if "open_oi" in df_contract.columns:
                            df_contract = df_contract.rename(columns={"open_oi": "open_interest"})
                        if not df_contract.empty:
                            df_contract.set_index("datetime", inplace=True)
                            contract_data[contract_code] = df_contract
                            download_ok += 1
                            logger.info(f"[{symbol}] {contract_code}: {len(df_contract)} 条")
                        else:
                            download_fail += 1

                    except Exception as e:
                        download_fail += 1
                        logger.debug(f"[{symbol}] {contract_code} 获取失败: {e}")

                logger.info(f"[{symbol}] 合约数据下载: {download_ok} 成功, {download_fail} 失败")

            # 缓存结果（即使为空也缓存，避免重复尝试）
            self._contract_data_cache[cache_key] = (contract_data, all_contract_expiry)

        # 如果没有有效的合约数据，使用缓存中的旧数据
        if not contract_data and symbol in self._contract_data_cache:
            contract_data, _ = self._contract_data_cache[symbol]

        if not contract_data:
            logger.warning(f"[{symbol}] 无合约K线数据，使用到期日规则推断近月/远月合约")
            result = main_df.copy()
            result["main_contract"] = ""
            result["near_contract"] = ""
            result["far_contract"] = ""
            result["near_close"] = np.nan
            result["far_close"] = np.nan
            result["days_to_expiry"] = 30

            contract_mapping = []

            for dt_ts in result.index:
                dt_ts = pd.Timestamp(dt_ts)
                # 找到所有到期日在当前时间之后的合约
                future = [(c, e) for c, e in all_contract_expiry if e > dt_ts]
                future.sort(key=lambda x: x[1])

                if future:
                    near_code, near_expiry = future[0]
                    near_contract = near_code  # 合约代码已含交易所前缀，如 CZCE.MA2409
                    days_to_expiry = (near_expiry - dt_ts).days
                else:
                    near_contract = ""
                    days_to_expiry = 30

                if len(future) >= 2:
                    far_code, far_expiry = future[1]
                    far_contract = far_code
                else:
                    far_contract = ""

                if future:
                    main_contract = future[0][0]
                else:
                    main_contract = symbol

                result.iloc[result.index.get_loc(dt_ts), result.columns.get_loc("main_contract")] = main_contract
                result.iloc[result.index.get_loc(dt_ts), result.columns.get_loc("near_contract")] = near_contract
                result.iloc[result.index.get_loc(dt_ts), result.columns.get_loc("far_contract")] = far_contract
                result.iloc[result.index.get_loc(dt_ts), result.columns.get_loc("days_to_expiry")] = days_to_expiry

                contract_mapping.append({
                    "datetime": dt_ts,
                    "main_contract": main_contract,
                    "near_contract": near_contract,
                    "far_contract": far_contract,
                    "days_to_expiry": days_to_expiry,
                })

            # 近月/远月价格用主连价格填充（无合约K线数据时的折衷）
            result["near_close"] = result["close"]
            result["far_close"] = result["close"]

            unique_mains = set(m["main_contract"] for m in contract_mapping if m["main_contract"])
            logger.info(f"[{symbol}] 无合约数据，到期日规则推断完成: {len(result)} 条, "
                        f"合约变更: {len(unique_mains)} 次")
            return result, contract_mapping

        # ========== 第4步：遍历主连时间轴，用持仓量确定主力合约 ==========
        result = main_df.copy()
        result["main_contract"] = None
        result["near_contract"] = None
        result["far_contract"] = None
        result["near_close"] = np.nan
        result["far_close"] = np.nan
        result["days_to_expiry"] = 30

        contract_mapping = []

        # 将合约数据按时间索引对齐，方便快速查询
        aligned_oi: Dict[str, pd.Series] = {}
        for code, df_c in contract_data.items():
            if "open_interest" in df_c.columns:
                aligned_oi[code] = df_c["open_interest"]
            else:
                aligned_oi[code] = pd.Series(index=df_c.index, dtype=float)

        for dt_ts in result.index:
            dt_ts = pd.Timestamp(dt_ts)

            # ---- 4a: 通过持仓量确定主力合约 ----
            oi_at_dt = {}
            for code, oi_series in aligned_oi.items():
                if dt_ts in oi_series.index:
                    oi_val = oi_series.loc[dt_ts]
                    if pd.notna(oi_val) and oi_val > 0:
                        oi_at_dt[code] = oi_val

            if oi_at_dt:
                main_contract = max(oi_at_dt, key=oi_at_dt.get)
            else:
                # 回退：用到期日排序，选择第2接近的合约
                active_now = [(c, e) for c, e in all_contract_expiry if e > dt_ts]
                if len(active_now) >= 2:
                    main_contract = active_now[1][0]  # 第2近 = 主力
                elif active_now:
                    main_contract = active_now[0][0]
                else:
                    continue

            # ---- 4b: 确定近月和远月合约 ----
            # 排除主力合约自己，按到期日排序
            others = [
                (c, e) for c, e in all_contract_expiry
                if c != main_contract and e > dt_ts
            ]
            others.sort(key=lambda x: x[1])

            near_contract = others[0][0] if len(others) >= 1 else None
            far_contract = others[1][0] if len(others) >= 2 else None

            near_expiry = others[0][1] if len(others) >= 1 else None
            days_to_expiry = (near_expiry - dt_ts).days if near_expiry else 30

            # ---- 4c: 填充数据 ----
            idx_loc = result.index.get_loc(dt_ts)

            result.iloc[idx_loc, result.columns.get_loc("main_contract")] = main_contract
            result.iloc[idx_loc, result.columns.get_loc("near_contract")] = near_contract
            result.iloc[idx_loc, result.columns.get_loc("far_contract")] = far_contract
            result.iloc[idx_loc, result.columns.get_loc("days_to_expiry")] = days_to_expiry

            # 近月价格
            if near_contract and near_contract in contract_data:
                ndf = contract_data[near_contract]
                if "close" in ndf.columns:
                    if dt_ts in ndf.index:
                        result.iloc[idx_loc, result.columns.get_loc("near_close")] = ndf.loc[dt_ts, "close"]
                    else:
                        prev = ndf.index[ndf.index <= dt_ts]
                        if len(prev) > 0:
                            result.iloc[idx_loc, result.columns.get_loc("near_close")] = ndf.loc[prev[-1], "close"]

            # 远月价格
            if far_contract and far_contract in contract_data:
                fdf = contract_data[far_contract]
                if "close" in fdf.columns:
                    if dt_ts in fdf.index:
                        result.iloc[idx_loc, result.columns.get_loc("far_close")] = fdf.loc[dt_ts, "close"]
                    else:
                        prev = fdf.index[fdf.index <= dt_ts]
                        if len(prev) > 0:
                            result.iloc[idx_loc, result.columns.get_loc("far_close")] = fdf.loc[prev[-1], "close"]

            contract_mapping.append({
                "datetime": dt_ts,
                "main_contract": main_contract,
                "near_contract": near_contract,
                "far_contract": far_contract,
                "days_to_expiry": days_to_expiry,
            })

        # 前向填充缺失值
        result["near_close"] = result["near_close"].ffill().fillna(result["close"])
        result["far_close"] = result["far_close"].ffill().fillna(result["close"])

        # 统计换月次数
        unique_mains = result["main_contract"].dropna().unique()
        logger.info(f"[{symbol}] 期限结构完成: {len(result)} 条, "
                     f"合约数: {download_ok}, 主力变更: {len(unique_mains)} 次")

        return result, contract_mapping

    def get_main_contract_history(
        self,
        symbol: str,
        start_dt: Union[str, pd.Timestamp],
        end_dt: Union[str, pd.Timestamp],
        duration_seconds: int = 3600,
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        获取主连合约历史数据及换月记录（兼容旧接口）

        内部调用 download_term_structure_data 获取数据后提取主连部分

        Returns
        -------
        Tuple[pd.DataFrame, List[Dict]]
            (主连K线数据, 换月记录)
        """
        result_df, contract_mapping = self.download_term_structure_data(
            symbol, start_dt, end_dt, duration_seconds
        )

        if result_df.empty:
            return result_df, []

        # 提取主连列
        main_cols = ["open", "high", "low", "close", "volume", "open_interest",
                      "main_contract", "near_contract", "far_contract", "days_to_expiry"]
        main_df = result_df[[c for c in main_cols if c in result_df.columns]].copy()
        main_df["underlying_contract"] = main_df.get("main_contract", None)

        # 构建换月记录
        switch_table = []
        if "main_contract" in main_df.columns:
            changes = main_df["main_contract"].dropna()
            changes = changes[changes != changes.shift(1)]
            for dt_val, contract in changes.items():
                switch_table.append({
                    "contract": contract,
                    "datetime": pd.Timestamp(dt_val),
                })

        return main_df, switch_table

    def get_near_far_for_time(
        self,
        all_contracts_expiry: List[Tuple[str, datetime]],
        point_dt: Union[str, pd.Timestamp, datetime],
        main_contract: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], int]:
        """
        获取某时间点的近月、远月合约（兼容旧接口）

        Parameters
        ----------
        all_contracts_expiry : List[Tuple[str, datetime]]
            所有合约及其到期日（已排序）
        point_dt : datetime
            查询时间点
        main_contract : str, optional
            主力合约（已不用，保留兼容性）

        Returns
        -------
        Tuple[Optional[str], Optional[str], int]
            (近月合约, 远月合约, 近月到期天数)
        """
        point_dt = pd.Timestamp(point_dt)
        if point_dt.tzinfo is not None:
            point_dt = point_dt.tz_localize(None)

        if not all_contracts_expiry:
            return None, None, 30

        active = [(c, e) for c, e in all_contracts_expiry if e >= point_dt]
        if not active:
            return None, None, 30

        near_contract, near_expiry = active[0]
        days_to_expiry = (near_expiry - point_dt).days
        far_contract = active[1][0] if len(active) > 1 else None

        return near_contract, far_contract, days_to_expiry
