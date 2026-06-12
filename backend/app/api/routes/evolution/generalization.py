"""
Generalization test API routes
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db import get_db
from quant_engine.ops.generalization_test import GeneralizationTestEngine

router = APIRouter()


class GeneralizationTestRequest(BaseModel):
    factor_id: str
    original_symbol: str
    test_symbols: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class BatchGeneralizationTestRequest(BaseModel):
    factor_ids: List[str]
    test_symbols: List[str]


@router.post("/test")
async def test_factor_generalization(
    request: GeneralizationTestRequest,
    db: Session = Depends(get_db)
):
    """Test factor generalization across symbols"""
    # TODO: Initialize engine with data hub
    engine = GeneralizationTestEngine(data_hub=None)
    
    result = engine.test_factor(
        factor_id=request.factor_id,
        original_symbol=request.original_symbol,
        test_symbols=request.test_symbols,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    return {
        "factor_id": result.factor_id,
        "test_symbols": result.test_symbols,
        "original_symbol": result.original_symbol,
        "is_universal": result.is_universal,
        "generalization_score": result.generalization_score,
        "symbol_performance": result.symbol_performance,
        "performance_std": result.performance_std,
        "performance_mean": result.performance_mean,
        "ic_correlation": result.ic_correlation,
        "tested_at": result.tested_at.isoformat()
    }


@router.post("/batch-test")
async def batch_test_generalization(
    request: BatchGeneralizationTestRequest,
    db: Session = Depends(get_db)
):
    """Test multiple factors for generalization"""
    # TODO: Initialize engine with data hub
    engine = GeneralizationTestEngine(data_hub=None)
    
    results = engine.batch_test_factors(
        factor_ids=request.factor_ids,
        test_symbols=request.test_symbols
    )
    
    return {
        "results": [
            {
                "factor_id": r.factor_id,
                "is_universal": r.is_universal,
                "generalization_score": r.generalization_score
            }
            for r in results.values()
        ]
    }
