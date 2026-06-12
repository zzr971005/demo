"""
quant_engine.ops — 进化与搜索模块

包含：
- evolve_search: DEAP遗传编程核心封装
- evolution_center: 进化中心（多品种调度）
- broad_alpha_search: 单因子挖掘与搜索
- combo_search: 因子组合搜索
- combo_search_prune: 组合剪枝
- combo_tune: 组合参数调优
- orchestrator: 流程编排器
"""

from .evolve_search import (
    DEAPEvolutionEngine,
    EvolutionResult,
    FitnessMetrics,
    FamilyPrimitiveSet,
    evaluate_individual,
    POPULATION_SIZE,
    MAX_GENERATIONS,
)

__all__ = [
    "DEAPEvolutionEngine",
    "EvolutionResult",
    "FitnessMetrics",
    "FamilyPrimitiveSet",
    "evaluate_individual",
    "POPULATION_SIZE",
    "MAX_GENERATIONS",
]
