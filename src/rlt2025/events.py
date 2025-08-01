from dataclasses import dataclass
from typing import Optional

from rlt2025.ecs import Entity


@dataclass
class EntityMovedEvent:
    entity: int
    old_position: tuple[int, int]
    new_position: tuple[int, int]


@dataclass
class RenderFrameEvent:
    # Triggered when a frame needs to be rendered
    pass


@dataclass
class FrameRenderedEvent:
    # Triggered after a frame has been rendered
    pass


@dataclass
class IntentFailedEvent:
    entity_id: int
    reason: Optional[str] = None


@dataclass
class TimeAdvanceRequestEvent:
    pass


@dataclass
class TurnCompletedEvent:
    entity: Entity


@dataclass
class TimeElapsedEvent:
    elapsed_ticks: int
