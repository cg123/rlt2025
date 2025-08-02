from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import numpy as np
from tcod.console import Console

from rlt2025.components import Player, Position, Renderable, VisibilityInfo
from rlt2025.map.simple_dungeon import generate_dungeon
from rlt2025.map.tile_types import SHROUD, TileData

if TYPE_CHECKING:
    from rlt2025.ecs import Entity, World


@dataclass
class Chunk:
    coords: tuple[int, int]  # (x, y) coordinates of top-left corner
    tiles: np.ndarray
    entities: set["Entity"] = field(default_factory=set)


class Realm:
    # placeholder for now - just a single screen-sized chunk
    # in the future, this will be a collection of chunks that can be loaded/unloaded
    # as the player moves around the world
    width: int
    height: int
    chunk: Optional[Chunk] = None

    def __init__(self):
        self.width = 0
        self.height = 0

    def generate(self, world: "World", width: int, height: int) -> None:
        """Generate the initial chunk for the realm."""

        self.width = width
        self.height = height

        tiles, player_pos = generate_dungeon(
            width=self.width,
            height=self.height,
            max_rooms=30,
            room_min_size=5,
            room_max_size=10,
        )
        self.chunk = Chunk(
            coords=(0, 0),
            tiles=tiles,
        )

        player_entity = world.entities.create_entity()
        world.entities.add_component(
            player_entity, Position(x=player_pos[0], y=player_pos[1])
        )
        world.entities.add_component(
            player_entity,
            Player(),
        )
        world.entities.add_component(
            player_entity, Renderable(text="@", fg=(255, 255, 255), bg=None, layer=1)
        )
        world.entities.add_component(
            player_entity,
            VisibilityInfo(compute_explored=True, dirty=True, sight_radius=10),
        )

        self.chunk.entities.add(player_entity)

    def render(
        self, console: Console, visible: np.ndarray, explored: np.ndarray
    ) -> None:
        if self.chunk is None:
            raise ValueError("Realm chunk is not initialized.")
        console.rgb[0 : self.width, 0 : self.height] = np.select(
            condlist=[
                visible,
                explored,
            ],
            choicelist=[
                self.chunk.tiles["light"],
                self.chunk.tiles["dark"],
            ],
            default=SHROUD,
        )

    def get_tile(self, x: int, y: int) -> Optional[TileData]:
        """Get the tile at the given coordinates."""
        if self.chunk is None:
            raise ValueError("Realm chunk is not initialized.")
        if not self.in_bounds(x, y):
            return None
        res = self.chunk.tiles[x, y]
        return TileData(
            walkable=res["walkable"],
            transparent=res["transparent"],
            dark=res["dark"],
            light=res["light"],
        )

    def set_tile(self, x: int, y: int, tile_data: TileData) -> None:
        """Set the tile at the given coordinates."""
        if self.chunk is None:
            raise ValueError("Realm chunk is not initialized.")
        if not self.in_bounds(x, y):
            raise ValueError(f"Coordinates ({x}, {y}) are out of bounds.")
        self.chunk.tiles[x, y] = tile_data

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this realm."""
        if self.chunk is None:
            raise ValueError("Realm chunk is not initialized.")
        return 0 <= x < self.chunk.tiles.shape[0] and 0 <= y < self.chunk.tiles.shape[1]
