from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rlt2025.ecs import World, Entity

from rlt2025.components import Position
from rlt2025.events import EntityMovedEvent


class Action(ABC):
    @abstractmethod
    def perform(self, world: World, entity: Entity) -> None:
        """Perform the action."""
        pass


class EscapeAction(Action):
    def perform(self, world: World, entity: Entity) -> None:
        raise SystemExit()


class MovementAction(Action):
    def __init__(self, dx: int, dy: int):
        super().__init__()

        self.dx = dx
        self.dy = dy

    def perform(self, world: World, entity: Entity) -> None:
        pos_0 = world.entities.get_component(entity, Position)
        if pos_0 is None:
            return

        dest_x = pos_0.x + self.dx
        dest_y = pos_0.y + self.dy

        if not world.realm.in_bounds(dest_x, dest_y):
            return
        tile_id = world.realm.read_tile(dest_x, dest_y)
        if not world.realm.tiles.get(tile_id).blocks_move:
            return

        # Move the entity to the new position
        pos_0.x = dest_x
        pos_0.y = dest_y
        world.entities.add_component(entity, pos_0)

        # Dispatch an event for the movement
        world.event_bus.post(
            EntityMovedEvent(
                entity=entity,
                new_position=(dest_x, dest_y),
                old_position=(pos_0.x, pos_0.y),
            )
        )
