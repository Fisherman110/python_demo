from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .particle import Particle


@dataclass(slots=True)
class SpatialHash:
    cell_size: float
    cells: dict[tuple[int, int, int], list[int]] = field(default_factory=lambda: defaultdict(list))

    def key(self, x: float, y: float, z: float) -> tuple[int, int, int]:
        return (
            int(x // self.cell_size),
            int(y // self.cell_size),
            int(z // self.cell_size),
        )

    def rebuild(self, particles: list[Particle]):
        self.cells.clear()
        for index, particle in enumerate(particles):
            key = self.key(particle.position.x, particle.position.y, particle.position.z)
            self.cells[key].append(index)

    def neighbor_indices(self, particle: Particle):
        cx, cy, cz = self.key(particle.position.x, particle.position.y, particle.position.z)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    yield from self.cells.get((cx + dx, cy + dy, cz + dz), ())
