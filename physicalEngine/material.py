from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Phase(str, Enum):
    SOLID = "solid"
    FLUID = "fluid"
    GRANULAR = "granular"


@dataclass(frozen=True, slots=True)
class Material:
    name: str
    phase: Phase
    density: float = 1000.0
    stiffness: float = 0.8
    damping: float = 0.02
    viscosity: float = 0.1
    cohesion: float = 0.0
    restitution: float = 0.15
    friction: float = 0.45


STONE = Material(
    name="stone",
    phase=Phase.SOLID,
    density=2600.0,
    stiffness=0.96,
    damping=0.04,
    viscosity=0.0,
    cohesion=1.0,
    restitution=0.08,
    friction=0.75,
)

WATER = Material(
    name="water",
    phase=Phase.FLUID,
    density=1000.0,
    stiffness=0.35,
    damping=0.01,
    viscosity=0.18,
    cohesion=0.08,
    restitution=0.02,
    friction=0.02,
)

SAND = Material(
    name="sand",
    phase=Phase.GRANULAR,
    density=1600.0,
    stiffness=0.55,
    damping=0.08,
    viscosity=0.02,
    cohesion=0.18,
    restitution=0.05,
    friction=0.85,
)
