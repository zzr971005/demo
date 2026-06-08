"""
相关性分析API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import CorrelationMatrix

router = APIRouter(prefix="/api/correlation-analysis", tags=["correlation-analysis"])


class CorrelationMatrixRequest(BaseModel):
    symbols: List[str]
    period: str = "1d"


@router.post("/matrix")
async def get_correlation_matrix(request: CorrelationMatrixRequest) -> Dict[str, Any]:
    """获取相关性矩阵"""
    with get_session() as session:
        # Get correlation data for the requested period
        query = select(CorrelationMatrix).where(CorrelationMatrix.period == request.period)
        result = session.execute(query)
        correlations = result.scalars().all()
        
        # Build correlation matrix
        matrix = {}
        total_correlation = 0.0
        count = 0
        
        for c in correlations:
            symbol_pair = c.symbol_pair  # "RB,MA"
            if symbol_pair in matrix:
                matrix[symbol_pair] = c.correlation
                total_correlation += abs(c.correlation)
                count += 1
        
        avg_correlation = total_correlation / count if count > 0 else 0.0
        
        return {
            "correlation_matrix": matrix,
            "avg_correlation": avg_correlation
        }


@router.get("/highly-correlated")
async def get_highly_correlated_pairs(
    threshold: float = 0.7
) -> Dict[str, Any]:
    """获取高相关性策略对"""
    with get_session() as session:
        # Get correlations above threshold
        query = select(CorrelationMatrix).where(CorrelationMatrix.correlation >= threshold)
        result = session.execute(query)
        correlations = result.scalars().all()
        
        pairs = [{"symbol_pair": c.symbol_pair, "correlation": c.correlation} for c in correlations]
        
        return {
            "pairs": pairs
        }


@router.post("/diversify")
async def diversify_portfolio(
    strategies: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """分散化组合"""
    with get_session() as session:
        # Extract symbols from strategies
        symbols = [s.get("symbol") for s in strategies if s.get("symbol")]
        
        if len(symbols) < 2:
            return {
                "diversified_strategies": strategies,
                "message": "需要至少2个策略进行分散化"
            }
        
        # Get correlation data for these symbols
        query = select(CorrelationMatrix).where(
            CorrelationMatrix.period == "1d"
        )
        result = session.execute(query)
        correlations = result.scalars().all()
        
        # Build correlation map
        corr_map = {}
        for c in correlations:
            symbol_pair = c.symbol_pair
            corr_map[symbol_pair] = c.correlation
        
        # Calculate diversification score for each strategy
        strategy_scores = []
        for i, strategy in enumerate(strategies):
            symbol = strategy.get("symbol")
            if not symbol:
                continue
            
            # Calculate average correlation with other strategies
            avg_corr = 0.0
            corr_count = 0
            
            for j, other_strategy in enumerate(strategies):
                if i == j:
                    continue
                other_symbol = other_strategy.get("symbol")
                if not other_symbol:
                    continue
                
                # Check both orderings of the pair
                pair1 = f"{symbol},{other_symbol}"
                pair2 = f"{other_symbol},{symbol}"
                
                corr = corr_map.get(pair1, corr_map.get(pair2, 0.0))
                avg_corr += abs(corr)
                corr_count += 1
            
            if corr_count > 0:
                avg_corr /= corr_count
            
            # Lower correlation = better diversification
            diversification_score = 1.0 - avg_corr
            strategy_scores.append({
                "strategy": strategy,
                "diversification_score": diversification_score,
                "avg_correlation": avg_corr
            })
        
        # Sort by diversification score (higher is better)
        strategy_scores.sort(key=lambda x: x["diversification_score"], reverse=True)
        
        # Return diversified strategies
        diversified_strategies = [item["strategy"] for item in strategy_scores]
        
        return {
            "diversified_strategies": diversified_strategies,
            "diversification_scores": [
                {
                    "symbol": item["strategy"].get("symbol"),
                    "score": item["diversification_score"],
                    "avg_correlation": item["avg_correlation"]
                }
                for item in strategy_scores
            ]
        }
