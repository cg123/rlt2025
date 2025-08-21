"""YAML blueprint loader for content-driven generation."""

import logging
import os
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Type

import yaml

from ..components import MovementProperties, Player, Position, Renderable, StableId
from ..spatial import Vec3
from .edits import EntitySpawn
from .features import Blueprint, FeatureRegistry


class ComponentRegistry:
    """A registry for component factory functions for blueprint loading."""

    def __init__(self):
        self.factories: Dict[str, Callable] = {}

    def register(self, name: str, factory: Callable):
        self.factories[name] = factory

    def register_type(self, component_type: Type):
        self.register(
            component_type.__name__, lambda **kwargs: component_type(**kwargs)
        )

    def get(self, name: str) -> Callable | None:
        return self.factories.get(name)


def create_default_component_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register_type(Position)
    registry.register_type(Renderable)
    registry.register_type(MovementProperties)
    registry.register_type(Player)
    return registry


class BlueprintLoader:
    """
    Loads blueprints from YAML files.

    This allows content authors to define blueprints in a friendly
    YAML format with ASCII art and entity definitions.
    """

    def __init__(self, component_registry: ComponentRegistry | None = None):
        self.component_registry = (
            component_registry or create_default_component_registry()
        )

    def load_from_file(self, file_path: str) -> Blueprint:
        """Load a single blueprint from a YAML file."""

        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Blueprint file not found: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in blueprint file {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error reading blueprint file {file_path}: {e}")

        if not isinstance(data, dict):
            raise ValueError(
                f"Blueprint file {file_path} must contain a YAML dictionary"
            )

        try:
            # Validate first with file context
            errors = self._validate_blueprint_data(data, file_path)
            if errors:
                raise ValueError("Blueprint validation failed:\n" + "\n".join(errors))

            return self._create_blueprint_from_data(data, strict=True)
        except Exception as e:
            raise ValueError(f"Error parsing blueprint from {file_path}: {e}")

    def load_from_directory(
        self, directory: str, feature_registry: FeatureRegistry, strict: bool = True
    ) -> dict[str, str]:
        """
        Load all blueprint YAML files from a directory into the feature registry.

        Supports both .yaml and .yml file extensions.
        By default, this is strict and will raise an exception on the first error.

        Args:
            directory: Path to directory containing YAML files (.yaml or .yml)
            feature_registry: Registry to load blueprints into
            strict: If True, raise exception on any error. If False, log and continue.

        Returns:
            If strict is False, a dictionary mapping file paths to error messages.
            If strict is True, an empty dictionary is returned on success.
        """
        errors = {}

        if not os.path.exists(directory):
            error_msg = f"Blueprint directory does not exist: {directory}"
            if strict:
                raise FileNotFoundError(error_msg)
            errors[directory] = error_msg
            return errors

        if not os.path.isdir(directory):
            error_msg = f"Path is not a directory: {directory}"
            if strict:
                raise ValueError(error_msg)
            errors[directory] = error_msg
            return errors

        # Support both .yaml and .yml extensions
        yaml_files = list(Path(directory).glob("*.yaml")) + list(
            Path(directory).glob("*.yml")
        )
        if not yaml_files:
            # No YAML files found - not necessarily an error
            return errors

        for file_path in yaml_files:
            try:
                if strict:
                    blueprint = self.load_from_file(str(file_path))
                else:
                    # Load with non-strict mode for component validation
                    try:
                        with open(file_path, "r") as f:
                            data = yaml.safe_load(f)
                    except Exception as e:
                        error_msg = f"Failed to read {file_path}: {e}"
                        errors[str(file_path)] = error_msg
                        logging.warning(error_msg)
                        continue

                    if not isinstance(data, dict):
                        error_msg = f"{file_path} must contain a YAML dictionary"
                        errors[str(file_path)] = error_msg
                        logging.warning(error_msg)
                        continue

                    # Validate first
                    validation_errors = self._validate_blueprint_data(
                        data, str(file_path)
                    )
                    if validation_errors:
                        error_msg = "Blueprint validation failed:\n" + "\n".join(
                            validation_errors
                        )
                        errors[str(file_path)] = error_msg
                        logging.warning(error_msg)
                        continue

                    blueprint = self._create_blueprint_from_data(data, strict=False)

                feature_registry.register(blueprint)
            except Exception as e:
                error_msg = f"Failed to load blueprint from {file_path}: {e}"
                errors[str(file_path)] = error_msg

                if strict:
                    raise
                else:
                    logging.warning(error_msg)

        return errors

    def _validate_blueprint_data(
        self, data: Dict[str, Any], file_path: str = "<unknown>"
    ) -> List[str]:
        """
        Validate blueprint data and return list of validation errors.

        Args:
            data: Parsed YAML data
            file_path: Path to the file being validated (for error context)

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for unknown top-level keys to catch typos
        known_fields = {"id", "rows", "size", "legend", "tags", "entities"}
        unknown_fields = set(data.keys()) - known_fields
        if unknown_fields:
            errors.append(
                f"{file_path}: Unknown top-level keys (possible typos): {sorted(unknown_fields)}"
            )

        # Check required fields
        required_fields = ["id", "rows"]
        for field in required_fields:
            if field not in data:
                errors.append(f"{file_path}: Missing required field '{field}'")

        if not data.get("id") or not data.get(
            "rows"
        ):  # Can't continue validation without required fields
            return errors

        # Validate ID
        blueprint_id = data["id"]
        if not isinstance(blueprint_id, str) or not blueprint_id.strip():
            errors.append(f"{file_path}: Blueprint 'id' must be a non-empty string")

        # Validate or infer size
        size = data.get("size")
        if size is not None:
            # Explicit size provided - validate it
            if not isinstance(size, (list, tuple)) or len(size) != 2:
                errors.append(
                    f"{file_path}: Blueprint 'size' must be a 2-element list/tuple [width, height]"
                )
            else:
                try:
                    w, h = int(size[0]), int(size[1])
                    if w <= 0 or h <= 0:
                        errors.append(
                            f"{file_path}: Blueprint dimensions must be positive, got [{w}, {h}]"
                        )
                except (ValueError, TypeError):
                    errors.append(
                        f"{file_path}: Blueprint 'size' elements must be positive integers, got {size}"
                    )

        # Validate rows and check dimensions
        rows = data["rows"]
        if not isinstance(rows, (list, tuple)):
            errors.append(
                f"{file_path}: Blueprint 'rows' must be a list or tuple of strings"
            )
        else:
            # Infer dimensions from rows for consistency checking
            if rows:
                inferred_h = len(rows)
                inferred_w = len(str(rows[0])) if rows else 0

                # Check that all rows have the same width
                for i, row in enumerate(rows):
                    row_str = str(row)
                    if len(row_str) != inferred_w:
                        # Show a preview of the problematic row for easier debugging
                        row_preview = (
                            repr(row_str)
                            if len(row_str) <= 20
                            else f"{repr(row_str[:17])}..."
                        )
                        errors.append(
                            f"{file_path}: Row {i} has width {len(row_str)}, but row 0 has width {inferred_w}. All rows must have the same width. Row content: {row_preview}"
                        )

                # If explicit size is provided, check it matches the inferred size
                if size is not None and len(size) == 2:
                    try:
                        expected_w, expected_h = int(size[0]), int(size[1])
                        if inferred_h != expected_h:
                            errors.append(
                                f"{file_path}: Size specifies {expected_h} rows but {inferred_h} rows found"
                            )
                        if inferred_w != expected_w:
                            errors.append(
                                f"{file_path}: Size specifies width {expected_w} but rows have width {inferred_w}"
                            )
                    except (ValueError, TypeError):
                        pass  # Size validation already caught this
            else:
                errors.append(f"{file_path}: Blueprint must have at least one row")

        # Validate legend if present
        legend = data.get("legend", {})
        if not isinstance(legend, dict):
            errors.append(f"{file_path}: Blueprint 'legend' must be a dictionary")
        else:
            # Check legend coverage - all non-space characters in rows must be in legend
            if rows and isinstance(rows, (list, tuple)):
                used_chars = set()
                char_locations = {}  # Track where each character appears for better error messages

                for row_idx, row in enumerate(rows):
                    row_str = str(row)
                    for char_idx, char in enumerate(row_str):
                        if char != " ":  # Space is reserved for void/empty
                            used_chars.add(char)
                            if char not in char_locations:
                                char_locations[char] = []
                            char_locations[char].append(
                                f"row {row_idx}, col {char_idx}"
                            )

                missing_chars = used_chars - set(legend.keys())
                if missing_chars:
                    # Provide detailed context for missing characters
                    missing_details = []
                    for char in sorted(missing_chars):
                        locations = char_locations.get(char, ["unknown"])
                        if len(locations) <= 3:
                            location_str = ", ".join(locations)
                        else:
                            location_str = f"{', '.join(locations[:3])}, and {len(locations) - 3} more"
                        missing_details.append(f"'{char}' (found at: {location_str})")

                    errors.append(
                        f"{file_path}: Characters used in rows but missing from legend: {'; '.join(missing_details)}"
                    )

        # Validate tags if present
        if "tags" in data:
            tags_data = data["tags"]
            if not isinstance(tags_data, (str, list, tuple)):
                errors.append(
                    f"{file_path}: Blueprint 'tags' must be a string or list of strings"
                )

        # Validate entities if present
        if "entities" in data:
            entities_data = data["entities"]
            if not isinstance(entities_data, (list, tuple)):
                errors.append(f"{file_path}: Blueprint 'entities' must be a list")
            else:
                for i, entity_data in enumerate(entities_data):
                    if not isinstance(entity_data, dict):
                        errors.append(f"{file_path}: Entity {i} must be a dictionary")
                        continue

                    if "pos" not in entity_data:
                        errors.append(
                            f"{file_path}: Entity {i} missing required 'pos' field"
                        )
                    else:
                        pos = entity_data["pos"]
                        if not isinstance(pos, (list, tuple)) or len(pos) < 2:
                            errors.append(
                                f"{file_path}: Entity {i} 'pos' must be a list/tuple with at least [x, y]"
                            )
                        else:
                            # Validate position bounds (assuming we have dimensions from earlier validation)
                            try:
                                x, y = pos[0], pos[1]
                                # Get blueprint dimensions for bounds checking
                                if (
                                    "size" in data
                                    and isinstance(data["size"], (list, tuple))
                                    and len(data["size"]) == 2
                                ):
                                    w, h = int(data["size"][0]), int(data["size"][1])
                                elif rows and isinstance(rows, (list, tuple)):
                                    h = len(rows)
                                    w = len(str(rows[0])) if rows else 0
                                else:
                                    w, h = (
                                        0,
                                        0,
                                    )  # Skip bounds check if dimensions unknown

                                if (
                                    w > 0 and h > 0
                                ):  # Only check bounds if we have valid dimensions
                                    if not (0 <= x < w and 0 <= y < h):
                                        errors.append(
                                            f"{file_path}: Entity {i} position [{x}, {y}] out of bounds for blueprint size [{w}, {h}]"
                                        )
                            except (ValueError, TypeError, IndexError):
                                errors.append(
                                    f"{file_path}: Entity {i} position must contain numeric coordinates"
                                )

                    # Validate entity components structure
                    if "components" in entity_data:
                        components_data = entity_data["components"]
                        if not isinstance(components_data, (list, tuple)):
                            errors.append(
                                f"{file_path}: Entity {i} 'components' must be a list"
                            )
                        else:
                            for j, comp_data in enumerate(components_data):
                                if not isinstance(comp_data, dict):
                                    errors.append(
                                        f"{file_path}: Entity {i} component {j} must be a dictionary"
                                    )
                                    continue

                                if "type" not in comp_data:
                                    errors.append(
                                        f"{file_path}: Entity {i} component {j} missing required 'type' field"
                                    )
                                elif not isinstance(comp_data["type"], str):
                                    errors.append(
                                        f"{file_path}: Entity {i} component {j} 'type' must be a string"
                                    )

                                if "args" in comp_data and not isinstance(
                                    comp_data["args"], dict
                                ):
                                    errors.append(
                                        f"{file_path}: Entity {i} component {j} 'args' must be a dictionary"
                                    )

        return errors

    def _create_blueprint_from_data(
        self, data: Dict[str, Any], strict: bool = True
    ) -> Blueprint:
        """Create a Blueprint object from parsed YAML data. Assumes data is already validated."""
        # Extract validated data
        blueprint_id = data["id"]

        # Get dimensions from explicit size or infer from rows
        if "size" in data:
            w, h = int(data["size"][0]), int(data["size"][1])
        else:
            rows = data["rows"]
            h = len(rows)
            w = len(str(rows[0])) if rows else 0

        rows = tuple(str(row) for row in data["rows"])  # Ensure all rows are strings
        legend = data.get("legend", {})

        # Optional fields
        tags_data = data.get("tags", ["feature"])
        if isinstance(tags_data, str):
            tags = frozenset([tags_data])
        else:
            tags = frozenset(str(tag) for tag in tags_data)

        entities_data = data.get("entities", [])

        # Create entity spawns
        entities = []
        used_labels = set()
        for entity_index, entity_data in enumerate(entities_data):
            pos = entity_data["pos"]
            components_data = entity_data.get("components", [])
            entity_tags = frozenset(entity_data.get("tags", []))

            # Generate unique label if none provided
            if "label" in entity_data:
                user_label = entity_data["label"]
                # Only prepend "explicit:" if it's not already there
                if not user_label.startswith("explicit:"):
                    label = "explicit:" + user_label
                else:
                    label = user_label

                if label in used_labels:
                    raise ValueError(
                        f"Duplicate label '{user_label}' in blueprint {blueprint_id}"
                    )
                used_labels.add(label)
            else:
                label = f"autogen:__autogen_{entity_index}"
                used_labels.add(label)

            # Create component factories
            component_factories = []
            for comp_data in components_data:
                comp_type = comp_data["type"]
                comp_args = comp_data.get("args", {})

                factory_func = self.component_registry.get(comp_type)
                if factory_func:
                    factory = partial(factory_func, **comp_args)
                    component_factories.append(factory)
                else:
                    if strict:
                        raise ValueError(
                            f"Unknown component type '{comp_type}' in blueprint {blueprint_id}"
                        )
                    else:
                        logging.warning(
                            f"Unknown component type '{comp_type}' in blueprint {blueprint_id}"
                        )

            stable_id = StableId(guid=label)

            # For ergonomic positioning: the blueprint cell (pos) is used to anchor the spawn.
            # The spawn's local_pos is an optional extra offset relative to that anchor.
            anchor_cell = (pos[0], pos[1])
            local_offset = Vec3(0, 0, pos[2] if len(pos) > 2 else 0)

            entity_spawn = EntitySpawn(
                stable_id=stable_id,
                local_pos=local_offset,
                components=component_factories,
                tags=entity_tags,
            )

            entities.append((anchor_cell, entity_spawn))

        return Blueprint(
            id=blueprint_id,
            w=w,
            h=h,
            rows=rows,
            legend=legend,
            entities=entities,
            tags=tags,
        )


def create_example_blueprints() -> List[Blueprint]:
    loader = BlueprintLoader()
    features = FeatureRegistry()
    loader.load_from_directory("data/blueprints", features)
    return features.get_all()
