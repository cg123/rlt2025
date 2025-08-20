"""System for materializing deferred entity spawns when chunks are activated."""

from typing import TYPE_CHECKING

from ..components import Position
from ..events import ChunkActivateRequestEvent, ChunkDeactivateRequestEvent

if TYPE_CHECKING:
    from ..ecs.world import World
    from ..map.chunks import Chunk


def materialize_chunk_spawns(chunk: "Chunk", world: "World") -> None:
    """
    Materialize all deferred entity spawns in a chunk.

    This is called when a chunk becomes active. It creates all entities
    and components that were deferred during world generation.

    Preserves the original spawn list so chunks can be reactivated later.
    """
    if not chunk.spawns:
        return  # Nothing to do

    for world_pos, spawn in chunk.spawns:
        components = [spawn.stable_id, Position(world_pos.x, world_pos.y)]
        for comp_factory in spawn.components:
            components.append(comp_factory())
        entity_id = world.create_entity(*components)

        # Track this entity as belonging to this chunk
        chunk.materialized_entities.add(entity_id)


def cleanup_chunk_entities(chunk: "Chunk", world: "World") -> None:
    """
    Clean up entities that were materialized from this chunk.

    This is called when a chunk becomes inactive. It removes all entities
    that were created from the chunk's spawn list.
    """
    for entity_id in chunk.materialized_entities:
        # Only destroy if the entity still exists (it might have been destroyed already)
        if world.entities.exists(entity_id):
            world.entities.destroy_entity(entity_id)

    # Clear the materialized entities set
    chunk.materialized_entities.clear()


class ChunkActivationSystem:
    """ECS system that handles chunk activation/deactivation via events."""

    def __init__(self, world: "World"):
        world.event_bus.subscribe(
            ChunkActivateRequestEvent, self._handle_activate_request
        )
        world.event_bus.subscribe(
            ChunkDeactivateRequestEvent, self._handle_deactivate_request
        )

    def _handle_activate_request(
        self, event: ChunkActivateRequestEvent, world: "World"
    ) -> None:
        """Handle chunk activation request event."""
        # Get the realm from the world (assuming it's stored there)
        realm = getattr(world, "realm", None)
        if realm and event.chunk_key in realm.chunks:
            chunk = realm.chunks[event.chunk_key]
            materialize_chunk_spawns(chunk, world)

    def _handle_deactivate_request(
        self, event: ChunkDeactivateRequestEvent, world: "World"
    ) -> None:
        """Handle chunk deactivation request event."""
        # Get the realm from the world (assuming it's stored there)
        realm = getattr(world, "realm", None)
        if realm and event.chunk_key in realm.chunks:
            chunk = realm.chunks[event.chunk_key]
            cleanup_chunk_entities(chunk, world)
            # Remove the chunk from memory
            del realm.chunks[event.chunk_key]
