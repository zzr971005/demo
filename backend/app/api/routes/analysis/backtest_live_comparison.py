"""
回测实盘对比API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select

from app.db import get_session
from app.models import BacktestLiveComparison

router = APIRouter(prefix="/api/backtest-live-comparison", tags=["backtest-live-comparison"])


@router.get("/comparison/{strategy_id}")
async def get_backtest_live_comparison(strategy_id: str) -> Dict[str, Any]:
    """获取回测实盘对比"""
    with get_session() as session:
        # Get the most recent comparison for this strategy
        query = select(BacktestLiveComparison).where(
            BacktestLiveComparison.strategy_id == strategy_id
        ).order_by(BacktestLiveComparison.comparison_date.desc()).limit(1)
        result = session.execute(query)
        comparison = result.scalar_one_or_none()
        
        if comparison:
            return {
                "strategy_id": strategy_id,
                "backtest_metrics": {
                    "sharpe_ratio": comparison.backtest_sharpe,
                    "return": comparison.backtest_return,
                },
                "live_metrics": {
                    "sharpe_ratio": comparison.live_sharpe,
                    "return": comparison.live_return,
                },
                "differences": {
                    "sharpe_diff": comparison.backtest_sharpe - comparison.live_sharpe,
                    "return_diff": comparison.backtest_return - comparison.live_return,
                },
                "overfitting_detected": comparison.overfitting_detected,
                "overall_health": comparison.overall_health,
                "comparison_date": comparison.comparison_date.isoformat(),
            }
        else:
            return {
                "strategy_id": strategy_id,
                "backtest_metrics": {},
                "live_metrics": {},
                "differences": {},
                "overfitting_detected": False
            }


@router.post("/compare")
async def compare_backtest_live(
    strategy_id: str = Query(..., description="策略ID"),
    period: Optional[str] = Query(default="30d", description="对比周期")
) -> Dict[str, Any]:
    """执行回测实盘对比"""
    with get_session() as session:
        # Get the most recent comparison for this strategy
        query = select(BacktestLiveComparison).where(
            BacktestLiveComparison.strategy_id == strategy_id
        ).order_by(BacktestLiveComparison.comparison_date.desc()).limit(1)
        result = session.execute(query)
        comparison = result.scalar_one_or_none()
        
        if comparison:
            return {
                "strategy_id": strategy_id,
                "backtest_metrics": {
                    "sharpe_ratio": comparison.backtest_sharpe,
                    "return": comparison.backtest_return,
                    "max_drawdown": comparison.backtest_max_drawdown,
                },
                "live_metrics": {
                    "sharpe_ratio": comparison.live_sharpe,
                    "return": comparison.live_return,
                    "max_drawdown": comparison.live_max_drawdown,
                },
                "differences": {
                    "sharpe_diff": comparison.backtest_sharpe - comparison.live_sharpe,
                    "return_diff": comparison.backtest_return - comparison.live_return,
                    "max_drawdown_diff": comparison.backtest_max_drawdown - comparison.live_max_drawdown,
                },
                "overfitting_detected": comparison.overfitting_detected,
                "overall_health": comparison.overall_health,
                "comparison_date": comparison.comparison_date.isoformat(),
                "period": period,
            }
        else:
            return {
                "strategy_id": strategy_id,
                "backtest_metrics": {},
                "live_metrics": {},
                "differences": {},
                "overfitting_detected": False,
                "overall_health": False,
                "period": period,
                "message": "No comparison data available"
            }


@router.get("/report/{strategy_id}")
async def generate_comparison_report(strategy_id: str) -> Dict[str, Any]:
    """生成对比报告"""
    with get_session() as session:
        # Get the most recent comparison for this strategy
        query = select(BacktestLiveComparison).where(
            BacktestLiveComparison.strategy_id == strategy_id
        ).order_by(BacktestLiveComparison.comparison_date.desc()).limit(1)
        result = session.execute(query)
        comparison = result.scalar_one_or_none()
        
        if not comparison:
            return {
                "strategy_id": strategy_id,
                "report_date": datetime.utcnow().isoformat(),
                "overall_health": False,
                "message": "No comparison data available"
            }
        
        # Calculate differences
        sharpe_diff = comparison.backtest_sharpe - comparison.live_sharpe
        return_diff = comparison.backtest_return - comparison.live_return
        
        # Determine overall health based on differences
        # If live performance is significantly worse than backtest, it may indicate overfitting
        sharpe_ratio_threshold = 0.5  # 50% difference in Sharpe ratio
        return_threshold = 0.3  # 30% difference in return
        
        sharpe_health = abs(sharpe_diff) < sharpe_ratio_threshold
        return_health = abs(return_diff) < return_threshold
        
        overall_health = sharpe_health and return_health
        
        # Generate detailed report
        report = {
            "strategy_id": strategy_id,
            "report_date": datetime.utcnow().isoformat(),
            "comparison_date": comparison.comparison_date.isoformat(),
            "overall_health": overall_health,
            "metrics": {
                "backtest": {
                    "sharpe_ratio": comparison.backtest_sharpe,
                    "return": comparison.backtest_return,
                    "max_drawdown": comparison.backtest_max_drawdown
                },
                "live": {
                    "sharpe_ratio": comparison.live_sharpe,
                    "return": comparison.live_return,
                    "max_drawdown": comparison.live_max_drawdown
                }
            },
            "differences": {
                "sharpe_diff": sharpe_diff,
                "return_diff": return_diff,
                "sharpe_diff_pct": (sharpe_diff / comparison.backtest_sharpe * 100) if comparison.backtest_sharpe else 0,
                "return_diff_pct": (return_diff / comparison.backtest_return * 100) if comparison.backtest_return else 0
            },
            "health_indicators": {
                "sharpe_health": sharpe_health,
                "return_health": return_health,
                "overfitting_detected": comparison.overfitting_detected
            },
            "recommendations": []
        }
        
        # Add recommendations based on health indicators
        if not sharpe_health:
            report["recommendations"].append("实盘Sharpe比率与回测差异较大，可能存在过拟合")
        if not return_health:
            report["recommendations"].append("实盘收益率与回测差异较大，需要检查策略参数")
        if comparison.overfitting_detected:
            report["recommendations"].append("检测到过拟合风险，建议重新训练或简化策略")
        
        if overall_health:
            report["recommendations"].append("策略表现健康，可继续运行")
        
        return report
