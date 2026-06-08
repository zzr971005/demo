"""
实盘交易API

提供因子上线/下线、实盘性能监控等功能
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_config
from app.config import Settings
from quant_engine.ops.evolution_service import get_evolution_service

router = APIRouter(tags=["live_trading"])

# 获取进化服务实例
evolution_service = get_evolution_service()


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class FactorDeployRequest(BaseModel):
    """因子部署请求"""
    factor_id: str = Field(..., description="因子ID")


class FactorDeployResponse(BaseModel):
    """因子部署响应"""
    success: bool
    factor_id: str
    symbol: Optional[str] = None
    message: str


class FactorRemoveRequest(BaseModel):
    """因子移除请求"""
    factor_id: str = Field(..., description="因子ID")


class FactorRemoveResponse(BaseModel):
    """因子移除响应"""
    success: bool
    factor_id: str
    message: str


class LiveFactorInfo(BaseModel):
    """实盘因子信息"""
    factor_id: str
    task_id: str
    symbol: str
    expression: str
    generation: int
    origin: str
    sharpe_ratio: float
    calmar_ratio: float
    max_drawdown: float
    total_return: float
    win_rate: float
    total_trades: int
    avg_trade_pnl: float
    turnover_rate: float
    pbo: Optional[float] = None
    dsr: Optional[float] = None
    wfe: Optional[float] = None
    overfitting_passed: bool
    node_count: int
    tree_depth: int
    is_live: bool
    is_candidate: bool
    live_since: Optional[str] = None
    rank_in_generation: Optional[int] = None
    overall_rank: Optional[int] = None
    created_at: str
    # 实盘统计
    live_stats: Optional[Dict[str, Any]] = None


class LiveStatsUpdateRequest(BaseModel):
    """实盘统计更新请求"""
    live_sharpe_ratio: Optional[float] = None
    live_total_return: Optional[float] = None
    live_max_drawdown: Optional[float] = None
    live_win_rate: Optional[float] = None
    live_total_trades: Optional[int] = None
    live_pnl_total: Optional[float] = None
    live_pnl_daily: Optional[float] = None
    days_running: Optional[int] = None


class LiveStatsResponse(BaseModel):
    """实盘统计响应"""
    success: bool
    factor_id: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class LivePerformanceSummary(BaseModel):
    """实盘性能汇总"""
    count: int
    avg_live_sharpe: float
    avg_live_return: float
    avg_performance_decay: float
    positive_sharpe_ratio: float
    factors: List[Dict[str, Any]]


class CandidateFactorInfo(BaseModel):
    """候选因子信息"""
    factor_id: str
    task_id: str
    symbol: str
    expression: str
    generation: int
    origin: str
    sharpe_ratio: float
    calmar_ratio: float
    max_drawdown: float
    total_return: float
    win_rate: float
    total_trades: int
    pbo: Optional[float] = None
    dsr: Optional[float] = None
    wfe: Optional[float] = None
    overfitting_passed: bool
    node_count: int
    tree_depth: int
    rank_in_generation: Optional[int] = None
    overall_rank: Optional[int] = None
    created_at: str


# ---------------------------------------------------------------------------
# API端点 - 因子上线/下线
# ---------------------------------------------------------------------------

@router.post(
    "/live/deploy",
    response_model=FactorDeployResponse,
    summary="部署因子到实盘",
    description="将因子从候选状态部署到实盘交易",
)
async def deploy_factor(
    request: FactorDeployRequest,
) -> FactorDeployResponse:
    """部署因子到实盘"""
    result = evolution_service.deploy_to_live(request.factor_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "部署失败"),
        )

    return FactorDeployResponse(
        success=True,
        factor_id=result["factor_id"],
        symbol=result.get("symbol"),
        message="因子已成功部署到实盘",
    )


@router.post(
    "/live/remove",
    response_model=FactorRemoveResponse,
    summary="从实盘移除因子",
    description="将因子从实盘交易中移除",
)
async def remove_factor(
    request: FactorRemoveRequest,
) -> FactorRemoveResponse:
    """从实盘移除因子"""
    result = evolution_service.remove_from_live(request.factor_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "移除失败"),
        )

    return FactorRemoveResponse(
        success=True,
        factor_id=result["factor_id"],
        message="因子已从实盘移除",
    )


@router.post(
    "/live/candidate/{factor_id}",
    response_model=FactorDeployResponse,
    summary="标记为候选因子",
    description="将因子标记为候选状态，准备部署",
)
async def mark_as_candidate(
    factor_id: str,
) -> FactorDeployResponse:
    """标记为候选因子"""
    result = evolution_service.mark_as_candidate(factor_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "标记失败"),
        )

    return FactorDeployResponse(
        success=True,
        factor_id=result["factor_id"],
        message="因子已标记为候选",
    )


# ---------------------------------------------------------------------------
# API端点 - 实盘因子查询
# ---------------------------------------------------------------------------

@router.get(
    "/live/factors",
    response_model=Dict[str, Any],
    summary="获取实盘因子列表",
    description="获取当前正在实盘交易的因子列表",
)
async def get_live_factors(
    symbol: Optional[str] = Query(default=None, description="品种代码，为空返回所有品种"),
) -> Dict[str, Any]:
    """获取实盘因子列表"""
    factors = evolution_service.get_live_factors(symbol)

    return {
        "symbol": symbol or "all",
        "total": len(factors),
        "factors": factors,
    }


@router.get(
    "/live/candidates",
    response_model=Dict[str, Any],
    summary="获取候选因子列表",
    description="获取候选状态的因子列表",
)
async def get_candidate_factors(
    symbol: Optional[str] = Query(default=None, description="品种代码，为空返回所有品种"),
) -> Dict[str, Any]:
    """获取候选因子列表"""
    factors = evolution_service.get_candidate_factors(symbol)

    return {
        "symbol": symbol or "all",
        "total": len(factors),
        "factors": factors,
    }


@router.get(
    "/live/factors/{factor_id}",
    response_model=Dict[str, Any],
    summary="获取实盘因子详情",
    description="获取指定实盘因子的详细信息和统计",
)
async def get_live_factor_detail(
    factor_id: str,
) -> Dict[str, Any]:
    """获取实盘因子详情"""
    factor = evolution_service.get_factor(factor_id)

    if not factor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"因子 {factor_id} 不存在",
        )

    # 获取实盘统计
    live_stats = evolution_service.get_live_stats(factor_id)

    return {
        "factor": factor,
        "live_stats": live_stats,
    }


# ---------------------------------------------------------------------------
# API端点 - 实盘性能监控
# ---------------------------------------------------------------------------

@router.post(
    "/live/stats/{factor_id}",
    response_model=LiveStatsResponse,
    summary="更新因子实盘统计",
    description="更新指定因子的实盘交易统计数据",
)
async def update_live_stats(
    factor_id: str,
    request: LiveStatsUpdateRequest,
) -> LiveStatsResponse:
    """更新因子实盘统计"""
    stats_data = request.model_dump(exclude_none=True)

    result = evolution_service.update_live_stats(factor_id, stats_data)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "更新失败"),
        )

    return LiveStatsResponse(
        success=True,
        factor_id=factor_id,
        data=result.get("data"),
        message="实盘统计已更新",
    )


@router.get(
    "/live/stats/{factor_id}",
    response_model=Dict[str, Any],
    summary="获取因子实盘统计",
    description="获取指定因子的实盘交易统计数据",
)
async def get_live_stats(
    factor_id: str,
) -> Dict[str, Any]:
    """获取因子实盘统计"""
    stats = evolution_service.get_live_stats(factor_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"因子 {factor_id} 的实盘统计不存在",
        )

    return {
        "factor_id": factor_id,
        "stats": stats,
    }


@router.get(
    "/live/summary",
    response_model=Dict[str, Any],
    summary="获取实盘性能汇总",
    description="获取所有实盘因子的性能汇总统计",
)
async def get_live_performance_summary(
    symbol: Optional[str] = Query(default=None, description="品种代码，为空返回所有品种"),
) -> Dict[str, Any]:
    """获取实盘性能汇总"""
    summary = evolution_service.get_live_performance_summary(symbol)

    return summary


@router.get(
    "/live/all-stats",
    response_model=Dict[str, Any],
    summary="获取所有实盘因子统计",
    description="获取所有活跃实盘因子的详细统计",
)
async def get_all_live_stats(
    symbol: Optional[str] = Query(default=None, description="品种代码，为空返回所有品种"),
) -> Dict[str, Any]:
    """获取所有实盘因子统计"""
    stats = evolution_service.get_all_live_stats(symbol)

    return {
        "symbol": symbol or "all",
        "total": len(stats),
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# API端点 - 因子对比分析
# ---------------------------------------------------------------------------

@router.get(
    "/live/compare",
    response_model=Dict[str, Any],
    summary="对比回测与实盘表现",
    description="对比因子的回测表现与实盘表现",
)
async def compare_backtest_live(
    factor_ids: str = Query(..., description="逗号分隔的因子ID列表"),
) -> Dict[str, Any]:
    """对比回测与实盘表现"""
    factor_id_list = [f.strip() for f in factor_ids.split(",")]

    comparisons = []
    for factor_id in factor_id_list:
        factor = evolution_service.get_factor(factor_id)
        stats = evolution_service.get_live_stats(factor_id)

        if factor and stats:
            comparisons.append({
                "factor_id": factor_id,
                "symbol": factor["symbol"],
                "expression": factor["expression"],
                "backtest": {
                    "sharpe_ratio": factor["sharpe_ratio"],
                    "total_return": factor["total_return"],
                    "max_drawdown": factor["max_drawdown"],
                    "win_rate": factor["win_rate"],
                },
                "live": {
                    "sharpe_ratio": stats["live_sharpe_ratio"],
                    "total_return": stats["live_total_return"],
                    "max_drawdown": stats["live_max_drawdown"],
                    "win_rate": stats["live_win_rate"],
                    "total_trades": stats["live_total_trades"],
                    "pnl_total": stats["live_pnl_total"],
                },
                "decay": stats["performance_decay"],
                "days_running": stats["days_running"],
            })

    return {
        "total": len(comparisons),
        "comparisons": comparisons,
    }
