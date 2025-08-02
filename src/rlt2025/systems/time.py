from rlt2025.components import ScheduledEvent
from rlt2025.ecs import World
from rlt2025.events import TimeAdvanceRequestEvent, TimeElapsedEvent


class TimeSystem:
    def __init__(self, world: World):
        world.event_bus.register(TimeAdvanceRequestEvent, self.advance_time)

    def advance_time(self, event: TimeAdvanceRequestEvent, world: World) -> None:
        current_tick = world.tick_count
        waiting = list(world.entities.query(ScheduledEvent))
        if not waiting:
            return

        min_delay = None
        min_ent = None
        for entity, component in waiting:
            next_turn = component.tick
            if min_ent is None or min_delay is None or next_turn < min_delay:
                min_delay = next_turn
                min_ent = entity

        if min_ent is not None:
            c = world.entities.get_component(min_ent, ScheduledEvent)
            assert c is not None, "ScheduledEvent component is None"

            # slap that bad boy into the event bus
            world.event_bus.post(c.event)

            if c.tick > current_tick:
                world.tick_count = c.tick
                elapsed = c.tick - current_tick
                world.event_bus.post(TimeElapsedEvent(elapsed_ticks=elapsed))
            world.entities.remove_component(min_ent, ScheduledEvent)
