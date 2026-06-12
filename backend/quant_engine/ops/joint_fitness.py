"""
Joint evolution fitness functions for multi-symbol factor mining
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class JointFitnessResult:
    """Joint evolution fitness result"""
    overall_fitness: float
    symbol_fitness: Dict[str, float]
    consistency_score: float
    generalization_score: float
    sharpe_mean: float
    sharpe_std: float
    ic_mean: float
    ic_std: float


def calculate_joint_fitness(
    symbol_results: Dict[str, Dict],
    weights: Optional[Dict[str, float]] = None
) -> JointFitnessResult:
    """
    Calculate joint fitness across multiple symbols
    
    Args:
        symbol_results: Dictionary of {symbol: {sharpe, ic, ...}}
        weights: Optional weights for each symbol
        
    Returns:
        JointFitnessResult with combined metrics
    """
    if not symbol_results:
        return JointFitnessResult(0.0, {}, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    # Extract Sharpe ratios
    sharpe_values = []
    for symbol, result in symbol_results.items():
        sharpe = result.get('sharpe', 0.0)
        sharpe_values.append(sharpe)
    
    sharpe_mean = np.mean(sharpe_values)
    sharpe_std = np.std(sharpe_values) if len(sharpe_values) > 1 else 0.0
    
    # Extract IC values
    ic_values = []
    for symbol, result in symbol_results.items():
        ic = result.get('ic_mean', 0.0)
        ic_values.append(ic)
    
    ic_mean = np.mean(ic_values)
    ic_std = np.std(ic_values) if len(ic_values) > 1 else 0.0
    
    # Calculate consistency score (lower std = higher consistency)
    consistency_score = 1.0 / (1.0 + sharpe_std) if sharpe_std > 0 else 1.0
    
    # Calculate generalization score (based on IC stability)
    generalization_score = 1.0 / (1.0 + ic_std) if ic_std > 0 else 1.0
    
    # Calculate symbol-specific fitness with weights
    if weights is None:
        weights = {symbol: 1.0 for symbol in symbol_results.keys()}
    
    weighted_fitness = 0.0
    total_weight = 0.0
    symbol_fitness = {}
    
    for symbol, result in symbol_results.items():
        weight = weights.get(symbol, 1.0)
        sharpe = result.get('sharpe', 0.0)
        ic = result.get('ic_mean', 0.0)
        
        # Combine Sharpe and IC for symbol fitness
        symbol_fit = (sharpe * 0.7 + ic * 0.3)
        symbol_fitness[symbol] = symbol_fit
        
        weighted_fitness += symbol_fit * weight
        total_weight += weight
    
    overall_fitness = weighted_fitness / total_weight if total_weight > 0 else 0.0
    
    # Apply consistency and generalization bonuses
    overall_fitness = overall_fitness * (0.6 + consistency_score * 0.2 + generalization_score * 0.2)
    
    return JointFitnessResult(
        overall_fitness=overall_fitness,
        symbol_fitness=symbol_fitness,
        consistency_score=consistency_score,
        generalization_score=generalization_score,
        sharpe_mean=sharpe_mean,
        sharpe_std=sharpe_std,
        ic_mean=ic_mean,
        ic_std=ic_std
    )


def calculate_hybrid_fitness(
    universal_results: Dict[str, Dict],
    symbol_specific_results: Dict[str, Dict],
    universal_weight: float = 0.5
) -> JointFitnessResult:
    """
    Calculate hybrid fitness combining universal and symbol-specific factors
    
    Args:
        universal_results: Results from universal factor evaluation
        symbol_specific_results: Results from symbol-specific factor evaluation
        universal_weight: Weight for universal factors (0-1)
        
    Returns:
        JointFitnessResult with combined metrics
    """
    # Calculate universal fitness
    universal_fitness = calculate_joint_fitness(universal_results)
    
    # Calculate symbol-specific fitness
    symbol_fitness = calculate_joint_fitness(symbol_specific_results)
    
    # Combine with weights
    overall_fitness = (
        universal_fitness.overall_fitness * universal_weight +
        symbol_fitness.overall_fitness * (1.0 - universal_weight)
    )
    
    # Combine symbol fitness dictionaries
    combined_symbol_fitness = {}
    all_symbols = set(universal_fitness.symbol_fitness.keys()) | set(symbol_fitness.symbol_fitness.keys())
    
    for symbol in all_symbols:
        universal_fit = universal_fitness.symbol_fitness.get(symbol, 0.0)
        specific_fit = symbol_fitness.symbol_fitness.get(symbol, 0.0)
        combined_symbol_fitness[symbol] = (
            universal_fit * universal_weight +
            specific_fit * (1.0 - universal_weight)
        )
    
    # Combine other metrics
    sharpe_mean = (
        universal_fitness.sharpe_mean * universal_weight +
        symbol_fitness.sharpe_mean * (1.0 - universal_weight)
    )
    
    ic_mean = (
        universal_fitness.ic_mean * universal_weight +
        symbol_fitness.ic_mean * (1.0 - universal_weight)
    )
    
    return JointFitnessResult(
        overall_fitness=overall_fitness,
        symbol_fitness=combined_symbol_fitness,
        consistency_score=(
            universal_fitness.consistency_score * universal_weight +
            symbol_fitness.consistency_score * (1.0 - universal_weight)
        ),
        generalization_score=(
            universal_fitness.generalization_score * universal_weight +
            symbol_fitness.generalization_score * (1.0 - universal_weight)
        ),
        sharpe_mean=sharpe_mean,
        sharpe_std=(
            universal_fitness.sharpe_std * universal_weight +
            symbol_fitness.sharpe_std * (1.0 - universal_weight)
        ),
        ic_mean=ic_mean,
        ic_std=(
            universal_fitness.ic_std * universal_weight +
            symbol_fitness.ic_std * (1.0 - universal_weight)
        )
    )
