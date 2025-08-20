"""Blueprint and feature registry for content-driven procedural generation."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from rlt2025.gen.guid import make_blueprint_entity_guid, make_guid

from ..spatial import Vec3
from .edits import Edits, EntitySpawn, StableId

if TYPE_CHECKING:
    from ..map.tiles import TileRegistry


@dataclass
class Blueprint:
    """
    A prefab/vault/blueprint that can be stamped into the world.

    Blueprints are defined using ASCII art with a legend that maps
    characters to tile names or entity spawn instructions.
    """

    id: str
    w: int
    h: int
    rows: tuple[str, ...]  # ASCII rows, top to bottom
    legend: dict[str, str]  # Character -> tile name mapping
    entities: list[tuple[tuple[int, int], EntitySpawn]] = field(default_factory=list)
    tags: frozenset[str] = frozenset({"feature"})
    _tile_cache: dict[tuple[str, ...], Edits] = field(
        default_factory=dict, init=False, repr=False
    )

    def stamp(
        self,
        origin: Vec3,
        tiles: "TileRegistry",
        world_seed: int = 0,
        instance_id_salt: Optional[str] = None,
    ) -> Edits:
        """
        Stamp this blueprint at the given origin position.

        Returns Edits that can be committed to apply the blueprint.
        Uses caching to avoid regenerating tile patterns for repeated stamping.

        Args:
            origin: The top-left-front origin of the blueprint in world space.
            tiles: The tile registry for converting names to IDs.
            world_seed: The world seed, for deterministic randomness.
            instance_id_salt: Optional salt to ensure unique instance ID if
                the same blueprint is stamped at the same location multiple times.
                If None, a default salt will be generated automatically.
        """
        # Create a cache key based on the tile registry state that affects this blueprint
        tile_cache_key = self._get_tile_cache_key(tiles)

        # Get or create the cached base edits for this tile configuration
        if tile_cache_key not in self._tile_cache:
            self._tile_cache[tile_cache_key] = self._create_base_edits(tiles)

        base_edits = self._tile_cache[tile_cache_key]

        # Create a new Edits object with the origin offset applied
        edits = Edits()

        # Apply origin offset to cached tile writes
        for tile_write in base_edits.tiles:
            edits.add_tile(
                origin.x + tile_write.pos.x,
                origin.y + tile_write.pos.y,
                origin.z + tile_write.pos.z,
                tile_write.tile,
            )

        # Generate a unique, stable ID for this blueprint instance
        # If no salt provided, use an empty string (most common case)
        salt = instance_id_salt if instance_id_salt is not None else ""
        instance_id = make_guid(
            world_seed,
            self.id,
            (origin.x, origin.y, origin.z),
            salt,
        )

        # Add entity spawns with origin offset and resolved GUIDs
        for (rx, ry), spawn in self.entities:
            world_pos = Vec3(origin.x + rx, origin.y + ry, origin.z)
            stable_guid = make_blueprint_entity_guid(
                blueprint_instance_id=instance_id,
                label_or_index=spawn.stable_id.guid,
            )
            actual_spawn = EntitySpawn(
                stable_id=StableId(guid=stable_guid),
                local_pos=spawn.local_pos,
                components=spawn.components,
                tags=spawn.tags,
            )
            edits.add_spawn(world_pos, actual_spawn)

        return edits

    def _get_tile_cache_key(self, tiles: "TileRegistry") -> tuple[str, ...]:
        """Generate a cache key based on tile mappings used by this blueprint."""
        tile_ids = []
        for char, tile_name in self.legend.items():
            tile_ids.append(f"{char}:{tiles.id(tile_name)}")
        return tuple(sorted(tile_ids))

    def _create_base_edits(self, tiles: "TileRegistry") -> Edits:
        """Create the base edits for this blueprint without origin offset."""
        edits = Edits()

        # Process ASCII rows into tile writes (with relative coordinates)
        for y, row in enumerate(self.rows):
            for x, char in enumerate(row):
                tile_name = self.legend.get(char)
                if tile_name is None:
                    # Skip unmapped characters - this was validated during blueprint loading
                    continue

                # Validate tile exists in registry
                try:
                    tile_id = tiles.id(tile_name)
                except KeyError:
                    raise ValueError(
                        f"Blueprint '{self.id}' references unknown tile '{tile_name}' "
                        f"for character '{char}' at position ({x}, {y})"
                    )

                edits.add_tile(x, y, 0, tile_id)

        return edits


@dataclass
class FeatureRegistry:
    """
    Registry for blueprints and features with tag-based queries.

    This allows content authors to query for features by tags
    (e.g., "house & stone_wall") rather than hardcoding specific blueprints.
    """

    by_id: dict[str, Blueprint] = field(default_factory=dict)
    by_tag: dict[str, set[str]] = field(
        default_factory=dict
    )  # tag -> set of blueprint IDs

    def register(self, blueprint: Blueprint) -> None:
        """Register a blueprint and validate its contents."""
        if blueprint.id in self.by_id:
            raise ValueError(f"Blueprint ID '{blueprint.id}' already registered")

        self.by_id[blueprint.id] = blueprint

        # Index by tags
        for tag in blueprint.tags:
            self.by_tag.setdefault(tag, set()).add(blueprint.id)

    def get_by_id(self, blueprint_id: str) -> Optional[Blueprint]:
        """Get a blueprint by ID."""
        return self.by_id.get(blueprint_id)

    def query(
        self,
        include: set[str] = frozenset(),
        exclude: set[str] = frozenset(),
        size_at_most: Optional[tuple[int, int]] = None,
        filter_fn: Optional[Callable[[Blueprint], bool]] = None,
    ) -> list[Blueprint]:
        """
        Query blueprints by tags and optional filters.

        Args:
            include: Tags that must be present (AND operation)
            exclude: Tags that must not be present
            size_at_most: Maximum (width, height) - filter out larger blueprints
            filter_fn: Additional predicate to filter blueprints

        Returns:
            List of matching blueprints
        """
        # Start with all blueprints if no include tags specified
        if include:
            # Get intersection of all required tags
            candidate_ids = None
            for tag in include:
                tag_ids = self.by_tag.get(tag, set())
                if candidate_ids is None:
                    candidate_ids = tag_ids.copy()
                else:
                    candidate_ids &= tag_ids

            if candidate_ids is None:
                candidate_ids = set()
        else:
            candidate_ids = set(self.by_id.keys())

        # Remove excluded tags
        for tag in exclude:
            excluded_ids = self.by_tag.get(tag, set())
            candidate_ids -= excluded_ids

        # Apply filters
        results = []
        for blueprint_id in candidate_ids:
            blueprint = self.by_id[blueprint_id]

            # Size filter
            if size_at_most and not (
                blueprint.w <= size_at_most[0] and blueprint.h <= size_at_most[1]
            ):
                continue

            # Custom filter
            if filter_fn and not filter_fn(blueprint):
                continue

            results.append(blueprint)

        return results

    def get_tags(self) -> set[str]:
        """Get all tags in the registry."""
        return set(self.by_tag.keys())

    def get_all(self) -> list[Blueprint]:
        """Get all blueprints in the registry."""
        return list(self.by_id.values())

    def get_blueprints_with_tag(self, tag: str) -> list[Blueprint]:
        """Get all blueprints with a specific tag."""
        blueprint_ids = self.by_tag.get(tag, set())
        return [self.by_id[bid] for bid in blueprint_ids]
