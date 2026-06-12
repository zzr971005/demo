"""
Factor classification API routes
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db import get_db
from quant_engine.ops.factor_classifier import FactorClassifier, FactorCategory

router = APIRouter()


class FactorClassificationRequest(BaseModel):
    factor_id: str
    test_symbols: List[str]
    threshold: float = 0.7


class BatchClassificationRequest(BaseModel):
    factor_ids: List[str]
    test_symbols: List[str]


@router.post("/classify")
async def classify_factor(
    request: FactorClassificationRequest,
    db: Session = Depends(get_db)
):
    """Classify a factor by type (universal/symbol-specific)"""
    # TODO: Initialize classifier with generalization engine
    classifier = FactorClassifier(generalization_engine=None)
    
    classification = classifier.classify_factor(
        factor_id=request.factor_id,
        test_symbols=request.test_symbols,
        threshold=request.threshold
    )
    
    return {
        "factor_id": classification.factor_id,
        "category": classification.category.value,
        "confidence": classification.confidence,
        "applicable_symbols": classification.applicable_symbols,
        "excluded_symbols": classification.excluded_symbols,
        "classification_reason": classification.classification_reason
    }


@router.post("/batch-classify")
async def batch_classify_factors(
    request: BatchClassificationRequest,
    db: Session = Depends(get_db)
):
    """Classify multiple factors"""
    # TODO: Initialize classifier with generalization engine
    classifier = FactorClassifier(generalization_engine=None)
    
    results = classifier.batch_classify(
        factor_ids=request.factor_ids,
        test_symbols=request.test_symbols
    )
    
    return {
        "results": [
            {
                "factor_id": r.factor_id,
                "category": r.category.value,
                "confidence": r.confidence,
                "applicable_symbols": r.applicable_symbols
            }
            for r in results.values()
        ]
    }


@router.get("/by-category/{category}")
async def get_factors_by_category(
    category: str,
    db: Session = Depends(get_db)
):
    """Get all factors of a specific category"""
    # TODO: Initialize classifier
    classifier = FactorClassifier(generalization_engine=None)
    
    try:
        factor_category = FactorCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    factor_ids = classifier.get_factors_by_category(factor_category)
    
    return {
        "category": category,
        "factor_ids": factor_ids,
        "count": len(factor_ids)
    }


@router.get("/summary")
async def get_classification_summary(db: Session = Depends(get_db)):
    """Get summary of factor classifications"""
    # TODO: Initialize classifier
    classifier = FactorClassifier(generalization_engine=None)
    
    summary = classifier.get_classification_summary()
    
    return summary
