"""Simple noise-based terrain generation stage."""

from typing import TYPE_CHECKING

from ..context import GenContext
from ..edits import Edits

if TYPE_CHECKING:
    pass


class NoiseTerrain:
    """
    Generate basic terrain using simple noise.

    This is a minimal example that demonstrates how to create a generation stage.
    Uses a simple hash-based noise for demonstration purposes.
    """

    def __init__(self, thresholds: list[tuple[float, str]]):
        """
        Initialize with terrain thresholds.

        Args:
            thresholds: List of (threshold, tile_name) pairs, sorted by threshold.
                       The first threshold that the noise value is <= will be used.
        """
        self.thresholds = sorted(thresholds, key=lambda x: x[0])

    @property
    def id(self) -> str:
        return "noise_terrain"

    @property
    def provides(self) -> set[str]:
        return {"terrain"}

    @property
    def requires(self) -> set[str]:
        return set()

    def apply(self, ctx: GenContext) -> Edits:
        """Generate terrain tiles using simple noise."""
        edits = Edits()

        # Simple hash-based noise for demonstration
        # In a real implementation, you'd use proper noise libraries like OpenSimplex
        for x, y in ctx.area.iter_xy():
            # Create deterministic but pseudo-random noise value
            noise_input = (x * 73856093) ^ (y * 19349663) ^ ctx.world_seed
            noise_value = (hash(noise_input) & 0xFFFFFFFF) / 0xFFFFFFFF

            # Find the appropriate tile for this noise value
            tile_name = self.thresholds[-1][1]  # Default to last threshold
            for threshold, name in self.thresholds:
                if noise_value <= threshold:
                    tile_name = name
                    break

            # Write the tile
            try:
                tile_id = ctx.procgen.realm.tiles.id(tile_name)
                edits.add_tile(x, y, ctx.area.min.z, tile_id)
            except KeyError:
                # Tile doesn't exist in registry, skip it
                continue

        return edits
