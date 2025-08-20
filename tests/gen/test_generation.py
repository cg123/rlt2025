"""Tests for deterministic procedural generation."""

import hashlib
import os
import tempfile

from rlt2025.ecs.world import World
from rlt2025.gen.blueprint_loader import BlueprintLoader
from rlt2025.gen.context import GenContext, ProceduralInterface
from rlt2025.gen.features import FeatureRegistry
from rlt2025.gen.pipeline import Pipeline
from rlt2025.gen.stages.buildings import PlaceBuildings
from rlt2025.gen.stages.cellular_automata import CellularAutomata
from rlt2025.gen.stages.noise_terrain import NoiseTerrain
from rlt2025.gen.stream import ChunkManager
from rlt2025.spatial import AABB, Vec3


def test_deterministic_generation():
    """
    Test that generation is deterministic - same seed produces same results.

    This is crucial for streaming worlds where the same area might be
    generated multiple times.
    """
    # Create two identical worlds
    world1 = World()
    world2 = World()

    # Create empty feature registries for testing
    from rlt2025.gen.features import FeatureRegistry

    features1 = FeatureRegistry()
    features2 = FeatureRegistry()

    # Create ProceduralInterfaces
    procgen1 = ProceduralInterface(world1, world1.realm, features1)
    procgen2 = ProceduralInterface(world2, world2.realm, features2)

    # Create identical pipelines
    pipeline1 = Pipeline([NoiseTerrain([(0.3, "wall"), (1.0, "floor")])])
    pipeline2 = Pipeline([NoiseTerrain([(0.3, "wall"), (1.0, "floor")])])

    # Same generation parameters
    seed = 12345
    area = AABB(Vec3(0, 0, 0), Vec3(32, 32, 1))

    # Generate in both worlds
    ctx1 = GenContext(area, seed, procgen1)
    ctx2 = GenContext(area, seed, procgen2)

    pipeline1.run(ctx1)
    pipeline2.run(ctx2)

    # Compare results by hashing tile contents
    def hash_tiles(realm, area: AABB) -> str:
        hasher = hashlib.blake2b()
        for x, y in area.iter_xy():
            tile_id = realm.read_tile(x, y, 0)
            hasher.update(tile_id.to_bytes(4, "little"))
        return hasher.hexdigest()

    hash1 = hash_tiles(world1.realm, area)
    hash2 = hash_tiles(world2.realm, area)

    assert hash1 == hash2, f"Generation not deterministic: {hash1} != {hash2}"
    print("✓ Deterministic generation test PASSED")


def test_pipeline_dependency_validation():
    """
    Test that pipeline dependency validation works correctly.
    """

    # Create pipeline with unsatisfied dependencies
    pipeline = Pipeline()

    # Add a stage that requires something not provided
    buildings_stage = PlaceBuildings({"building"})
    pipeline.add_stage(buildings_stage)

    try:
        pipeline.validate_dependencies()
        assert False, "Should have thrown RuntimeError for missing dependencies"
    except RuntimeError as e:
        assert "parcels" in str(e), f"Wrong error message: {e}"
        print("✓ Dependency validation test PASSED")


def test_blueprint_stamping():
    """Test that blueprints stamp correctly."""
    from rlt2025.gen.features import Blueprint

    # Create a simple test blueprint
    blueprint = Blueprint(
        id="test_room",
        w=3,
        h=3,
        rows=("###", "#.#", "###"),
        legend={"#": "wall", ".": "floor"},
        tags=frozenset({"test"}),
    )

    # Create test environment
    world = World()

    # Stamp the blueprint
    origin = Vec3(10, 10, 0)
    edits = blueprint.stamp(origin, world.realm.tiles, world_seed=12345)

    # Check that we got the right number of tile writes
    # 3x3 grid = 9 total tiles (8 wall tiles + 1 floor tile)
    assert len(edits.tiles) == 9, f"Expected 9 tiles, got {len(edits.tiles)}"
    print("✓ Blueprint stamping test PASSED")


def test_blueprint_loader_validation():
    """Test that BlueprintLoader properly validates YAML data."""
    loader = BlueprintLoader()

    # Test invalid YAML structure
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("not a dict but a string")
        temp_path = f.name

    try:
        loader.load_from_file(temp_path)
        assert False, "Should have rejected non-dict YAML"
    except ValueError as e:
        assert "dictionary" in str(e), f"Wrong error message: {e}"
        print("✓ Blueprint loader validation test PASSED - rejects non-dict YAML")
    finally:
        os.unlink(temp_path)

    # Test missing required fields
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("id: test\n# missing size and rows")
        temp_path = f.name

    try:
        loader.load_from_file(temp_path)
        assert False, "Should have required size and rows fields"
    except ValueError as e:
        assert "Missing required field" in str(e), f"Wrong error message: {e}"
        print("✓ Blueprint loader validation test PASSED - validates required fields")
    finally:
        os.unlink(temp_path)


def test_blueprint_loader_valid_file():
    """Test that BlueprintLoader can load a valid blueprint."""
    loader = BlueprintLoader()

    # Create a valid test blueprint
    yaml_content = """
id: test_room
size: [3, 3]
rows:
  - "###"
  - "#.#"
  - "###"
legend:
  "#": "wall"
  ".": "floor"
tags:
  - "test"
  - "room"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    try:
        blueprint = loader.load_from_file(temp_path)

        # Validate blueprint properties
        assert blueprint.id == "test_room", f"Wrong id: {blueprint.id}"
        assert blueprint.w == 3, f"Wrong width: {blueprint.w}"
        assert blueprint.h == 3, f"Wrong height: {blueprint.h}"
        assert len(blueprint.rows) == 3, f"Wrong number of rows: {len(blueprint.rows)}"
        assert "test" in blueprint.tags, f"Missing 'test' tag: {blueprint.tags}"
        assert "room" in blueprint.tags, f"Missing 'room' tag: {blueprint.tags}"
        print("✓ Blueprint loader valid file test PASSED")
    finally:
        os.unlink(temp_path)


def test_chunk_manager_basic_operations():
    """Test basic ChunkManager generation and caching."""

    # Create test world and pipeline
    world = World()
    features = FeatureRegistry()
    procgen = ProceduralInterface(world, world.realm, features)

    # Create simple pipeline for testing
    pipeline = Pipeline([NoiseTerrain([(0.5, "wall"), (1.0, "floor")])])

    chunk_manager = ChunkManager(world, pipeline, 12345, procgen)

    # Test that generation works
    test_area = AABB(Vec3(0, 0, 0), Vec3(32, 32, 1))

    # Should not raise exception
    chunk_manager.ensure_generated(test_area)

    # Test cache tracking
    stats = chunk_manager.get_cache_stats()
    assert stats["generated_regions"] > 0, "No regions were generated"
    print("✓ ChunkManager basic operations test PASSED")


def test_cellular_automata_double_buffering():
    """Test that cellular automata uses proper double-buffering."""
    world = World()
    features = FeatureRegistry()
    procgen = ProceduralInterface(world, world.realm, features)

    # Create a simple test pattern that should be affected by double-buffering
    area = AABB(Vec3(0, 0, 0), Vec3(5, 5, 1))

    # Set up initial pattern: single wall surrounded by floors
    for x, y in area.iter_xy():
        tile_id = 1 if (x == 2 and y == 2) else 2  # wall in center, floor elsewhere
        world.realm.write_tile(x, y, 0, tile_id)

    # Create CA stage with low threshold so center wall should disappear
    ca_stage = CellularAutomata("wall", "floor", iterations=1, wall_threshold=4)

    ctx = GenContext(area, 12345, procgen)
    edits = ca_stage.apply(ctx)

    # Apply edits
    for edit in edits.tiles:
        world.realm.write_tile(edit.pos.x, edit.pos.y, edit.pos.z, edit.tile)

    # Center should now be floor (tile_id 2) since it had < 4 wall neighbors
    center_tile = world.realm.read_tile(2, 2, 0)
    floor_id = world.realm.tiles.id("floor")

    assert center_tile == floor_id, f"Center tile is {center_tile}, expected {floor_id}"
    print("✓ Cellular automata double-buffering test PASSED")


def run_all_tests() -> bool:
    """Run all generation tests."""
    print("Running procedural generation tests...")
    print()

    tests = [
        test_deterministic_generation,
        test_pipeline_dependency_validation,
        test_blueprint_stamping,
        test_blueprint_loader_validation,
        test_blueprint_loader_valid_file,
        test_chunk_manager_basic_operations,
        test_cellular_automata_double_buffering,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} FAILED with exception: {e}")
            results.append(False)
        print()

    passed = sum(results)
    total = len(results)

    print(f"Tests completed: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    run_all_tests()
