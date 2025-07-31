from typing import Tuple

from tcod.console import Console


class Entity:
    """
    A generic object to represent players, enemies, items, etc.
    """

    def __init__(self, x: int, y: int, text: str, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.text = text
        self.color = color

    def move(self, dx: int, dy: int) -> None:
        # Move the entity by a given amount
        self.x += dx
        self.y += dy

    def render(self, console: Console) -> None:
        # Render the entity on the console
        console.print(x=self.x, y=self.y, text=self.text, fg=self.color)
