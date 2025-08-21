"""Cellular automata smoothing stage for terrain refinement."""

from typing import TYPE_CHECKING

from ..context import GenContext
from ..edits import Edits

if TYPE_CHECKING:
    pass


class CellularAutomata:
    """
    Apply cellular automata rules to smooth terrain.

    This stage reads existing terrain and applies smoothing rules
    to create more natural-looking cave systems or terrain features.
    """

    def __init__(
        self,
        wall_name: str,
        floor_name: str,
        iterations: int = 4,
        wall_threshold: int = 5,
        read_from_realm: bool = False,
    ):
        """
        Initialize cellular automata parameters.

        Args:
            wall_name: Name of the wall tile type
            floor_name: Name of the floor tile type
            iterations: Number of CA iterations to apply
            wall_threshold: Minimum neighbor walls needed to become/stay wall
            read_from_realm: If True, read out-of-area neighbors from realm on first iteration.
                           If False, treat out-of-area as walls (default behavior).
        """
        self.wall_name = wall_name
        self.floor_name = floor_name
        self.iterations = iterations
        self.wall_threshold = wall_threshold
        self.read_from_realm = read_from_realm

    @property
    def id(self) -> str:
        return "cellular_automata"

    @property
    def provides(self) -> set[str]:
        return set()  # Modifies existing terrain, doesn't provide new data

    @property
    def requires(self) -> set[str]:
        return {"terrain"}

    def apply(self, ctx: GenContext) -> Edits:
        """Apply cellular automata smoothing to the terrain."""
        edits = Edits()

        try:
            wall_id = ctx.procgen.realm.tiles.id(self.wall_name)
            floor_id = ctx.procgen.realm.tiles.id(self.floor_name)
        except KeyError as e:
            raise ValueError(f"Cellular automata stage: unknown tile type {e}")

        # Build initial state from realm
        current_state = {}
        for x, y in ctx.area.iter_xy():
            z = ctx.area.min.z
            current_state[(x, y)] = ctx.procgen.realm.read_tile(x, y, z)

        # Apply multiple iterations of cellular automata using double-buffering
        for iteration in range(self.iterations):
            next_state = {}

            for x, y in ctx.area.iter_xy():
                z = ctx.area.min.z

                # Count wall neighbors in 3x3 grid using current state
                wall_count = 0
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue  # Don't count center cell

                        neighbor_x, neighbor_y = x + dx, y + dy

                        # Use current state for consistency within this iteration
                        neighbor_tile = current_state.get((neighbor_x, neighbor_y))

                        # Handle out-of-bounds neighbors
                        if neighbor_tile is None:
                            # On first iteration with read_from_realm, read from existing realm
                            if self.read_from_realm and iteration == 0:
                                neighbor_tile = ctx.procgen.realm.read_tile(
                                    neighbor_x, neighbor_y, z
                                )
                            else:
                                # Default: treat out-of-bounds as walls
                                neighbor_tile = wall_id

                        if neighbor_tile == wall_id:
                            wall_count += 1

                # Apply CA rule
                if wall_count >= self.wall_threshold:
                    next_state[(x, y)] = wall_id
                else:
                    next_state[(x, y)] = floor_id

            # Double-buffer: current state becomes the result of this iteration
            current_state = next_state

        # Generate edits for all final changes
        for (x, y), tile_id in current_state.items():
            z = ctx.area.min.z
            edits.add_tile(x, y, z, tile_id)

        return edits
