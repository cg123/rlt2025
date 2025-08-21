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


@dataclass(frozen=True)
class StableId:
    """
    A stable, unique identifier for an entity that persists across saves.

    Used for deferred entity references during procedural generation
    and for maintaining entity identity across world changes.
    """

    guid: str


@dataclass
class ScheduledEvent:
    tick: int
    event: object


@dataclass
class VisibilityInfo:
    compute_explored: bool = True
    dirty: bool = True
    sight_radius: int = 10
    visible: Optional[np.ndarray] = None
    explored: Optional[np.ndarray] = None
