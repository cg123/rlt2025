import typing
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    from rlt2025.ecs.world import World


EventT = TypeVar("EventT")


@dataclass
class EventBus:
    handlers: dict[type, list[Callable[[object, "World"], None]]] = field(
        default_factory=dict
    )
    queue: list[object] = field(default_factory=list)

    def post(self, event: object) -> None:
        self.queue.append(event)

    def register(
        self, event_type: type[EventT], handler: Callable[[EventT, "World"], None]
    ) -> None:
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        handler_erased = typing.cast(Callable[[object, "World"], None], handler)
        self.handlers[event_type].append(handler_erased)

    def unregister(
        self, event_type: type[EventT], handler: Callable[[EventT, "World"], None]
    ) -> None:
        if event_type not in self.handlers:
            return
        handler_erased = typing.cast(Callable[[object, "World"], None], handler)
        if handler_erased in self.handlers[event_type]:
            self.handlers[event_type].remove(handler_erased)

    def _dispatch(self, event: object, world: "World") -> None:
        event_type = type(event)
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(event, world)

    def process_current(self, world: "World") -> None:
        to_process = list(self.queue)
        self.queue.clear()
        for event in to_process:
            self._dispatch(event, world)

    def process_recursive(self, world: "World", max_depth: int = 32) -> None:
        depth = 0
        while depth < max_depth:
            if not self.queue:
                break

            self.process_current(world)
            depth += 1
