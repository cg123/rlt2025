from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from tcod.console import Console

from rlt2025.events import ChunkActivateRequestEvent, ChunkDeactivateRequestEvent
from rlt2025.map.chunks import CHUNK_DEPTH, CHUNK_SIZE
from rlt2025.map.chunks import Chunk as NewChunk
from rlt2025.map.chunks import ChunkKey, world_to_chunk
from rlt2025.map.tile_types import SHROUD
from rlt2025.map.tiles import TileRegistry

if TYPE_CHECKING:
    from rlt2025.ecs import World


@dataclass
class Realm:
    """
    Realm with integrated chunk management and tile registry support.
    """

    width: int
    height: int
    tiles: TileRegistry = field(default_factory=TileRegistry)
    chunks: dict[ChunkKey, NewChunk] = field(default_factory=dict)

    def __post_init__(self):
        self._setup_default_tiles()

    def _setup_default_tiles(self):
        """Set up basic tile types for the generation system."""
        self.tiles.register_new(
            "void", " ", (0, 0, 0), (0, 0, 0), blocks_move=True, blocks_sight=True
        )
        self.tiles.register_new(
            "floor",
            ".",
            (130, 110, 50),
            (20, 20, 20),
            blocks_move=False,
            blocks_sight=False,
        )
        self.tiles.register_new(
            "wall", "#", (0, 100, 0), (0, 40, 0), blocks_move=True, blocks_sight=True
        )
        self.tiles.register_new(
            "door",
            "+",
            (130, 110, 50),
            (20, 20, 20),
            blocks_move=False,
            blocks_sight=False,
        )

    def render(
        self, console: Console, visible: np.ndarray, explored: np.ndarray
    ) -> None:
        if not self.chunks:
            return
        # This render method will need to be updated to handle multiple chunks if the viewport is larger than one chunk
        # For now, we assume the viewport is within a single chunk
        visible_tiles = np.full(
            (self.width, self.height), fill_value=self.tiles.id("void"), order="F"
        )
        for x in range(self.width):
            for y in range(self.height):
                visible_tiles[x, y] = self.read_tile(x, y)

        light_tiles = np.array(
            [self.tiles.get(tile_id).light for tile_id in visible_tiles.flatten()],
            dtype=SHROUD.dtype,
        ).reshape(visible_tiles.shape)
        dark_tiles = np.array(
            [self.tiles.get(tile_id).dark for tile_id in visible_tiles.flatten()],
            dtype=SHROUD.dtype,
        ).reshape(visible_tiles.shape)

        console.rgb[0 : self.width, 0 : self.height] = np.select(
            condlist=[
                visible,
                explored,
            ],
            choicelist=[
                light_tiles,
                dark_tiles,
            ],
            default=np.full((self.width, self.height), fill_value=SHROUD, order="F"),
        )

    def read_tile(self, x: int, y: int, z: int = 0) -> int:
        """Read a tile ID at world coordinates."""
        chunk_key, (lx, ly, lz) = world_to_chunk(x, y, z)
        if chunk_key in self.chunks:
            chunk = self.chunks[chunk_key]
            return chunk.get_local(lx, ly, lz)

        return self.tiles.id("void")

    def write_tile(self, x: int, y: int, z: int, tile_id: int) -> None:
        """Write a tile ID at world coordinates."""
        chunk_key, (lx, ly, lz) = world_to_chunk(x, y, z)
        chunk = self.get_or_create_chunk(chunk_key)
        chunk.set_local(lx, ly, lz, tile_id)

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this realm."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_or_create_chunk(self, chunk_key: ChunkKey) -> NewChunk:
        """Get or create a chunk at the given key."""
        if chunk_key not in self.chunks:
            self.chunks[chunk_key] = NewChunk(
                key=chunk_key,
                tiles=[self.tiles.id("void")] * (CHUNK_SIZE * CHUNK_SIZE * CHUNK_DEPTH),
            )
        return self.chunks[chunk_key]

    def activate_chunk(self, chunk_key: ChunkKey, world: "World") -> None:
        """Request chunk activation via event bus."""
        world.event_bus.post(ChunkActivateRequestEvent(chunk_key=chunk_key))

    def deactivate_chunk(self, chunk_key: ChunkKey, world: "World") -> None:
        """Request chunk deactivation via event bus."""
        world.event_bus.post(ChunkDeactivateRequestEvent(chunk_key=chunk_key))
