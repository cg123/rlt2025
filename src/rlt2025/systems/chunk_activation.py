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

    # Skip if already materialized to avoid duplicate entities
    if chunk.materialized_entities:
        return  # Already materialized

    for world_pos, spawn in chunk.spawns:
        # Combine anchor world position with spawn's local offset for final placement
        final_x = world_pos.x + getattr(spawn.local_pos, "x", 0)
        final_y = world_pos.y + getattr(spawn.local_pos, "y", 0)
        components = [spawn.stable_id, Position(final_x, final_y)]
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
    # Do not clear chunk.spawn_guids or chunk.spawns; reactivation relies on them


class ChunkActivationSystem:
    """ECS system that handles chunk activation/deactivation via events."""

    def __init__(self, world: "World"):
        # Register handlers with the EventBus API
        world.event_bus.register(
            ChunkActivateRequestEvent, self._handle_activate_request
        )
        world.event_bus.register(
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
            # Clean up entities but keep the chunk data resident so that
            # re-activation can restore entities without forcing regeneration.
            cleanup_chunk_entities(chunk, world)
