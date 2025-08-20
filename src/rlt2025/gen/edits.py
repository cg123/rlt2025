"""Pure data edits for procedural generation before atomic chunk commits."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from ..spatial import Vec3

if TYPE_CHECKING:
    pass


@dataclass
class TileWrite:
    """A tile write operation."""

    pos: Vec3
    tile: int  # TileID


@dataclass(frozen=True)
class StableId:
    """
    A stable, unique identifier for an entity that persists across saves.

    Used for deferred entity references during procedural generation.
    """

    guid: str


@dataclass
class EntitySpawn:
    """Pure data description of an entity to instantiate later."""

    stable_id: StableId  # Stable identifier for deferred references
    local_pos: Vec3  # Position relative to spawn location
    components: list[Callable[[], object]]  # Component factory functions
    tags: frozenset[str] = frozenset()


@dataclass
class Edits:
    """Collection of pure data edits to be applied to chunks atomically."""

    tiles: list[TileWrite] = field(default_factory=list)
    spawns: list[tuple[Vec3, EntitySpawn]] = field(
        default_factory=list
    )  # (world_pos, spawn)

    def add_tile(self, x: int, y: int, z: int, tile: int) -> None:
        """Add a tile write operation."""
        self.tiles.append(TileWrite(Vec3(x, y, z), tile))

    def add_spawn(self, world_pos: Vec3, spawn: EntitySpawn) -> None:
        """Add an entity spawn operation."""
        self.spawns.append((world_pos, spawn))

    def merge(self, other: "Edits") -> None:
        """Merge another Edits into this one."""
        self.tiles.extend(other.tiles)
        self.spawns.extend(other.spawns)

    def __len__(self) -> int:
        """Return total number of edits."""
        return len(self.tiles) + len(self.spawns)
