"""
向量化回测引擎 — Numba JIT 加速

输入：因子值序列(numpy array)、参数dict
输出：夏普、Calmar、最大回撤、换手率、交易次数、权益曲线、IC指标

支持：
- 期货开平方向（OPEN/CLOSE/CLOSE_TODAY）
- 保证金计算和占用跟踪
- 多空双向交易
- 1小时K线数据
- IC（信息系数）计算
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from numba import jit
from scipy.stats import pearsonr

from .fee_model import FeeModel, FuturesFeeConfig


# ---------------------------------------------------------------------------
# 常量与枚举
# ---------------------------------------------------------------------------

class Direction(Enum):
    LONG = 1
    SHORT = -1
    FLAT = 0


class OpenClose(Enum):
    OPEN = 1
    CLOSE = 2
    CLOSE_TODAY = 3


# ---------------------------------------------------------------------------
# Numba JIT 核心循环
# ---------------------------------------------------------------------------

@jit(nopython=True, cache=False)
def _nb_backtest_core(
    factor: np.ndarray,
    open_px: np.ndarray,
    high_px: np.ndarray,
    low_px: np.ndarray,
    close_px: np.ndarray,
    upper_threshold: float,
    lower_threshold: float,
    direction_mode: int,  # 0=双向, 1=只多, -1=只空
    max_holding_bars: int,
    use_margin: bool,
    margin_rate: float,
    contract_value_per_lot: float,
    contract_multiplier: float,  # 每手吨数（如螺纹钢=10吨/手）
    fee_open_rate: float,
    fee_close_rate: float,
    fee_close_today_rate: float,
    slippage_ticks: float,
    tick_size: float,
    init_capital: float,
    position_size_pct: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    向量化回测核心循环（Numba JIT 加速）

    Returns
    -------
    equity : np.ndarray — 权益曲线
    positions : np.ndarray — 持仓方向序列 (1=多, -1=空, 0=平)
    trades_pnl : np.ndarray — 每笔交易盈亏
    trades_cost : np.ndarray — 每笔交易成本
    margin_used : np.ndarray — 保证金占用
    turnover : np.ndarray — 成交额序列
    """
    n = len(factor)
    equity = np.empty(n, dtype=np.float64)
    positions = np.empty(n, dtype=np.int8)
    margin_used = np.empty(n, dtype=np.float64)
    turnover = np.empty(n, dtype=np.float64)

    equity[0] = init_capital
    positions[0] = 0
    margin_used[0] = 0.0
    turnover[0] = 0.0

    capital = init_capital
    pos = 0  # 当前持仓方向: 1=多, -1=空, 0=平
    pos_entry_px = 0.0
    pos_entry_bar = 0
    pos_lots = 0

    trades_pnl_list = []
    trades_cost_list = []

    slippage = slippage_ticks * tick_size
    
    for i in range(1, n):
        if np.isnan(factor[i]) or np.isnan(close_px[i]):
            equity[i] = capital
            positions[i] = pos
            margin_used[i] = margin_used[i - 1]
            turnover[i] = 0.0
            continue

        sig = 0
        if factor[i] > upper_threshold:
            sig = 1
        elif factor[i] < lower_threshold:
            sig = -1

        if direction_mode == 1 and sig < 0:
            sig = 0
        elif direction_mode == -1 and sig > 0:
            sig = 0

        exec_px = close_px[i]
        is_last_bar = (i == n - 1)
        holding_bars = i - pos_entry_bar if pos != 0 else 0
        time_exit = (max_holding_bars > 0 and holding_bars >= max_holding_bars)

        # 安全检查：防止 capital 已爆炸导致后续计算失控
        # 阈值从 1e12 降到 1e8：初始 1e6 的资本，增长 100 倍即触发（避免失真扩散）
        if np.isnan(capital) or np.isinf(capital) or capital < -1e8 or capital > 1e8:
            equity[i] = capital if not np.isnan(capital) else 0.0
            positions[i] = pos
            margin_used[i] = 0.0
            turnover[i] = 0.0
            continue

        if pos == 0 and sig != 0:
            # 开仓
            pos = int(sig)
            pos_entry_px = exec_px + slippage * pos
            pos_entry_bar = i
            # 安全检查：防止除以零/极小值导致 pnl 爆炸
            if abs(pos_entry_px) < 1e-6 or margin_rate < 1e-6 or contract_value_per_lot < 1e-6:
                pos = 0
                pos_entry_px = 0.0
                pos_lots = 0
                equity[i] = capital
                positions[i] = 0
                margin_used[i] = 0.0
                turnover[i] = 0.0
                continue
            notional = capital * position_size_pct
            if use_margin:
                pos_lots = int(notional / (contract_value_per_lot * margin_rate))
                margin = pos_lots * contract_value_per_lot * margin_rate
            else:
                pos_lots = int(notional / contract_value_per_lot)
                margin = pos_lots * contract_value_per_lot * margin_rate
            fee = pos_lots * contract_value_per_lot * fee_open_rate
            capital -= fee
            margin_used[i] = margin
            turnover[i] = pos_lots * contract_value_per_lot
            trades_cost_list.append(fee)

        elif pos != 0 and (sig == -pos or time_exit or is_last_bar):
            # 平仓
            exit_px = exec_px - slippage * pos
            # 正确的期货盈亏计算：价差(元/吨) × 每手吨数 × 手数
            # 示例：螺纹钢3500元/吨，每手10吨，涨100元 -> 盈亏 = 100 × 10 × 手数 = 1000元/手
            pnl = pos * (exit_px - pos_entry_px) * pos_lots * contract_multiplier

            if time_exit or is_last_bar:
                fee_rate = fee_close_rate
            else:
                # 判断平今/平昨：简单按持仓时间 < 1天(24根1H线)算平今
                if holding_bars <= 24:
                    fee_rate = fee_close_today_rate
                else:
                    fee_rate = fee_close_rate

            fee = pos_lots * contract_value_per_lot * fee_rate
            capital += pnl - fee
            trades_pnl_list.append(pnl - fee)
            trades_cost_list.append(fee)
            turnover[i] = pos_lots * contract_value_per_lot

            if sig != 0 and not is_last_bar and not time_exit:
                # 反手开仓
                pos = int(sig)
                pos_entry_px = exec_px + slippage * pos
                pos_entry_bar = i
                notional = capital * position_size_pct
                if use_margin:
                    pos_lots = int(notional / (contract_value_per_lot * margin_rate))
                    margin = pos_lots * contract_value_per_lot * margin_rate
                else:
                    pos_lots = int(notional / contract_value_per_lot)
                    margin = pos_lots * contract_value_per_lot * margin_rate
                fee = pos_lots * contract_value_per_lot * fee_open_rate
                capital -= fee
                margin_used[i] = margin
                turnover[i] += pos_lots * contract_value_per_lot
                trades_cost_list.append(fee)
            else:
                pos = 0
                pos_lots = 0
                margin_used[i] = 0.0

        else:
            # 持仓不变
            if pos != 0:
                # 浮动盈亏：价差 × 每手吨数 × 手数
                mtm = pos * (exec_px - pos_entry_px) * pos_lots * contract_multiplier
                margin_used[i] = margin_used[i - 1]
            else:
                mtm = 0.0
                margin_used[i] = 0.0
            turnover[i] = 0.0

        equity[i] = capital
        positions[i] = pos

    trades_pnl = np.array(trades_pnl_list, dtype=np.float64) if trades_pnl_list else np.empty(0, dtype=np.float64)
    trades_cost = np.array(trades_cost_list, dtype=np.float64) if trades_cost_list else np.empty(0, dtype=np.float64)

    return equity, positions, trades_pnl, trades_cost, margin_used, turnover


@jit(nopython=True, cache=False)
def _nb_calculate_metrics(equity: np.ndarray, trades_pnl: np.ndarray, turnover: np.ndarray, margin_used: np.ndarray, risk_free_rate: float, periods_per_year: float) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    计算回测指标（Numba JIT 加速）

    Returns
    -------
    sharpe, calmar, max_dd, turnover_rate, win_rate, avg_trade, total_return, avg_trade_return
    """
    n = len(equity)
    if n < 2 or equity[0] <= 0 or np.isnan(equity[0]) or np.isinf(equity[0]) or np.isnan(equity[-1]) or np.isinf(equity[-1]):
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    returns = np.empty(n - 1, dtype=np.float64)
    for i in range(1, n):
        if np.isnan(equity[i]) or np.isinf(equity[i]) or equity[i - 1] == 0:
            returns[i - 1] = 0.0
        else:
            returns[i - 1] = (equity[i] - equity[i - 1]) / equity[i - 1]

    total_return = (equity[-1] - equity[0]) / equity[0]
    # 不设置封顶，使用真实收益率值

    mean_ret = 0.0
    for i in range(len(returns)):
        mean_ret += returns[i]
    mean_ret /= len(returns)

    var = 0.0
    for i in range(len(returns)):
        d = returns[i] - mean_ret
        var += d * d
    var /= len(returns)
    std_ret = np.sqrt(var)

    # 防止标准差接近0导致夏普爆炸（权益曲线几乎不变时）
    std_ret = max(std_ret, 1e-6)

    # 正确的夏普计算：年化超额收益 / 年化标准差
    annual_excess_ret = mean_ret * periods_per_year - risk_free_rate
    annual_std = std_ret * np.sqrt(periods_per_year)
    sharpe = annual_excess_ret / (annual_std + 1e-12)

    # 限制夏普在合理范围内，防止极端值污染统计
    sharpe = max(-10.0, min(10.0, sharpe))

    # 最大回撤
    peak = equity[0]
    max_dd = 0.0
    for i in range(1, n):
        if equity[i] > peak:
            peak = equity[i]
        dd = (peak - equity[i]) / peak
        if dd > max_dd:
            max_dd = dd

    # Calmar = 年化收益 / 最大回撤
    annual_return = mean_ret * periods_per_year
    calmar = annual_return / (max_dd + 1e-12)
    # 封顶 Calmar，防止极端值污染适应度
    # 从 ±1000 降到 ±100
    calmar = max(-100.0, min(100.0, calmar))

    # 换手率 = 总成交额 / 平均权益
    avg_equity = 0.0
    for i in range(n):
        avg_equity += equity[i]
    avg_equity /= n
    total_turnover = 0.0
    for i in range(n):
        total_turnover += turnover[i]
    turnover_rate = total_turnover / (avg_equity + 1e-12)

    # 胜率
    win_count = 0
    for i in range(len(trades_pnl)):
        if trades_pnl[i] > 0:
            win_count += 1
    win_rate = win_count / len(trades_pnl) if len(trades_pnl) > 0 else 0.0

    # 平均盈亏
    avg_trade = 0.0
    for i in range(len(trades_pnl)):
        avg_trade += trades_pnl[i]
    avg_trade = avg_trade / len(trades_pnl) if len(trades_pnl) > 0 else 0.0

    # 单次交易平均收益率
    total_trades = len(trades_pnl)
    avg_trade_return = total_return / total_trades if total_trades > 0 else 0.0

    return sharpe, calmar, max_dd, turnover_rate, win_rate, avg_trade, total_return, avg_trade_return


def calculate_ic_metrics(
    factor: np.ndarray,
    close_px: np.ndarray,
    windows: List[int] = [4, 24, 168]
) -> Dict[str, Optional[float]]:
    """
    计算IC（信息系数）指标
    
    Parameters
    ----------
    factor : np.ndarray
        因子值序列
    close_px : np.ndarray
        收盘价序列
    windows : List[int]
        IC窗口（小时数），默认[4, 24, 168]
    
    Returns
    -------
    dict with keys: ic_mean_4h, ic_mean_24h, ic_mean_168h, ic_std, ic_ir, ic_half_life
    """
    n = len(factor)
    if n < max(windows) + 10:  # 需要足够的数据点
        return {
            "ic_mean_4h": None,
            "ic_mean_24h": None,
            "ic_mean_168h": None,
            "ic_std": None,
            "ic_ir": None,
            "ic_half_life": None,
        }
    
    # 计算未来收益率
    future_returns = {}
    for window in windows:
        # 未来window小时的收益率
        returns = np.zeros(n)
        for i in range(n - window):
            if close_px[i] > 0 and close_px[i + window] > 0:
                returns[i] = (close_px[i + window] - close_px[i]) / close_px[i]
        future_returns[window] = returns
    
    # 计算各窗口的IC
    ic_values = {}
    for window in windows:
        # 对齐因子值和未来收益率
        aligned_factor = factor[:n - window]
        aligned_returns = future_returns[window][:n - window]
        
        # 过滤NaN值
        valid_mask = ~np.isnan(aligned_factor) & ~np.isnan(aligned_returns)
        if np.sum(valid_mask) < 10:  # 需要至少10个有效数据点
            ic_values[window] = None
        else:
            try:
                ic, _ = pearsonr(aligned_factor[valid_mask], aligned_returns[valid_mask])
                ic_values[window] = ic
            except:
                ic_values[window] = None
    
    # 计算IC均值（加权）
    weights = {4: 0.5, 24: 0.3, 168: 0.2}
    valid_ics = [ic_values[w] for w in windows if ic_values[w] is not None]
    if not valid_ics:
        ic_mean = None
        ic_std = None
        ic_ir = None
    else:
        ic_mean = sum(ic_values[w] * weights.get(w, 0) for w in windows if ic_values[w] is not None)
        ic_std = np.std(valid_ics) if len(valid_ics) > 1 else 0.0
        ic_ir = ic_mean / (ic_std + 1e-12) if ic_std > 0 else 0.0
    
    # 计算IC半衰期
    ic_half_life = calculate_ic_half_life(factor, close_px)
    
    return {
        "ic_mean_4h": ic_values.get(4),
        "ic_mean_24h": ic_values.get(24),
        "ic_mean_168h": ic_values.get(168),
        "ic_std": ic_std,
        "ic_ir": ic_ir,
        "ic_half_life": ic_half_life,
    }


def calculate_ic_half_life(
    factor: np.ndarray,
    close_px: np.ndarray,
    max_lags: int = 10
) -> Optional[int]:
    """
    计算IC半衰期
    
    Parameters
    ----------
    factor : np.ndarray
        因子值序列
    close_px : np.ndarray
        收盘价序列
    max_lags : int
        最大滞后期数
    
    Returns
    -------
    半衰期（期数），如果无法计算则返回None
    """
    n = len(factor)
    if n < max_lags + 20:
        return None
    
    # 计算未来1期收益率
    future_returns = np.zeros(n)
    for i in range(n - 1):
        if close_px[i] > 0 and close_px[i + 1] > 0:
            future_returns[i] = (close_px[i + 1] - close_px[i]) / close_px[i]
    
    # 计算不同滞后期IC
    ic_decay = []
    for lag in range(max_lags + 1):
        aligned_factor = factor[:n - lag - 1]
        aligned_returns = future_returns[lag + 1:n]
        
        valid_mask = ~np.isnan(aligned_factor) & ~np.isnan(aligned_returns)
        if np.sum(valid_mask) < 10:
            ic_decay.append(None)
        else:
            try:
                ic, _ = pearsonr(aligned_factor[valid_mask], aligned_returns[valid_mask])
                ic_decay.append(ic)
            except:
                ic_decay.append(None)
    
    # 找到IC下降到一半的期数
    if ic_decay[0] is None or ic_decay[0] == 0:
        return None
    
    half_ic = ic_decay[0] / 2
    for lag in range(1, len(ic_decay)):
        if ic_decay[lag] is not None and abs(ic_decay[lag]) < abs(half_ic):
            return lag
    
    return max_lags  # 如果在max_lags内未降到一半，返回max_lags


# ---------------------------------------------------------------------------
# 回测结果数据结构
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    """回测结果"""

    sharpe: float
    calmar: float
    max_drawdown: float
    turnover_rate: float
    total_trades: int
    win_rate: float
    avg_trade_pnl: float
    total_return: float
    avg_trade_return: float
    equity_curve: np.ndarray
    positions: np.ndarray
    trades_pnl: np.ndarray
    trades_cost: np.ndarray
    margin_used: np.ndarray
    turnover: np.ndarray
    params: Dict[str, Any] = field(default_factory=dict)
    
    # IC相关指标
    ic_mean_4h: Optional[float] = None
    ic_mean_24h: Optional[float] = None
    ic_mean_168h: Optional[float] = None
    ic_std: Optional[float] = None
    ic_ir: Optional[float] = None
    ic_half_life: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sharpe": float(self.sharpe),
            "calmar": float(self.calmar),
            "max_drawdown": float(self.max_drawdown),
            "turnover_rate": float(self.turnover_rate),
            "total_trades": int(self.total_trades),
            "win_rate": float(self.win_rate),
            "avg_trade_pnl": float(self.avg_trade_pnl),
            "total_return": float(self.total_return),
            "params": self.params,
            "ic_mean_4h": self.ic_mean_4h,
            "ic_mean_24h": self.ic_mean_24h,
            "ic_mean_168h": self.ic_mean_168h,
            "ic_std": self.ic_std,
            "ic_ir": self.ic_ir,
            "ic_half_life": self.ic_half_life,
        }


# ---------------------------------------------------------------------------
# 回测引擎
# ---------------------------------------------------------------------------

class VectorizedBacktestEngine:
    """
    向量化回测引擎

    Parameters
    ----------
    fee_model : FeeModel
        手续费模型
    init_capital : float
        初始资金
    risk_free_rate : float
        无风险利率（年化）
    periods_per_year : float
        每年周期数（1H数据约为 252*5=1260 或 365*24=8760）
    """

    def __init__(
        self,
        fee_model: Optional[FeeModel] = None,
        init_capital: float = 1_000_000.0,
        risk_free_rate: float = 0.03,
        periods_per_year: float = 252 * 5,  # 1H 数据，每天约5根有效K线
    ):
        self.fee_model = fee_model or FeeModel()
        self.init_capital = init_capital
        self.risk_free_rate = risk_free_rate
        self.periods_per_year = periods_per_year

    def run(
        self,
        factor: np.ndarray,
        open_px: np.ndarray,
        high_px: np.ndarray,
        low_px: np.ndarray,
        close_px: np.ndarray,
        params: Dict[str, Any],
        symbol: str = "RB",
    ) -> BacktestResult:
        """
        执行向量化回测

        Parameters
        ----------
        factor : np.ndarray
            因子值序列，正=看多信号强度，负=看空信号强度
        open_px, high_px, low_px, close_px : np.ndarray
            OHLC 价格序列
        params : dict
            回测参数字典：
            - upper_threshold: 做多阈值（默认 0.5）
            - lower_threshold: 做空阈值（默认 -0.5）
            - direction_mode: 0=双向, 1=只多, -1=只空（默认 0）
            - max_holding_bars: 最大持仓K线数，0=不限（默认 0）
            - position_size_pct: 仓位比例（默认 0.95）
            - contract_value_per_lot: 每手合约名义价值（默认 50000）
            - tick_size: 最小变动价位（默认 1.0）
            - slippage_ticks: 滑点tick数（默认 1）
            - use_margin: 是否使用保证金（默认 True）
            - margin_rate: 保证金率（默认 0.12）
        symbol : str
            品种代码，用于手续费查询

        Returns
        -------
        BacktestResult
        """
        factor = np.asarray(factor, dtype=np.float64)
        open_px = np.asarray(open_px, dtype=np.float64)
        high_px = np.asarray(high_px, dtype=np.float64)
        low_px = np.asarray(low_px, dtype=np.float64)
        close_px = np.asarray(close_px, dtype=np.float64)

        n = len(factor)
        assert len(open_px) == n and len(high_px) == n and len(low_px) == n and len(close_px) == n

        # 提前检查因子值有效性
        if np.all(np.isnan(factor)):
            # 因子值全为NaN，返回无效结果
            return BacktestResult(
                sharpe=0.0,
                calmar=0.0,
                max_drawdown=0.0,
                turnover_rate=0.0,
                total_trades=0,
                win_rate=0.0,
                avg_trade_pnl=0.0,
                total_return=0.0,
                avg_trade_return=0.0,
                equity_curve=np.full(n, self.init_capital, dtype=np.float64),
                positions=np.zeros(n, dtype=np.int8),
                trades_pnl=np.empty(0, dtype=np.float64),
                trades_cost=np.empty(0, dtype=np.float64),
                margin_used=np.zeros(n, dtype=np.float64),
                turnover=np.zeros(n, dtype=np.float64),
                params=params,
            )

        upper_threshold = params.get("upper_threshold", 0.5)
        lower_threshold = params.get("lower_threshold", -0.5)
        direction_mode = params.get("direction_mode", 0)
        max_holding_bars = params.get("max_holding_bars", 0)
        position_size_pct = params.get("position_size_pct", 0.95)
        contract_value_per_lot = params.get("contract_value_per_lot", 50000.0)
        # 合约乘数（每手吨数），默认10吨（螺纹钢等大多数商品期货）
        contract_multiplier = params.get("contract_multiplier", 10.0)
        tick_size = params.get("tick_size", 1.0)
        slippage_ticks = params.get("slippage_ticks", 1)
        use_margin = params.get("use_margin", True)
        margin_rate = params.get("margin_rate", 0.12)

        # 获取手续费配置
        fee_cfg = self.fee_model.get_config(symbol)
        fee_open_rate = fee_cfg.open_rate
        fee_close_rate = fee_cfg.close_rate
        fee_close_today_rate = fee_cfg.close_today_rate

        equity, positions, trades_pnl, trades_cost, margin_used, turnover = _nb_backtest_core(
            factor, open_px, high_px, low_px, close_px,
            float(upper_threshold),
            float(lower_threshold),
            int(direction_mode),
            int(max_holding_bars),
            bool(use_margin),
            float(margin_rate),
            float(contract_value_per_lot),
            float(contract_multiplier),
            float(fee_open_rate),
            float(fee_close_rate),
            float(fee_close_today_rate),
            float(slippage_ticks),
            float(tick_size),
            float(self.init_capital),
            float(position_size_pct),
        )

        sharpe, calmar, max_dd, turnover_rate, win_rate, avg_trade, total_return, avg_trade_return = _nb_calculate_metrics(
            equity, trades_pnl, turnover, margin_used,
            float(self.risk_free_rate),
            float(self.periods_per_year),
        )

        # 计算IC指标
        ic_metrics = calculate_ic_metrics(factor, close_px)

        return BacktestResult(
            sharpe=float(sharpe),
            calmar=float(calmar),
            max_drawdown=float(max_dd),
            turnover_rate=float(turnover_rate),
            total_trades=len(trades_pnl),
            win_rate=float(win_rate),
            avg_trade_pnl=float(avg_trade),
            total_return=float(total_return),
            avg_trade_return=float(avg_trade_return),
            equity_curve=equity,
            positions=positions,
            trades_pnl=trades_pnl,
            trades_cost=trades_cost,
            margin_used=margin_used,
            turnover=turnover,
            params=params,
            ic_mean_4h=ic_metrics["ic_mean_4h"],
            ic_mean_24h=ic_metrics["ic_mean_24h"],
            ic_mean_168h=ic_metrics["ic_mean_168h"],
            ic_std=ic_metrics["ic_std"],
            ic_ir=ic_metrics["ic_ir"],
            ic_half_life=ic_metrics["ic_half_life"],
        )

    def run_batch(
        self,
        factor_dict: Dict[str, np.ndarray],
        ohlcv_dict: Dict[str, Dict[str, np.ndarray]],
        params: Dict[str, Any],
    ) -> Dict[str, BacktestResult]:
        """
        批量回测多个品种

        Parameters
        ----------
        factor_dict : dict[str, np.ndarray]
            各品种因子序列
        ohlcv_dict : dict[str, dict[str, np.ndarray]]
            各品种 OHLCV 数据，格式 {symbol: {"open": ..., "high": ..., "low": ..., "close": ...}}
        params : dict
            回测参数

        Returns
        -------
        dict[str, BacktestResult]
        """
        results = {}
        for symbol, factor in factor_dict.items():
            ohlcv = ohlcv_dict.get(symbol)
            if ohlcv is None:
                continue
            result = self.run(
                factor=factor,
                open_px=ohlcv["open"],
                high_px=ohlcv["high"],
                low_px=ohlcv["low"],
                close_px=ohlcv["close"],
                params=params,
                symbol=symbol,
            )
            results[symbol] = result
        return results
