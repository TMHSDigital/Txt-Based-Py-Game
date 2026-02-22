"""
ECS World - central entity and component registry.

Entities are plain integer IDs. Components are dataclass instances
stored in a two-level dict keyed first by component type, then by
entity ID. Systems iterate over entities that possess a specific
combination of component types by calling ``World.query()``.

Tags are lightweight string labels attached to entities (e.g. "player",
"enemy", "room") and are stored separately from components for fast
set-based filtering.

The ``snapshot()`` / ``restore()`` pair serialises and deserialises the
full world state so the save system can write it to JSON without
coupling to individual component internals.
"""

from __future__ import annotations

from typing import Any, Iterator, Type, TypeVar

T = TypeVar("T")


class World:
    """
    The ECS registry.

    Owns all entities, their components, and their tags. It is the
    single source of truth for game state and the only object that
    systems read from and write to.
    """

    def __init__(self) -> None:
        self._next_id: int = 1
        # {ComponentType: {entity_id: component_instance}}
        self._storage: dict[type, dict[int, Any]] = {}
        # set of all living entity IDs
        self._entities: set[int] = set()
        # {entity_id: set[tag_strings]}
        self._tags: dict[int, set[str]] = {}

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------

    def create_entity(self, *tags: str) -> int:
        """
        Allocate a new entity ID and return it.

        Any positional string arguments are attached as tags immediately.
        Tags can also be added later via :meth:`add_tag`.
        """
        entity_id = self._next_id
        self._next_id += 1
        self._entities.add(entity_id)
        self._tags[entity_id] = set(tags)
        return entity_id

    def destroy_entity(self, entity: int) -> None:
        """
        Remove an entity and all of its components from the world.

        Silently does nothing if the entity does not exist. After this
        call, ``entity_exists(entity)`` returns ``False`` and
        ``get_component(entity, ...)`` returns ``None`` for all types.
        """
        if entity not in self._entities:
            return
        self._entities.discard(entity)
        self._tags.pop(entity, None)
        for store in self._storage.values():
            store.pop(entity, None)

    def entity_exists(self, entity: int) -> bool:
        """Return ``True`` if the entity is alive in this world."""
        return entity in self._entities

    def all_entities(self) -> set[int]:
        """Return a snapshot copy of the set of all living entity IDs."""
        return set(self._entities)

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def add_tag(self, entity: int, tag: str) -> None:
        """Attach a string tag to an entity."""
        self._tags.setdefault(entity, set()).add(tag)

    def has_tag(self, entity: int, tag: str) -> bool:
        """Return ``True`` if the entity carries the given tag."""
        return tag in self._tags.get(entity, set())

    def get_tags(self, entity: int) -> set[str]:
        """Return a copy of all tags attached to the entity."""
        return set(self._tags.get(entity, set()))

    def entities_with_tag(self, tag: str) -> list[int]:
        """Return all living entities that carry the given tag."""
        return [e for e, tags in self._tags.items() if tag in tags and e in self._entities]

    # ------------------------------------------------------------------
    # Components
    # ------------------------------------------------------------------

    def add_component(self, entity: int, component: Any) -> None:
        """
        Attach a component instance to an entity.

        If the entity already has a component of the same type it is
        silently replaced.
        """
        ctype = type(component)
        if ctype not in self._storage:
            self._storage[ctype] = {}
        self._storage[ctype][entity] = component

    def remove_component(self, entity: int, component_type: Type[T]) -> None:
        """
        Detach the component of the given type from an entity.

        Silently does nothing if the entity does not have that component.
        """
        self._storage.get(component_type, {}).pop(entity, None)

    def get_component(self, entity: int, component_type: Type[T]) -> T | None:
        """
        Return the component instance of the given type, or ``None``.

        This is the primary way for systems to read component data.
        """
        return self._storage.get(component_type, {}).get(entity)

    def has_component(self, entity: int, component_type: type) -> bool:
        """Return ``True`` if the entity has the given component type."""
        return entity in self._storage.get(component_type, {})

    def query(self, *component_types: type) -> Iterator[tuple[int, tuple]]:
        """
        Yield ``(entity_id, (comp_a, comp_b, ...))`` for every living
        entity that has all of the requested component types.

        Iteration starts from the smallest component store for efficiency.
        The returned component tuple preserves the order of the arguments.

        Example::

            for entity, (health, stats) in world.query(Health, Stats):
                print(entity, health.current, stats.strength)
        """
        if not component_types:
            return
        stores = [self._storage.get(ct, {}) for ct in component_types]
        primary = min(stores, key=len)
        for entity in list(primary.keys()):
            if entity not in self._entities:
                continue
            components = []
            for store in stores:
                comp = store.get(entity)
                if comp is None:
                    break
                components.append(comp)
            else:
                yield entity, tuple(components)

    def query_one(self, entity: int, *component_types: type) -> tuple | None:
        """
        Return ``(comp_a, comp_b, ...)`` for a single known entity, or
        ``None`` if the entity is missing any of the requested types.

        Useful when you already have an entity ID and just need to fetch
        multiple components in one call.
        """
        result = []
        for ct in component_types:
            comp = self._storage.get(ct, {}).get(entity)
            if comp is None:
                return None
            result.append(comp)
        return tuple(result)

    # ------------------------------------------------------------------
    # Serialisation (used by the save system)
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """
        Return a JSON-serialisable dictionary representing the full world
        state.

        The dictionary contains entity IDs, their tags, and each
        component's ``__dict__``. Pass it to :meth:`restore` on a fresh
        ``World`` instance to reconstruct the state.
        """
        return {
            "next_id": self._next_id,
            "entities": list(self._entities),
            "tags": {str(k): list(v) for k, v in self._tags.items()},
            "storage": {
                f"{ct.__module__}.{ct.__qualname__}": {
                    str(eid): comp.__dict__
                    for eid, comp in store.items()
                    if eid in self._entities
                }
                for ct, store in self._storage.items()
            },
        }

    def restore(self, snapshot: dict, component_registry: dict[str, type]) -> None:
        """
        Rebuild world state from a snapshot produced by :meth:`snapshot`.

        ``component_registry`` maps fully-qualified class names
        (``"module.ClassName"``) to the corresponding Python types so
        that components can be reinstantiated without using ``eval``.

        Any component type not present in the registry is silently
        skipped, which means new components added after a save was
        written will simply be absent rather than causing a crash.
        """
        self._next_id = snapshot["next_id"]
        self._entities = set(snapshot["entities"])
        self._tags = {int(k): set(v) for k, v in snapshot["tags"].items()}
        self._storage = {}
        for type_key, instances in snapshot.get("storage", {}).items():
            ct = component_registry.get(type_key)
            if ct is None:
                continue
            store: dict[int, Any] = {}
            for eid_str, fields in instances.items():
                obj = ct.__new__(ct)
                obj.__dict__.update(fields)
                store[int(eid_str)] = obj
            self._storage[ct] = store
