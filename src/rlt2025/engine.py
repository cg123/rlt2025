import logging
from typing import Any, Iterable
import tcod

from rlt2025.components import Renderable
from rlt2025.components import Player, Position
from rlt2025.ecs import World
from rlt2025.input_handlers import EventHandler

LOG = logging.getLogger(__name__)


class Engine:
    def __init__(
        self,
        world: World,
    ):
        self.tcod_event_handler = EventHandler()
        self.world = world

    def handle_tcod_events(self, events: Iterable[Any]) -> None:
        for event in events:
            action = self.tcod_event_handler.dispatch(event)

            if action is None:
                continue
            player_ent = list(self.world.entities.get_entities_with_component(Player))[
                0
            ]
            action.perform(world=self.world, entity=player_ent)

    def render(
        self, console: tcod.console.Console, context: tcod.context.Context
    ) -> None:
        console.clear()
        self.world.game_map.render(console)

        renderables = list(self.world.entities.query(Position, Renderable))
        renderables.sort(key=lambda r: r[2].layer)
        for _entity, pos, r in renderables:
            console.print(x=pos.x, y=pos.y, text=r.text, fg=r.fg, bg=r.bg)
        context.present(console)
