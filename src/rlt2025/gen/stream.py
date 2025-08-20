"""Streaming world generation for infinite worlds."""

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..map.chunks import CHUNK_SIZE, ChunkKey
from ..spatial import AABB, Vec3
from .context import GenContext, ProceduralInterface

if TYPE_CHECKING:
    from ..ecs.world import World
    from .pipeline import Pipeline


@dataclass
class ChunkManager:
    """
    Manages chunk generation and streaming for infinite worlds.

    This system:
    - Determines which chunks need to be generated based on player interest
    - Generates expanded regions to avoid border artifacts
    - Tracks what has been generated to avoid duplicate work
    - Manages chunk loading/unloading as the player moves
    """

    world: "World"
    pipeline: "Pipeline"
    seed: int
    procgen: ProceduralInterface
    generated_regions: OrderedDict[tuple[int, int, int, int, int, int], bool] = field(
        default_factory=OrderedDict
    )
    active_chunks: set[ChunkKey] = field(default_factory=set)
    expansion_buffer_size: int = (
        16  # Configurable expansion buffer for feature placement
    )
    chunk_size: int = CHUNK_SIZE  # Configurable chunk size for this world
    max_cached_regions: int = 1000  # Maximum number of generated regions to track
    cleanup_threshold: float = 0.8  # Clean up when cache reaches this fraction of max
    grid_snap_size: int = (
        64  # Snap generation requests to this grid size to avoid redundant caching
    )

    def _snap_area_to_grid(self, area: AABB) -> AABB:
        """
        Snap an area to the generation grid to avoid redundant caching.

        This ensures that overlapping generation requests use the same cache key.
        """

        def snap_coord_down(coord: int) -> int:
            """Snap coordinate down to grid boundary."""
            return (coord // self.grid_snap_size) * self.grid_snap_size

        def snap_coord_up(coord: int) -> int:
            """Snap coordinate up to grid boundary."""
            return (
                (coord + self.grid_snap_size - 1) // self.grid_snap_size
            ) * self.grid_snap_size

        return AABB(
            Vec3(
                snap_coord_down(area.min.x),
                snap_coord_down(area.min.y),
                area.min.z,  # Don't snap Z for now
            ),
            Vec3(
                snap_coord_up(area.max.x),
                snap_coord_up(area.max.y),
                area.max.z,  # Don't snap Z for now
            ),
        )

    def ensure_generated(self, area: AABB) -> None:
        """
        Ensure that the given area has been generated.

        This may generate a larger area to avoid border artifacts.
        """
        if (
            area.min.x >= area.max.x
            or area.min.y >= area.max.y
            or area.min.z >= area.max.z
        ):
            raise ValueError(
                f"Invalid AABB: min {area.min} must be less than max {area.max}"
            )

        # Expand area to avoid border artifacts when placing large features
        expanded_area = area.expand(self.expansion_buffer_size)

        # Snap the expanded area to grid to avoid redundant caching
        snapped_area = self._snap_area_to_grid(expanded_area)

        # Check if we've already generated this region using the snapped coordinates
        region_key = (
            snapped_area.min.x,
            snapped_area.min.y,
            snapped_area.min.z,
            snapped_area.max.x,
            snapped_area.max.y,
            snapped_area.max.z,
        )

        if region_key in self.generated_regions:
            # Move to end (most recently accessed)
            self.generated_regions.move_to_end(region_key)
            return  # Already generated

        # Check if we need to clean up old regions
        self._cleanup_old_regions_if_needed()

        # Run the generation pipeline using the snapped area
        ctx = GenContext(
            area=snapped_area,
            world_seed=self.seed,
            procgen=self.procgen,
        )

        self.pipeline.run(ctx)

        # Mark as generated (OrderedDict will track insertion order)
        self.generated_regions[region_key] = True

    def interest_aabb(self, center: Vec3, radius_chunks: int) -> AABB:
        """Calculate the area of interest around a center point."""
        radius_tiles = radius_chunks * self.chunk_size
        return AABB(
            Vec3(center.x - radius_tiles, center.y - radius_tiles, center.z),
            Vec3(center.x + radius_tiles, center.y + radius_tiles, center.z + 1),
        )

    def update_player_interest(self, player_pos: Vec3, radius_chunks: int = 2) -> None:
        """
        Update world generation based on player position.

        Args:
            player_pos: Current player position in world coordinates
            radius_chunks: Radius in chunks around player to keep loaded
        """
        if radius_chunks < 0:
            raise ValueError(f"radius_chunks must be non-negative, got {radius_chunks}")

        interest_area = self.interest_aabb(player_pos, radius_chunks)

        # Ensure the area is generated
        self.ensure_generated(interest_area)

        # Determine which chunks should be active
        new_active_chunks = set()

        # Find all chunks that overlap with the interest area
        min_chunk_x = interest_area.min.x // self.chunk_size
        max_chunk_x = (interest_area.max.x - 1) // self.chunk_size
        min_chunk_y = interest_area.min.y // self.chunk_size
        max_chunk_y = (interest_area.max.y - 1) // self.chunk_size

        for cx in range(min_chunk_x, max_chunk_x + 1):
            for cy in range(min_chunk_y, max_chunk_y + 1):
                chunk_key = ChunkKey(cx, cy, 0)
                new_active_chunks.add(chunk_key)

        # Deactivate chunks that are no longer needed
        newly_inactive = self.active_chunks - new_active_chunks
        for chunk_key in newly_inactive:
            self.world.realm.deactivate_chunk(chunk_key, self.world)

        # Activate newly loaded chunks
        newly_active = new_active_chunks - self.active_chunks
        for chunk_key in newly_active:
            self.world.realm.activate_chunk(chunk_key, self.world)

        self.active_chunks = new_active_chunks

    def get_chunk_bounds(self, chunk_key: ChunkKey) -> AABB:
        """Get the world coordinate bounds of a chunk."""
        x = chunk_key.cx * self.chunk_size
        y = chunk_key.cy * self.chunk_size
        z = chunk_key.cz * self.chunk_size

        return AABB(
            Vec3(x, y, z), Vec3(x + self.chunk_size, y + self.chunk_size, z + 1)
        )

    def _cleanup_old_regions_if_needed(self) -> None:
        """Clean up old generated regions if cache is getting too full."""
        if len(self.generated_regions) < int(
            self.max_cached_regions * self.cleanup_threshold
        ):
            return  # No cleanup needed yet

        # Calculate how many regions to remove
        target_size = int(self.max_cached_regions * 0.5)  # Clean down to 50% of max
        regions_to_remove = len(self.generated_regions) - target_size

        if regions_to_remove <= 0:
            return

        # Remove oldest regions (FIFO from OrderedDict)
        removed_count = 0
        for _ in range(regions_to_remove):
            if not self.generated_regions:
                break

            region_key, _ = self.generated_regions.popitem(last=False)  # Remove oldest
            removed_count += 1

        if removed_count > 0:
            logging.info(
                f"ChunkManager: Cleaned up {removed_count} old generated regions "
                f"(cache size: {len(self.generated_regions)}/{self.max_cached_regions})"
            )

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring."""
        return {
            "generated_regions": len(self.generated_regions),
            "max_cached_regions": self.max_cached_regions,
            "active_chunks": len(self.active_chunks),
        }
