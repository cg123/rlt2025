"""Deterministic GUID generation for stable entity references."""

import hashlib
from typing import Any


def make_guid(*parts: Any) -> str:
    """
    Generate a deterministic GUID from the given parts.

    This creates stable identifiers that are consistent across
    world generation runs with the same parameters.

    Args:
        *parts: Any number of objects that will be stringified and hashed

    Returns:
        A 32-character hexadecimal GUID
    """
    hasher = hashlib.blake2b(digest_size=16)

    for part in parts:
        hasher.update(str(part).encode("utf-8"))
        hasher.update(b"|")  # Separator to avoid collisions

    return hasher.hexdigest()


def make_blueprint_entity_guid(
    blueprint_instance_id: str,
    label_or_index: Any,
) -> str:
    """
    Generate a stable GUID for an entity spawned from a blueprint.

    This ensures that entities within the same blueprint instance have unique,
    stable, and predictable GUIDs.

    Args:
        blueprint_instance_id: A unique identifier for this specific
            stamping of the blueprint.
        label_or_index: The entity's unique label or index within the blueprint.
    """
    return make_guid("blueprint_entity", blueprint_instance_id, label_or_index)


def make_procedural_entity_guid(
    world_seed: int,
    stage_id: str,
    world_pos: tuple[int, int, int],
    entity_type: str,
    index: int = 0,
) -> str:
    """
    Generate a stable GUID for an entity spawned procedurally by a stage.

    This is for entities created by generation stages rather than blueprints.
    """
    return make_guid(world_seed, "procedural", stage_id, world_pos, entity_type, index)
