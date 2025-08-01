from rlt2025.components import ScheduledEvent
from rlt2025.engine import Engine
from rlt2025.events import TimeAdvanceRequestEvent, TimeElapsedEvent


class TimeSystem:
    def __init__(self, engine: Engine):
        engine.event_bus.register(TimeAdvanceRequestEvent, self.advance_time)

    def advance_time(self, event: TimeAdvanceRequestEvent, engine: Engine) -> None:
        current_tick = engine.tick_count
        waiting = list(engine.entities.query(ScheduledEvent))
        if not waiting:
            return

        min_delay = None
        min_ent = None
        for entity, component in waiting:
            next_turn = component.tick
            if min_ent is None or next_turn < min_delay:
                min_delay = next_turn
                min_ent = entity

        if min_ent is not None:
            c = engine.entities.get_component(min_ent, ScheduledEvent)
            engine.event_bus.post(c.event)
            if c.tick > current_tick:
                engine.tick_count = c.tick
                elapsed = c.tick - current_tick
                engine.event_bus.post(TimeElapsedEvent(elapsed_ticks=elapsed))
            engine.entities.remove_component(min_ent, ScheduledEvent)
