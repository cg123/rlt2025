from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from rlt2025.ecs import Entity

if TYPE_CHECKING:
    from rlt2025.map.chunks import ChunkKey


@dataclass
class EntityMovedEvent:
    entity: int
    old_position: tuple[int, int]
    new_position: tuple[int, int]


@dataclass
class BeforeFrameRenderEvent:
    # Triggered before rendering a frame
    pass


@dataclass
class AfterFrameRenderEvent:
    # Triggered after a frame has been rendered
    pass


@dataclass
class RenderFrameEvent:
    # Indicates a frame needs to be rendered
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


@dataclass
class ChunkActivateRequestEvent:
    """Request to activate a chunk (materialize entities)."""

    chunk_key: "ChunkKey"


@dataclass
class ChunkDeactivateRequestEvent:
    """Request to deactivate a chunk (cleanup entities)."""

    chunk_key: "ChunkKey"
