"""Evolution related routes"""

from app.api.routes.evolution import (
    candidates,
    classification,
    evolution,
    evolution_cycles,
    factors,
    factors_realtime,
    generalization,
    joint_evolution,
)

__all__ = [
    "candidates",
    "classification",
    "evolution",
    "evolution_cycles",
    "factors",
    "factors_realtime",
    "generalization",
    "joint_evolution",
]
