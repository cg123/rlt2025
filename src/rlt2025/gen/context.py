"""Generation context and deterministic RNG for procedural generation."""

import hashlib
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..map.chunks import world_to_chunk
from ..spatial import AABB

LOG = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..ecs.world import World
    from ..map.realm import Realm
    from .features import FeatureRegistry


def _hash_i64(s: str) -> int:
    """Convert a string to a deterministic 64-bit integer."""
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "little")


@dataclass
class ProceduralInterface:
    """
    A simplified interface to the world for procedural generation stages.

    This provides safe, read-only access to the realm and features.
    """

    world: "World"
    realm: "Realm"
    features: "FeatureRegistry"

    def commit(self, edits) -> None:
        """
        Commit procedural generation edits to the world.

        This is the bridge between procedural generation and the core world,
        keeping generation-specific logic separate from the core World class.

        Edits are grouped by chunk and applied per-chunk. Each chunk's edits
        are applied atomically, but if one chunk fails, other chunks are still
        committed.
        """

        # Group edits by chunk for atomic application
        tiles_by_chunk = defaultdict(list)
        spawns_by_chunk = defaultdict(list)

        # Group tile writes by chunk
        for tile_write in edits.tiles:
            chunk_key, _ = world_to_chunk(
                tile_write.pos.x, tile_write.pos.y, tile_write.pos.z
            )
            tiles_by_chunk[chunk_key].append(tile_write)

        # Group spawns by chunk
        for spawn in edits.spawns:
            chunk_key, _ = world_to_chunk(spawn[0].x, spawn[0].y, spawn[0].z)
            spawns_by_chunk[chunk_key].append(spawn)

        # Get all affected chunks
        all_chunk_keys = set(tiles_by_chunk.keys()) | set(spawns_by_chunk.keys())

        # Apply edits atomically per chunk. If a chunk fails, skip it but continue others.
        for chunk_key in all_chunk_keys:
            chunk = self.realm.get_or_create_chunk(chunk_key)

            # Buffer current state for atomic application
            new_tiles = chunk.tiles.copy()
            new_spawns = list(chunk.spawns)
            new_spawn_guids = set(getattr(chunk, "spawn_guids", set()))

            try:
                # Apply tile writes to the buffered tile array
                for tile_write in tiles_by_chunk[chunk_key]:
                    # Convert to local coordinates for this chunk
                    _, (lx, ly, lz) = world_to_chunk(
                        tile_write.pos.x, tile_write.pos.y, tile_write.pos.z
                    )
                    idx = chunk.local_index(lx, ly, lz)
                    new_tiles[idx] = tile_write.tile

                # Apply spawns for this chunk (deduplicated by GUID)
                for spawn in spawns_by_chunk[chunk_key]:
                    spawn_guid = spawn[1].stable_id.guid
                    if spawn_guid in new_spawn_guids:
                        continue
                    new_spawns.append(spawn)
                    new_spawn_guids.add(spawn_guid)

                # Commit atomically by swapping references
                chunk.tiles = new_tiles
                chunk.spawns = new_spawns
                # Ensure the GUID set exists and update it
                if not hasattr(chunk, "spawn_guids"):
                    chunk.spawn_guids = set()
                chunk.spawn_guids = new_spawn_guids
                LOG.debug(
                    "Committed chunk %s: %d tile writes, %d spawns (total spawns=%d)",
                    chunk_key,
                    len(tiles_by_chunk[chunk_key]),
                    len(spawns_by_chunk[chunk_key]),
                    len(chunk.spawns),
                )
            except Exception as e:
                # Skip committing this chunk's edits on error, continue others
                LOG.warning("Failed to commit edits for chunk %s: %s", chunk_key, e)
                continue


@dataclass
class GenContext:
    """
    Context for procedural generation containing shared state and utilities.

    This carries information between generation stages, including:
    - The world being generated (ECS and realm)
    - The area being generated
    - Deterministic RNG seeded per namespace
    - Shared blackboard for stage communication
    """

    area: AABB
    world_seed: int
    procgen: ProceduralInterface
    blackboard: dict[str, Any] = field(default_factory=dict)

    def rng(self, namespace: str) -> random.Random:
        """
        Get a deterministic RNG for the given namespace.

        The RNG is seeded based on (world_seed, area, namespace) so that:
        - Same parameters always produce same results (deterministic)
        - Different namespaces produce independent sequences
        - Overlapping areas generate consistently

        Note: For area-invariant randomness, prefer rng_at() or rng_for_pos().
        """
        salt = f"{self.world_seed}:{self.area.min}:{self.area.max}:{namespace}"
        seed = _hash_i64(salt)
        return random.Random(seed)

    def rng_at(self, namespace: str, *key_parts) -> random.Random:
        """
        Get a deterministic RNG seeded by position-independent key parts.

        This provides area-invariant randomness that depends only on the key parts,
        not on the current area bounds. Useful for per-cell or per-parcel generation
        where you want the same result regardless of area size/overlap.

        Args:
            namespace: Base namespace for the RNG
            *key_parts: Additional key components (positions, IDs, etc.)

        Example:
            # Same result regardless of area bounds
            rng = ctx.rng_at("terrain", x, y, z)
            # Or with string keys
            rng = ctx.rng_at("buildings", "house_placement", parcel_id)
        """
        key_str = ":".join(str(part) for part in key_parts)
        salt = f"{self.world_seed}:{namespace}:{key_str}"
        seed = _hash_i64(salt)
        return random.Random(seed)

    def rng_for_pos(self, namespace: str, x: int, y: int, z: int = 0) -> random.Random:
        """
        Get a deterministic RNG for a specific world position.

        This is a convenience wrapper around rng_at() for position-based randomness.
        The result is independent of the current area bounds.

        Args:
            namespace: Base namespace for the RNG
            x, y, z: World coordinates
        """
        return self.rng_at(namespace, x, y, z)

    def get_blackboard(self, key: str, default: Any = None) -> Any:
        """Get a value from the blackboard with optional default."""
        return self.blackboard.get(key, default)

    def set_blackboard(self, key: str, value: Any) -> None:
        """Set a value in the blackboard."""
        self.blackboard[key] = value

    def has_blackboard(self, key: str) -> bool:
        """Check if a key exists in the blackboard."""
        return key in self.blackboard
