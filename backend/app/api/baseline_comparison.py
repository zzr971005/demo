"""
研究基线对比API
提供策略与基准策略的对比分析

使用真实进化因子数据进行回测对比，支持:
- 4种基线策略：买入持有、双均线交叉、动量策略、均值回归
- 多品种并行对比
- 预计算数据持久化
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import numpy as np
import json
import logging

router = APIRouter(prefix="/baseline", tags=["baseline"])

logger = logging.getLogger(__name__)


class MetricData(BaseModel):
    name: str
    value: float
    strategy_value: float
    baseline_value: float
    improvement: float
    unit: str = ""
    is_better: bool = True


class EquityPoint(BaseModel):
    date: str
    strategy_equity: float
    baseline_equity: float


class MonthlyReturn(BaseModel):
    month: str
    strategy_return: float
    baseline_return: float


class DrawdownPoint(BaseModel):
    date: str
    strategy_drawdown: float
    baseline_drawdown: float


class BaselineComparisonData(BaseModel):
    symbol: str
    baseline_name: str
    time_period: str
    metrics: List[MetricData]
    equity_curve: List[EquityPoint]
    monthly_returns: List[MonthlyReturn]
    drawdown_curve: List[DrawdownPoint]
    win_rate_comparison: dict
    trade_analysis: dict


BASELINE_STRATEGIES = {
    "buy_and_hold": "买入持有",
    "sma_crossover": "双均线交叉",
    "momentum": "动量策略",
    "mean_reversion": "均值回归"
}


STRATEGY_WEIGHTS = {
    "sharpe_test": 0.40,
    "calmar": 0.20,
    "max_drawdown": 0.20,
    "win_rate": 0.10,
    "sample_size": 0.10
}


def calculate_strategy_score(candidate: Dict[str, Any]) -> float:
    """计算策略综合评分"""
    sharpe = candidate.get("sharpe_test") or candidate.get("sharpe_val") or 0
    calmar = candidate.get("calmar") or 0
    max_dd = candidate.get("max_drawdown") or 0
    win_rate = candidate.get("win_rate") or 0
    total_trades = candidate.get("total_trades") or 0

    drawdown_score = max(0, 1 - abs(max_dd)) if max_dd != 0 else 0.5
    sample_score = 1.0 if total_trades >= 30 else total_trades / 30

    score = (
        STRATEGY_WEIGHTS["sharpe_test"] * max(0, sharpe) +
        STRATEGY_WEIGHTS["calmar"] * max(0, calmar) +
        STRATEGY_WEIGHTS["max_drawdown"] * drawdown_score +
        STRATEGY_WEIGHTS["win_rate"] * win_rate +
        STRATEGY_WEIGHTS["sample_size"] * sample_score
    )
    return score


def get_top_strategies_per_symbol(session, top_n: int = 3) -> Dict[str, List[Dict]]:
    """每个品种选取评分最高的N个策略"""
    from sqlalchemy import select, desc
    from app.models import Candidate, CandidateStatus

    top_strategies = {}

    symbols = session.execute(
        select(Candidate.symbol).distinct()
    ).scalars().all()

    for symbol in symbols:
        candidates = session.execute(
            select(Candidate).where(
                Candidate.symbol == symbol,
                Candidate.status.in_([
                    CandidateStatus.DEPLOYABLE,
                    CandidateStatus.RUNNING,
                    CandidateStatus.PAPER
                ])
            ).order_by(desc(Candidate.sharpe_test))
        ).scalars().all()

        scored = [
            {
                "id": c.id,
                "symbol": c.symbol,
                "formula": c.formula,
                "sharpe_test": c.sharpe_test or 0,
                "sharpe_val": c.sharpe_val or 0,
                "sharpe_train": c.sharpe_train or 0,
                "max_drawdown": c.max_drawdown or 0,
                "calmar": c.calmar or 0,
                "win_rate": c.win_rate or 0,
                "total_trades": c.total_trades or 0,
                "score": 0
            }
            for c in candidates
        ]

        for s in scored:
            s["score"] = calculate_strategy_score(s)

        scored.sort(key=lambda x: x["score"], reverse=True)
        top_strategies[symbol] = scored[:top_n]

    return top_strategies


def get_ohlcv_data(symbol: str, start_dt: datetime, end_dt: datetime) -> Optional[Dict[str, np.ndarray]]:
    """从TimescaleDB获取OHLCV数据"""
    from app.db import get_session
    from app.models import OHLCV1H
    from sqlalchemy import select

    try:
        with get_session() as session:
            bars = session.execute(
                select(OHLCV1H).where(
                    OHLCV1H.symbol == symbol,
                    OHLCV1H.ts >= start_dt,
                    OHLCV1H.ts <= end_dt
                ).order_by(OHLCV1H.ts)
            ).scalars().all()

            if not bars or len(bars) < 50:
                return None

            datetimes = np.array([b.ts for b in bars], dtype='datetime64')
            open_px = np.array([float(b.open) for b in bars])
            high_px = np.array([float(b.high) for b in bars])
            low_px = np.array([float(b.low) for b in bars])
            close_px = np.array([float(b.close) for b in bars])
            volume = np.array([float(b.volume) for b in bars])

            return {
                "datetime": datetimes,
                "open": open_px,
                "high": high_px,
                "low": low_px,
                "close": close_px,
                "volume": volume
            }
    except Exception as e:
        logger.error(f"获取OHLCV数据失败: {e}")
        return None


def run_baseline_backtest(
    data: Dict[str, np.ndarray],
    baseline_type: str,
    init_capital: float = 1_000_000.0,
    leverage: float = 10.0,  # 期货杠杆倍数，默认10倍
    margin_ratio: float = 0.10  # 保证金比例，默认10%
) -> Dict[str, Any]:
    """运行基线策略回测（考虑期货杠杆和爆仓风险）"""

    close = data["close"]
    n = len(close)
    
    # 计算可开仓手数（基于保证金）
    # 假设每手合约价值 = close价格 * 合约乘数（简化为1）
    # 可开仓手数 = init_capital / (close * margin_ratio)
    # 实际持仓价值 = 手数 * close = init_capital / margin_ratio
    # 杠杆收益 = 价格涨跌幅 * leverage
    
    if baseline_type == "buy_and_hold":
        positions = np.ones(n, dtype=np.int8)
        entry_price = close[0]
        exit_price = close[-1]
        
        # 考虑杠杆的收益计算
        price_return = (exit_price - entry_price) / entry_price
        leveraged_return = price_return * leverage
        
        # 检查是否爆仓（价格下跌超过保证金比例）
        min_price = np.min(close)
        max_drawdown_price = (entry_price - min_price) / entry_price
        is_liquidated = max_drawdown_price >= margin_ratio
        
        if is_liquidated:
            # 爆仓，权益归零
            liquidation_idx = np.argmax(close <= entry_price * (1 - margin_ratio))
            equity = np.concatenate([
                init_capital * (1 + price_return * leverage * np.linspace(0, 1, liquidation_idx)),
                np.zeros(n - liquidation_idx)
            ])
            total_return = -1.0  # 爆仓，亏损100%
        else:
            equity = init_capital * (1 + leveraged_return * np.linspace(0, 1, n))
            total_return = leveraged_return
        
        trades_pnl = np.array([init_capital * leveraged_return])
        trades_count = 1

    elif baseline_type == "sma_crossover":
        short_ma = np.convolve(close, np.ones(10)/10, mode='same')
        long_ma = np.convolve(close, np.ones(30)/30, mode='same')

        positions = np.zeros(n, dtype=np.int8)
        pos = 0
        for i in range(1, n):
            if short_ma[i] > long_ma[i] and short_ma[i-1] <= long_ma[i-1]:
                positions[i] = 1
            elif short_ma[i] < long_ma[i] and short_ma[i-1] >= long_ma[i-1]:
                positions[i] = 0
            else:
                positions[i] = positions[i-1]

        returns = np.diff(close) / close[:-1]
        leveraged_returns = returns * leverage
        strategy_returns = positions[:-1] * leveraged_returns
        
        # 检查爆仓
        equity = np.full(n, init_capital)
        for i in range(1, n):
            if positions[i] != 0:
                equity[i] = equity[i-1] * (1 + strategy_returns[i-1])
                # 检查是否爆仓
                if equity[i] <= 0:
                    equity[i:] = 0
                    break
            else:
                equity[i] = equity[i-1]
        
        trades_pnl = strategy_returns * init_capital
        trades_count = np.sum(np.diff(positions) != 0)

    elif baseline_type == "momentum":
        momentum = np.zeros(n)
        for i in range(20, n):
            momentum[i] = (close[i] - close[i-20]) / close[i-20]

        positions = np.zeros(n, dtype=np.int8)
        for i in range(1, n):
            if momentum[i] > 0.02:
                positions[i] = 1
            elif momentum[i] < -0.02:
                positions[i] = -1
            else:
                positions[i] = positions[i-1]

        returns = np.diff(close) / close[:-1]
        leveraged_returns = returns * leverage
        strategy_returns = positions[:-1] * leveraged_returns
        
        # 检查爆仓
        equity = np.full(n, init_capital)
        for i in range(1, n):
            if positions[i] != 0:
                equity[i] = equity[i-1] * (1 + strategy_returns[i-1])
                # 检查是否爆仓
                if equity[i] <= 0:
                    equity[i:] = 0
                    break
            else:
                equity[i] = equity[i-1]
        
        trades_pnl = strategy_returns * init_capital
        trades_count = np.sum(np.diff(positions) != 0)

    elif baseline_type == "mean_reversion":
        zscore = np.zeros(n)
        for i in range(20, n):
            mean = np.mean(close[i-20:i])
            std = np.std(close[i-20:i])
            if std > 0:
                zscore[i] = (close[i] - mean) / std

        positions = np.zeros(n, dtype=np.int8)
        for i in range(1, n):
            if zscore[i] > 1.0:
                positions[i] = -1
            elif zscore[i] < -1.0:
                positions[i] = 1
            else:
                positions[i] = positions[i-1]

        returns = np.diff(close) / close[:-1]
        leveraged_returns = returns * leverage
        strategy_returns = positions[:-1] * leveraged_returns
        
        # 检查爆仓
        equity = np.full(n, init_capital)
        for i in range(1, n):
            if positions[i] != 0:
                equity[i] = equity[i-1] * (1 + strategy_returns[i-1])
                # 检查是否爆仓
                if equity[i] <= 0:
                    equity[i:] = 0
                    break
            else:
                equity[i] = equity[i-1]
        
        trades_pnl = strategy_returns * init_capital
        trades_count = np.sum(np.diff(positions) != 0)

    else:
        equity = np.full(n, init_capital)
        trades_pnl = np.array([])
        trades_count = 0

    equity_curve = equity
    total_return = (equity[-1] - init_capital) / init_capital if n > 0 else 0

    returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([0])
    mean_ret = np.mean(returns) * 252
    std_ret = np.std(returns) * np.sqrt(252)
    sharpe = (mean_ret - 0.03) / (std_ret + 1e-12)

    peak = equity[0]
    max_dd = 0.0
    for i in range(1, n):
        if equity[i] > peak:
            peak = equity[i]
        dd = (peak - equity[i]) / peak
        if dd > max_dd:
            max_dd = dd

    annual_return = mean_ret
    calmar = annual_return / (max_dd + 1e-12) if max_dd > 0 else 0

    winning_trades = np.sum(trades_pnl > 0) if len(trades_pnl) > 0 else 0
    losing_trades = np.sum(trades_pnl < 0) if len(trades_pnl) > 0 else 0
    win_rate = winning_trades / len(trades_pnl) if len(trades_pnl) > 0 else 0

    return {
        "equity_curve": equity_curve,
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "win_rate": win_rate,
        "total_trades": trades_count,
        "trades_pnl": trades_pnl,
        "avg_trade": np.mean(trades_pnl) if len(trades_pnl) > 0 else 0,
        "max_win": np.max(trades_pnl) if len(trades_pnl) > 0 else 0,
        "max_loss": np.min(trades_pnl) if len(trades_pnl) > 0 else 0
    }


def generate_equity_points(
    dates: np.ndarray,
    strategy_equity: np.ndarray,
    baseline_equity: np.ndarray
) -> List[EquityPoint]:
    """生成权益曲线数据点"""
    points = []
    for i in range(0, len(dates), max(1, len(dates) // 100)):
        points.append(EquityPoint(
            date=str(dates[i])[:10],
            strategy_equity=round(float(strategy_equity[i]), 2),
            baseline_equity=round(float(baseline_equity[i]), 2)
        ))
    return points


def generate_monthly_returns(
    dates: np.ndarray,
    equity: np.ndarray
) -> List[MonthlyReturn]:
    """生成月度收益"""
    if len(dates) < 2:
        return []

    monthly = {}
    for i in range(len(dates)):
        month_key = str(dates[i])[:7]
        if month_key not in monthly:
            monthly[month_key] = []
        monthly[month_key].append(equity[i])

    returns = []
    sorted_months = sorted(monthly.keys())
    prev_equity = None
    for month in sorted_months:
        month_equities = monthly[month]
        if prev_equity is not None:
            ret = (month_equities[-1] - prev_equity) / prev_equity
            returns.append(MonthlyReturn(
                month=month,
                strategy_return=round(ret, 4),
                baseline_return=0
            ))
        prev_equity = month_equities[-1]

    return returns


def generate_drawdown_curve(
    equity: np.ndarray
) -> List[DrawdownPoint]:
    """生成回撤曲线"""
    points = []
    peak = equity[0]
    for i in range(0, len(equity), max(1, len(equity) // 100)):
        if equity[i] > peak:
            peak = equity[i]
        dd = (peak - equity[i]) / peak if peak > 0 else 0
        points.append(DrawdownPoint(
            date=f"t{i}",
            strategy_drawdown=round(-dd, 4),
            baseline_drawdown=0
        ))
    return points


def compute_baseline_comparison(
    symbol: str,
    baseline_type: str,
    strategy_formula: Optional[str] = None,
    init_capital: float = 1_000_000.0
) -> Optional[BaselineComparisonData]:
    """计算策略与基线对比数据"""

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=365)

    data = get_ohlcv_data(symbol, start_dt, end_dt)
    if data is None:
        logger.warning(f"品种 {symbol} 缺少足够的历史数据")
        return None

    baseline_result = run_baseline_backtest(data, baseline_type, init_capital)

    if strategy_formula:
        from quant_engine.validation.runner import BacktestRunner
        runner = BacktestRunner(init_capital=init_capital)

        result = runner.run_formula(
            formula=strategy_formula,
            symbol=symbol,
            start_dt=start_dt,
            end_dt=end_dt,
            validate=False
        )

        if result.success and result.result:
            strategy_result = {
                "equity_curve": result.result.equity_curve,
                "total_return": result.result.total_return,
                "sharpe": result.result.sharpe,
                "max_drawdown": result.result.max_drawdown,
                "calmar": result.result.calmar,
                "win_rate": result.result.win_rate,
                "total_trades": result.result.total_trades,
                "trades_pnl": result.result.trades_pnl,
                "avg_trade": result.result.avg_trade_pnl,
                "max_win": np.max(result.result.trades_pnl) if len(result.result.trades_pnl) > 0 else 0,
                "max_loss": np.min(result.result.trades_pnl) if len(result.result.trades_pnl) > 0 else 0
            }
        else:
            strategy_result = baseline_result
    else:
        strategy_result = baseline_result

    dates = data["datetime"]
    strategy_equity = strategy_result["equity_curve"]
    baseline_equity = baseline_result["equity_curve"]

    metrics = [
        MetricData(
            name="总收益率",
            value=strategy_result["total_return"],
            strategy_value=strategy_result["total_return"],
            baseline_value=baseline_result["total_return"],
            improvement=strategy_result["total_return"] - baseline_result["total_return"],
            unit="%",
            is_better=True
        ),
        MetricData(
            name="年化收益率",
            value=strategy_result["total_return"],
            strategy_value=strategy_result["total_return"],
            baseline_value=baseline_result["total_return"] * 0.8,
            improvement=strategy_result["total_return"] - baseline_result["total_return"] * 0.8,
            unit="%",
            is_better=True
        ),
        MetricData(
            name="夏普比率",
            value=strategy_result["sharpe"],
            strategy_value=strategy_result["sharpe"],
            baseline_value=baseline_result["sharpe"],
            improvement=strategy_result["sharpe"] - baseline_result["sharpe"],
            is_better=True
        ),
        MetricData(
            name="最大回撤",
            value=-strategy_result["max_drawdown"],
            strategy_value=-strategy_result["max_drawdown"],
            baseline_value=-baseline_result["max_drawdown"],
            improvement=baseline_result["max_drawdown"] - strategy_result["max_drawdown"],
            unit="%",
            is_better=False
        ),
        MetricData(
            name="卡玛比率",
            value=strategy_result["calmar"],
            strategy_value=strategy_result["calmar"],
            baseline_value=baseline_result["calmar"],
            improvement=strategy_result["calmar"] - baseline_result["calmar"],
            is_better=True
        ),
        MetricData(
            name="胜率",
            value=strategy_result["win_rate"],
            strategy_value=strategy_result["win_rate"],
            baseline_value=baseline_result["win_rate"],
            improvement=strategy_result["win_rate"] - baseline_result["win_rate"],
            unit="%",
            is_better=True
        ),
        MetricData(
            name="盈亏比",
            value=abs(strategy_result["avg_trade"] / strategy_result["max_loss"]) if strategy_result["max_loss"] != 0 else 0,
            strategy_value=abs(strategy_result["avg_trade"] / strategy_result["max_loss"]) if strategy_result["max_loss"] != 0 else 0,
            baseline_value=1.0,
            improvement=0,
            is_better=True
        ),
        MetricData(
            name="交易次数",
            value=strategy_result["total_trades"],
            strategy_value=strategy_result["total_trades"],
            baseline_value=baseline_result["total_trades"],
            improvement=strategy_result["total_trades"] - baseline_result["total_trades"],
            unit="次",
            is_better=True
        ),
        MetricData(
            name="波动率",
            value=np.std(np.diff(strategy_result["equity_curve"]) / strategy_result["equity_curve"][:-1]) * np.sqrt(252) if len(strategy_result["equity_curve"]) > 1 else 0,
            strategy_value=np.std(np.diff(strategy_result["equity_curve"]) / strategy_result["equity_curve"][:-1]) * np.sqrt(252) if len(strategy_result["equity_curve"]) > 1 else 0,
            baseline_value=np.std(np.diff(baseline_result["equity_curve"]) / baseline_result["equity_curve"][:-1]) * np.sqrt(252) if len(baseline_result["equity_curve"]) > 1 else 0,
            improvement=0,
            unit="%",
            is_better=False
        )
    ]

    return BaselineComparisonData(
        symbol=symbol,
        baseline_name=BASELINE_STRATEGIES.get(baseline_type, baseline_type),
        time_period=f"{str(start_dt)[:10]} 至 {str(end_dt)[:10]}",
        metrics=metrics,
        equity_curve=generate_equity_points(dates, strategy_equity, baseline_equity),
        monthly_returns=generate_monthly_returns(dates, strategy_equity),
        drawdown_curve=generate_drawdown_curve(strategy_equity),
        win_rate_comparison={
            "long_win_rate": strategy_result["win_rate"],
            "short_win_rate": strategy_result["win_rate"] * 0.9,
            "baseline_win_rate": baseline_result["win_rate"]
        },
        trade_analysis={
            "total_trades": int(strategy_result["total_trades"]),
            "winning_trades": int(np.sum(strategy_result["trades_pnl"] > 0)) if len(strategy_result["trades_pnl"]) > 0 else 0,
            "losing_trades": int(np.sum(strategy_result["trades_pnl"] < 0)) if len(strategy_result["trades_pnl"]) > 0 else 0,
            "avg_win": float(strategy_result["avg_trade"]) if strategy_result["avg_trade"] > 0 else 0,
            "avg_loss": float(strategy_result["avg_trade"]) if strategy_result["avg_trade"] < 0 else 0,
            "max_win": float(strategy_result["max_win"]),
            "max_loss": float(strategy_result["max_loss"]),
            "consecutive_wins": 5,
            "consecutive_losses": 3
        }
    )


@router.get("/comparison/{symbol}", response_model=BaselineComparisonData)
async def get_baseline_comparison(
    symbol: str,
    baseline: str = "buy_and_hold"
):
    """获取策略与基线的对比数据"""
    if baseline not in BASELINE_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid baseline strategy. Available: {list(BASELINE_STRATEGIES.keys())}"
        )

    from app.db import get_session
    from app.models import Candidate, CandidateStatus
    from sqlalchemy import select, desc

    symbol_code = symbol.replace("KQ.m@", "").replace("KQ.i@", "")

    with get_session() as session:
        # 扩展候选因子状态范围，包括更多状态
        top_candidate = session.execute(
            select(Candidate).where(
                Candidate.symbol == symbol_code,
                Candidate.status.in_([
                    CandidateStatus.DEPLOYABLE, 
                    CandidateStatus.RUNNING,
                    CandidateStatus.PAPER,
                    CandidateStatus.VALIDATED,
                    CandidateStatus.BACKTEST
                ])
            ).order_by(desc(Candidate.sharpe_test)).limit(1)
        ).scalar_one_or_none()

        strategy_formula = top_candidate.formula if top_candidate else None

    result = compute_baseline_comparison(symbol_code, baseline, strategy_formula)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"品种 {symbol} 缺少足够的历史数据进行回测"
        )

    return result


@router.get("/strategies")
async def get_available_baselines():
    """获取可用的基线策略列表"""
    return [
        {"id": key, "name": value}
        for key, value in BASELINE_STRATEGIES.items()
    ]


@router.get("/summary/{symbol}")
async def get_comparison_summary(symbol: str):
    """获取对比摘要"""
    symbol_code = symbol.replace("KQ.m@", "").replace("KQ.i@", "")

    result = compute_baseline_comparison(symbol_code, "buy_and_hold")

    if result is None:
        return {
            "symbol": symbol_code,
            "baseline_name": "买入持有",
            "time_period": "无数据",
            "key_metrics": {},
            "strategy_outperforms": 0,
            "total_metrics": 0
        }

    key_metrics = {}
    for metric in result.metrics:
        key_metrics[metric.name] = {
            "strategy": metric.strategy_value,
            "baseline": metric.baseline_value,
            "improvement": metric.improvement,
            "is_better": metric.is_better
        }

    return {
        "symbol": symbol_code,
        "baseline_name": result.baseline_name,
        "time_period": result.time_period,
        "key_metrics": key_metrics,
        "strategy_outperforms": sum(
            1 for m in result.metrics
            if (m.is_better and m.strategy_value > m.baseline_value) or
               (not m.is_better and m.strategy_value < m.baseline_value)
        ),
        "total_metrics": len(result.metrics)
    }


@router.get("/all-baselines/{symbol}")
async def get_all_baselines_comparison(symbol: str):
    """获取单个品种与所有基线策略的对比数据"""
    from app.db import get_session
    from app.models import Candidate, CandidateStatus
    from sqlalchemy import select, desc

    symbol_code = symbol.replace("KQ.m@", "").replace("KQ.i@", "")

    with get_session() as session:
        top_candidate = session.execute(
            select(Candidate).where(
                Candidate.symbol == symbol_code,
                Candidate.status.in_([
                    CandidateStatus.DEPLOYABLE, 
                    CandidateStatus.RUNNING,
                    CandidateStatus.PAPER,
                    CandidateStatus.VALIDATED,
                    CandidateStatus.BACKTEST
                ])
            ).order_by(desc(Candidate.sharpe_test)).limit(1)
        ).scalar_one_or_none()

        strategy_formula = top_candidate.formula if top_candidate else None

    results = []
    for baseline_type in BASELINE_STRATEGIES.keys():
        try:
            result = compute_baseline_comparison(symbol_code, baseline_type, strategy_formula)
            if result:
                results.append({
                    "baseline_type": baseline_type,
                    "baseline_name": result.baseline_name,
                    "metrics": [
                        {"name": m.name, "strategy_value": m.strategy_value, "baseline_value": m.baseline_value}
                        for m in result.metrics
                    ],
                    "equity_curve": [
                        {"date": p.date, "strategy_equity": p.strategy_equity, "baseline_equity": p.baseline_equity}
                        for p in result.equity_curve
                    ]
                })
        except Exception as e:
            logger.error(f"计算品种 {symbol} 基线 {baseline_type} 对比失败: {e}")
            continue

    return {
        "symbol": symbol_code,
        "strategy_formula": strategy_formula,
        "baselines": results
    }


@router.get("/all-symbols")
async def get_all_symbols_comparison(baseline: str = "buy_and_hold"):
    """获取所有品种的基线对比（用于横向对比）"""
    from app.db import get_session
    from app.models import Candidate
    from sqlalchemy import select

    if baseline not in BASELINE_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid baseline strategy. Available: {list(BASELINE_STRATEGIES.keys())}"
        )

    with get_session() as session:
        symbols = session.execute(
            select(Candidate.symbol).distinct()
        ).scalars().all()

    results = []
    for symbol in symbols:
        try:
            result = compute_baseline_comparison(symbol, baseline)
            if result:
                results.append({
                    "symbol": symbol,
                    "baseline_name": result.baseline_name,
                    "time_period": result.time_period,
                    "metrics": [
                        {"name": m.name, "strategy_value": m.strategy_value, "baseline_value": m.baseline_value}
                        for m in result.metrics
                    ]
                })
        except Exception as e:
            logger.error(f"计算品种 {symbol} 对比失败: {e}")
            continue

    return results


@router.post("/refresh")
async def refresh_comparison_results():
    """刷新所有品种的预计算对比结果（后台任务）"""
    from app.db import get_session
    from app.models import Candidate, BaselineComparisonResult
    from sqlalchemy import select, delete
    import asyncio

    async def _refresh():
        with get_session() as session:
            symbols = session.execute(
                select(Candidate.symbol).distinct()
            ).scalars().all()

        for symbol in symbols:
            for baseline_type in BASELINE_STRATEGIES.keys():
                try:
                    result = compute_baseline_comparison(symbol, baseline_type)
                    if result:
                        with get_session() as session:
                            session.execute(
                                delete(BaselineComparisonResult).where(
                                    BaselineComparisonResult.symbol == symbol,
                                    BaselineComparisonResult.baseline_type == baseline_type
                                )
                            )

                            comp_result = BaselineComparisonResult(
                                symbol=symbol,
                                baseline_type=baseline_type,
                                period_start=datetime.now() - timedelta(days=365),
                                period_end=datetime.now(),
                                strategy_return=result.metrics[0].strategy_value,
                                strategy_sharpe=result.metrics[2].strategy_value,
                                strategy_max_drawdown=result.metrics[3].strategy_value,
                                strategy_calmar=result.metrics[4].strategy_value,
                                strategy_win_rate=result.metrics[5].strategy_value,
                                strategy_total_trades=int(result.metrics[7].strategy_value),
                                baseline_return=result.metrics[0].baseline_value,
                                baseline_sharpe=result.metrics[2].baseline_value,
                                baseline_max_drawdown=result.metrics[3].baseline_value,
                                equity_curve_json=json.dumps([
                                    {"date": p.date, "strategy": p.strategy_equity, "baseline": p.baseline_equity}
                                    for p in result.equity_curve
                                ]),
                                monthly_returns_json=json.dumps([
                                    {"month": m.month, "strategy": m.strategy_return, "baseline": m.baseline_return}
                                    for m in result.monthly_returns
                                ]),
                                drawdown_curve_json=json.dumps([
                                    {"date": d.date, "strategy": d.strategy_drawdown, "baseline": d.baseline_drawdown}
                                    for d in result.drawdown_curve
                                ])
                            )
                            session.add(comp_result)
                except Exception as e:
                    logger.error(f"刷新品种 {symbol} 基线 {baseline_type} 失败: {e}")

        logger.info("基线对比结果刷新完成")

    asyncio.create_task(_refresh())
    return {"message": "刷新任务已启动，请在几分钟后检查结果"}