"""
A/B测试API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select
import uuid

from app.db import get_session
from app.models import ABTestResult

router = APIRouter(prefix="/api/ab-testing", tags=["ab-testing"])


class TestRequest(BaseModel):
    strategy_a_id: str
    strategy_b_id: str
    test_duration_days: int = 30


@router.post("/test")
async def create_ab_test(request: TestRequest) -> Dict[str, Any]:
    """创建A/B测试"""
    with get_session() as session:
        test_id = f"test_{uuid.uuid4().hex[:16]}"
        
        # Create initial results for both strategies
        for strategy_id in [request.strategy_a_id, request.strategy_b_id]:
            result = ABTestResult(
                test_id=test_id,
                strategy_id=strategy_id,
                sharpe_ratio=0.0,
                total_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                recorded_at=datetime.utcnow()
            )
            session.add(result)
        
        session.commit()
        
        return {
            "test_id": test_id,
            "status": "RUNNING",
            "started_at": datetime.utcnow().isoformat()
        }


@router.get("/tests")
async def list_tests(
    status: Optional[str] = None
) -> Dict[str, Any]:
    """列出测试"""
    with get_session() as session:
        query = select(ABTestResult)
        result = session.execute(query)
        results = result.scalars().all()
        
        # Group by test_id
        tests = {}
        for r in results:
            if r.test_id not in tests:
                tests[r.test_id] = {
                    "test_id": r.test_id,
                    "strategies": [],
                    "started_at": r.recorded_at.isoformat(),
                }
            tests[r.test_id]["strategies"].append({
                "strategy_id": r.strategy_id,
                "sharpe_ratio": r.sharpe_ratio,
                "total_return": r.total_return,
            })
        
        return {
            "tests": list(tests.values())
        }


@router.get("/tests/{test_id}")
async def get_test(test_id: str) -> Dict[str, Any]:
    """获取测试详情"""
    with get_session() as session:
        query = select(ABTestResult).where(ABTestResult.test_id == test_id)
        result = session.execute(query)
        results = result.scalars().all()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")
        
        metrics = {
            r.strategy_id: {
                "sharpe_ratio": r.sharpe_ratio,
                "total_return": r.total_return,
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
            }
            for r in results
        }
        
        return {
            "test_id": test_id,
            "status": "RUNNING",
            "metrics": metrics
        }


@router.post("/tests/{test_id}/finalize")
async def finalize_test(test_id: str) -> Dict[str, Any]:
    """完成测试"""
    with get_session() as session:
        # Get all results for this test
        query = select(ABTestResult).where(ABTestResult.test_id == test_id)
        result = session.execute(query)
        results = result.scalars().all()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")
        
        if len(results) < 2:
            raise HTTPException(status_code=400, detail="Test must have at least 2 strategies")
        
        # Compare results to determine winner
        strategy_metrics = {}
        for r in results:
            strategy_metrics[r.strategy_id] = {
                "sharpe_ratio": r.sharpe_ratio,
                "total_return": r.total_return,
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
            }
        
        # Calculate composite score (weighted average of metrics)
        # Weights: Sharpe (40%), Return (30%), Win Rate (20%), -Drawdown (10%)
        scores = {}
        for strategy_id, metrics in strategy_metrics.items():
            sharpe_score = metrics["sharpe_ratio"] * 0.4
            return_score = metrics["total_return"] * 0.3
            win_rate_score = metrics["win_rate"] * 0.2
            drawdown_score = -metrics["max_drawdown"] * 0.1  # Lower drawdown is better
            
            scores[strategy_id] = sharpe_score + return_score + win_rate_score + drawdown_score
        
        # Determine winner
        winner_id = max(scores, key=scores.get)
        
        # Calculate statistical significance (simplified)
        winner_score = scores[winner_id]
        runner_up_score = scores[max([k for k in scores if k != winner_id], key=scores.get)]
        score_diff = winner_score - runner_up_score
        is_significant = abs(score_diff) > 0.1  # Threshold for significance
        
        # Update results with completion status
        for r in results:
            r.recorded_at = datetime.utcnow()
        
        session.commit()
        
        return {
            "test_id": test_id,
            "status": "COMPLETED",
            "winner": winner_id,
            "is_significant": is_significant,
            "scores": scores,
            "metrics": strategy_metrics,
            "finished_at": datetime.utcnow().isoformat()
        }
