"""Tile definitions and registry for the map system."""

from dataclasses import dataclass
from typing import TypeAlias

TileID: TypeAlias = int


@dataclass(frozen=True)
class TileDef:
    """Definition of a tile type."""

    id: TileID
    name: str
    glyph: str
    light_fg: tuple[int, int, int]
    light_bg: tuple[int, int, int]
    dark_fg: tuple[int, int, int]
    dark_bg: tuple[int, int, int]
    blocks_move: bool = False
    blocks_sight: bool = False
    tags: frozenset[str] = frozenset()


class TileRegistry:
    """Registry for tile definitions, providing lookup by ID or name."""

    def __init__(self):
        self.by_id: dict[TileID, TileDef] = {}
        self.by_name: dict[str, TileDef] = {}
        self._next_id = 1

    def register(self, tile: TileDef) -> None:
        """Register a tile definition."""
        if tile.id in self.by_id:
            raise ValueError(f"Tile ID {tile.id} already registered")
        if tile.name in self.by_name:
            raise ValueError(f"Tile name '{tile.name}' already registered")

        self.by_id[tile.id] = tile
        self.by_name[tile.name] = tile

    def register_new(
        self,
        name: str,
        glyph: str,
        light_fg: tuple[int, int, int],
        light_bg: tuple[int, int, int],
        dark_fg: tuple[int, int, int],
        dark_bg: tuple[int, int, int],
        blocks_move: bool = False,
        blocks_sight: bool = False,
        tags: frozenset[str] = frozenset(),
    ) -> TileDef:
        """Register a new tile with auto-assigned ID."""
        tile = TileDef(
            id=self._next_id,
            name=name,
            glyph=glyph,
            light_fg=light_fg,
            light_bg=light_bg,
            dark_fg=dark_fg,
            dark_bg=dark_bg,
            blocks_move=blocks_move,
            blocks_sight=blocks_sight,
            tags=tags,
        )
        self._next_id += 1
        self.register(tile)
        return tile

    def get(self, tile_id: TileID) -> TileDef:
        """Get tile definition by ID."""
        return self.by_id[tile_id]

    def get_by_name(self, name: str) -> TileDef:
        """Get tile definition by name."""
        return self.by_name[name]

    def id(self, name: str) -> TileID:
        """Get tile ID by name."""
        return self.by_name[name].id

    def name(self, tile_id: TileID) -> str:
        """Get tile name by ID."""
        return self.by_id[tile_id].name

    def has_tile(self, name: str) -> bool:
        """Check if a tile with the given name exists."""
        return name in self.by_name
