from __future__ import annotations

from dataclasses import dataclass

from .particle import Particle


@dataclass(slots=True)
class DistanceConstraint:
    particle_a: int
    particle_b: int
    rest_length: float
    stiffness: float = 1.0

    def solve(self, particles: list[Particle]):
        a = particles[self.particle_a]
        b = particles[self.particle_b]
        delta = b.position - a.position
        distance = delta.length()
        if distance <= 1e-9:
            return

        inv_mass_sum = a.inv_mass + b.inv_mass
        if inv_mass_sum <= 0:
            return

        error = distance - self.rest_length
        correction = delta * (self.stiffness * error / (distance * inv_mass_sum))

        if not a.fixed:
            a.position = a.position + correction * a.inv_mass
        if not b.fixed:
            b.position = b.position - correction * b.inv_mass


@dataclass(slots=True)
class PinConstraint:
    particle_id: int
    x: float
    y: float
    z: float
    stiffness: float = 1.0

    def solve(self, particles: list[Particle]):
        particle = particles[self.particle_id]
        if particle.fixed:
            return
        target = particle.position.__class__(self.x, self.y, self.z)
        particle.position = particle.position + (target - particle.position) * self.stiffness
