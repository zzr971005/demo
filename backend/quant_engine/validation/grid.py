"""
ç½æ ¼æç´¢ â?åæ°ä¼åä¸?Walk-Forward éªè¯

æ¯æï¼?- åæ°ç½æ ¼æç´¢
- Walk-Forward ä¼åï¼é²æ­¢è¿æåï¼?- å¹¶è¡æ§è¡
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from numba import jit

from .engine import BacktestResult, VectorizedBacktestEngine
from .split import TemporalSplitter, WalkForwardSplit


# ---------------------------------------------------------------------------
# åæ°ç½æ ¼
# ---------------------------------------------------------------------------

@dataclass
class ParamGrid:
    """åæ°ç½æ ¼å®ä¹"""

    params: Dict[str, List[Any]] = field(default_factory=dict)

    def add(self, name: str, values: List[Any]) -> "ParamGrid":
        """æ·»å åæ°ç»´åº¦"""
        self.params[name] = values
        return self

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """éåææåæ°ç»å?""
        if not self.params:
            yield {}
            return

        keys = list(self.params.keys())
        values = [self.params[k] for k in keys]

        def _product(*args):
            if len(args) == 0:
                yield []
                return
            if len(args) == 1:
                for v in args[0]:
                    yield [v]
                return
            for v in args[0]:
                for rest in _product(*args[1:]):
                    yield [v] + rest

        for combo in _product(*values):
            yield dict(zip(keys, combo))

    def __len__(self) -> int:
        if not self.params:
            return 1
        total = 1
        for v in self.params.values():
            total *= len(v)
        return total


# ---------------------------------------------------------------------------
# ç½æ ¼æç´¢ç»æ
# ---------------------------------------------------------------------------

@dataclass
class GridSearchResult:
    """ç½æ ¼æç´¢ç»æ"""

    best_params: Dict[str, Any]
    best_score: float
    best_result: Optional[BacktestResult]
    all_results: List[Tuple[Dict[str, Any], BacktestResult]]
    metric: str

    def top_k(self, k: int = 5) -> List[Tuple[Dict[str, Any], BacktestResult]]:
        """å?Top K åæ°ç»å"""
        sorted_results = sorted(
            self.all_results,
            key=lambda x: getattr(x[1], self.metric),
            reverse=True,
        )
        return sorted_results[:k]

    def to_dataframe(self) -> pd.DataFrame:
        """è½¬ä¸º DataFrame ä¾¿äºåæ"""
        records = []
        for params, result in self.all_results:
            row = params.copy()
            row.update(result.to_dict())
            records.append(row)
        return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Walk-Forward ç»æ
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardResult:
    """Walk-Forward ä¼åç»æ"""

    best_params_per_fold: List[Dict[str, Any]]
    fold_results: List[Dict[str, Any]]
    aggregated_score: float
    wfe_metrics: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_params_per_fold": self.best_params_per_fold,
            "aggregated_score": self.aggregated_score,
            "wfe_metrics": self.wfe_metrics,
        }


# ---------------------------------------------------------------------------
# ç½æ ¼æç´¢å?# ---------------------------------------------------------------------------

class GridSearch:
    """
    åæ°ç½æ ¼æç´¢å?
    Parameters
    ----------
    engine : VectorizedBacktestEngine
        åæµå¼æ
    metric : str
        ä¼åç®æ ææ  ('sharpe', 'calmar', 'total_return')
    """

    def __init__(
        self,
        engine: VectorizedBacktestEngine,
        metric: str = "sharpe",
    ):
        self.engine = engine
        self.metric = metric

    def search(
        self,
        factor: np.ndarray,
        open_px: np.ndarray,
        high_px: np.ndarray,
        low_px: np.ndarray,
        close_px: np.ndarray,
        param_grid: ParamGrid,
        symbol: str = "RB",
    ) -> GridSearchResult:
        """
        æ§è¡ç½æ ¼æç´¢

        Parameters
        ----------
        factor : np.ndarray
            å å­å¼åºå?        open_px, high_px, low_px, close_px : np.ndarray
            OHLC ä»·æ ¼åºå
        param_grid : ParamGrid
            åæ°ç½æ ¼
        symbol : str
            åç§ä»£ç 

        Returns
        -------
        GridSearchResult
        """
        all_results: List[Tuple[Dict[str, Any], BacktestResult]] = []
        best_score = -np.inf
        best_params = {}
        best_result = None

        for params in param_grid:
            result = self.engine.run(
                factor=factor,
                open_px=open_px,
                high_px=high_px,
                low_px=low_px,
                close_px=close_px,
                params=params,
                symbol=symbol,
            )

            score = getattr(result, self.metric, result.sharpe)
            all_results.append((params, result))

            if score > best_score:
                best_score = score
                best_params = params.copy()
                best_result = result

        return GridSearchResult(
            best_params=best_params,
            best_score=best_score,
            best_result=best_result,
            all_results=all_results,
            metric=self.metric,
        )

    def search_walk_forward(
        self,
        factor: np.ndarray,
        open_px: np.ndarray,
        high_px: np.ndarray,
        low_px: np.ndarray,
        close_px: np.ndarray,
        param_grid: ParamGrid,
        index: Union[pd.DatetimeIndex, np.ndarray],
        splitter: Optional[TemporalSplitter] = None,
        symbol: str = "RB",
    ) -> WalkForwardResult:
        """
        Walk-Forward åæ°ä¼å

        æ¯æå¨è®­ç»éä¸éæä¼åæ°ï¼å¨æµè¯éä¸éªè¯ã?
        Parameters
        ----------
        factor : np.ndarray
        open_px, high_px, low_px, close_px : np.ndarray
        param_grid : ParamGrid
        index : DatetimeIndex or array
            æ¶é´ç´¢å¼
        splitter : TemporalSplitter, optional
        symbol : str

        Returns
        -------
        WalkForwardResult
        """
        if splitter is None:
            splitter = TemporalSplitter(train_months=6, val_months=6, test_months=6)

        splits = splitter.split(index, n_splits=3)

        best_params_per_fold = []
        fold_results = []
        is_returns_list = []
        oos_returns_list = []

        for fold, split in enumerate(splits):
            train_idx = split.train_idx
            test_idx = split.test_idx

            if len(train_idx) == 0 or len(test_idx) == 0:
                continue

            # è®­ç»éä¸éæä¼åæ?            train_factor = factor[train_idx]
            train_open = open_px[train_idx]
            train_high = high_px[train_idx]
            train_low = low_px[train_idx]
            train_close = close_px[train_idx]

            grid_result = self.search(
                factor=train_factor,
                open_px=train_open,
                high_px=train_high,
                low_px=train_low,
                close_px=train_close,
                param_grid=param_grid,
                symbol=symbol,
            )

            best_params = grid_result.best_params
            best_params_per_fold.append(best_params)

            # æµè¯éä¸éªè¯
            test_factor = factor[test_idx]
            test_open = open_px[test_idx]
            test_high = high_px[test_idx]
            test_low = low_px[test_idx]
            test_close = close_px[test_idx]

            test_result = self.engine.run(
                factor=test_factor,
                open_px=test_open,
                high_px=test_high,
                low_px=test_low,
                close_px=test_close,
                params=best_params,
                symbol=symbol,
            )

            # è®¡ç®æ¶çåºå
            train_equity = grid_result.best_result.equity_curve if grid_result.best_result else np.array([])
            test_equity = test_result.equity_curve

            if len(train_equity) > 1:
                train_returns = np.diff(train_equity) / train_equity[:-1]
                is_returns_list.append(train_returns)
            else:
                is_returns_list.append(np.array([]))

            if len(test_equity) > 1:
                test_returns = np.diff(test_equity) / test_equity[:-1]
                oos_returns_list.append(test_returns)
            else:
                oos_returns_list.append(np.array([]))

            fold_results.append({
                "fold": fold,
                "best_params": best_params,
                "train_sharpe": grid_result.best_result.sharpe if grid_result.best_result else 0.0,
                "test_sharpe": test_result.sharpe,
                "test_calmar": test_result.calmar,
                "test_max_dd": test_result.max_drawdown,
            })

        # è®¡ç® WFE
        from .pbo_dsr import wfe_multiple_folds

        wfe_metrics = wfe_multiple_folds(is_returns_list, oos_returns_list)

        # èååæ°ï¼å¹³åæµè¯å¤æ?        if fold_results:
            aggregated_score = np.mean([f["test_sharpe"] for f in fold_results])
        else:
            aggregated_score = 0.0

        return WalkForwardResult(
            best_params_per_fold=best_params_per_fold,
            fold_results=fold_results,
            aggregated_score=float(aggregated_score),
            wfe_metrics=wfe_metrics,
        )


# ---------------------------------------------------------------------------
# å¿«éåæ°æ«æï¼Numba å éï¼
# ---------------------------------------------------------------------------

@jit(nopython=True, cache=False)
def _nb_fast_grid_search(
    factor: np.ndarray,
    close_px: np.ndarray,
    thresholds: np.ndarray,
    upper_fixed: float,
    init_capital: float,
    position_size_pct: float,
    contract_value_per_lot: float,
    fee_rate: float,
    periods_per_year: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    å¿«ééå¼ç½æ ¼æç´¢ï¼Numba JIT å éï¼

    åªæç´?lower_thresholdï¼upper_threshold åºå®ã?
    Returns
    -------
    sharpe_array : np.ndarray
    return_array : np.ndarray
    """
    n = len(factor)
    n_grid = len(thresholds)
    sharpe_array = np.empty(n_grid, dtype=np.float64)
    return_array = np.empty(n_grid, dtype=np.float64)

    for g in range(n_grid):
        lower_th = thresholds[g]
        upper_th = upper_fixed

        capital = init_capital
        pos = 0
        pos_entry_px = 0.0
        pos_lots = 0

        equity = np.empty(n, dtype=np.float64)
        equity[0] = init_capital

        for i in range(1, n):
            if np.isnan(factor[i]) or np.isnan(close_px[i]):
                equity[i] = capital
                continue

            sig = 0
            if factor[i] > upper_th:
                sig = 1
            elif factor[i] < lower_th:
                sig = -1

            exec_px = close_px[i]
            is_last = (i == n - 1)

            if pos == 0 and sig != 0:
                pos = int(sig)
                pos_entry_px = exec_px
                notional = capital * position_size_pct
                pos_lots = int(notional / contract_value_per_lot)
                fee = pos_lots * contract_value_per_lot * fee_rate
                capital -= fee

            elif pos != 0 and (sig == -pos or is_last):
                pnl = pos * (exec_px - pos_entry_px) * pos_lots * contract_value_per_lot
                fee = pos_lots * contract_value_per_lot * fee_rate
                capital += pnl - fee

                if sig != 0 and not is_last:
                    pos = int(sig)
                    pos_entry_px = exec_px
                    notional = capital * position_size_pct
                    pos_lots = int(notional / contract_value_per_lot)
                    fee = pos_lots * contract_value_per_lot * fee_rate
                    capital -= fee
                else:
                    pos = 0
                    pos_lots = 0

            equity[i] = capital

        # è®¡ç®å¤æ®
        returns = np.empty(n - 1, dtype=np.float64)
        for i in range(1, n):
            returns[i - 1] = (equity[i] - equity[i - 1]) / equity[i - 1]

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

        excess_ret = mean_ret * periods_per_year
        sharpe = excess_ret / (std_ret * np.sqrt(periods_per_year) + 1e-12)
        total_ret = (equity[-1] - equity[0]) / equity[0]

        sharpe_array[g] = sharpe
        return_array[g] = total_ret

    return sharpe_array, return_array


class FastThresholdScanner:
    """
    å¿«ééå¼æ«æå¨ï¼Numba å éï¼

    éç¨äºåªéè¦æç´¢ä¸ä¸éå¼ä¸¤ä¸ªåæ°çåºæ¯ã?    """

    def __init__(
        self,
        init_capital: float = 1_000_000.0,
        periods_per_year: float = 252 * 5,
    ):
        self.init_capital = init_capital
        self.periods_per_year = periods_per_year

    def scan(
        self,
        factor: np.ndarray,
        close_px: np.ndarray,
        lower_thresholds: np.ndarray,
        upper_threshold: float = 0.5,
        position_size_pct: float = 0.95,
        contract_value_per_lot: float = 50000.0,
        fee_rate: float = 0.0002,
    ) -> pd.DataFrame:
        """
        æ«æ lower_threshold åæ°

        Parameters
        ----------
        factor : np.ndarray
        close_px : np.ndarray
        lower_thresholds : np.ndarray
            è¦æç´¢çä¸éå¼æ°ç»?        upper_threshold : float
            åºå®çä¸éå?
        Returns
        -------
        pd.DataFrame â?æ¯è¡ä¸ä¸ªåæ°ï¼ååå?threshold, sharpe, total_return
        """
        factor = np.asarray(factor, dtype=np.float64)
        close_px = np.asarray(close_px, dtype=np.float64)
        lower_thresholds = np.asarray(lower_thresholds, dtype=np.float64)

        sharpe_arr, return_arr = _nb_fast_grid_search(
            factor, close_px, lower_thresholds,
            float(upper_threshold),
            float(self.init_capital),
            float(position_size_pct),
            float(contract_value_per_lot),
            float(fee_rate),
            float(self.periods_per_year),
        )

        df = pd.DataFrame({
            "lower_threshold": lower_thresholds,
            "sharpe": sharpe_arr,
            "total_return": return_arr,
        })
        return df
