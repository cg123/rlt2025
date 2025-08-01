from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Position:
    x: int
    y: int


@dataclass
class Renderable:
    text: str
    fg: tuple[int, int, int]
    bg: Optional[tuple[int, int, int]] = None
    layer: int = 0


@dataclass
class MovementProperties:
    walkable: bool
    opaque: bool


@dataclass
class Player:
    # marker component for player entity
    pass


@dataclass
class TileMap:
    width: int
    height: int
    tiles: np.ndarray


@dataclass
class ScheduledEvent:
    tick: int
    event: object
