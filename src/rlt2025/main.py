#!/usr/bin/env python3
import tcod

from rlt2025.components import Player, Position, Renderable, VisibilityInfo
from rlt2025.ecs import World
from rlt2025.engine import Engine
from rlt2025.gen.blueprint_loader import (
    BlueprintLoader,
    create_default_component_registry,
)
from rlt2025.gen.context import ProceduralInterface
from rlt2025.gen.features import FeatureRegistry
from rlt2025.gen.pipeline import Pipeline
from rlt2025.gen.stages.buildings import PlaceBuildings, SimpleRoomParcels
from rlt2025.gen.stages.cellular_automata import CellularAutomata
from rlt2025.gen.stages.noise_terrain import NoiseTerrain
from rlt2025.gen.stream import ChunkManager
from rlt2025.spatial import Vec3

TILESET = tcod.tileset.load_tilesheet(
    "dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
)


def setup_feature_registry() -> FeatureRegistry:
    """Set up the feature registry with example blueprints."""
    registry = FeatureRegistry()
    loader = BlueprintLoader(create_default_component_registry())
    loader.load_from_directory("data/blueprints", registry)
    return registry


def setup_generation_pipeline() -> Pipeline:
    """Set up a basic generation pipeline."""
    return Pipeline(
        [
            NoiseTerrain([(0.4, "wall"), (1.0, "floor")]),
            CellularAutomata(
                wall_name="wall", floor_name="floor", iterations=3, wall_threshold=4
            ),
            SimpleRoomParcels(room_size=(6, 4), padding=2),
            PlaceBuildings(tags={"room", "dungeon_room"}, density=0.3),
        ]
    )


def main() -> None:
    screen_width = 80
    screen_height = 50

    world = World()
    feature_registry = setup_feature_registry()
    pipeline = setup_generation_pipeline()

    procgen_interface = ProceduralInterface(
        world=world,
        realm=world.realm,
        features=feature_registry,
    )

    chunk_manager = ChunkManager(
        world=world,
        pipeline=pipeline,
        seed=12345,
        procgen=procgen_interface,
    )

    # Generate the initial area around the player
    initial_player_pos = Vec3(screen_width // 2, screen_height // 2, 0)
    chunk_manager.update_player_interest(initial_player_pos)

    world.create_entity(
        Position(x=initial_player_pos.x, y=initial_player_pos.y),
        Player(),
        Renderable(text="@", fg=(255, 255, 255), bg=None, layer=1),
        VisibilityInfo(compute_explored=True, dirty=True, sight_radius=10),
    )

    engine = Engine(
        world=world,
    )

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
