"""
Quest components.

:class:`QuestObjective` tracks a single measurable goal within a quest.
:class:`Quest` groups objectives with metadata and reward information.
:class:`QuestLog` is attached to the player and holds all known quests.
:class:`QuestGiver` is attached to NPCs and lists the quests they offer.

Quest progression is driven entirely by events: the quest system
subscribes to :class:`~engine.event_bus.EntityDied`,
:class:`~engine.event_bus.ItemPickedUp`, and
:class:`~engine.event_bus.RoomEntered` and advances the appropriate
objectives automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuestStatus(str, Enum):
    """Lifecycle status of a quest."""

    AVAILABLE = "available"
    """The quest exists but has not been accepted."""
    ACTIVE = "active"
    """The player has accepted the quest and is working on it."""
    COMPLETED = "completed"
    """All objectives have been met."""
    FAILED = "failed"
    """The quest can no longer be completed (e.g. an NPC died)."""


@dataclass
class QuestObjective:
    """
    A single measurable goal within a quest.

    ``objective_type`` controls which game events advance this
    objective:

    - ``"kill"``    -- incremented when an enemy with matching
                       ``template_id`` dies.
    - ``"collect"`` -- incremented when the player picks up an item
                       with matching ``item_id``.
    - ``"visit"``   -- incremented the first time the player enters a
                       room with matching key.
    - ``"talk"``    -- reserved for future NPC dialogue objectives.
    """

    objective_id: str
    description: str
    objective_type: str
    target_id: str = ""
    required_count: int = 1
    current_count: int = 0

    @property
    def is_complete(self) -> bool:
        """Return ``True`` if the objective has been fully satisfied."""
        return self.current_count >= self.required_count

    def increment(self, amount: int = 1) -> None:
        """Advance progress by ``amount``, capped at ``required_count``."""
        self.current_count = min(self.required_count, self.current_count + amount)


@dataclass
class Quest:
    """
    A complete quest: metadata, objectives, and rewards.

    When all objectives are complete and ``status`` is ``ACTIVE``, the
    quest system transitions ``status`` to ``COMPLETED`` and publishes
    a :class:`~engine.event_bus.QuestCompleted` event.
    """

    quest_id: str
    title: str
    description: str
    status: QuestStatus = QuestStatus.AVAILABLE
    objectives: list[QuestObjective] = field(default_factory=list)
    reward_gold: int = 0
    reward_items: list[str] = field(default_factory=list)
    reward_xp: int = 0

    @property
    def is_complete(self) -> bool:
        """Return ``True`` if every objective is satisfied."""
        return all(o.is_complete for o in self.objectives)


@dataclass
class QuestLog:
    """
    The player's quest journal, keyed by ``quest_id``.

    All quests (available, active, completed) are held here so the
    player can review them at any time.
    """

    quests: dict[str, Quest] = field(default_factory=dict)

    def add_quest(self, quest: Quest) -> None:
        """Add or replace a quest entry."""
        self.quests[quest.quest_id] = quest

    def get_quest(self, quest_id: str) -> Quest | None:
        """Return the quest with this ID, or ``None``."""
        return self.quests.get(quest_id)

    def active_quests(self) -> list[Quest]:
        """Return all quests currently in the ``ACTIVE`` state."""
        return [q for q in self.quests.values() if q.status == QuestStatus.ACTIVE]

    def completed_quests(self) -> list[Quest]:
        """Return all quests in the ``COMPLETED`` state."""
        return [q for q in self.quests.values() if q.status == QuestStatus.COMPLETED]


@dataclass
class QuestGiver:
    """
    Attached to NPC entities that can offer quests to the player.

    ``quest_ids`` lists the IDs of quests this NPC makes available.
    ``dialogue_template`` is a key into a future dialogue data file.
    """

    quest_ids: list[str] = field(default_factory=list)
    dialogue_template: str = ""
