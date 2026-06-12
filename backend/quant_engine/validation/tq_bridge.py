"""
天勤回测桥接 — TqSdk BacktestClient 封装

功能：
- 将系统生成的交易信号转换为天勤回测
- 与向量化回测结果交叉验证
- 差异>5%时告警
- 支持主力合约自动换月
- 支持模拟盘运行

与 validation/engine.py 的 BacktestResult 格式对齐，
与 data/source.py 的 TqDataSource 配合使用。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ..data.source import TqDataSource, get_main_contract
from .engine import BacktestResult, VectorizedBacktestEngine
from .fee_model import FeeModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DIFF_ALERT_THRESHOLD = 0.05  # 差异告警阈值 5%

# 品种交易所映射（与 data/source.py 保持一致）
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


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TqTradeRecord:
    """天勤回测交易记录"""

    trade_id: str
    symbol: str
    direction: str  # BUY / SELL
    offset: str  # OPEN / CLOSE / CLOSE_TODAY
    volume: int
    price: float
    trade_time: pd.Timestamp
    commission: float = 0.0
    pnl: float = 0.0


@dataclass
class TqBacktestState:
    """天勤回测中间状态"""

    datetime: pd.DatetimeIndex
    equity: np.ndarray
    positions: np.ndarray
    trades: List[TqTradeRecord] = field(default_factory=list)
    margin_used: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class CrossValidationReport:
    """交叉验证差异报告"""

    vector_result: BacktestResult
    tq_result: BacktestResult
    diff: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector_metrics": self.vector_result.to_dict(),
            "tq_metrics": self.tq_result.to_dict(),
            "diff": self.diff,
            "alerts": self.alerts,
            "passed": self.passed,
        }


# ---------------------------------------------------------------------------
# 信号转换器
# ---------------------------------------------------------------------------

class SignalConverter:
    """
    将系统因子信号序列转换为天勤交易指令

    因子值 > upper_threshold → 做多（BUY OPEN）
    因子值 < lower_threshold → 做空（SELL OPEN）
    方向反转时先平仓再开仓
    """

    def __init__(
        self,
        upper_threshold: float = 0.5,
        lower_threshold: float = -0.5,
        direction_mode: int = 0,  # 0=双向, 1=只多, -1=只空
        max_holding_bars: int = 0,
        position_size_pct: float = 0.95,
        contract_value_per_lot: float = 50000.0,
        use_margin: bool = True,
        margin_rate: float = 0.12,
    ):
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold
        self.direction_mode = direction_mode
        self.max_holding_bars = max_holding_bars
        self.position_size_pct = position_size_pct
        self.contract_value_per_lot = contract_value_per_lot
        self.use_margin = use_margin
        self.margin_rate = margin_rate

    def convert(
        self,
        factor: np.ndarray,
        close_px: np.ndarray,
        init_capital: float = 1_000_000.0,
    ) -> List[Dict[str, Any]]:
        """
        将因子序列转换为交易指令列表

        Returns
        -------
        list[dict] — 每条指令包含 symbol, direction, offset, volume, price, bar_idx
        """
        n = len(factor)
        orders = []
        pos = 0
        pos_entry_bar = 0
        capital = init_capital

        for i in range(1, n):
            # T-1 截断：用上一根 K 线的因子值决策，避免与向量化引擎不一致的前视偏差
            signal_factor = factor[i - 1]
            if np.isnan(signal_factor) or np.isnan(close_px[i]):
                continue

            sig = 0
            if signal_factor > self.upper_threshold:
                sig = 1
            elif signal_factor < self.lower_threshold:
                sig = -1

            if self.direction_mode == 1 and sig < 0:
                sig = 0
            elif self.direction_mode == -1 and sig > 0:
                sig = 0

            exec_px = close_px[i]
            is_last_bar = i == n - 1
            holding_bars = i - pos_entry_bar if pos != 0 else 0
            time_exit = self.max_holding_bars > 0 and holding_bars >= self.max_holding_bars

            if pos == 0 and sig != 0:
                # 开仓
                lots = self._calc_lots(capital)
                direction = "BUY" if sig > 0 else "SELL"
                orders.append({
                    "bar_idx": i,
                    "direction": direction,
                    "offset": "OPEN",
                    "volume": lots,
                    "price": exec_px,
                    "action": "open",
                })
                pos = int(sig)
                pos_entry_bar = i

            elif pos != 0 and (sig == -pos or time_exit or is_last_bar):
                # 平仓
                close_direction = "SELL" if pos > 0 else "BUY"
                lots = self._calc_lots(capital)
                offset = "CLOSE_TODAY" if holding_bars <= 24 else "CLOSE"
                orders.append({
                    "bar_idx": i,
                    "direction": close_direction,
                    "offset": offset,
                    "volume": lots,
                    "price": exec_px,
                    "action": "close",
                })

                if sig != 0 and not is_last_bar and not time_exit:
                    # 反手开仓
                    direction = "BUY" if sig > 0 else "SELL"
                    orders.append({
                        "bar_idx": i,
                        "direction": direction,
                        "offset": "OPEN",
                        "volume": lots,
                        "price": exec_px,
                        "action": "open",
                    })
                    pos = int(sig)
                    pos_entry_bar = i
                else:
                    pos = 0

        return orders

    def _calc_lots(self, capital: float) -> int:
        notional = capital * self.position_size_pct
        if self.use_margin:
            lots = int(notional / (self.contract_value_per_lot * self.margin_rate))
        else:
            lots = int(notional / self.contract_value_per_lot)
        return max(lots, 1)


# ---------------------------------------------------------------------------
# 天勤回测桥接引擎
# ---------------------------------------------------------------------------

class TqBacktestBridge:
    """
    天勤回测桥接引擎

    封装天勤 TqSdk 的 BacktestClient，
    将系统生成的交易信号转换为天勤回测，
    并与向量化回测结果进行交叉验证。

    Parameters
    ----------
    start_dt : str or Timestamp
        回测开始时间
    end_dt : str or Timestamp
        回测结束时间
    init_capital : float
        初始资金
    fee_model : FeeModel
        手续费模型
    account : str, optional
        天勤账号
    password : str, optional
        天勤密码
    sim : bool
        是否使用模拟盘（默认True）
    """

    def __init__(
        self,
        start_dt: Union[str, pd.Timestamp],
        end_dt: Union[str, pd.Timestamp],
        init_capital: float = 1_000_000.0,
        fee_model: Optional[FeeModel] = None,
        account: Optional[str] = None,
        password: Optional[str] = None,
        sim: bool = True,
    ):
        self.start_dt = pd.Timestamp(start_dt)
        self.end_dt = pd.Timestamp(end_dt)
        self.init_capital = init_capital
        self.fee_model = fee_model or FeeModel()
        self.account = account
        self.password = password
        self.sim = sim
        self._api = None
        self._data_source: Optional[TqDataSource] = None

    # ------------------------------------------------------------------
    # 天勤API初始化
    # ------------------------------------------------------------------

    def _init_api(self, backtest: bool = True):
        """初始化天勤API（回测模式或模拟盘模式）"""
        try:
            from tqsdk import TqApi, TqAuth, TqSim, TqBacktest
        except ImportError as exc:
            raise ImportError("tqsdk 未安装，请执行: pip install tqsdk") from exc

        auth = None
        if self.account and self.password:
            auth = TqAuth(self.account, self.password)

        if backtest:
            backtest_cfg = TqBacktest(
                start_dt=self.start_dt.to_pydatetime(),
                end_dt=self.end_dt.to_pydatetime(),
            )
            self._api = TqApi(
                account=TqSim(init_balance=self.init_capital),
                auth=auth,
                backtest=backtest_cfg,
            )
        else:
            self._api = TqApi(auth=auth)

        self._data_source = TqDataSource(
            account=self.account,
            password=self.password,
            sim=self.sim,
        )
        self._data_source._api = self._api
        return self._api

    # ------------------------------------------------------------------
    # 核心：天勤回测执行
    # ------------------------------------------------------------------

    def run_backtest(
        self,
        symbol: str,
        factor: np.ndarray,
        ohlcv: Dict[str, np.ndarray],
        params: Dict[str, Any],
    ) -> BacktestResult:
        """
        使用天勤SDK执行回测

        Parameters
        ----------
        symbol : str
            品种代码
        factor : np.ndarray
            因子值序列
        ohlcv : dict[str, np.ndarray]
            OHLCV数据
        params : dict
            回测参数（与 VectorizedBacktestEngine.run 兼容）

        Returns
        -------
        BacktestResult
        """
        api = self._init_api(backtest=True)
        tq_symbol = get_main_contract(symbol)

        # 订阅K线
        duration_seconds = params.get("duration_seconds", 3600)
        klines = api.get_kline_serial(tq_symbol, duration_seconds)

        # 等待K线数据就绪
        deadline = self.end_dt + pd.Timedelta(days=1)
        while True:
            api.wait_update(deadline=deadline)
            if not klines.empty:
                break
            if pd.Timestamp(api._get_current_datetime()) >= deadline:
                raise TimeoutError(f"天勤回测K线数据超时: {tq_symbol}")

        # 信号转换
        converter = SignalConverter(
            upper_threshold=params.get("upper_threshold", 0.5),
            lower_threshold=params.get("lower_threshold", -0.5),
            direction_mode=params.get("direction_mode", 0),
            max_holding_bars=params.get("max_holding_bars", 0),
            position_size_pct=params.get("position_size_pct", 0.95),
            contract_value_per_lot=params.get("contract_value_per_lot", 50000.0),
            use_margin=params.get("use_margin", True),
            margin_rate=params.get("margin_rate", 0.12),
        )

        close_px = ohlcv.get("close", np.array([]))
        orders = converter.convert(factor, close_px, self.init_capital)

        # 执行交易指令
        trade_records: List[TqTradeRecord] = []
        equity_curve: List[float] = [self.init_capital]
        positions_arr: List[int] = [0]
        margin_arr: List[float] = [0.0]

        current_pos = 0
        entry_price = 0.0
        entry_bar = 0

        for order in orders:
            bar_idx = order["bar_idx"]
            direction = order["direction"]
            offset = order["offset"]
            volume = order["volume"]
            price = order["price"]

            # 天勤下单
            tq_direction = direction  # BUY / SELL
            tq_offset = offset  # OPEN / CLOSE / CLOSE_TODAY

            try:
                tq_order = api.insert_order(
                    symbol=tq_symbol,
                    direction=tq_direction,
                    offset=tq_offset,
                    volume=volume,
                    limit_price=price,
                )
                # 等待成交
                while tq_order.status != "FINISHED":
                    api.wait_update()
            except Exception as exc:
                logger.error(f"天勤下单失败: {exc}")
                continue

            # 记录交易
            commission = sum(tq_order.trade_records.get(t, {}).get("commission", 0) for t in tq_order.trade_records) if hasattr(tq_order, "trade_records") else 0.0
            record = TqTradeRecord(
                trade_id=tq_order.order_id,
                symbol=tq_symbol,
                direction=direction,
                offset=offset,
                volume=volume,
                price=price,
                trade_time=pd.Timestamp(api._get_current_datetime()),
                commission=commission,
            )
            trade_records.append(record)

            # 更新持仓状态
            if offset == "OPEN":
                current_pos = volume if direction == "BUY" else -volume
                entry_price = price
                entry_bar = bar_idx
            else:
                if current_pos != 0:
                    pnl = current_pos * (price - entry_price) * volume * params.get("contract_value_per_lot", 50000.0) if entry_price != 0 else 0.0
                    record.pnl = pnl
                current_pos = 0

            # 更新权益曲线（简化：用close_px近似）
            if bar_idx < len(close_px):
                account = api.get_account()
                equity_curve.append(account.balance)
                positions_arr.append(current_pos)
                margin_arr.append(account.margin)
            else:
                equity_curve.append(equity_curve[-1])
                positions_arr.append(current_pos)
                margin_arr.append(0.0)

        # 补齐权益曲线长度
        target_len = len(factor)
        while len(equity_curve) < target_len:
            equity_curve.append(equity_curve[-1])
            positions_arr.append(positions_arr[-1])
            margin_arr.append(margin_arr[-1])

        equity = np.array(equity_curve[:target_len], dtype=np.float64)
        positions = np.array(positions_arr[:target_len], dtype=np.int8)
        margin_used = np.array(margin_arr[:target_len], dtype=np.float64)

        # 计算交易盈亏
        trades_pnl = np.array([t.pnl for t in trade_records], dtype=np.float64)
        trades_cost = np.array([t.commission for t in trade_records], dtype=np.float64)
        turnover = np.zeros(target_len, dtype=np.float64)
        for t in trade_records:
            if t.bar_idx < target_len:
                turnover[t.bar_idx] += t.volume * params.get("contract_value_per_lot", 50000.0)

        # 计算指标（复用 engine.py 的指标计算逻辑）
        from .engine import _nb_calculate_metrics
        risk_free_rate = params.get("risk_free_rate", 0.03)
        periods_per_year = params.get("periods_per_year", 252 * 5)

        sharpe, calmar, max_dd, turnover_rate, win_rate, avg_trade, total_return = _nb_calculate_metrics(
            equity, trades_pnl, turnover, margin_used, risk_free_rate, periods_per_year
        )

        result = BacktestResult(
            sharpe=float(sharpe),
            calmar=float(calmar),
            max_drawdown=float(max_dd),
            turnover_rate=float(turnover_rate),
            total_trades=len(trade_records),
            win_rate=float(win_rate),
            avg_trade_pnl=float(avg_trade),
            total_return=float(total_return),
            equity_curve=equity,
            positions=positions,
            trades_pnl=trades_pnl,
            trades_cost=trades_cost,
            margin_used=margin_used,
            turnover=turnover,
            params=params,
        )

        api.close()
        self._api = None
        return result

    # ------------------------------------------------------------------
    # 交叉验证
    # ------------------------------------------------------------------

    def cross_validate(
        self,
        symbol: str,
        factor: np.ndarray,
        ohlcv: Dict[str, np.ndarray],
        params: Dict[str, Any],
        vector_result: Optional[BacktestResult] = None,
    ) -> CrossValidationReport:
        """
        向量化回测 vs 天勤回测 交叉验证

        Parameters
        ----------
        symbol : str
            品种代码
        factor : np.ndarray
            因子序列
        ohlcv : dict[str, np.ndarray]
            OHLCV数据
        params : dict
            回测参数
        vector_result : BacktestResult, optional
            已有的向量化回测结果（为None时自动运行）

        Returns
        -------
        CrossValidationReport
        """
        # 1. 向量化回测（如未提供）
        if vector_result is None:
            vec_engine = VectorizedBacktestEngine(
                fee_model=self.fee_model,
                init_capital=self.init_capital,
            )
            vector_result = vec_engine.run(
                factor=factor,
                open_px=ohlcv["open"],
                high_px=ohlcv["high"],
                low_px=ohlcv["low"],
                close_px=ohlcv["close"],
                params=params,
                symbol=symbol,
            )

        # 2. 天勤回测
        tq_result = self.run_backtest(symbol, factor, ohlcv, params)

        # 3. 差异计算
        diff = self._compute_diff(vector_result, tq_result)
        alerts = self._generate_alerts(diff)
        passed = len(alerts) == 0

        report = CrossValidationReport(
            vector_result=vector_result,
            tq_result=tq_result,
            diff=diff,
            alerts=alerts,
            passed=passed,
        )

        if not passed:
            for alert in alerts:
                logger.warning(f"[回测差异告警] {alert}")

        return report

    @staticmethod
    def _compute_diff(v: BacktestResult, t: BacktestResult) -> Dict[str, float]:
        """计算两个回测结果的差异比例"""
        keys = ["sharpe", "calmar", "max_drawdown", "turnover_rate", "total_return", "win_rate"]
        diff = {}
        for k in keys:
            vv = getattr(v, k, 0.0)
            tv = getattr(t, k, 0.0)
            if abs(vv) > 1e-12:
                diff[k] = (tv - vv) / abs(vv)
            else:
                diff[k] = tv - vv
        # 交易次数差异（绝对值）
        diff["total_trades"] = float(t.total_trades - v.total_trades)
        return diff

    @staticmethod
    def _generate_alerts(diff: Dict[str, float], threshold: float = DIFF_ALERT_THRESHOLD) -> List[str]:
        """根据差异生成告警信息"""
        alerts = []
        for k, d in diff.items():
            if k == "total_trades":
                if abs(d) > 5:
                    alerts.append(f"交易次数差异: {int(d)} 笔")
                continue
            if abs(d) > threshold:
                alerts.append(f"{k} 差异 {d*100:.1f}% (阈值 {threshold*100:.0f}%)")
        return alerts

    # ------------------------------------------------------------------
    # 模拟盘运行
    # ------------------------------------------------------------------

    def run_paper_trading(
        self,
        symbol: str,
        signal_fn: callable,
        check_interval_seconds: int = 60,
        max_iterations: Optional[int] = None,
    ) -> None:
        """
        模拟盘运行（基于天勤模拟账户）

        Parameters
        ----------
        symbol : str
            品种代码
        signal_fn : callable
            信号生成函数，接收 (api, klines) 返回方向信号 1/0/-1
        check_interval_seconds : int
            检查间隔（秒）
        max_iterations : int, optional
            最大迭代次数（None=无限）
        """
        api = self._init_api(backtest=False)
        tq_symbol = get_main_contract(symbol)

        # 订阅K线
        klines = api.get_kline_serial(tq_symbol, 3600)
        logger.info(f"模拟盘启动: {tq_symbol}, 初始资金: {self.init_capital}")

        iteration = 0
        last_pos = 0

        while True:
            if max_iterations is not None and iteration >= max_iterations:
                break
            iteration += 1

            api.wait_update(deadline=pd.Timestamp.now() + pd.Timedelta(seconds=check_interval_seconds))

            if api.is_changing(klines):
                sig = signal_fn(api, klines)
                account = api.get_account()
                positions = api.get_position()
                pos = positions.get(tq_symbol)
                current_long = pos.volume_long if pos else 0
                current_short = pos.volume_short if pos else 0
                current_pos = current_long - current_short

                if sig == 1 and current_pos <= 0:
                    # 开多/平空开多
                    if current_short > 0:
                        api.insert_order(tq_symbol, "BUY", "CLOSE", current_short)
                    lots = self._calc_paper_lots(account.balance)
                    if lots > 0:
                        api.insert_order(tq_symbol, "BUY", "OPEN", lots)
                    logger.info(f"[{iteration}] 做多信号 | 权益: {account.balance:.2f}")

                elif sig == -1 and current_pos >= 0:
                    # 开空/平多开空
                    if current_long > 0:
                        api.insert_order(tq_symbol, "SELL", "CLOSE", current_long)
                    lots = self._calc_paper_lots(account.balance)
                    if lots > 0:
                        api.insert_order(tq_symbol, "SELL", "OPEN", lots)
                    logger.info(f"[{iteration}] 做空信号 | 权益: {account.balance:.2f}")

                elif sig == 0 and current_pos != 0:
                    # 平仓
                    if current_long > 0:
                        api.insert_order(tq_symbol, "SELL", "CLOSE", current_long)
                    if current_short > 0:
                        api.insert_order(tq_symbol, "BUY", "CLOSE", current_short)
                    logger.info(f"[{iteration}] 平仓信号 | 权益: {account.balance:.2f}")

                last_pos = current_pos

        api.close()
        self._api = None

    def _calc_paper_lots(self, capital: float, position_size_pct: float = 0.95, contract_value: float = 50000.0, margin_rate: float = 0.12) -> int:
        notional = capital * position_size_pct
        lots = int(notional / (contract_value * margin_rate))
        return max(lots, 1)

    # ------------------------------------------------------------------
    # 主力合约自动换月
    # ------------------------------------------------------------------

    def rollover_main_contract(
        self,
        symbol: str,
        current_contract: str,
        rollover_days_before_expire: int = 5,
    ) -> Optional[str]:
        """
        检查并执行主力合约换月

        Parameters
        ----------
        symbol : str
            品种代码
        current_contract : str
            当前持仓合约代码
        rollover_days_before_expire : int
            到期前N天换月

        Returns
        -------
        str or None — 新合约代码（无需换月返回None）
        """
        if self._data_source is None:
            self._data_source = TqDataSource(
                account=self.account,
                password=self.password,
                sim=self.sim,
            )

        new_main = self._data_source.get_current_main_contract(symbol)
        if new_main != current_contract:
            logger.info(f"主力合约换月: {current_contract} -> {new_main}")
            return new_main
        return None

    # ------------------------------------------------------------------
    # 差异报告生成
    # ------------------------------------------------------------------

    def generate_report(
        self,
        reports: List[CrossValidationReport],
        output_path: Optional[Path] = None,
    ) -> pd.DataFrame:
        """
        生成批量交叉验证差异报告

        Parameters
        ----------
        reports : list[CrossValidationReport]
            多组交叉验证结果
        output_path : Path, optional
            输出CSV路径

        Returns
        -------
        pd.DataFrame
        """
        rows = []
        for r in reports:
            row = {
                "vector_sharpe": r.vector_result.sharpe,
                "tq_sharpe": r.tq_result.sharpe,
                "diff_sharpe": r.diff.get("sharpe", 0),
                "vector_calmar": r.vector_result.calmar,
                "tq_calmar": r.tq_result.calmar,
                "diff_calmar": r.diff.get("calmar", 0),
                "vector_max_dd": r.vector_result.max_drawdown,
                "tq_max_dd": r.tq_result.max_drawdown,
                "diff_max_dd": r.diff.get("max_drawdown", 0),
                "vector_total_return": r.vector_result.total_return,
                "tq_total_return": r.tq_result.total_return,
                "diff_total_return": r.diff.get("total_return", 0),
                "vector_trades": r.vector_result.total_trades,
                "tq_trades": r.tq_result.total_trades,
                "diff_trades": r.diff.get("total_trades", 0),
                "passed": r.passed,
                "alerts": "; ".join(r.alerts),
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        if output_path is not None:
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            logger.info(f"差异报告已保存: {output_path}")
        return df

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._api is not None:
            try:
                self._api.close()
            except Exception as exc:
                logger.warning(f"关闭天勤API异常: {exc}")
            finally:
                self._api = None
        if self._data_source is not None:
            self._data_source.close()
            self._data_source = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
