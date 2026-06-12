"""
策略规格定义 — 标准化策略接口与参数契约

定义：
- 策略输入/输出规格
- 参数类型与范围约束
- 信号生成接口
- 仓位计算接口
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 枚举定义
# ---------------------------------------------------------------------------

class SignalDirection(Enum):
    LONG = 1
    SHORT = -1
    FLAT = 0


class PositionAction(Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    CLOSE_TODAY = "CLOSE_TODAY"
    HOLD = "HOLD"
    REVERSE = "REVERSE"


class StrategyRegime(Enum):
    TREND = "TREND"
    BAND = "BAND"
    REVERSAL = "REVERSAL"
    ALL = "ALL"


# ---------------------------------------------------------------------------
# 数据规格
# ---------------------------------------------------------------------------

@dataclass
class MarketDataSnapshot:
    """市场数据快照"""

    symbol: str
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: Optional[int] = None

    @classmethod
    def from_series(cls, symbol: str, series: pd.Series) -> "MarketDataSnapshot":
        return cls(
            symbol=symbol,
            timestamp=series.name if isinstance(series.name, pd.Timestamp) else pd.Timestamp.now(),
            open=float(series["open"]),
            high=float(series["high"]),
            low=float(series["low"]),
            close=float(series["close"]),
            volume=int(series["volume"]),
            open_interest=int(series["open_interest"]) if "open_interest" in series else None,
        )


@dataclass
class FactorSnapshot:
    """因子值快照"""

    symbol: str
    timestamp: pd.Timestamp
    factor_name: str
    value: float
    generation: Optional[int] = None
    candidate_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 信号规格
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    """交易信号"""

    candidate_id: str
    symbol: str
    direction: SignalDirection
    strength: float  # 信号强度 [-1, 1]
    timestamp: pd.Timestamp
    regime: StrategyRegime = StrategyRegime.ALL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return -1.0 <= self.strength <= 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "direction": self.direction.name,
            "strength": round(self.strength, 4),
            "timestamp": self.timestamp.isoformat(),
            "regime": self.regime.value,
            "metadata": self.metadata,
        }


@dataclass
class PositionIntent:
    """仓位意图 — 策略层发出的原始交易意图"""

    candidate_id: str
    symbol: str
    target_direction: SignalDirection
    target_lots: int
    action: PositionAction
    timestamp: pd.Timestamp
    reason: str = ""
    urgency: str = "normal"  # normal | urgent
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "target_direction": self.target_direction.name,
            "target_lots": self.target_lots,
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "urgency": self.urgency,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# 策略规格协议
# ---------------------------------------------------------------------------

class StrategySpec(Protocol):
    """策略规格协议 — 所有策略必须实现的接口"""

    candidate_id: str
    symbol: str
    regime: StrategyRegime

    def generate_signal(
        self,
        data: pd.DataFrame,
        factor_values: Optional[np.ndarray] = None,
    ) -> Signal:
        """生成交易信号。"""
        ...

    def calculate_position(
        self,
        signal: Signal,
        current_capital: float,
        current_position_lots: int,
        symbol_config: Dict[str, Any],
    ) -> PositionIntent:
        """根据信号计算目标仓位。"""
        ...

    def get_params(self) -> Dict[str, Any]:
        """获取策略参数。"""
        ...

    def set_params(self, params: Dict[str, Any]) -> None:
        """设置策略参数。"""
        ...


# ---------------------------------------------------------------------------
# 参数约束
# ---------------------------------------------------------------------------

@dataclass
class ParamConstraint:
    """参数约束定义"""

    name: str
    type: str  # int | float | bool | str | choice
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[List[Any]] = None
    description: str = ""

    def validate(self, value: Any) -> Tuple[bool, str]:
        """验证参数值是否合法。"""
        if self.type == "int":
            if not isinstance(value, int):
                return False, f"{self.name} 必须是整数"
            if self.min_value is not None and value < self.min_value:
                return False, f"{self.name} 必须 ≥ {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"{self.name} 必须 ≤ {self.max_value}"
        elif self.type == "float":
            if not isinstance(value, (int, float)):
                return False, f"{self.name} 必须是数值"
            if self.min_value is not None and value < self.min_value:
                return False, f"{self.name} 必须 ≥ {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"{self.name} 必须 ≤ {self.max_value}"
        elif self.type == "bool":
            if not isinstance(value, bool):
                return False, f"{self.name} 必须是布尔值"
        elif self.type == "choice":
            if self.choices is not None and value not in self.choices:
                return False, f"{self.name} 必须是 {self.choices} 之一"
        return True, ""


@dataclass
class StrategyTemplate:
    """策略模板 — 定义一类策略的参数约束和默认配置"""

    name: str
    description: str
    family: str
    regime: StrategyRegime
    constraints: List[ParamConstraint] = field(default_factory=list)
    default_params: Dict[str, Any] = field(default_factory=dict)

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证参数字典。"""
        errors = []
        for c in self.constraints:
            value = params.get(c.name, c.default)
            ok, msg = c.validate(value)
            if not ok:
                errors.append(msg)
        return len(errors) == 0, errors

    def merge_params(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """合并默认参数和用户覆盖参数。"""
        merged = dict(self.default_params)
        if overrides:
            merged.update(overrides)
        return merged


# ---------------------------------------------------------------------------
# 内置策略模板
# ---------------------------------------------------------------------------

TREND_FOLLOWING_TEMPLATE = StrategyTemplate(
    name="trend_following",
    description="趋势跟踪策略 — 基于因子阈值产生多空信号",
    family="momentum",
    regime=StrategyRegime.TREND,
    constraints=[
        ParamConstraint("upper_threshold", "float", 0.5, 0.0, 5.0, description="做多阈值"),
        ParamConstraint("lower_threshold", "float", -0.5, -5.0, 0.0, description="做空阈值"),
        ParamConstraint("max_holding_bars", "int", 0, 0, 1000, description="最大持仓K线数"),
        ParamConstraint("position_size_pct", "float", 0.95, 0.1, 1.0, description="仓位比例"),
        ParamConstraint("direction_mode", "choice", 0, choices=[0, 1, -1], description="方向模式"),
    ],
    default_params={
        "upper_threshold": 0.5,
        "lower_threshold": -0.5,
        "max_holding_bars": 0,
        "position_size_pct": 0.95,
        "direction_mode": 0,
    },
)

MEAN_REVERSION_TEMPLATE = StrategyTemplate(
    name="mean_reversion",
    description="均值回归策略 — 因子偏离均值时反向交易",
    family="mean_reversion",
    regime=StrategyRegime.BAND,
    constraints=[
        ParamConstraint("lookback", "int", 20, 5, 100, description="回看周期"),
        ParamConstraint("zscore_threshold", "float", 2.0, 0.5, 5.0, description="ZScore阈值"),
        ParamConstraint("position_size_pct", "float", 0.5, 0.1, 1.0, description="仓位比例"),
    ],
    default_params={
        "lookback": 20,
        "zscore_threshold": 2.0,
        "position_size_pct": 0.5,
    },
)

VOLATILITY_BREAKOUT_TEMPLATE = StrategyTemplate(
    name="volatility_breakout",
    description="波动率突破策略",
    family="volatility",
    regime=StrategyRegime.TREND,
    constraints=[
        ParamConstraint("atr_period", "int", 14, 5, 50, description="ATR周期"),
        ParamConstraint("atr_multiplier", "float", 2.0, 0.5, 5.0, description="ATR乘数"),
        ParamConstraint("position_size_pct", "float", 0.5, 0.1, 1.0, description="仓位比例"),
    ],
    default_params={
        "atr_period": 14,
        "atr_multiplier": 2.0,
        "position_size_pct": 0.5,
    },
)

STRATEGY_TEMPLATES: Dict[str, StrategyTemplate] = {
    "trend_following": TREND_FOLLOWING_TEMPLATE,
    "mean_reversion": MEAN_REVERSION_TEMPLATE,
    "volatility_breakout": VOLATILITY_BREAKOUT_TEMPLATE,
}


def get_template(name: str) -> Optional[StrategyTemplate]:
    """获取策略模板。"""
    return STRATEGY_TEMPLATES.get(name)


def list_templates() -> List[str]:
    """列出所有可用模板。"""
    return list(STRATEGY_TEMPLATES.keys())
