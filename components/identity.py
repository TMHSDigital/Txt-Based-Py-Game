"""
Identity components.

Every named entity in the game carries an :class:`Identity` component.
It provides the human-readable name and description used by the renderer
and by command matching (e.g. "take sword" matches an item whose name
contains "sword").
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Identity:
    """Human-readable name and flavour description for any entity."""

    name: str
    description: str = ""


@dataclass
class Tags:
    """
    A set of string labels attached to an entity as a component.

    This is the component-based counterpart to the world-level tag
    system. The world-level system (``World.add_tag``) is preferred for
    broad queries such as "all enemies"; this component is available for
    per-entity tag lookups that need to survive a world snapshot.
    """

    values: set[str] = field(default_factory=set)

    def has(self, tag: str) -> bool:
        """Return ``True`` if the tag is present."""
        return tag in self.values

    def add(self, tag: str) -> None:
        """Add a tag. No-op if already present."""
        self.values.add(tag)

    def remove(self, tag: str) -> None:
        """Remove a tag. No-op if not present."""
        self.values.discard(tag)
