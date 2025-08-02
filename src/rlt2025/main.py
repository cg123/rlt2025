#!/usr/bin/env python3
import tcod

from rlt2025.components import Position, Renderable
from rlt2025.ecs import World
from rlt2025.engine import Engine

TILESET = tcod.tileset.load_tilesheet(
    "dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
)


def main() -> None:
    screen_width = 80
    screen_height = 50

    world = World()
    world.realm.generate(
        world=world,
        width=screen_width,
        height=screen_height,
    )
    engine = Engine(
        world=world,
    )

    npc = world.entities.create_entity()
    world.entities.add_component(
        npc, Position(x=screen_width // 2 - 5, y=screen_height // 2)
    )
    world.entities.add_component(npc, Renderable(text="@", fg=(255, 255, 0)))

    with tcod.context.new(
        columns=screen_width,
        rows=screen_height,
        tileset=TILESET,
        title="Yet Another Roguelike Tutorial",
        vsync=True,
    ) as context:
        root_console = tcod.console.Console(screen_width, screen_height, order="F")
        while True:
            engine.render(console=root_console, context=context)
            events = tcod.event.wait()
            engine.handle_tcod_events(events)


if __name__ == "__main__":
    main()
