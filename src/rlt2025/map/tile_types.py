from typing import NamedTuple, Tuple

import numpy as np  # type: ignore

# Tile graphics structured type compatible with Console.tiles_rgb.
graphic_dt = np.dtype(
    [
        ("char", np.int32),
        ("fg", "3B"),
        ("bg", "3B"),
    ]
)

# Tile struct used for statically defined tile data.
tile_dt = np.dtype(
    [
        ("walkable", np.bool),  # True if this tile can be walked over.
        ("transparent", np.bool),  # True if this tile doesn't block FOV.
        ("dark", graphic_dt),  # Graphics for when this tile is not in FOV.
        ("light", graphic_dt),  # Graphics for when this tile is in FOV.
    ]
)


class GraphicTuple(NamedTuple):
    char: int
    fg: Tuple[int, int, int]
    bg: Tuple[int, int, int]


class TileData(NamedTuple):
    walkable: bool
    transparent: bool
    dark: GraphicTuple
    light: GraphicTuple


def new_tile(
    *,  # Enforce the use of keywords, so that parameter order doesn't matter.
    walkable: int,
    transparent: int,
    dark: GraphicTuple,
    light: GraphicTuple,
) -> np.ndarray:
    """Helper function for defining individual tile types"""
    return np.array((walkable, transparent, dark, light), dtype=tile_dt)


# for unseen tiles
SHROUD = np.array((ord(" "), (255, 255, 255), (0, 0, 0)), dtype=graphic_dt)

floor = new_tile(
    walkable=True,
    transparent=True,
    dark=GraphicTuple(
        char=ord(" "),
        fg=(255, 255, 255),
        bg=(50, 50, 150),
    ),
    light=GraphicTuple(
        char=ord(" "),
        fg=(255, 255, 255),
        bg=(200, 200, 250),
    ),
)
wall = new_tile(
    walkable=False,
    transparent=False,
    dark=GraphicTuple(
        char=ord(" "),
        fg=(255, 255, 255),
        bg=(0, 0, 100),
    ),
    light=GraphicTuple(
        char=ord(" "),
        fg=(255, 255, 255),
        bg=(130, 130, 130),
    ),
)
