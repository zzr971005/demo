"""
Joint evolution API routes
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db import get_session
from quant_engine.ops.joint_evolution_center import JointEvolutionCenter, JointEvolutionConfig

router = APIRouter()


class JointEvolutionRequest(BaseModel):
    symbols: List[str]
    population_size: int = 100
    max_generations: int = 50
    universal_weight: float = 0.5
    enable_generalization_test: bool = True
    generalization_threshold: float = 0.7


class HybridEvolutionRequest(BaseModel):
    symbols: List[str]
    population_size: int = 100
    max_generations: int = 50
    universal_weight: float = 0.5


@router.post("/joint-start")
async def start_joint_evolution(
    request: JointEvolutionRequest,
    db: Session = Depends(get_session)
):
    """Start joint evolution for multiple symbols"""
    config = JointEvolutionConfig(
        symbols=request.symbols,
        population_size=request.population_size,
        max_generations=request.max_generations,
        universal_weight=request.universal_weight,
        enable_generalization_test=request.enable_generalization_test,
        generalization_threshold=request.generalization_threshold
    )
    
    center = JointEvolutionCenter(config)
    task_id = center.start_joint_evolution()
    
    return {
        "task_id": task_id,
        "status": "started",
        "symbols": request.symbols,
        "mode": "joint"
    }


@router.post("/hybrid-start")
async def start_hybrid_evolution(
    request: HybridEvolutionRequest,
    db: Session = Depends(get_session)
):
    """Start hybrid evolution (universal + symbol-specific)"""
    config = JointEvolutionConfig(
        symbols=request.symbols,
        population_size=request.population_size,
        max_generations=request.max_generations,
        universal_weight=request.universal_weight
    )
    
    center = JointEvolutionCenter(config)
    task_id = center.start_hybrid_evolution()
    
    return {
        "task_id": task_id,
        "status": "started",
        "symbols": request.symbols,
        "mode": "hybrid"
    }


@router.get("/joint-status/{task_id}")
async def get_joint_evolution_status(
    task_id: str,
    db: Session = Depends(get_session)
):
    """Get joint evolution task status"""
    # TODO: Implement status retrieval
    return {
        "task_id": task_id,
        "status": "running",
        "generation": 0,
        "best_fitness": 0.0
    }
