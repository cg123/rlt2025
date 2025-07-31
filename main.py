#!/usr/bin/env python3
import tcod

from engine import Engine
from entity import Entity
from game_map import GameMap
from input_handlers import EventHandler


def main() -> None:
    screen_width = 80
    screen_height = 50

    tileset = tcod.tileset.load_tilesheet(
        "dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    )

    player = Entity(
        x=screen_width // 2, y=screen_height // 2, text="@", color=(255, 255, 255)
    )
    npc = Entity(
        x=screen_width // 2 - 5, y=screen_height // 2, text="@", color=(255, 255, 0)
    )

    event_handler = EventHandler()
    game_map = GameMap(width=screen_width, height=screen_height)
    engine = Engine(
        entities={player, npc},
        event_handler=event_handler,
        game_map=game_map,
        player=player,
    )

    with tcod.context.new(
        columns=screen_width,
        rows=screen_height,
        tileset=tileset,
        title="Yet Another Roguelike Tutorial",
        vsync=True,
    ) as context:
        root_console = tcod.console.Console(screen_width, screen_height, order="F")
        while True:
            engine.render(console=root_console, context=context)
            events = tcod.event.wait()
            engine.handle_events(events)


if __name__ == "__main__":
    main()
