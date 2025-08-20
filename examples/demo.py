"""Demonstration of the procedural generation system."""

import sys
from pathlib import Path

# Add the src directory to Python path so we can import rlt2025
# Note: This is needed because we're running from the examples directory
# ruff: noqa: E402
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from rlt2025.ecs.world import World  # noqa: E402
from rlt2025.gen.blueprint_loader import BlueprintLoader  # noqa: E402
from rlt2025.gen.blueprint_loader import create_default_component_registry
from rlt2025.gen.context import GenContext, ProceduralInterface  # noqa: E402
from rlt2025.gen.features import FeatureRegistry  # noqa: E402
from rlt2025.gen.pipeline import Pipeline  # noqa: E402
from rlt2025.gen.stages.buildings import PlaceBuildings  # noqa: E402
from rlt2025.gen.stages.buildings import SimpleRoomParcels
from rlt2025.gen.stages.cellular_automata import CellularAutomata  # noqa: E402
from rlt2025.gen.stages.noise_terrain import NoiseTerrain  # noqa: E402
from rlt2025.gen.stream import ChunkManager  # noqa: E402
from rlt2025.spatial import AABB, Vec3  # noqa: E402


def create_dungeon_pipeline() -> Pipeline:
    """Create a pipeline for dungeon generation."""
    return Pipeline(
        [
            # 1. Generate basic terrain with noise
            NoiseTerrain([(0.4, "wall"), (1.0, "floor")]),
            # 2. Smooth terrain with cellular automata
            CellularAutomata(
                wall_name="wall", floor_name="floor", iterations=3, wall_threshold=4
            ),
            # 3. Create room parcels for content placement
            SimpleRoomParcels(room_size=(6, 4), padding=2),
            # 4. Place rooms/buildings from blueprints
            PlaceBuildings(tags={"room", "dungeon_room"}, density=0.3),
        ]
    )


def create_city_pipeline() -> Pipeline:
    """Create a pipeline for city generation."""
    return Pipeline(
        [
            # 1. Generate base terrain (mostly floor)
            NoiseTerrain(
                [
                    (0.1, "wall"),  # Very few walls
                    (1.0, "floor"),
                ]
            ),
            # 2. Create building plots
            SimpleRoomParcels(room_size=(10, 8), padding=3),
            # 3. Place buildings
            PlaceBuildings(tags={"building", "house"}, density=0.7),
        ]
    )


def demo_generation():
    """Demonstrate the generation system with different scenarios."""
    print("🎮 Procedural Generation System Demo")
    print("=" * 50)

    # Create world and setup
    world = World()
    # The realm now has integrated generation capabilities

    # Setup feature registry with example blueprints
    features = FeatureRegistry()
    loader = BlueprintLoader(create_default_component_registry())
    loader.load_from_directory("data/blueprints", features)

    print(f"📚 Loaded {len(features.by_id)} blueprints")
    print(f"🏷️  Available tags: {', '.join(features.get_tags())}")
    print()

    procgen_interface = ProceduralInterface(world, world.realm, features)

    # Demo 1: Small dungeon area
    print("🏰 Generating dungeon area...")
    dungeon_pipeline = create_dungeon_pipeline()

    area1 = AABB(Vec3(0, 0, 0), Vec3(64, 64, 1))
    ctx1 = GenContext(area1, 42, procgen_interface)

    print(f"📋 Pipeline stages: {', '.join(dungeon_pipeline.get_stage_order())}")
    print(f"🎯 Provides: {', '.join(dungeon_pipeline.get_all_provides())}")

    dungeon_pipeline.run(ctx1)

    print(f"✅ Generated {area1.width()}x{area1.height()} dungeon area")
    print(f"📦 Created parcels: {len(ctx1.get_blackboard('parcels', []))}")
    print()

    # Demo 2: City area with different pipeline
    print("🏙️ Generating city area...")
    city_pipeline = create_city_pipeline()

    area2 = AABB(Vec3(100, 0, 0), Vec3(164, 64, 1))
    ctx2 = GenContext(area2, 42, procgen_interface)

    city_pipeline.run(ctx2)
    print(f"✅ Generated {area2.width()}x{area2.height()} city area")
    print()

    # Demo 3: Streaming generation
    print("🌊 Setting up streaming generation...")
    chunk_manager = ChunkManager(
        world=world, pipeline=dungeon_pipeline, seed=42, procgen=procgen_interface
    )

    # Simulate player movement
    player_positions = [
        Vec3(32, 32, 0),
        Vec3(64, 32, 0),
        Vec3(96, 32, 0),
    ]

    for i, pos in enumerate(player_positions):
        print(f"📍 Player at {pos}")
        chunk_manager.update_player_interest(pos, radius_chunks=2)
        print(f"🎯 Active chunks: {len(chunk_manager.active_chunks)}")
        print(f"🏗️  Generated regions: {len(chunk_manager.generated_regions)}")
        print()

    print("🎉 Demo completed!")
    print()
    print("💡 Key features demonstrated:")
    print("   • Deterministic generation with stable RNG")
    print("   • Pipeline-based stage composition")
    print("   • Blueprint/feature system with tag queries")
    print("   • Cross-chunk atomic commits")
    print("   • Streaming generation for infinite worlds")
    print("   • Blackboard communication between stages")


def print_tile_map(realm, area: AABB, char_map: dict = None):
    """Print a simple ASCII visualization of generated tiles."""
    if char_map is None:
        char_map = {
            realm.tiles.id("void"): " ",
            realm.tiles.id("floor"): ".",
            realm.tiles.id("wall"): "#",
            realm.tiles.id("door"): "+",
        }

    print("Generated map:")
    for y in range(area.min.y, area.max.y):
        row = ""
        for x in range(area.min.x, area.max.x):
            tile_id = realm.read_tile(x, y, 0)
            row += char_map.get(tile_id, "?")
        print(row)
    print()


if __name__ == "__main__":
    demo_generation()
