# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This repository uses `uv` to manage Python environments and run commands. Here are some common commands:

- **Run the game:** `uv run python -m rlt2025.main`
- **Run linter:** `uv run ruff check .`
- **Format code:** `uv run ruff format .`
- **Run tests:** `uv run pytest`

## Architecture

This is a roguelike game built using Python and the `tcod` library. It follows an Entity-Component-System (ECS) architecture.

### Core Components

- **`src/rlt2025/main.py`**: The main entry point of the game. It initializes the game world, entities, and the main game loop.
- **`src/rlt2025/engine.py`**: Contains the `Engine` class, which manages the main game loop, rendering, and event handling. It also holds instances of the various systems.
- **`src/rlt2025/ecs/`**: The ECS implementation.
  - **`world.py`**: The `World` class is a container for the `EntityRegistry`, `EventBus`, and `Realm`.
  - **`entity_registry.py`**: The `EntityRegistry` class manages entities and their components. It provides methods for creating, querying, and updating entities.
  - **`event_bus.py`**: A simple event bus for communication between different parts of the game.
- **`src/rlt2025/components.py`**: Defines the data-only component classes used in the ECS.
- **`src/rlt2025/events.py`**: Defines data-only event classes that can be posted to the `EventBus`.
- **`src/rlt2025/systems/`**: Contains the game systems, which implement game logic. For example, the `VisibilitySystem` calculates what the player can see.
- **`src/rlt2025/map/`**: Handles the creation and management of the game map.
- **`src/rlt2025/input_handlers.py`**: Manages player input.

### Development Workflow

1. **Add a new component:** Create a new dataclass in `src/rlt2025/components.py`.
2. **Add a new system:** Create a new class in the `src/rlt2025/systems/` directory. The system should typically operate on entities with a specific set of components.
3. **Integrate the system:** Instantiate the new system in the `Engine` class and call its update method in the appropriate place in the game loop.
4. **Add new events:** Define new event classes in `src/rlt2025/events.py` and post them to the `EventBus`. Register handlers to respond to these events.
