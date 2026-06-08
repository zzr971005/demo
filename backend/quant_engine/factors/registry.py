"""
因子注册8族原语定义
所有原语函数接numpy array pandas Series，返回同长度 numpy array关键循环使用 numba @jit 加速每个原语标注：所属族、参数说明、支持周期(1H/1D))"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from numba import jit

# ---------------------------------------------------------------------------
# 工具函数（numba 加速）
# ---------------------------------------------------------------------------

@jit(nopython=True, cache=False)
def _nb_rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        elif i == w - 1:
            s = 0.0
            for j in range(w):
                s += arr[j]
            out[i] = s / w
        else:
            s = out[i - 1] * w + arr[i] - arr[i - w]
            out[i] = s / w
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        else:
            m = 0.0
            start = i - w + 1
            for j in range(start, i + 1):
                m += arr[j]
            m /= w
            v = 0.0
            for j in range(start, i + 1):
                d = arr[j] - m
                v += d * d
            out[i] = np.sqrt(v / w)
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_max(arr: np.ndarray, window: int) -> np.ndarray:
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        else:
            mx = arr[i - w + 1]
            for j in range(i - w + 2, i + 1):
                if arr[j] > mx:
                    mx = arr[j]
            out[i] = mx
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_min(arr: np.ndarray, window: int) -> np.ndarray:
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        else:
            mn = arr[i - w + 1]
            for j in range(i - w + 2, i + 1):
                if arr[j] < mn:
                    mn = arr[j]
            out[i] = mn
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_sum(arr: np.ndarray, window: int) -> np.ndarray:
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        elif i == w - 1:
            s = 0.0
            for j in range(w):
                s += arr[j]
            out[i] = s
        else:
            out[i] = out[i - 1] + arr[i] - arr[i - w]
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_corr(x: np.ndarray, y: np.ndarray, window: int) -> np.ndarray:
    n = x.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        else:
            sx = 0.0
            sy = 0.0
            start = i - w + 1
            for j in range(start, i + 1):
                sx += x[j]
                sy += y[j]
            mx = sx / w
            my = sy / w
            num = 0.0
            denx = 0.0
            deny = 0.0
            for j in range(start, i + 1):
                dx = x[j] - mx
                dy = y[j] - my
                num += dx * dy
                denx += dx * dx
                deny += dy * dy
            d = np.sqrt(denx * deny)
            out[i] = num / d if d > 1e-12 else 0.0
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_rank(arr: np.ndarray, window: int) -> np.ndarray:
    """返回当前值在滚动窗口中的分位排名 (0~1)"""
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        else:
            cur = arr[i]
            cnt = 0
            eq = 0
            start = i - w + 1
            for j in range(start, i + 1):
                if arr[j] < cur:
                    cnt += 1
                elif arr[j] == cur:
                    eq += 1
            out[i] = (cnt + eq * 0.5) / w
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_skew(arr: np.ndarray, window: int) -> np.ndarray:
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        else:
            m = 0.0
            start = i - w + 1
            for j in range(start, i + 1):
                m += arr[j]
            m /= w
            m2 = 0.0
            m3 = 0.0
            for j in range(start, i + 1):
                d = arr[j] - m
                m2 += d * d
                m3 += d * d * d
            std = np.sqrt(m2 / w)
            out[i] = (m3 / w) / (std ** 3) if std > 1e-12 else 0.0
    return out


@jit(nopython=True, cache=False)
def _nb_rolling_kurt(arr: np.ndarray, window: int) -> np.ndarray:
    n = arr.shape[0]
    out = np.empty(n, dtype=np.float64)
    w = window
    for i in range(n):
        if i < w - 1:
            out[i] = np.nan
        else:
            m = 0.0
            start = i - w + 1
            for j in range(start, i + 1):
                m += arr[j]
            m /= w
            m2 = 0.0
            m4 = 0.0
            for j in range(start, i + 1):
                d = arr[j] - m
                m2 += d * d
                m4 += d * d * d * d
            std2 = m2 / w
            out[i] = (m4 / w) / (std2 * std2) - 3.0 if std2 > 1e-12 else 0.0
    return out


# ---------------------------------------------------------------------------
# 元数据定义
# ---------------------------------------------------------------------------

class PrimitiveFamily(str, Enum):
    MOMENTUM = "F1动量族"
    MEAN_REVERSION = "F2均值回归族"
    VOLATILITY = "F3波动率族"
    PRICE_VOLUME = "F4价量族"
    TERM_STRUCTURE = "F5期限结构族"
    OPEN_INTEREST = "F6持仓量族"
    MICROSTRUCTURE = "F7微观结构族"
    MACRO_PROXY = "F8宏观映射族"


@dataclass
class PrimitiveMeta:
    name: str
    family: PrimitiveFamily
    params: List[Tuple[str, type, Any]]  # (param_name, type, default)
    description: str
    supports: List[str] = field(default_factory=lambda: ["1H", "1D"])
    func: Optional[Callable] = None


# ---------------------------------------------------------------------------
# 注册# ---------------------------------------------------------------------------

FACTOR_REGISTRY: Dict[str, PrimitiveMeta] = {}


def register_primitive(
    name: str,
    family: PrimitiveFamily,
    params: List[Tuple[str, type, Any]],
    description: str,
    supports: Optional[List[str]] = None,
):
    def decorator(func: Callable) -> Callable:
        meta = PrimitiveMeta(
            name=name,
            family=family,
            params=params,
            description=description,
            supports=supports or ["1H", "1D"],
            func=func,
        )
        FACTOR_REGISTRY[name] = meta
        return func

    return decorator


def list_primitives(family: Optional[PrimitiveFamily] = None) -> List[str]:
    if family is None:
        return list(FACTOR_REGISTRY.keys())
    return [k for k, v in FACTOR_REGISTRY.items() if v.family == family]


def _to_array(x: Union[np.ndarray, pd.Series]) -> np.ndarray:
    if isinstance(x, pd.Series):
        return x.to_numpy(dtype=np.float64)
    return np.asarray(x, dtype=np.float64)


# ---------------------------------------------------------------------------
# F1 动量# ---------------------------------------------------------------------------

@register_primitive(
    "ts_return",
    PrimitiveFamily.MOMENTUM,
    [("close", str, "close"), ("window", int, 20)],
    "滚动窗口收益= (current - lag) / lag",
)
def ts_return(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    out = np.empty_like(arr)
    out[:window] = np.nan
    out[window:] = (arr[window:] - arr[:-window]) / (arr[:-window] + 1e-12)
    return out


@register_primitive(
    "ts_corr",
    PrimitiveFamily.MOMENTUM,
    [("close", str, "close"), ("volume", str, "volume"), ("window", int, 20)],
    "收盘价与成交量的滚动相关系数",
)
def ts_corr(
    close: Union[np.ndarray, pd.Series],
    volume: Union[np.ndarray, pd.Series],
    window: int = 20,
) -> np.ndarray:
    c = _to_array(close)
    v = _to_array(volume)
    return _nb_rolling_corr(c, v, window)


@register_primitive(
    "ts_rank",
    PrimitiveFamily.MOMENTUM,
    [("close", str, "close"), ("window", int, 20)],
    "收盘价在滚动窗口中的分位排名 (0~1)",
)
def ts_rank(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    return _nb_rolling_rank(arr, window)


@register_primitive(
    "ts_delta",
    PrimitiveFamily.MOMENTUM,
    [("close", str, "close"), ("window", int, 1)],
    "一阶差= current - lag",
)
def ts_delta(close: Union[np.ndarray, pd.Series], window: int = 1) -> np.ndarray:
    arr = _to_array(close)
    out = np.empty_like(arr)
    out[:window] = np.nan
    out[window:] = arr[window:] - arr[:-window]
    return out


@register_primitive(
    "ts_max",
    PrimitiveFamily.MOMENTUM,
    [("high", str, "high"), ("window", int, 20)],
    "滚动窗口最高价",
)
def ts_max(high: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(high)
    return _nb_rolling_max(arr, window)


@register_primitive(
    "ts_min",
    PrimitiveFamily.MOMENTUM,
    [("low", str, "low"), ("window", int, 20)],
    "滚动窗口最低价",
)
def ts_min(low: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(low)
    return _nb_rolling_min(arr, window)


# ---------------------------------------------------------------------------
# F2 均值回归族
# ---------------------------------------------------------------------------

@register_primitive(
    "zscore",
    PrimitiveFamily.MEAN_REVERSION,
    [("close", str, "close"), ("window", int, 20)],
    "Z-Score = (x - mean) / std",
)
def zscore(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    mean = _nb_rolling_mean(arr, window)
    std = _nb_rolling_std(arr, window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (arr - mean) / (std + 1e-12)


@register_primitive(
    "ts_mean",
    PrimitiveFamily.MEAN_REVERSION,
    [("close", str, "close"), ("window", int, 20)],
    "滚动均值",
)
def ts_mean(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    return _nb_rolling_mean(arr, window)


@register_primitive(
    "ts_std",
    PrimitiveFamily.MEAN_REVERSION,
    [("close", str, "close"), ("window", int, 20)],
    "滚动标准差",
)
def ts_std(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    return _nb_rolling_std(arr, window)


@register_primitive(
    "ts_skew",
    PrimitiveFamily.MEAN_REVERSION,
    [("close", str, "close"), ("window", int, 20)],
    "滚动偏度",
)
def ts_skew(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    return _nb_rolling_skew(arr, window)


@register_primitive(
    "ts_kurt",
    PrimitiveFamily.MEAN_REVERSION,
    [("close", str, "close"), ("window", int, 20)],
    "滚动峰度（超额峰度）",
)
def ts_kurt(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    return _nb_rolling_kurt(arr, window)


@register_primitive(
    "bb_position",
    PrimitiveFamily.MEAN_REVERSION,
    [("close", str, "close"), ("window", int, 20), ("nb_std", float, 2.0)],
    "布林带位= (close - lower) / (upper - lower)",
)
def bb_position(
    close: Union[np.ndarray, pd.Series],
    window: int = 20,
    nb_std: float = 2.0,
) -> np.ndarray:
    arr = _to_array(close)
    mean = _nb_rolling_mean(arr, window)
    std = _nb_rolling_std(arr, window)
    upper = mean + nb_std * std
    lower = mean - nb_std * std
    band = upper - lower
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (arr - lower) / (band + 1e-12)


# ---------------------------------------------------------------------------
# F3 波动率族
# ---------------------------------------------------------------------------

@register_primitive(
    "atr",
    PrimitiveFamily.VOLATILITY,
    [("high", str, "high"), ("low", str, "low"), ("close", str, "close"), ("window", int, 14)],
    "平均真实波幅 ATR",
)
def atr(
    high: Union[np.ndarray, pd.Series],
    low: Union[np.ndarray, pd.Series],
    close: Union[np.ndarray, pd.Series],
    window: int = 14,
) -> np.ndarray:
    h = _to_array(high)
    l = _to_array(low)
    c = _to_array(close)
    tr0 = h - l
    tr1 = np.abs(h - np.roll(c, 1))
    tr2 = np.abs(l - np.roll(c, 1))
    tr = np.maximum(np.maximum(tr0, tr1), tr2)
    tr[0] = tr0[0]
    return _nb_rolling_mean(tr, window)


@register_primitive(
    "ts_volatility",
    PrimitiveFamily.VOLATILITY,
    [("close", str, "close"), ("window", int, 20)],
    "滚动对数收益率标准差（已实现波动率）",
)
def ts_volatility(close: Union[np.ndarray, pd.Series], window: int = 20) -> np.ndarray:
    arr = _to_array(close)
    log_ret = np.empty_like(arr)
    log_ret[0] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        log_ret[1:] = np.log(arr[1:] / (arr[:-1] + 1e-12))
    return _nb_rolling_std(log_ret, window)


@register_primitive(
    "ts_range",
    PrimitiveFamily.VOLATILITY,
    [("high", str, "high"), ("low", str, "low"), ("close", str, "close"), ("window", int, 20)],
    "滚动窗口 (high - low) / close 均值",
)
def ts_range(
    high: Union[np.ndarray, pd.Series],
    low: Union[np.ndarray, pd.Series],
    close: Union[np.ndarray, pd.Series],
    window: int = 20,
) -> np.ndarray:
    h = _to_array(high)
    l = _to_array(low)
    c = _to_array(close)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rng = (h - l) / (c + 1e-12)
    return _nb_rolling_mean(rng, window)


@register_primitive(
    "garman_klass_vol",
    PrimitiveFamily.VOLATILITY,
    [("high", str, "high"), ("low", str, "low"), ("close", str, "close"), ("open_", str, "open"), ("window", int, 20)],
    "Garman-Klass 波动率估计量",
)
def garman_klass_vol(
    high: Union[np.ndarray, pd.Series],
    low: Union[np.ndarray, pd.Series],
    close: Union[np.ndarray, pd.Series],
    open_: Union[np.ndarray, pd.Series],
    window: int = 20,
) -> np.ndarray:
    h = _to_array(high)
    l = _to_array(low)
    c = _to_array(close)
    o = _to_array(open_)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        var = 0.5 * (np.log(h / (l + 1e-12)) ** 2) - (2 * np.log(2) - 1) * (np.log(c / (o + 1e-12)) ** 2)
    var[var < 0] = 0
    return np.sqrt(_nb_rolling_mean(var, window))


# ---------------------------------------------------------------------------
# F4 价量族
# ---------------------------------------------------------------------------

@register_primitive(
    "obv",
    PrimitiveFamily.PRICE_VOLUME,
    [("close", str, "close"), ("volume", str, "volume")],
    "能量OBV = cumsum(sign(delta_close) * volume)",
)
def obv(
    close: Union[np.ndarray, pd.Series],
    volume: Union[np.ndarray, pd.Series],
) -> np.ndarray:
    c = _to_array(close)
    v = _to_array(volume)
    delta = np.empty_like(c)
    delta[0] = np.nan
    delta[1:] = np.diff(c)
    sign = np.sign(delta)
    sign[0] = 0
    return np.cumsum(sign * v)


@register_primitive(
    "vwap_ratio",
    PrimitiveFamily.PRICE_VOLUME,
    [("close", str, "close"), ("volume", str, "volume"), ("window", int, 20)],
    "VWAP 比率 = close / VWAP",
)
def vwap_ratio(
    close: Union[np.ndarray, pd.Series],
    volume: Union[np.ndarray, pd.Series],
    window: int = 20,
) -> np.ndarray:
    c = _to_array(close)
    v = _to_array(volume)
    pv = c * v
    sum_pv = _nb_rolling_sum(pv, window)
    sum_v = _nb_rolling_sum(v, window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        vwap = sum_pv / (sum_v + 1e-12)
    return c / (vwap + 1e-12)


@register_primitive(
    "volume_zscore",
    PrimitiveFamily.PRICE_VOLUME,
    [("volume", str, "volume"), ("window", int, 20)],
    "成交Z-Score",
)
def volume_zscore(
    volume: Union[np.ndarray, pd.Series], window: int = 20
) -> np.ndarray:
    arr = _to_array(volume)
    mean = _nb_rolling_mean(arr, window)
    std = _nb_rolling_std(arr, window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (arr - mean) / (std + 1e-12)


@register_primitive(
    "money_flow",
    PrimitiveFamily.PRICE_VOLUME,
    [("high", str, "high"), ("low", str, "low"), ("close", str, "close"), ("volume", str, "volume"), ("window", int, 20)],
    "资金流量 = 典型价格 * volume 的滚动和",
)
def money_flow(
    high: Union[np.ndarray, pd.Series],
    low: Union[np.ndarray, pd.Series],
    close: Union[np.ndarray, pd.Series],
    volume: Union[np.ndarray, pd.Series],
    window: int = 20,
) -> np.ndarray:
    h = _to_array(high)
    l = _to_array(low)
    c = _to_array(close)
    v = _to_array(volume)
    tp = (h + l + c) / 3.0
    return _nb_rolling_sum(tp * v, window)


# ---------------------------------------------------------------------------
# F5 期限结构族（跨期价差因子，无需现货数据）
# ---------------------------------------------------------------------------

@register_primitive(
    "spread_near_main",
    PrimitiveFamily.TERM_STRUCTURE,
    [("near_close", str, "near_close"), ("main_close", str, "close")],
    "近月与主力价差率 = (近月 - 主力) / 主力，正值表示近月升水",
)
def spread_near_main(
    near_close: Union[np.ndarray, pd.Series],
    main_close: Union[np.ndarray, pd.Series],
) -> np.ndarray:
    n = _to_array(near_close)
    m = _to_array(main_close)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (n - m) / (m + 1e-12)


@register_primitive(
    "spread_far_near",
    PrimitiveFamily.TERM_STRUCTURE,
    [("far_close", str, "far_close"), ("near_close", str, "near_close")],
    "远月与近月价差率 = (远月 - 近月) / 近月，正值表示远月升水",
)
def spread_far_near(
    far_close: Union[np.ndarray, pd.Series],
    near_close: Union[np.ndarray, pd.Series],
) -> np.ndarray:
    f = _to_array(far_close)
    n = _to_array(near_close)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (f - n) / (n + 1e-12)


@register_primitive(
    "term_slope",
    PrimitiveFamily.TERM_STRUCTURE,
    [("far_close", str, "far_close"), ("near_close", str, "near_close"), ("days_diff", int, 30)],
    "期限结构斜率 = (远月 - 近月) / 天数差，每单位时间的价差变化",
)
def term_slope(
    far_close: Union[np.ndarray, pd.Series],
    near_close: Union[np.ndarray, pd.Series],
    days_diff: int = 30,
) -> np.ndarray:
    f = _to_array(far_close)
    n = _to_array(near_close)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (f - n) / (n + 1e-12) / (days_diff + 1e-12)


@register_primitive(
    "roll_yield",
    PrimitiveFamily.TERM_STRUCTURE,
    [("near_close", str, "near_close"), ("main_close", str, "close"), ("days_to_expiry", int, 30)],
    "年化展期收益 = (近月 - 主力) / 主力 / 天数 * 365，正值表示展期盈利",
)
def roll_yield(
    near_close: Union[np.ndarray, pd.Series],
    main_close: Union[np.ndarray, pd.Series],
    days_to_expiry: int = 30,
) -> np.ndarray:
    n = _to_array(near_close)
    m = _to_array(main_close)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ((n - m) / (m + 1e-12)) / (days_to_expiry + 1e-12) * 365.0


@register_primitive(
    "spread_near_far",
    PrimitiveFamily.TERM_STRUCTURE,
    [("near", str, "close"), ("far", str, "close")],
    "远近月价差率 = (远月 - 近月) / 近月（兼容旧接口）",
)
def spread_near_far(
    near: Union[np.ndarray, pd.Series],
    far: Union[np.ndarray, pd.Series],
) -> np.ndarray:
    n = _to_array(near)
    f = _to_array(far)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (f - n) / (n + 1e-12)


# ---------------------------------------------------------------------------
# F6 持仓量族
# ---------------------------------------------------------------------------

@register_primitive(
    "oi_change",
    PrimitiveFamily.OPEN_INTEREST,
    [("open_interest", str, "open_interest"), ("window", int, 5)],
    "持仓量变化率 = (current - lag) / lag",
)
def oi_change(
    open_interest: Union[np.ndarray, pd.Series], window: int = 5
) -> np.ndarray:
    arr = _to_array(open_interest)
    out = np.empty_like(arr)
    out[:window] = np.nan
    out[window:] = (arr[window:] - arr[:-window]) / (arr[:-window] + 1e-12)
    return out


@register_primitive(
    "oi_trend",
    PrimitiveFamily.OPEN_INTEREST,
    [("open_interest", str, "open_interest"), ("window", int, 20)],
    "持仓量趋势 = 当前OI / 滚动均值 - 1",
)
def oi_trend(
    open_interest: Union[np.ndarray, pd.Series], window: int = 20
) -> np.ndarray:
    arr = _to_array(open_interest)
    mean = _nb_rolling_mean(arr, window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return arr / (mean + 1e-12) - 1.0


@register_primitive(
    "oi_price_corr",
    PrimitiveFamily.OPEN_INTEREST,
    [("open_interest", str, "open_interest"), ("close", str, "close"), ("window", int, 20)],
    "持仓量与收盘价的滚动相关系数",
)
def oi_price_corr(
    open_interest: Union[np.ndarray, pd.Series],
    close: Union[np.ndarray, pd.Series],
    window: int = 20,
) -> np.ndarray:
    oi = _to_array(open_interest)
    c = _to_array(close)
    return _nb_rolling_corr(oi, c, window)


# ---------------------------------------------------------------------------
# F7 微观结构族
# ---------------------------------------------------------------------------

@register_primitive(
    "night_gap",
    PrimitiveFamily.MICROSTRUCTURE,
    [("open_", str, "open"), ("close", str, "close")],
    "夜盘跳空 = (今开 - 昨收) / 昨收，支持1H/1D",
)
def night_gap(
    open_: Union[np.ndarray, pd.Series],
    close: Union[np.ndarray, pd.Series],
) -> np.ndarray:
    o = _to_array(open_)
    c = _to_array(close)
    prev_close = np.empty_like(c)
    prev_close[0] = np.nan
    prev_close[1:] = c[:-1]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (o - prev_close) / (prev_close + 1e-12)


@register_primitive(
    "am_pm_gap",
    PrimitiveFamily.MICROSTRUCTURE,
    [("am_close", str, "close"), ("pm_open", str, "open")],
    "午盘跳空 = 下午开盘价 / 上午收盘- 1（需按交易时段传入）",
)
def am_pm_gap(
    am_close: Union[np.ndarray, pd.Series],
    pm_open: Union[np.ndarray, pd.Series],
) -> np.ndarray:
    am = _to_array(am_close)
    pm = _to_array(pm_open)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pm / (am + 1e-12) - 1.0


@register_primitive(
    "intraday_range",
    PrimitiveFamily.MICROSTRUCTURE,
    [("high", str, "high"), ("low", str, "low"), ("open_", str, "open")],
    "日内振幅 = (high - low) / open",
)
def intraday_range(
    high: Union[np.ndarray, pd.Series],
    low: Union[np.ndarray, pd.Series],
    open_: Union[np.ndarray, pd.Series],
) -> np.ndarray:
    h = _to_array(high)
    l = _to_array(low)
    o = _to_array(open_)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return (h - l) / (o + 1e-12)


# ---------------------------------------------------------------------------
# F8 宏观映射族
# ---------------------------------------------------------------------------

@register_primitive(
    "trend_strength",
    PrimitiveFamily.MACRO_PROXY,
    [("close", str, "close"), ("window", int, 20)],
    "趋势强度 = |收益率| / 波动率",
)
def trend_strength(
    close: Union[np.ndarray, pd.Series], window: int = 20
) -> np.ndarray:
    arr = _to_array(close)
    ret = ts_return(arr, window)
    vol = ts_volatility(arr, window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.abs(ret) / (vol + 1e-12)


@register_primitive(
    "vol_regime",
    PrimitiveFamily.MACRO_PROXY,
    [("close", str, "close"), ("window", int, 20), ("threshold", float, 1.5)],
    "波动率状态 = 当前波动 / 历史均值波动率",
)
def vol_regime(
    close: Union[np.ndarray, pd.Series],
    window: int = 20,
    threshold: float = 1.5,
) -> np.ndarray:
    arr = _to_array(close)
    vol = ts_volatility(arr, window)
    mean_vol = _nb_rolling_mean(vol, window)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ratio = vol / (mean_vol + 1e-12)
    return np.where(ratio > threshold, 1.0, np.where(ratio < 1.0 / threshold, -1.0, 0.0))


@register_primitive(
    "momentum_regime",
    PrimitiveFamily.MACRO_PROXY,
    [("close", str, "close"), ("fast", int, 10), ("slow", int, 30)],
    "动量状态 = fast_return - slow_return 的符号",
)
def momentum_regime(
    close: Union[np.ndarray, pd.Series],
    fast: int = 10,
    slow: int = 30,
) -> np.ndarray:
    arr = _to_array(close)
    fast_ret = ts_return(arr, fast)
    slow_ret = ts_return(arr, slow)
    diff = fast_ret - slow_ret
    return np.sign(diff)
