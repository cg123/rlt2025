from typing import TYPE_CHECKING

from rlt2025.ecs.entity_registry import EntityRegistry
from rlt2025.ecs.event_bus import EventBus

if TYPE_CHECKING:
    from rlt2025.map.realm import Realm


class World:
    entities: EntityRegistry
    event_bus: EventBus
    tick_count: int
    realm: "Realm"  # Forward reference to avoid circular import

    def __init__(self):
        self.entities = EntityRegistry()
        self.event_bus = EventBus()
        self.tick_count = 0
        # Initialize realm lazily to avoid circular import
        from rlt2025.map.realm import Realm

        self.realm = Realm(80, 50)

    def create_entity(self, *components: object) -> int:
        """
        Create a new entity with the given components.
        """
        entity = self.entities.create_entity()

        # Add all components
        for component in components:
            self.entities.add_component(entity, component)

        return entity

    def add_component(self, entity: int, component: object) -> None:
        """Add a component to an existing entity."""
        self.entities.add_component(entity, component)
