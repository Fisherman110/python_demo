from __future__ import annotations

from dataclasses import dataclass, field

from .material import Material, WATER
from .vector import Vec3


@dataclass(slots=True)
class Particle:
    id: int
    position: Vec3
    mass: float = 1.0
    radius: float = 0.08
    material: Material = WATER
    velocity: Vec3 = field(default_factory=Vec3)
    force: Vec3 = field(default_factory=Vec3)
    previous_position: Vec3 = field(default_factory=Vec3)
    density: float = 0.0
    pressure: float = 0.0
    fixed: bool = False
    group: str = ""

    @property
    def inv_mass(self) -> float:
        if self.fixed or self.mass <= 0:
            return 0.0
        return 1.0 / self.mass

    def apply_force(self, force: Vec3):
        if not self.fixed:
            self.force = self.force + force

    def clear_force(self):
        self.force = Vec3()

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "group": self.group,
            "material": self.material.name,
            "phase": self.material.phase.value,
            "position": self.position.as_tuple(),
            "velocity": self.velocity.as_tuple(),
            "force": self.force.as_tuple(),
            "mass": self.mass,
            "radius": self.radius,
            "density": self.density,
            "pressure": self.pressure,
            "fixed": self.fixed,
        }
