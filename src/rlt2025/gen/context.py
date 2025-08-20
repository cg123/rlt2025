"""Generation context and deterministic RNG for procedural generation."""

import hashlib
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..spatial import AABB

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
        """
        from ..map.chunks import world_to_chunk

        for tile_write in edits.tiles:
            self.realm.write_tile(
                tile_write.pos.x, tile_write.pos.y, tile_write.pos.z, tile_write.tile
            )
        for spawn in edits.spawns:
            self.realm.get_or_create_chunk(
                world_to_chunk(spawn[0].x, spawn[0].y, spawn[0].z)[0]
            ).spawns.append(spawn)


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
        """
        salt = f"{self.world_seed}:{self.area.min}:{self.area.max}:{namespace}"
        seed = _hash_i64(salt)
        return random.Random(seed)

    def get_blackboard(self, key: str, default: Any = None) -> Any:
        """Get a value from the blackboard with optional default."""
        return self.blackboard.get(key, default)

    def set_blackboard(self, key: str, value: Any) -> None:
        """Set a value in the blackboard."""
        self.blackboard[key] = value

    def has_blackboard(self, key: str) -> bool:
        """Check if a key exists in the blackboard."""
        return key in self.blackboard
