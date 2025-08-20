"""Procedural generation system for RLT2025.

This module provides a comprehensive procedural generation architecture featuring:

- Region-first generation with atomic chunk commits
- Deterministic RNG per namespace for stable streaming
- Data-driven content with tag-based blueprint queries
- Blackboard context for inter-stage communication
- Deferred entity spawning for memory efficiency
- Stable entity handles for cross-chunk references

Usage:
    from rlt2025.gen import Pipeline, GenContext, FeatureRegistry
    from rlt2025.gen.stages import NoiseTerrain, PlaceBuildings
    from rlt2025.gen.blueprint_loader import BlueprintLoader

    # Create pipeline
    pipeline = Pipeline([
        NoiseTerrain([...]),
        PlaceBuildings({...})
    ])

    # Run generation
    ctx = GenContext(world, area, seed, features=registry)
    pipeline.run(ctx)
"""

# Core generation system
from .context import GenContext, ProceduralInterface
from .edits import Edits, EntitySpawn, TileWrite
from .features import Blueprint, FeatureRegistry

# Utilities
from .guid import make_blueprint_entity_guid, make_guid, make_procedural_entity_guid
from .pipeline import Pipeline
from .stage import Stage
from .stages.buildings import PlaceBuildings, SimpleRoomParcels
from .stages.cellular_automata import CellularAutomata

# Example stages
from .stages.noise_terrain import NoiseTerrain

# Integration
from .stream import ChunkManager

__all__ = [
    # Core system
    "GenContext",
    "ProceduralInterface",
    "Edits",
    "TileWrite",
    "EntitySpawn",
    "Stage",
    "Pipeline",
    "Blueprint",
    "FeatureRegistry",
    # Utilities
    "make_guid",
    "make_blueprint_entity_guid",
    "make_procedural_entity_guid",
    # Integration
    "ChunkManager",
    # Example stages
    "NoiseTerrain",
    "CellularAutomata",
    "PlaceBuildings",
    "SimpleRoomParcels",
]
