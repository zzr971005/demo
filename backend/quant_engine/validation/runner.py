"""
回测引擎集成层 — DSL表达式 + 数据 + 回测 = 结果

负责：
- 从TimescaleDB获取OHLCV数据
- 编译DSL表达式为因子值
- 运行向量化回测
- 返回标准BacktestResult
- 支持批量回测和参数扫描
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ..data.hub import TimescaleHub
from ..factors.formula_dsl import expr_to_func, parse_expr
from ..factors.semantic_validator import SemanticValidator, ValidationResult, quick_check
from .engine import BacktestResult, VectorizedBacktestEngine
from .fee_model import FeeModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 参数定义
# ---------------------------------------------------------------------------

DEFAULT_BACKTEST_PARAMS = {
    "upper_threshold": 0.5,
    "lower_threshold": -0.5,
    "direction_mode": 0,
    "max_holding_bars": 4,  # 固定持仓4小时（4根1H K线），基于豆包专家建议
    "position_size_pct": 0.3,  # 降低仓位比例到30%，降低风险
    "contract_value_per_lot": 50000,
    "tick_size": 1.0,
    "slippage_ticks": 1,
    "use_margin": False,  # 关闭保证金交易，避免高杠杆风险
    "margin_rate": 0.12,
}

SYMBOL_SPECIFIC_PARAMS = {
    "RB": {"contract_value_per_lot": 50000, "tick_size": 1.0, "max_holding_bars": 4},  # 螺纹钢：4小时
    "MA": {"contract_value_per_lot": 50000, "tick_size": 1.0, "max_holding_bars": 8},  # 甲醇：8小时（趋势市场）
    "TA": {"contract_value_per_lot": 50000, "tick_size": 2.0, "max_holding_bars": 4},  # PTA：4小时
    "FG": {"contract_value_per_lot": 40000, "tick_size": 1.0, "max_holding_bars": 4},  # 玻璃：4小时
    "SR": {"contract_value_per_lot": 50000, "tick_size": 1.0, "max_holding_bars": 6},  # 白糖：6小时
    "SA": {"contract_value_per_lot": 50000, "tick_size": 1.0, "max_holding_bars": 4},  # 纯碱：4小时
    "CU": {"contract_value_per_lot": 50000, "tick_size": 10.0, "max_holding_bars": 4}, # 铜：4小时
    "AL": {"contract_value_per_lot": 50000, "tick_size": 5.0, "max_holding_bars": 4},  # 铝：4小时
    "ZN": {"contract_value_per_lot": 50000, "tick_size": 5.0, "max_holding_bars": 4},  # 锌：4小时
    "NI": {"contract_value_per_lot": 50000, "tick_size": 10.0, "max_holding_bars": 4}, # 镍：4小时
    "PB": {"contract_value_per_lot": 50000, "tick_size": 5.0, "max_holding_bars": 4},  # 铅：4小时
    "SN": {"contract_value_per_lot": 50000, "tick_size": 10.0, "max_holding_bars": 4}, # 锡：4小时
}


# ---------------------------------------------------------------------------
# 回测运行器
# ---------------------------------------------------------------------------

@dataclass
class BacktestRunResult:
    """完整的回测运行结果，包含因子值和元数据"""

    success: bool
    result: Optional[BacktestResult] = None
    formula: str = ""
    symbol: str = ""
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None
    factor_values: Optional[np.ndarray] = None
    validation_result: Optional[ValidationResult] = None
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "formula": self.formula,
            "symbol": self.symbol,
            "start_dt": str(self.start_dt) if self.start_dt else None,
            "end_dt": str(self.end_dt) if self.end_dt else None,
            "result": self.result.to_dict() if self.result else None,
            "validation_result": self.validation_result.to_dict() if self.validation_result else None,
            "error_message": self.error_message,
        }


class BacktestRunner:
    """
    完整的回测运行器

    流程：
    1. 从TimescaleDB获取OHLCV数据
    2. 编译DSL表达式为因子值
    3. 语义验证（可选）
    4. 运行向量化回测
    5. 返回完整结果

    Parameters
    ----------
    timescale_hub : TimescaleHub, optional
        数据中心，如果为None则创建新实例
    fee_model : FeeModel, optional
        手续费模型
    """

    def __init__(
        self,
        timescale_hub: Optional[TimescaleHub] = None,
        fee_model: Optional[FeeModel] = None,
        init_capital: float = 1_000_000.0,
    ):
        self._owns_hub = timescale_hub is None
        self.timescale = timescale_hub or TimescaleHub()
        self.engine = VectorizedBacktestEngine(
            fee_model=fee_model,
            init_capital=init_capital,
        )
        self.validator = SemanticValidator()

    def run_formula(
        self,
        formula: str,
        symbol: str,
        start_dt: Optional[Union[str, datetime]] = None,
        end_dt: Optional[Union[str, datetime]] = None,
        params: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> BacktestRunResult:
        """
        运行单个公式的回测

        Parameters
        ----------
        formula : str
            DSL表达式，如 "zscore(close, 20) * ts_corr(close, volume, 10)"
        symbol : str
            品种代码
        start_dt : str or datetime, optional
            开始时间（None表示使用所有可用数据）
        end_dt : str or datetime, optional
            结束时间（None表示使用所有可用数据）
        params : dict, optional
            回测参数（覆盖默认值）
        validate : bool
            是否进行语义验证

        Returns
        -------
        BacktestRunResult
        """
        try:
            # 1. 语义验证
            validation_result = None
            if validate:
                validation_result = self.validator.validate(parse_expr(formula), symbol)
                if not validation_result.is_valid:
                    return BacktestRunResult(
                        success=False,
                        formula=formula,
                        symbol=symbol,
                        validation_result=validation_result,
                        error_message=f"表达式验证失败: {[v.message for v in validation_result.violations if v.severity == 'fatal']}",
                    )

            # 2. 获取OHLCV数据
            df = self.timescale.query_ohlcv(
                symbol=symbol,
                start_dt=start_dt,
                end_dt=end_dt,
                duration_seconds=3600,
            )

            if df.empty:
                return BacktestRunResult(
                    success=False,
                    formula=formula,
                    symbol=symbol,
                    error_message=f"没有 {symbol} 的K线数据",
                )

            # 3. 编译表达式并计算因子值
            func, _ = expr_to_func(formula)
            factor_values = func(
                open=df["open"].values,
                high=df["high"].values,
                low=df["low"].values,
                close=df["close"].values,
                volume=df["volume"].values,
                open_interest=df.get("open_interest", np.zeros(len(df))).values,
            )

            # 4. 应用惩罚系数
            if validation_result is not None and validation_result.penalty_factor < 1.0:
                penalty = validation_result.penalty_factor
                factor_values = factor_values * penalty

            # 5. 准备回测参数
            bt_params = DEFAULT_BACKTEST_PARAMS.copy()
            if symbol in SYMBOL_SPECIFIC_PARAMS:
                bt_params.update(SYMBOL_SPECIFIC_PARAMS[symbol])
            if params:
                bt_params.update(params)

            # 6. 运行回测
            result = self.engine.run(
                factor=factor_values,
                open_px=df["open"].values,
                high_px=df["high"].values,
                low_px=df["low"].values,
                close_px=df["close"].values,
                params=bt_params,
                symbol=symbol,
            )

            return BacktestRunResult(
                success=True,
                result=result,
                formula=formula,
                symbol=symbol,
                start_dt=df.index[0].to_pydatetime(),
                end_dt=df.index[-1].to_pydatetime(),
                factor_values=factor_values,
                validation_result=validation_result,
            )

        except Exception as exc:
            logger.exception(f"回测失败: {formula}")
            return BacktestRunResult(
                success=False,
                formula=formula,
                symbol=symbol,
                error_message=str(exc),
            )

    def batch_run(
        self,
        formulas: List[str],
        symbol: str,
        start_dt: Optional[Union[str, datetime]] = None,
        end_dt: Optional[Union[str, datetime]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[BacktestRunResult]:
        """批量运行多个公式的回测"""
        results = []
        for formula in formulas:
            result = self.run_formula(
                formula=formula,
                symbol=symbol,
                start_dt=start_dt,
                end_dt=end_dt,
                params=params,
            )
            results.append(result)
        return results

    def walk_forward_split(
        self,
        data: pd.DataFrame,
        train_window: int = 630,  # 6个月约630根1H线（252交易日×5根/日÷12月×6月）
        val_window: int = 126,   # 1个月约126根1H线
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        生成Walk-Forward训练/验证分段

        Parameters
        ----------
        data : pd.DataFrame
            OHLCV数据
        train_window : int
            训练窗口大小（K线数）
        val_window : int
            验证窗口大小（K线数）

        Returns
        -------
        list of (train_df, val_df)
        """
        splits = []
        n = len(data)
        step = val_window // 2  # 50%重叠

        for start in range(0, n - train_window - val_window + 1, step):
            train_end = start + train_window
            val_end = train_end + val_window
            if val_end > n:
                break

            train_df = data.iloc[start:train_end].copy()
            val_df = data.iloc[train_end:val_end].copy()
            splits.append((train_df, val_df))

        return splits

    def walk_forward_test(
        self,
        formula: str,
        symbol: str,
        train_window: int = 630,
        val_window: int = 126,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Walk-Forward回测测试

        Returns
        -------
        dict with:
            - n_splits: 分段数
            - avg_sharpe_train: 训练集平均夏普
            - avg_sharpe_val: 验证集平均夏普
            - sharpe_stability: 夏普稳定性（val夏普标准差）
            - efficiency: val夏普 / train夏普
            - results: 各分段结果列表
        """
        df = self.timescale.query_ohlcv(symbol=symbol, duration_seconds=3600)
        if df.empty:
            return {"error": "没有数据"}

        splits = self.walk_forward_split(df, train_window, val_window)

        all_results = []
        train_sharpes = []
        val_sharpes = []

        bt_params = DEFAULT_BACKTEST_PARAMS.copy()
        if symbol in SYMBOL_SPECIFIC_PARAMS:
            bt_params.update(SYMBOL_SPECIFIC_PARAMS[symbol])
        if params:
            bt_params.update(params)

        func, _ = expr_to_func(formula)

        for i, (train_df, val_df) in enumerate(splits):
            # 训练集因子
            train_factor = func(
                open=train_df["open"].values,
                high=train_df["high"].values,
                low=train_df["low"].values,
                close=train_df["close"].values,
                volume=train_df["volume"].values,
                open_interest=train_df.get("open_interest", np.zeros(len(train_df))).values,
            )

            # 验证集因子
            val_factor = func(
                open=val_df["open"].values,
                high=val_df["high"].values,
                low=val_df["low"].values,
                close=val_df["close"].values,
                volume=val_df["volume"].values,
                open_interest=val_df.get("open_interest", np.zeros(len(val_df))).values,
            )

            train_result = self.engine.run(
                factor=train_factor,
                open_px=train_df["open"].values,
                high_px=train_df["high"].values,
                low_px=train_df["low"].values,
                close_px=train_df["close"].values,
                params=bt_params,
                symbol=symbol,
            )

            val_result = self.engine.run(
                factor=val_factor,
                open_px=val_df["open"].values,
                high_px=val_df["high"].values,
                low_px=val_df["low"].values,
                close_px=val_df["close"].values,
                params=bt_params,
                symbol=symbol,
            )

            train_sharpes.append(train_result.sharpe)
            val_sharpes.append(val_result.sharpe)

            all_results.append({
                "split_idx": i,
                "train_period": f"{train_df.index[0]} - {train_df.index[-1]}",
                "val_period": f"{val_df.index[0]} - {val_df.index[-1]}",
                "train_sharpe": float(train_result.sharpe),
                "val_sharpe": float(val_result.sharpe),
                "train_dd": float(train_result.max_drawdown),
                "val_dd": float(val_result.max_drawdown),
                "train_trades": train_result.total_trades,
                "val_trades": val_result.total_trades,
            })

        avg_train_sharpe = float(np.mean(train_sharpes)) if train_sharpes else 0.0
        avg_val_sharpe = float(np.mean(val_sharpes)) if val_sharpes else 0.0
        std_val_sharpe = float(np.std(val_sharpes)) if val_sharpes else 0.0

        efficiency = avg_val_sharpe / (avg_train_sharpe + 1e-12) if avg_train_sharpe > 0 else 0.0

        return {
            "n_splits": len(splits),
            "avg_sharpe_train": avg_train_sharpe,
            "avg_sharpe_val": avg_val_sharpe,
            "sharpe_stability": std_val_sharpe,
            "efficiency": efficiency,
            "results": all_results,
        }

    def parameter_scan(
        self,
        formula: str,
        symbol: str,
        param_ranges: Dict[str, List[Any]],
        start_dt: Optional[Union[str, datetime]] = None,
        end_dt: Optional[Union[str, datetime]] = None,
    ) -> List[Dict[str, Any]]:
        """
        参数扫描：测试不同参数组合的回测结果

        Parameters
        ----------
        formula : str
            表达式
        symbol : str
            品种
        param_ranges : dict
            参数范围，如 {"upper_threshold": [0.3, 0.5, 0.7], "max_holding_bars": [20, 50, 100]}
        start_dt, end_dt : optional
            时间范围

        Returns
        -------
        list of dict，每个包含 params + metrics
        """
        import itertools

        keys = list(param_ranges.keys())
        values = [param_ranges[k] for k in keys]
        combinations = list(itertools.product(*values))

        results = []
        for combo in combinations:
            params = dict(zip(keys, combo))
            result = self.run_formula(
                formula=formula,
                symbol=symbol,
                start_dt=start_dt,
                end_dt=end_dt,
                params=params,
            )

            if result.success and result.result:
                results.append({
                    "params": params,
                    "sharpe": result.result.sharpe,
                    "calmar": result.result.calmar,
                    "max_drawdown": result.result.max_drawdown,
                    "win_rate": result.result.win_rate,
                    "total_trades": result.result.total_trades,
                    "total_return": result.result.total_return,
                })

        return sorted(results, key=lambda x: x["sharpe"], reverse=True)

    def close(self) -> None:
        """关闭资源"""
        if self._owns_hub:
            self.timescale.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def quick_backtest(
    formula: str,
    symbol: str,
    start_dt: Optional[Union[str, datetime]] = None,
    end_dt: Optional[Union[str, datetime]] = None,
    **kwargs,
) -> BacktestRunResult:
    """快速回测便捷函数"""
    with BacktestRunner() as runner:
        return runner.run_formula(formula, symbol, start_dt, end_dt, kwargs)


def validate_formula(formula: str, symbol: str = "RB") -> Tuple[bool, str]:
    """
    验证公式是否有效（可编译 + 语义验证）

    Returns
    -------
    (is_valid, message)
    """
    try:
        parse_expr(formula)
        is_valid, _ = quick_check(formula, symbol)
        if is_valid:
            return True, "OK"
        return False, "语义验证失败"
    except Exception as exc:
        return False, str(exc)
