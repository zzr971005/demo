"""
市场上下文 — 品种特性、分组、交易时间、主力合约映射

数据来源：backend/config/system.yaml 中的 symbols 配置
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# 从 system.yaml 加载品种配置（若文件不存在则使用硬编码兜底）
# ---------------------------------------------------------------------------

_CONFIG_PATH = "config/system.yaml"


def _load_yaml_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


_raw_cfg = _load_yaml_config()
_symbols_cfg = _raw_cfg.get("symbols", {})

# ---------------------------------------------------------------------------
# 品种特性定义
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SymbolSpec:
    code: str
    name: str
    exchange: str
    lot: int
    margin_rate: float
    commission_rate: float
    max_margin: int
    evolution_pool: int
    group: str
    trading_hours: Dict[str, List[str]]
    close_today_commission_rate: Optional[float] = None
    if_close_today_forbidden: bool = False


# 硬编码兜底（与 system.yaml 保持一致）
_SYMBOL_DEFAULTS: Dict[str, dict] = {
    "MA": {
        "name": "甲醇",
        "exchange": "CZCE",
        "lot": 10,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "A化工能源",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:00"]},
    },
    "RB": {
        "name": "螺纹钢",
        "exchange": "SHFE",
        "lot": 10,
        "margin_rate": 0.13,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "B黑色建材",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:00"]},
    },
    "M": {
        "name": "豆粕",
        "exchange": "DCE",
        "lot": 10,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "C农产品",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:00"]},
    },
    "TA": {
        "name": "PTA",
        "exchange": "CZCE",
        "lot": 5,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "A化工能源",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:00"]},
    },
    "FG": {
        "name": "玻璃",
        "exchange": "CZCE",
        "lot": 20,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "B黑色建材",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:00"]},
    },
    "SR": {
        "name": "白糖",
        "exchange": "CZCE",
        "lot": 10,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "C农产品",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:30"]},
    },
    "SA": {
        "name": "纯碱",
        "exchange": "CZCE",
        "lot": 20,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "A化工能源",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:00"]},
    },
    "PP": {
        "name": "聚丙烯",
        "exchange": "DCE",
        "lot": 5,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 15000,
        "evolution_pool": 300,
        "group": "A化工能源",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-23:00"]},
    },
    "AU": {
        "name": "黄金",
        "exchange": "SHFE",
        "lot": 1000,
        "margin_rate": 0.10,
        "commission_rate": 0.0001,
        "max_margin": 100000,
        "evolution_pool": 300,
        "group": "D贵金属金融",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-02:30"]},
    },
    "CU": {
        "name": "铜",
        "exchange": "SHFE",
        "lot": 5,
        "margin_rate": 0.12,
        "commission_rate": 0.0001,
        "max_margin": 80000,
        "evolution_pool": 300,
        "group": "D贵金属金融",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-01:00"]},
    },
    "SC": {
        "name": "原油",
        "exchange": "INE",
        "lot": 1000,
        "margin_rate": 0.15,
        "commission_rate": 0.0001,
        "max_margin": 80000,
        "evolution_pool": 300,
        "group": "A化工能源",
        "trading_hours": {"day": ["09:00-10:15", "10:30-11:30", "13:30-15:00"], "night": ["21:00-02:30"]},
    },
    "IF": {
        "name": "股指",
        "exchange": "CFFEX",
        "lot": 1,
        "margin_rate": 0.12,
        "commission_rate": 0.000023,
        "max_margin": 200000,
        "evolution_pool": 300,
        "group": "D贵金属金融",
        "trading_hours": {"day": ["09:30-11:30", "13:00-15:00"], "night": []},
        "close_today_commission_rate": 0.00023,
        "if_close_today_forbidden": True,
    },
}


def _build_symbol_configs() -> Dict[str, SymbolSpec]:
    configs: Dict[str, SymbolSpec] = {}
    for tier in ("low_margin", "high_margin"):
        tier_data = _symbols_cfg.get(tier, {})
        for code, data in tier_data.items():
            defaults = _SYMBOL_DEFAULTS.get(code, {})
            merged = {**defaults, **data}
            configs[code] = SymbolSpec(
                code=code,
                name=merged.get("name", code),
                exchange=merged.get("exchange", ""),
                lot=merged.get("lot", 1),
                margin_rate=merged.get("margin_rate", 0.1),
                commission_rate=merged.get("commission_rate", 0.0),
                max_margin=merged.get("max_margin", 15000),
                evolution_pool=merged.get("evolution_pool", 300),
                group=merged.get("group", "Z其他"),
                trading_hours=merged.get("trading_hours", {"day": [], "night": []}),
                close_today_commission_rate=merged.get("close_today_commission_rate"),
                if_close_today_forbidden=merged.get("if_close_today_forbidden", False),
            )
    for code, data in _SYMBOL_DEFAULTS.items():
        if code not in configs:
            configs[code] = SymbolSpec(
                code=code,
                name=data["name"],
                exchange=data["exchange"],
                lot=data["lot"],
                margin_rate=data["margin_rate"],
                commission_rate=data["commission_rate"],
                max_margin=data["max_margin"],
                evolution_pool=data["evolution_pool"],
                group=data["group"],
                trading_hours=data["trading_hours"],
                close_today_commission_rate=data.get("close_today_commission_rate"),
                if_close_today_forbidden=data.get("if_close_today_forbidden", False),
            )
    return configs


SYMBOL_CONFIGS: Dict[str, SymbolSpec] = _build_symbol_configs()

# ---------------------------------------------------------------------------
# 品种分组
# ---------------------------------------------------------------------------

SYMBOL_GROUPS: Dict[str, List[str]] = {
    "A化工能源": [],
    "B黑色建材": [],
    "C农产品": [],
    "D贵金属金融": [],
}

for _code, _spec in SYMBOL_CONFIGS.items():
    if _spec.group in SYMBOL_GROUPS:
        SYMBOL_GROUPS[_spec.group].append(_code)
    else:
        SYMBOL_GROUPS.setdefault(_spec.group, []).append(_code)

# ---------------------------------------------------------------------------
# 交易时间解析与判断
# ---------------------------------------------------------------------------


def _parse_time_range(tr: str) -> Tuple[time, time]:
    start_str, end_str = tr.split("-")
    h1, m1 = map(int, start_str.split(":"))
    h2, m2 = map(int, end_str.split(":"))
    return time(h1, m1), time(h2, m2)


class MarketContext:
    """提供品种特性查询、交易时间判断、主力合约映射。"""

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.spec = SYMBOL_CONFIGS.get(self.symbol)
        if self.spec is None:
            raise ValueError(f"未知品种: {symbol}")
        self._day_ranges: List[Tuple[time, time]] = [
            _parse_time_range(tr) for tr in self.spec.trading_hours.get("day", [])
        ]
        self._night_ranges: List[Tuple[time, time]] = [
            _parse_time_range(tr) for tr in self.spec.trading_hours.get("night", [])
        ]

    # --- 基础属性 ---

    @property
    def contract_multiplier(self) -> int:
        return self.spec.lot

    @property
    def margin_rate(self) -> float:
        return self.spec.margin_rate

    @property
    def commission_rate(self) -> float:
        return self.spec.commission_rate

    @property
    def max_margin(self) -> int:
        return self.spec.max_margin

    @property
    def group(self) -> str:
        return self.spec.group

    @property
    def exchange(self) -> str:
        return self.spec.exchange

    @property
    def has_night_session(self) -> bool:
        return len(self._night_ranges) > 0

    # --- 交易时间判断 ---

    def is_trading_time(self, dt: datetime) -> bool:
        """判断给定 datetime 是否处于该品种的交易时段内。"""
        t = dt.time()
        for s, e in self._day_ranges:
            if s <= t <= e:
                return True
        for s, e in self._night_ranges:
            if s <= e:
                if s <= t <= e:
                    return True
            else:
                if t >= s or t <= e:
                    return True
        return False

    def next_session_open(self, dt: datetime) -> Optional[datetime]:
        """返回下一个交易时段开盘时间（仅考虑当天）。"""
        t = dt.time()
        for s, e in self._day_ranges + self._night_ranges:
            if t < s:
                return datetime.combine(dt.date(), s)
        return None

    def session_type(self, dt: datetime) -> str:
        """返回 'day' / 'night' / 'closed'。"""
        t = dt.time()
        for s, e in self._day_ranges:
            if s <= t <= e:
                return "day"
        for s, e in self._night_ranges:
            if s <= e:
                if s <= t <= e:
                    return "night"
            else:
                if t >= s or t <= e:
                    return "night"
        return "closed"

    # --- 主力合约映射（简化版） ---

    @staticmethod
    def dominant_contract(symbol: str, dt: Optional[datetime] = None) -> str:
        """
        返回某品种在指定日期的主力合约代码（简化规则）。
        实际生产环境应从交易所或数据服务商获取主力合约映射表。
        """
        symbol = symbol.upper()
        if dt is None:
            dt = datetime.now()
        month = dt.month
        year = dt.year % 100
        if symbol in ("IF", "IC", "IH"):
            return f"{symbol}{year:02d}{month:02d}"
        if symbol in SYMBOL_CONFIGS:
            return f"{symbol}{year:02d}{month:02d}"
        return symbol

    # --- 保证金/手续费计算 ---

    def margin_per_lot(self, price: float) -> float:
        return price * self.spec.lot * self.spec.margin_rate

    def commission(self, price: float, volume: int, close_today: bool = False) -> float:
        rate = self.spec.commission_rate
        if close_today and self.spec.close_today_commission_rate:
            rate = self.spec.close_today_commission_rate
        return price * volume * self.spec.lot * rate

    # --- 批量判断（用于 DataFrame） ---

    def trading_mask(self, index: pd.DatetimeIndex) -> np.ndarray:
        """返回布尔数组，标记 index 中每个时刻是否在交易时段内。"""
        return np.array([self.is_trading_time(t) for t in index])

    def session_mask(self, index: pd.DatetimeIndex, session: str) -> np.ndarray:
        """返回布尔数组，标记 index 中每个时刻是否属于指定 session ('day'/'night')。"""
        return np.array([self.session_type(t) == session for t in index])


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def get_context(symbol: str) -> MarketContext:
    return MarketContext(symbol)


def symbols_in_group(group: str) -> List[str]:
    return SYMBOL_GROUPS.get(group, [])


def all_symbols() -> List[str]:
    return list(SYMBOL_CONFIGS.keys())
