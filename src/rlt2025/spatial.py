"""Core spatial utilities for procedural generation."""

from typing import Iterator, NamedTuple


class Vec3(NamedTuple):
    """3D integer vector for world coordinates."""

    x: int
    y: int
    z: int = 0

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)


class AABB:
    """Axis-aligned bounding box with inclusive min, exclusive max (half-open)."""

    def __init__(self, min_pos: Vec3, max_pos: Vec3):
        self.min = min_pos
        self.max = max_pos

    def width(self) -> int:
        return self.max.x - self.min.x

    def height(self) -> int:
        return self.max.y - self.min.y

    def depth(self) -> int:
        return self.max.z - self.min.z

    def iter_xy(self) -> Iterator[tuple[int, int]]:
        """Iterate over all (x, y) coordinates in the bounding box."""
        for y in range(self.min.y, self.max.y):
            for x in range(self.min.x, self.max.x):
                yield x, y

    def iter_xyz(self) -> Iterator[tuple[int, int, int]]:
        """Iterate over all (x, y, z) coordinates in the bounding box."""
        for z in range(self.min.z, self.max.z):
            for y in range(self.min.y, self.max.y):
                for x in range(self.min.x, self.max.x):
                    yield x, y, z

    def expand(self, n: int) -> "AABB":
        """Return a new AABB expanded by n units in all directions."""
        return AABB(
            Vec3(self.min.x - n, self.min.y - n, self.min.z),
            Vec3(self.max.x + n, self.max.y + n, self.max.z),
        )

    def contains(self, pos: Vec3) -> bool:
        """Check if a position is within this bounding box."""
        return (
            self.min.x <= pos.x < self.max.x
            and self.min.y <= pos.y < self.max.y
            and self.min.z <= pos.z < self.max.z
        )

    def intersects(self, other: "AABB") -> bool:
        """Check if this AABB intersects with another."""
        return (
            self.min.x < other.max.x
            and self.max.x > other.min.x
            and self.min.y < other.max.y
            and self.max.y > other.min.y
            and self.min.z < other.max.z
            and self.max.z > other.min.z
        )

    def __repr__(self) -> str:
        return f"AABB({self.min}, {self.max})"
