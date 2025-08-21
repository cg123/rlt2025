import logging
from typing import Any, Iterable

import tcod

from rlt2025.components import Player, Position, Renderable, VisibilityInfo
from rlt2025.ecs import Entity, World
from rlt2025.events import AfterFrameRenderEvent, BeforeFrameRenderEvent
from rlt2025.input_handlers import EventHandler
from rlt2025.systems.chunk_activation import ChunkActivationSystem
from rlt2025.systems.visibility import VisibilitySystem

LOG = logging.getLogger(__name__)


class Engine:
    def __init__(
        self,
        world: World,
    ):
        self.tcod_event_handler = EventHandler()
        self.world = world

        self.sys_visibility = VisibilitySystem(world)
        self.sys_chunk_activation = ChunkActivationSystem(world)

    def handle_tcod_events(self, events: Iterable[Any]) -> None:
        for event in events:
            action = self.tcod_event_handler.dispatch(event)

            if action is None:
                continue
            action.perform(world=self.world, entity=self._get_player_entity())

    def _get_player_entity(self) -> Entity:
        player_entities = list(self.world.entities.get_entities_with_component(Player))
        if not player_entities:
            raise ValueError("No player entity found in the world.")
        if len(player_entities) > 1:
            raise ValueError("Multiple player entities found in the world.")
        return player_entities[0]

    def render(
        self, console: tcod.console.Console, context: tcod.context.Context
    ) -> None:
        self.world.event_bus.post(BeforeFrameRenderEvent())
        self.world.event_bus.process_current(self.world)

        console.clear()

        player = self._get_player_entity()
        player_pos = self.world.entities.get_component(player, Position)
        if player_pos is None:
            raise ValueError("Player entity does not have a Position component.")

        visibility = self.world.entities.get_component(player, VisibilityInfo)
        if visibility is None:
            raise ValueError("Player entity does not have a VisibilityInfo component.")
        if visibility.visible is None or visibility.explored is None:
            raise ValueError("VisibilityInfo components are not initialized.")
        if visibility.dirty:
            raise ValueError("VisibilityInfo is dirty at render time.")

        self.world.realm.render(
            console, visible=visibility.visible, explored=visibility.explored
        )

        renderables = list(self.world.entities.query(Position, Renderable))
        renderables.sort(key=lambda r: r[2].layer)
        for _entity, pos, r in renderables:
            if visibility.visible[pos.x, pos.y]:
                console.print(x=pos.x, y=pos.y, text=r.text, fg=r.fg, bg=r.bg)
        context.present(console)

        self.world.event_bus.post(AfterFrameRenderEvent())
        self.world.event_bus.process_current(self.world)
