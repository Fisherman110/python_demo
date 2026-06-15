from __future__ import annotations

import math
from dataclasses import dataclass, field

from .constraint import DistanceConstraint, PinConstraint
from .material import Material, Phase, STONE, WATER
from .particle import Particle
from .spatial_hash import SpatialHash
from .vector import Vec3


@dataclass(slots=True)
class WorldBounds:
    min_corner: Vec3
    max_corner: Vec3

    def clamp_particle(self, particle: Particle):
        if particle.fixed:
            return

        for axis in ("x", "y", "z"):
            low = getattr(self.min_corner, axis) + particle.radius
            high = getattr(self.max_corner, axis) - particle.radius
            value = getattr(particle.position, axis)
            velocity_value = getattr(particle.velocity, axis)

            if value < low:
                setattr(particle.position, axis, low)
                setattr(particle.velocity, axis, -velocity_value * particle.material.restitution)
            elif value > high:
                setattr(particle.position, axis, high)
                setattr(particle.velocity, axis, -velocity_value * particle.material.restitution)


@dataclass(slots=True)
class SimulationConfig:
    time_step: float = 1.0 / 60.0
    gravity: Vec3 = field(default_factory=lambda: Vec3(0.0, -9.81, 0.0))
    smoothing_radius: float = 0.32
    pressure_scale: float = 6.0
    viscosity_scale: float = 0.6
    contact_stiffness: float = 900.0
    max_force: float = 5000.0
    constraint_iterations: int = 8
    bounds: WorldBounds | None = field(
        default_factory=lambda: WorldBounds(Vec3(-5.0, -1.0, -5.0), Vec3(5.0, 8.0, 5.0))
    )


class ParticleWorld:
    """Particle-based physics core for solid-like structures and fluids.

    The engine uses a practical hybrid:
    - solid objects are particle clusters held together by distance constraints;
    - fluids use SPH-style density, pressure and viscosity forces;
    - all phases interact through local contact repulsion and friction damping.
    """

    def __init__(self, config: SimulationConfig | None = None):
        self.config = config or SimulationConfig()
        self.particles: list[Particle] = []
        self.constraints: list[DistanceConstraint | PinConstraint] = []
        self.spatial_hash = SpatialHash(self.config.smoothing_radius)
        self.time = 0.0
        self._next_id = 1

    def add_particle(
        self,
        position: Vec3,
        mass: float = 1.0,
        radius: float = 0.08,
        material: Material = WATER,
        velocity: Vec3 | None = None,
        fixed: bool = False,
        group: str = "",
    ) -> int:
        particle = Particle(
            id=self._next_id,
            position=position.copy(),
            previous_position=position.copy(),
            mass=mass,
            radius=radius,
            material=material,
            velocity=velocity.copy() if velocity else Vec3(),
            fixed=fixed,
            group=group,
        )
        self.particles.append(particle)
        self._next_id += 1
        return len(self.particles) - 1

    def add_distance_constraint(self, a: int, b: int, stiffness: float | None = None):
        pa = self.particles[a]
        pb = self.particles[b]
        rest_length = (pb.position - pa.position).length()
        constraint_stiffness = stiffness if stiffness is not None else min(pa.material.stiffness, pb.material.stiffness)
        self.constraints.append(DistanceConstraint(a, b, rest_length, constraint_stiffness))

    def add_pin_constraint(self, particle_index: int, target: Vec3, stiffness: float = 1.0):
        self.constraints.append(PinConstraint(particle_index, target.x, target.y, target.z, stiffness))

    def create_rigid_cluster(
        self,
        points: list[Vec3],
        material: Material = STONE,
        particle_mass: float = 1.0,
        radius: float = 0.09,
        group: str = "solid",
        connection_radius: float | None = None,
        fixed: bool = False,
    ) -> list[int]:
        indices = [
            self.add_particle(point, mass=particle_mass, radius=radius, material=material, fixed=fixed, group=group)
            for point in points
        ]

        max_connection = connection_radius or radius * 3.1
        for i, index_a in enumerate(indices):
            for index_b in indices[i + 1 :]:
                distance = (self.particles[index_b].position - self.particles[index_a].position).length()
                if distance <= max_connection:
                    self.add_distance_constraint(index_a, index_b, material.stiffness)
        return indices

    def create_box_cluster(
        self,
        origin: Vec3,
        size: tuple[int, int, int],
        spacing: float,
        material: Material = STONE,
        group: str = "rock",
        fixed: bool = False,
    ) -> list[int]:
        nx, ny, nz = size
        points = []
        for ix in range(nx):
            for iy in range(ny):
                for iz in range(nz):
                    points.append(origin + Vec3(ix * spacing, iy * spacing, iz * spacing))
        return self.create_rigid_cluster(
            points,
            material=material,
            particle_mass=max(0.05, material.density * spacing**3),
            radius=spacing * 0.45,
            group=group,
            connection_radius=spacing * math.sqrt(3.0) * 1.05,
            fixed=fixed,
        )

    def create_fluid_block(
        self,
        origin: Vec3,
        size: tuple[int, int, int],
        spacing: float,
        material: Material = WATER,
        group: str = "water",
    ) -> list[int]:
        nx, ny, nz = size
        indices = []
        particle_mass = max(0.02, material.density * spacing**3)
        for ix in range(nx):
            for iy in range(ny):
                for iz in range(nz):
                    jitter = Vec3((ix % 2) * spacing * 0.08, 0.0, (iy % 2) * spacing * 0.08)
                    position = origin + Vec3(ix * spacing, iy * spacing, iz * spacing) + jitter
                    indices.append(
                        self.add_particle(
                            position,
                            mass=particle_mass,
                            radius=spacing * 0.42,
                            material=material,
                            group=group,
                        )
                    )
        return indices

    def step(self, substeps: int = 1):
        substeps = max(1, substeps)
        dt = self.config.time_step / substeps
        for _ in range(substeps):
            self._step_once(dt)
        return self.snapshot()

    def _step_once(self, dt: float):
        self.spatial_hash.rebuild(self.particles)
        self._clear_and_apply_body_forces()
        self._compute_fluid_forces()
        self._compute_contact_forces()
        self._integrate(dt)
        self._solve_constraints(dt)
        self._apply_bounds()
        self.time += dt

    def _clear_and_apply_body_forces(self):
        for particle in self.particles:
            particle.clear_force()
            particle.apply_force(self.config.gravity * particle.mass)

    def _compute_fluid_forces(self):
        h = self.config.smoothing_radius
        h2 = h * h
        fluid_indices = [index for index, particle in enumerate(self.particles) if particle.material.phase == Phase.FLUID]

        for index in fluid_indices:
            particle = self.particles[index]
            density = 0.0
            for neighbor_index in self.spatial_hash.neighbor_indices(particle):
                neighbor = self.particles[neighbor_index]
                r2 = (particle.position - neighbor.position).length_sq()
                if r2 < h2:
                    density += neighbor.mass * self._poly6_kernel(r2, h)
            particle.density = max(density, particle.material.density * 0.15)
            particle.pressure = max(0.0, (particle.density - particle.material.density) * self.config.pressure_scale)

        for index in fluid_indices:
            particle = self.particles[index]
            pressure_force = Vec3()
            viscosity_force = Vec3()
            cohesion_force = Vec3()

            for neighbor_index in self.spatial_hash.neighbor_indices(particle):
                if neighbor_index == index:
                    continue
                neighbor = self.particles[neighbor_index]
                delta = particle.position - neighbor.position
                distance = delta.length()
                if distance <= 1e-9 or distance >= h:
                    continue

                direction = delta / distance
                neighbor_density = max(neighbor.density, neighbor.material.density * 0.15)
                pressure_term = (particle.pressure + neighbor.pressure) / (2.0 * neighbor_density)
                pressure_force = pressure_force - direction * (neighbor.mass * pressure_term * self._spiky_gradient(distance, h))

                if neighbor.material.phase == Phase.FLUID:
                    viscosity = (neighbor.velocity - particle.velocity) * (
                        self.config.viscosity_scale
                        * particle.material.viscosity
                        * neighbor.mass
                        * self._viscosity_laplacian(distance, h)
                        / neighbor_density
                    )
                    viscosity_force = viscosity_force + viscosity

                if particle.material.cohesion > 0 and neighbor.material.phase == Phase.FLUID:
                    cohesion_force = cohesion_force - direction * (
                        particle.material.cohesion * neighbor.mass * max(0.0, h - distance)
                    )

            particle.apply_force((pressure_force + viscosity_force + cohesion_force).clamp_length(self.config.max_force))

    def _compute_contact_forces(self):
        h = self.config.smoothing_radius
        for index, particle in enumerate(self.particles):
            for neighbor_index in self.spatial_hash.neighbor_indices(particle):
                if neighbor_index <= index:
                    continue
                neighbor = self.particles[neighbor_index]
                delta = particle.position - neighbor.position
                distance = delta.length()
                min_distance = particle.radius + neighbor.radius
                if distance <= 1e-9 or distance >= min_distance:
                    continue

                normal = delta / distance
                penetration = min_distance - distance
                stiffness = self.config.contact_stiffness * min(particle.material.stiffness, neighbor.material.stiffness)
                force = normal * (stiffness * penetration)

                relative_velocity = particle.velocity - neighbor.velocity
                damping = normal * (relative_velocity.dot(normal) * (particle.material.damping + neighbor.material.damping))
                force = force - damping

                particle.apply_force(force)
                neighbor.apply_force(-force)

                if distance < h:
                    tangential = relative_velocity - normal * relative_velocity.dot(normal)
                    friction = tangential * (-min(particle.material.friction, neighbor.material.friction) * penetration)
                    particle.apply_force(friction)
                    neighbor.apply_force(-friction)

    def _integrate(self, dt: float):
        for particle in self.particles:
            particle.previous_position = particle.position.copy()
            if particle.fixed:
                particle.velocity = Vec3()
                continue

            acceleration = particle.force * particle.inv_mass
            particle.velocity = (particle.velocity + acceleration * dt) * (1.0 - particle.material.damping)
            particle.position = particle.position + particle.velocity * dt

    def _solve_constraints(self, dt: float):
        for _ in range(max(1, self.config.constraint_iterations)):
            for constraint in self.constraints:
                constraint.solve(self.particles)

        if dt <= 0:
            return
        for particle in self.particles:
            if not particle.fixed:
                particle.velocity = (particle.position - particle.previous_position) / dt

    def _apply_bounds(self):
        if not self.config.bounds:
            return
        for particle in self.particles:
            self.config.bounds.clamp_particle(particle)

    def snapshot(self) -> dict:
        return {
            "time": self.time,
            "particle_count": len(self.particles),
            "constraint_count": len(self.constraints),
            "particles": [particle.snapshot() for particle in self.particles],
        }

    @staticmethod
    def _poly6_kernel(r2: float, h: float) -> float:
        if r2 >= h * h:
            return 0.0
        return 315.0 / (64.0 * math.pi * h**9) * (h * h - r2) ** 3

    @staticmethod
    def _spiky_gradient(distance: float, h: float) -> float:
        if distance >= h:
            return 0.0
        return -45.0 / (math.pi * h**6) * (h - distance) ** 2

    @staticmethod
    def _viscosity_laplacian(distance: float, h: float) -> float:
        if distance >= h:
            return 0.0
        return 45.0 / (math.pi * h**6) * (h - distance)
