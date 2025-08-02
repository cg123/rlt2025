from rlt2025.ecs.entity_registry import EntityRegistry
from rlt2025.ecs.event_bus import EventBus
from rlt2025.map import GameMap


class World:
    entities: EntityRegistry
    event_bus: EventBus
    game_map: GameMap
    tick_count: int

    def __init__(self, game_map: GameMap):
        self.entities = EntityRegistry()
        self.event_bus = EventBus()
        self.game_map = game_map
        self.tick_count = 0
