from rlt2025.ecs.entity_registry import EntityRegistry
from rlt2025.ecs.event_bus import EventBus
from rlt2025.map import Realm


class World:
    entities: EntityRegistry
    event_bus: EventBus
    tick_count: int
    realm: Realm

    def __init__(self):
        self.entities = EntityRegistry()
        self.event_bus = EventBus()
        self.tick_count = 0
        self.realm = Realm()
