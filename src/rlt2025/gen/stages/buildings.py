"""Building placement stage using blueprints and features."""

from typing import TYPE_CHECKING

from ...spatial import Vec3
from ..context import GenContext
from ..edits import Edits

if TYPE_CHECKING:
    pass


class PlaceBuildings:
    """
    Place buildings from the feature registry based on tags.

    This demonstrates how to use the blueprint system to place
    pre-defined structures in the world.
    """

    def __init__(self, tags: set[str], density: float = 0.7):
        """
        Initialize building placement parameters.

        Args:
            tags: Set of tags to query from the feature registry
            density: Probability (0-1) of placing a building in each valid area
        """
        self.tags = tags
        self.density = density

    @property
    def id(self) -> str:
        return "place_buildings"

    @property
    def provides(self) -> set[str]:
        return {"buildings"}

    @property
    def requires(self) -> set[str]:
        return {"parcels"}  # Requires areas to place buildings in

    def apply(self, ctx: GenContext) -> Edits:
        """Place buildings in available parcels."""
        edits = Edits()
        rng = ctx.rng("buildings")

        # Get parcels from blackboard (should be set by a previous stage)
        parcels = ctx.get_blackboard("parcels", [])
        if not parcels:
            return edits  # No parcels to place buildings in

        for parcel in parcels:
            # Each parcel should be (x0, y0, x1, y1) bounding box
            if len(parcel) != 4:
                continue

            x0, y0, x1, y1 = parcel

            # Randomly decide whether to place a building here
            if rng.random() > self.density:
                continue

            # Calculate available space
            width = x1 - x0
            height = y1 - y0

            if width <= 0 or height <= 0:
                continue

            # Query for appropriate buildings
            candidates = ctx.procgen.features.query(
                include=self.tags, size_at_most=(width, height)
            )

            if not candidates:
                continue  # No suitable buildings found

            # Pick a random building
            blueprint = rng.choice(candidates)

            # Center the building in the parcel
            offset_x = (width - blueprint.w) // 2
            offset_y = (height - blueprint.h) // 2

            origin = Vec3(x0 + offset_x, y0 + offset_y, ctx.area.min.z)

            # Stamp the blueprint
            building_edits = blueprint.stamp(
                origin, ctx.procgen.realm.tiles, ctx.world_seed
            )
            edits.merge(building_edits)

        return edits


class SimpleRoomParcels:
    """
    Create simple rectangular parcels for building placement.

    This is a helper stage that creates basic room layouts
    that the PlaceBuildings stage can use.
    """

    def __init__(self, room_size: tuple[int, int] = (8, 6), padding: int = 2):
        """
        Initialize room generation parameters.

        Args:
            room_size: (width, height) of rooms to create
            padding: Minimum space between rooms
        """
        self.room_size = room_size
        self.padding = padding

    @property
    def id(self) -> str:
        return "simple_room_parcels"

    @property
    def provides(self) -> set[str]:
        return {"parcels"}

    @property
    def requires(self) -> set[str]:
        return set()

    def apply(self, ctx: GenContext) -> Edits:
        """Generate simple room parcels."""
        edits = Edits()

        parcels = []
        room_w, room_h = self.room_size
        step_x = room_w + self.padding
        step_y = room_h + self.padding

        # Create a grid of room parcels
        for y in range(ctx.area.min.y, ctx.area.max.y - room_h, step_y):
            for x in range(ctx.area.min.x, ctx.area.max.x - room_w, step_x):
                # Make sure room fits in area
                if x + room_w <= ctx.area.max.x and y + room_h <= ctx.area.max.y:
                    parcels.append((x, y, x + room_w, y + room_h))

        # Store parcels in blackboard for other stages
        ctx.set_blackboard("parcels", parcels)

        return edits  # This stage doesn't generate tiles, just data
