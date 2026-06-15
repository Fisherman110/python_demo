from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, value: float) -> Vec3:
        return Vec3(self.x * value, self.y * value, self.z * value)

    def __rmul__(self, value: float) -> Vec3:
        return self * value

    def __truediv__(self, value: float) -> Vec3:
        if value == 0:
            return Vec3()
        return Vec3(self.x / value, self.y / value, self.z / value)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    def copy(self) -> Vec3:
        return Vec3(self.x, self.y, self.z)

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length_sq(self) -> float:
        return self.dot(self)

    def length(self) -> float:
        return math.sqrt(self.length_sq())

    def normalized(self) -> Vec3:
        length = self.length()
        if length <= 1e-12:
            return Vec3()
        return self / length

    def clamp_length(self, max_length: float) -> Vec3:
        length = self.length()
        if length <= max_length or length <= 1e-12:
            return self.copy()
        return self * (max_length / length)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


ZERO = Vec3()
