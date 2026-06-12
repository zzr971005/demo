"""
组合优化API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select
import uuid
import numpy as np

from app.db import get_session
from app.models import PortfolioOptimization, Candidate

router = APIRouter(prefix="/api/portfolio-optimization", tags=["portfolio-optimization"])


class OptimizationRequest(BaseModel):
    strategies: List[str]
    optimization_method: str = "risk_parity"
    target_return: Optional[float] = None


@router.post("/optimize")
async def optimize_portfolio(request: OptimizationRequest) -> Dict[str, Any]:
    """优化组合"""
    with get_session() as session:
        # Get candidate strategies data for optimization
        query = select(Candidate).where(Candidate.id.in_(request.strategies))
        result = session.execute(query)
        candidates = result.scalars().all()
        
        if len(candidates) != len(request.strategies):
            raise HTTPException(
                status_code=404,
                detail=f"Some strategies not found. Found {len(candidates)} of {len(request.strategies)}"
            )
        
        # Extract performance metrics
        sharpe_ratios = []
        returns = []
        for candidate in candidates:
            sharpe_ratios.append(candidate.sharpe_val if candidate.sharpe_val else 0.0)
            returns.append(candidate.return_val if candidate.return_val else 0.0)
        
        # Perform optimization based on method
        if request.optimization_method == "equal_weight":
            # Equal weight allocation
            weights = {s: 1.0 / len(request.strategies) for s in request.strategies}
        elif request.optimization_method == "risk_parity":
            # Risk parity: allocate based on inverse of volatility (simplified as inverse of Sharpe)
            total_inv_sharpe = sum(1.0 / (s + 1e-6) for s in sharpe_ratios)
            weights = {
                request.strategies[i]: (1.0 / (sharpe_ratios[i] + 1e-6)) / total_inv_sharpe
                for i in range(len(request.strategies))
            }
        elif request.optimization_method == "max_sharpe":
            # Maximize Sharpe ratio (simplified: allocate to highest Sharpe)
            max_idx = np.argmax(sharpe_ratios)
            weights = {s: 0.0 for s in request.strategies}
            weights[request.strategies[max_idx]] = 1.0
        else:
            # Default to equal weight
            weights = {s: 1.0 / len(request.strategies) for s in request.strategies}
        
        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Create optimization record
        optimization_id = f"opt_{uuid.uuid4().hex[:16]}"
        optimization = PortfolioOptimization(
            id=optimization_id,
            optimization_method=request.optimization_method,
            target_return=request.target_return,
            weights_json=str(weights),
            optimized_at=datetime.utcnow(),
            created_by="api"
        )
        session.add(optimization)
        session.commit()
        
        return {
            "success": True,
            "optimization_id": optimization_id,
            "weights": weights,
            "optimized_at": datetime.utcnow()
        }


@router.get("/metrics")
async def get_portfolio_metrics() -> Dict[str, Any]:
    """获取组合指标"""
    with get_session() as session:
        # Get the most recent optimization
        query = select(PortfolioOptimization).order_by(
            PortfolioOptimization.created_at.desc()
        ).limit(1)
        result = session.execute(query)
        optimization = result.scalar_one_or_none()
        
        if not optimization:
            return {
                "annual_return": 0.0,
                "annual_volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }
        
        # Parse weights
        import json
        try:
            weights = json.loads(optimization.weights_json.replace("'", '"'))
        except:
            weights = {}
        
        if not weights:
            return {
                "annual_return": 0.0,
                "annual_volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }
        
        # Get candidate strategies
        strategy_ids = list(weights.keys())
        query = select(Candidate).where(Candidate.id.in_(strategy_ids))
        result = session.execute(query)
        candidates = result.scalars().all()
        
        # Calculate portfolio metrics
        weighted_return = 0.0
        weighted_sharpe = 0.0
        weighted_drawdown = 0.0
        
        for candidate in candidates:
            weight = weights.get(candidate.id, 0.0)
            weighted_return += (candidate.return_val if candidate.return_val else 0.0) * weight
            weighted_sharpe += (candidate.sharpe_val if candidate.sharpe_val else 0.0) * weight
            weighted_drawdown += (candidate.max_drawdown if candidate.max_drawdown else 0.0) * weight
        
        # Estimate volatility from Sharpe (assuming risk-free rate = 0)
        annual_volatility = abs(weighted_sharpe / weighted_return) if weighted_return != 0 else 0.0
        
        return {
            "annual_return": weighted_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": weighted_sharpe,
            "max_drawdown": weighted_drawdown
        }
