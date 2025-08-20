"""YAML blueprint loader for content-driven generation."""

import logging
import os
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Type

try:
    import yaml
except ImportError:
    yaml = None

from ..components import MovementProperties, Player, Position, Renderable
from ..spatial import Vec3
from .edits import EntitySpawn, StableId
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
        if yaml is None:
            raise ImportError(
                "PyYAML is required for blueprint loading. "
                "Install it with: pip install PyYAML"
            )
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

            return self._create_blueprint_from_data(data)
        except Exception as e:
            raise ValueError(f"Error parsing blueprint from {file_path}: {e}")

    def load_from_directory(
        self, directory: str, feature_registry: FeatureRegistry, strict: bool = True
    ) -> dict[str, str]:
        """
        Load all blueprint YAML files from a directory into the feature registry.

        By default, this is strict and will raise an exception on the first error.

        Args:
            directory: Path to directory containing YAML files
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

        yaml_files = list(Path(directory).glob("*.yaml"))
        if not yaml_files:
            # No YAML files found - not necessarily an error
            return errors

        for file_path in yaml_files:
            try:
                blueprint = self.load_from_file(str(file_path))
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

        # Check required fields
        required_fields = ["id", "rows"]
        for field in required_fields:
            if field not in data:
                errors.append(f"{file_path}: Missing required field '{field}'")

        if errors:  # Can't continue validation without required fields
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
                        errors.append(
                            f"{file_path}: Row {i} has width {len(row_str)}, but row 0 has width {inferred_w}. All rows must have the same width"
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

        return errors

    def _create_blueprint_from_data(self, data: Dict[str, Any]) -> Blueprint:
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
                    logging.warning(
                        f"Unknown component type '{comp_type}' in blueprint {blueprint_id}"
                    )

            stable_id = StableId(guid=label)

            entity_spawn = EntitySpawn(
                stable_id=stable_id,
                local_pos=Vec3(pos[0], pos[1], pos[2] if len(pos) > 2 else 0),
                components=component_factories,
                tags=entity_tags,
            )

            entities.append(((pos[0], pos[1]), entity_spawn))

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
