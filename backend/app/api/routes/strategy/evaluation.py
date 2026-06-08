"""
策略评估API
提供策略评分计算和排名展示功能，让评选过程透明可见
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy import select, desc
from datetime import datetime
import logging

from app.models import Candidate, CandidateStatus
from app.db import get_session

router = APIRouter(prefix="/strategy", tags=["strategy"])

logger = logging.getLogger(__name__)

# 评分权重配置
STRATEGY_WEIGHTS = {
    "sharpe_test": 0.40,
    "calmar": 0.20,
    "max_drawdown": 0.20,
    "win_rate": 0.10,
    "sample_size": 0.10,
}


class ScoreComponent(BaseModel):
    name: str
    weight: float
    value: float
    contribution: float


class StrategyScoreDetail(BaseModel):
    id: str
    symbol: str
    formula: str
    sharpe_test: float
    calmar: float
    max_drawdown: float
    win_rate: float
    total_trades: float
    score_components: List[ScoreComponent]
    total_score: float
    rank: int


def calculate_strategy_score(candidate: Any) -> Dict[str, Any]:
    """计算策略综合评分及其各成分"""
    sharpe = candidate.sharpe_test or candidate.sharpe_val or 0
    calmar = candidate.calmar or 0
    max_dd = candidate.max_drawdown or 0
    win_rate = candidate.win_rate or 0
    total_trades = candidate.total_trades or 0

    # 计算各成分得分
    drawdown_score = max(0, 1 - abs(max_dd)) if max_dd != 0 else 0.5
    sample_score = 1.0 if total_trades >= 30 else total_trades / 30

    # 计算各成分贡献
    components = [
        {
            "name": "夏普比率",
            "weight": STRATEGY_WEIGHTS["sharpe_test"],
            "value": sharpe,
            "contribution": STRATEGY_WEIGHTS["sharpe_test"] * max(0, sharpe),
        },
        {
            "name": "卡玛比率",
            "weight": STRATEGY_WEIGHTS["calmar"],
            "value": calmar,
            "contribution": STRATEGY_WEIGHTS["calmar"] * max(0, calmar),
        },
        {
            "name": "最大回撤",
            "weight": STRATEGY_WEIGHTS["max_drawdown"],
            "value": max_dd,
            "contribution": STRATEGY_WEIGHTS["max_drawdown"] * drawdown_score,
        },
        {
            "name": "胜率",
            "weight": STRATEGY_WEIGHTS["win_rate"],
            "value": win_rate,
            "contribution": STRATEGY_WEIGHTS["win_rate"] * win_rate,
        },
        {
            "name": "样本充足度",
            "weight": STRATEGY_WEIGHTS["sample_size"],
            "value": total_trades,
            "contribution": STRATEGY_WEIGHTS["sample_size"] * sample_score,
        },
    ]

    total_score = sum(comp["contribution"] for comp in components)

    return {
        "components": components,
        "total_score": total_score,
    }


@router.get(
    "/correlation-matrix",
    summary="计算因子相关性矩阵",
    description="计算IC筛选因子之间的相关性矩阵",
)
async def calculate_correlation_matrix(
    symbol: str,
    generation: Optional[int] = None,
) -> Dict[str, Any]:
    """
    计算因子相关性矩阵

    Args:
        symbol: 品种代码
        generation: 代数（可选）

    Returns:
        相关性矩阵
    """
    from quant_engine.ops.strategy_selector import StrategySelector

    try:
        # 获取IC筛选的前50个因子
        with get_session() as session:
            query = select(Candidate).where(
                Candidate.symbol == symbol,
                Candidate.status == CandidateStatus.APPROVED,
                Candidate.ic_mean_24h.isnot(None)
            )

            if generation:
                query = query.where(Candidate.generation == generation)

            query = query.order_by(desc(Candidate.ic_mean_24h)).limit(50)
            result = session.execute(query)
            candidates = result.scalars().all()

        if not candidates:
            return {
                "symbol": symbol,
                "factors": [],
                "matrix": [],
                "factor_ids": [],
            }

        # 使用策略选择器计算相关性
        selector = StrategySelector()
        factor_ids = [c.id for c in candidates]
        correlation_matrix = selector.calculate_correlation_matrix(factor_ids)

        return {
            "symbol": symbol,
            "factors": [
                {
                    "id": c.id,
                    "formula": c.formula,
                    "ic_mean_24h": c.ic_mean_24h,
                }
                for c in candidates
            ],
            "matrix": correlation_matrix,
            "factor_ids": factor_ids,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"计算相关性矩阵失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="计算相关性矩阵失败")


@router.post(
    "/generate-strategies",
    summary="生成策略组合",
    description="从前50个IC筛选因子中选择5个策略，考虑相关性",
)
async def generate_strategies(
    symbol: str,
    generation: Optional[int] = None,
    max_correlation: float = 0.7,
) -> Dict[str, Any]:
    """
    生成策略组合

    Args:
        symbol: 品种代码
        generation: 代数（可选）
        max_correlation: 最大相关性阈值

    Returns:
        策略组合
    """
    from quant_engine.ops.strategy_selector import StrategySelector

    try:
        # 获取IC筛选的前50个因子
        with get_session() as session:
            query = select(Candidate).where(
                Candidate.symbol == symbol,
                Candidate.status == CandidateStatus.APPROVED,
                Candidate.ic_mean_24h.isnot(None)
            )

            if generation:
                query = query.where(Candidate.generation == generation)

            query = query.order_by(desc(Candidate.ic_mean_24h)).limit(50)
            result = session.execute(query)
            candidates = result.scalars().all()

        if not candidates:
            return {
                "symbol": symbol,
                "strategies": [],
                "total_factors": 0,
            }

        # 使用策略选择器生成策略
        selector = StrategySelector()
        factor_ids = [c.id for c in candidates]
        selected_strategies = selector.select_strategies(
            factor_ids,
            max_strategies=5,
            max_correlation=max_correlation
        )

        # 获取策略详情
        strategy_details = []
        for strategy_id in selected_strategies:
            candidate = next((c for c in candidates if c.id == strategy_id), None)
            if candidate:
                score = calculate_strategy_score(candidate)
                strategy_details.append({
                    "id": candidate.id,
                    "formula": candidate.formula,
                    "ic_mean_24h": candidate.ic_mean_24h,
                    "sharpe_train": candidate.sharpe_train,
                    "total_score": score["total_score"],
                    "score_components": score["components"],
                })

        return {
            "symbol": symbol,
            "strategies": strategy_details,
            "total_factors": len(candidates),
            "selected_count": len(selected_strategies),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成策略失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="生成策略失败")


@router.get("/evaluation/{symbol}", response_model=List[StrategyScoreDetail])
def get_strategy_evaluation(symbol: str):
    """
    获取指定品种的策略评估详情
    返回该品种所有候选策略的评分计算过程
    """
    try:
        with get_session() as session:
            # 获取该品种的所有有效候选策略
            candidates = session.execute(
                select(Candidate).where(
                    Candidate.symbol == symbol.upper(),
                    Candidate.status.in_(
                        [
                            CandidateStatus.DEPLOYABLE,
                            CandidateStatus.RUNNING,
                            CandidateStatus.PAPER,
                            CandidateStatus.VALIDATED,
                        ]
                    ),
                    Candidate.sharpe_test.isnot(None),
                )
            ).scalars().all()

            if not candidates:
                return []

            # 计算每个策略的评分
            scored_strategies = []
            for candidate in candidates:
                score_result = calculate_strategy_score(candidate)
                scored_strategies.append(
                    {
                        "id": candidate.id,
                        "symbol": candidate.symbol,
                        "formula": candidate.formula,
                        "sharpe_test": candidate.sharpe_test or 0,
                        "calmar": candidate.calmar or 0,
                        "max_drawdown": candidate.max_drawdown or 0,
                        "win_rate": candidate.win_rate or 0,
                        "total_trades": candidate.total_trades or 0,
                        "score_components": score_result["components"],
                        "total_score": score_result["total_score"],
                        "rank": 0,
                    }
                )

            # 按综合得分排序并分配排名
            scored_strategies.sort(
                key=lambda x: x["total_score"], reverse=True
            )
            for i, strategy in enumerate(scored_strategies):
                strategy["rank"] = i + 1

            return scored_strategies

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略评估失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取策略评估失败")


@router.get("/evaluation/ranking/{symbol}")
def get_strategy_ranking(symbol: str):
    """
    获取指定品种的策略排名（仅返回排名信息）
    """
    try:
        with get_session() as session:
            candidates = session.execute(
                select(Candidate).where(
                    Candidate.symbol == symbol.upper(),
                    Candidate.status.in_(
                        [
                            CandidateStatus.DEPLOYABLE,
                            CandidateStatus.RUNNING,
                            CandidateStatus.PAPER,
                            CandidateStatus.VALIDATED,
                        ]
                    ),
                    Candidate.sharpe_test.isnot(None),
                )
            ).scalars().all()

            if not candidates:
                return {"symbol": symbol, "strategies": [], "count": 0}

            scored_strategies = []
            for candidate in candidates:
                score_result = calculate_strategy_score(candidate)
                scored_strategies.append(
                    {
                        "id": candidate.id,
                        "formula": candidate.formula,
                        "sharpe_test": candidate.sharpe_test or 0,
                        "max_drawdown": candidate.max_drawdown or 0,
                        "total_trades": candidate.total_trades or 0,
                        "total_score": score_result["total_score"],
                    }
                )

            scored_strategies.sort(
                key=lambda x: x["total_score"], reverse=True
            )

            return {
                "symbol": symbol,
                "strategies": scored_strategies,
                "count": len(scored_strategies),
                "top_strategy": scored_strategies[0] if scored_strategies else None,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略排名失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取策略排名失败")


@router.get("/evaluation/scoring-rules")
def get_scoring_rules():
    """
    获取评分规则配置
    """
    return {
        "weights": STRATEGY_WEIGHTS,
        "rules": [
            {
                "name": "夏普比率(测试集)",
                "weight": STRATEGY_WEIGHTS["sharpe_test"],
                "description": "衡量风险调整后收益，越高越好",
                "is_better_higher": True,
                "formula": "sharpe_test",
            },
            {
                "name": "卡玛比率",
                "weight": STRATEGY_WEIGHTS["calmar"],
                "description": "收益/最大回撤，衡量回报风险比",
                "is_better_higher": True,
                "formula": "calmar",
            },
            {
                "name": "最大回撤",
                "weight": STRATEGY_WEIGHTS["max_drawdown"],
                "description": "控制下行风险，越小越好",
                "is_better_higher": False,
                "formula": "1 - |max_drawdown|",
            },
            {
                "name": "胜率",
                "weight": STRATEGY_WEIGHTS["win_rate"],
                "description": "盈利交易占比，越高越好",
                "is_better_higher": True,
                "formula": "win_rate",
            },
            {
                "name": "样本充足度",
                "weight": STRATEGY_WEIGHTS["sample_size"],
                "description": "交易次数充足性，≥30次为满分",
                "is_better_higher": True,
                "formula": "min(total_trades/30, 1)",
            },
        ],
    }