"""
JSON-based save and load system.

:class:`SaveManager` serialises the full ECS world state to a
human-readable JSON file by calling :meth:`~engine.world.World.snapshot`
and writes it with a custom encoder that handles Python ``set`` objects
and dataclass instances.

On load, the JSON is decoded back into component instances using
``COMPONENT_REGISTRY``, a dict that maps each component type's fully-
qualified class name to the class itself. Any unknown type keys (e.g.
from a component added after the save was written) are silently skipped,
so old saves remain loadable after new components are introduced.

Why not pickle?
Pickle is insecure (arbitrary code execution on load), tightly coupled
to class internals, and breaks whenever a class is moved or renamed.
JSON snapshots are safe, human-readable, and forward-compatible.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.world import World

from components.identity import Identity, Tags
from components.spatial import Position, RoomData
from components.combat import (
    Health, Stats, CombatStats, StatusEffect, StatusEffects, Faction
)
from components.inventory import ItemData, Inventory, Equipment, RoomContents
from components.ai import AIBehavior, LootEntry, LootTable, SpawnData
from components.quest import QuestObjective, Quest, QuestLog, QuestGiver

COMPONENT_REGISTRY: dict[str, type] = {
    f"{cls.__module__}.{cls.__qualname__}": cls
    for cls in [
        Identity, Tags,
        Position, RoomData,
        Health, Stats, CombatStats, StatusEffect, StatusEffects, Faction,
        ItemData, Inventory, Equipment, RoomContents,
        AIBehavior, LootEntry, LootTable, SpawnData,
        QuestObjective, Quest, QuestLog, QuestGiver,
    ]
}
"""
Maps ``"module.ClassName"`` to the component class.

Add new component classes here when they are introduced so that save
files written after the change can reconstruct them correctly.
"""


class _ComponentEncoder(json.JSONEncoder):
    """
    JSON encoder that handles types not natively supported by the
    standard library.

    ``set`` is encoded as ``{"__set__": [...]}`` and reconstructed by
    the :func:`_decode_hook` object hook on load.
    Dataclass instances (and any object with ``__dict__``) are encoded
    as their ``__dict__``.
    """

    def default(self, obj):
        if isinstance(obj, set):
            return {"__set__": list(obj)}
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def _decode_hook(dct: dict):
    """Object hook for ``json.load`` that restores encoded ``set`` values."""
    if "__set__" in dct:
        return set(dct["__set__"])
    return dct


class SaveManager:
    """
    Handles saving and loading a :class:`~engine.world.World` to disk.

    Each instance is bound to one ``World``. Call :meth:`save` to write
    and :meth:`load` to read. Both methods accept a filesystem path so
    multiple save slots are supported by using different paths.
    """

    def __init__(self, world: "World") -> None:
        self._world = world

    def save(self, path: str) -> None:
        """
        Serialise the world state and write it to ``path`` as JSON.

        Parent directories are created automatically. The file is
        written with two-space indentation for readability.
        """
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        snapshot = self._world.snapshot()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, cls=_ComponentEncoder, indent=2)
        print(f"[Save] Game saved to {path}")

    def load(self, path: str) -> bool:
        """
        Read a save file and restore the world state from it.

        Returns ``True`` on success, ``False`` if the file does not
        exist. Any other error (malformed JSON, I/O failure) is caught,
        printed, and returns ``False`` rather than propagating.
        """
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                snapshot = json.load(f, object_hook=_decode_hook)
            self._world.restore(snapshot, COMPONENT_REGISTRY)
            print(f"[Save] Game loaded from {path}")
            return True
        except Exception as e:
            print(f"[Save] Failed to load: {e}")
            return False
