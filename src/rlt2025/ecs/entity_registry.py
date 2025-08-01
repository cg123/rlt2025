import typing
from dataclasses import dataclass, field, is_dataclass
from typing import Any, Iterable, Optional, TypeAlias, TypeVar, overload

Entity: TypeAlias = int


T = TypeVar("T")

T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")


@dataclass
class EntityRegistry:
    next_entity_id: int = 0
    components: dict[Entity, dict[type, object]] = field(default_factory=dict)
    _component_map: dict[type, set[Entity]] = field(default_factory=dict)

    def create_entity(self) -> Entity:
        entity = self.next_entity_id
        self.next_entity_id += 1
        self.components[entity] = {}
        return entity

    def add_component(self, entity: Entity, component: object) -> None:
        if entity not in self.components:
            raise ValueError(f"Entity {entity} does not exist.")
        assert is_dataclass(component), "Component must be a dataclass"
        self.components[entity][type(component)] = component
        if type(component) not in self._component_map:
            self._component_map[type(component)] = set()
        self._component_map[type(component)].add(entity)

    def get_component(self, entity: Entity, component_type: type[T]) -> Optional[T]:
        return typing.cast(
            Optional[T], self.components.get(entity, {}).get(component_type)
        )

    def remove_component(self, entity: Entity, component_type: type[T]) -> None:
        if entity in self.components and component_type in self.components[entity]:
            del self.components[entity][component_type]
        if component_type in self._component_map:
            self._component_map[component_type].discard(entity)
            if not self._component_map[component_type]:
                del self._component_map[component_type]

    def has_component(self, entity: Entity, component_type: type[T]) -> bool:
        return entity in self.components and component_type in self.components[entity]

    def exists(self, entity: Entity) -> bool:
        return entity in self.components

    def clear(self) -> None:
        self.components.clear()
        self._component_map.clear()
        # never reset next_entity_id, id reuse is verboten

    def remove_entity(self, entity: Entity) -> None:
        if entity not in self.components:
            raise ValueError(f"Entity {entity} does not exist.")

        for component_type in self.components[entity]:
            if component_type in self._component_map:
                self._component_map[component_type].discard(entity)
        del self.components[entity]

    def get_entities_with_component(self, component_type: type) -> Iterable[Entity]:
        return self._component_map.get(component_type, set())

    def get_entities_with_components(self, *component_types: type) -> Iterable[Entity]:
        if not component_types:
            return set(self.components.keys())

        sets = [self._component_map.get(ct, set()) for ct in component_types]
        sets.sort(key=len)

        if not sets or not sets[0]:
            return set()

        result = sets.pop(0)
        for s in sets:
            result.intersection_update(s)
        return result

    @overload
    def query(self) -> Iterable[tuple[Entity]]: ...
    @overload
    def query(self, ty_1: type[T1]) -> Iterable[tuple[Entity, T1]]: ...
    @overload
    def query(
        self, ty_1: type[T1], ty_2: type[T2]
    ) -> Iterable[tuple[Entity, T1, T2]]: ...
    @overload
    def query(
        self, ty_1: type[T1], ty_2: type[T2], ty_3: type[T3]
    ) -> Iterable[tuple[Entity, T1, T2, T3]]: ...
    @overload
    def query(
        self, ty_1: type[T1], ty_2: type[T2], ty_3: type[T3], ty_4: type[T4]
    ) -> Iterable[tuple[Entity, T1, T2, T3, T4]]: ...

    def query(self, *component_types: type, **kwargs) -> Iterable[tuple[Any, ...]]:
        assert not kwargs, "Invalid keyword arguments provided to query method."
        entities = self.get_entities_with_components(*component_types)
        for entity in entities:
            entity_components = self.components[entity]
            yield (entity, *[entity_components[ct] for ct in component_types])
