import random
from typing import Iterator, Tuple

import rlt2025.map.tile_types as tile_types
from rlt2025.map.game_map import GameMap

import tcod


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2

        return center_x, center_y

    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: "RectangularRoom") -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )


def tunnel_between(
    start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    x1, y1 = start
    x2, y2 = end

    if random.random() < 0.5:
        cx, cy = x2, y1
    else:
        cx, cy = x1, y2

    for x, y in tcod.los.bresenham((x1, y1), (cx, cy)):
        yield x, y

    for x, y in tcod.los.bresenham((cx, cy), (x2, y2)):
        yield x, y


def generate_dungeon(
    width: int, height: int, max_rooms: int, room_min_size: int, room_max_size: int
) -> Tuple[GameMap, Tuple[int, int]]:
    dungeon = GameMap(width, height)

    start_x, start_y = width // 2, height // 2

    rooms: list[RectangularRoom] = []
    for _ in range(max_rooms):
        w = random.randint(room_min_size, room_max_size)
        h = random.randint(room_min_size, room_max_size)
        x0 = random.randint(0, width - w - 1)
        y0 = random.randint(0, height - h - 1)

        new_room = RectangularRoom(x0, y0, w, h)

        if any(new_room.intersects(other) for other in rooms):
            continue

        dungeon.tiles[new_room.inner] = tile_types.floor

        if rooms:
            prev_room = rooms[-1]
            for x, y in tunnel_between(prev_room.center, new_room.center):
                dungeon.tiles[x, y] = tile_types.floor
        else:
            start_x, start_y = new_room.center

        rooms.append(new_room)

    return dungeon, (start_x, start_y)
