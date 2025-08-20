from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np


@dataclass
class AABB:
    x0: int
    y0: int
    x1: int
    y1: int

    def width(self) -> int:
        return self.x1 - self.x0

    def height(self) -> int:
        return self.y1 - self.y0

    def area(self) -> int:
        return self.width() * self.height()

    def intersects(self, other: "AABB") -> bool:
        return not (
            self.x1 <= other.x0
            or self.x0 >= other.x1
            or self.y1 <= other.y0
            or self.y0 >= other.y1
        )

    def contains(self, point: tuple[int, int]) -> bool:
        x, y = point
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1


@dataclass
class GenerationRegion:
    bounds: AABB
    mask: Optional[np.ndarray] = field(default=None)


@dataclass
class EntitySpawn:
    components: List[Any]


@dataclass
class RegionData:
    tiles: np.ndarray
