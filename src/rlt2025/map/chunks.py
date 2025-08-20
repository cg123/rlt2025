"""Chunk-based map storage with deferred entity spawning."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

from ..spatial import Vec3

if TYPE_CHECKING:
    from ..gen.edits import EntitySpawn


class ChunkKey(NamedTuple):
    """Unique identifier for a chunk."""

    cx: int
    cy: int
    cz: int = 0


CHUNK_SIZE = 32
CHUNK_DEPTH = 1  # Z dimension size for chunks (keeping 2D for now, but extensible)


@dataclass
class Chunk:
    """A chunk of the world containing tiles and deferred entity spawns."""

    key: ChunkKey
    tiles: list[int]  # flat array of TileIDs, length CHUNK_SIZE^2 * CHUNK_DEPTH
    spawns: list[tuple[Vec3, "EntitySpawn"]] = field(default_factory=list)
    materialized_entities: set[int] = field(
        default_factory=set
    )  # Track materialized entity IDs

    def __post_init__(self):
        """Initialize tiles array if empty."""
        if not self.tiles:
            self.tiles = [0] * (CHUNK_SIZE * CHUNK_SIZE * CHUNK_DEPTH)

    def local_index(self, lx: int, ly: int, lz: int = 0) -> int:
        """Convert local coordinates to flat array index."""
        return lz * CHUNK_SIZE * CHUNK_SIZE + ly * CHUNK_SIZE + lx

    def get_local(self, lx: int, ly: int, lz: int = 0) -> int:
        """Get tile at local coordinates."""
        if not (
            0 <= lx < CHUNK_SIZE and 0 <= ly < CHUNK_SIZE and 0 <= lz < CHUNK_DEPTH
        ):
            return 0  # Out of bounds returns void/empty tile
        return self.tiles[self.local_index(lx, ly, lz)]

    def set_local(self, lx: int, ly: int, lz: int, tile_id: int) -> None:
        """Set tile at local coordinates."""
        if not (
            0 <= lx < CHUNK_SIZE and 0 <= ly < CHUNK_SIZE and 0 <= lz < CHUNK_DEPTH
        ):
            return  # Ignore out of bounds writes
        self.tiles[self.local_index(lx, ly, lz)] = tile_id


def world_to_chunk(x: int, y: int, z: int = 0) -> tuple[ChunkKey, tuple[int, int, int]]:
    """Convert world coordinates to chunk key and local coordinates."""
    # Handle negative coordinates properly for chunk calculation
    # Python's // operator handles negative numbers correctly for chunk boundaries
    cx = x // CHUNK_SIZE
    cy = y // CHUNK_SIZE
    cz = z // CHUNK_DEPTH

    # For negative coordinates, adjust local coordinates to be positive
    lx = x - (cx * CHUNK_SIZE)
    ly = y - (cy * CHUNK_SIZE)
    lz = z - (cz * CHUNK_DEPTH)

    # Validate local coordinates are within bounds
    if not (0 <= lx < CHUNK_SIZE and 0 <= ly < CHUNK_SIZE and 0 <= lz < CHUNK_DEPTH):
        raise ValueError(
            f"Invalid local coordinates calculated: ({lx}, {ly}, {lz}) for world coords ({x}, {y}, {z})"
        )

    return ChunkKey(cx, cy, cz), (lx, ly, lz)


def chunk_to_world(chunk_key: ChunkKey, lx: int, ly: int, lz: int = 0) -> Vec3:
    """Convert chunk key and local coordinates to world coordinates."""
    # Validate local coordinates are within chunk bounds
    if not (0 <= lx < CHUNK_SIZE and 0 <= ly < CHUNK_SIZE and 0 <= lz < CHUNK_DEPTH):
        raise ValueError(
            f"Local coordinates ({lx}, {ly}, {lz}) out of bounds for chunk size {CHUNK_SIZE}x{CHUNK_SIZE}x{CHUNK_DEPTH}"
        )

    return Vec3(
        chunk_key.cx * CHUNK_SIZE + lx,
        chunk_key.cy * CHUNK_SIZE + ly,
        chunk_key.cz * CHUNK_DEPTH + lz,
    )
