"""Tests for the ECS World."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass
from engine.world import World


@dataclass
class Position:
    x: int
    y: int

@dataclass
class Health:
    current: int
    maximum: int


def test_create_entity():
    w = World()
    e = w.create_entity()
    assert w.entity_exists(e)


def test_destroy_entity():
    w = World()
    e = w.create_entity()
    w.destroy_entity(e)
    assert not w.entity_exists(e)


def test_add_and_get_component():
    w = World()
    e = w.create_entity()
    w.add_component(e, Position(1, 2))
    pos = w.get_component(e, Position)
    assert pos is not None
    assert pos.x == 1 and pos.y == 2


def test_has_component():
    w = World()
    e = w.create_entity()
    assert not w.has_component(e, Position)
    w.add_component(e, Position(0, 0))
    assert w.has_component(e, Position)


def test_remove_component():
    w = World()
    e = w.create_entity()
    w.add_component(e, Position(1, 1))
    w.remove_component(e, Position)
    assert not w.has_component(e, Position)


def test_query_single_component():
    w = World()
    e1 = w.create_entity()
    e2 = w.create_entity()
    w.add_component(e1, Position(1, 0))
    w.add_component(e2, Health(100, 100))
    results = list(w.query(Position))
    assert len(results) == 1
    assert results[0][0] == e1


def test_query_multiple_components():
    w = World()
    e1 = w.create_entity()
    e2 = w.create_entity()
    w.add_component(e1, Position(1, 0))
    w.add_component(e1, Health(100, 100))
    w.add_component(e2, Position(2, 0))  # No health
    results = list(w.query(Position, Health))
    assert len(results) == 1
    assert results[0][0] == e1


def test_tags():
    w = World()
    e = w.create_entity("player", "actor")
    assert w.has_tag(e, "player")
    assert w.has_tag(e, "actor")
    assert not w.has_tag(e, "enemy")

    w.add_tag(e, "special")
    assert w.has_tag(e, "special")

    tagged = w.entities_with_tag("player")
    assert e in tagged


def test_snapshot_and_restore():
    w = World()
    e = w.create_entity("player")
    w.add_component(e, Position(5, 10))

    snapshot = w.snapshot()

    w2 = World()

    @dataclass
    class _Pos:
        x: int
        y: int

    registry = {f"{Position.__module__}.{Position.__qualname__}": Position}
    w2.restore(snapshot, registry)
    assert w2.entity_exists(e)
    pos = w2.get_component(e, Position)
    assert pos is not None
    assert pos.x == 5


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as ex:
            print(f"  FAIL  {t.__name__}: {ex}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
