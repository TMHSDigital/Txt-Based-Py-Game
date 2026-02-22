# Contributing

Thank you for considering a contribution. This document covers the
conventions and workflow used in this project.

---

## Getting Started

There are no external dependencies. Clone the repository and run the
game directly with Python 3.10 or higher:

```bash
git clone https://github.com/your-username/dungeon-crawler.git
cd dungeon-crawler
python main.py
```

Run the test suite to confirm everything is working:

```bash
python tests/test_world.py
python tests/test_combat.py
python tests/test_inventory.py
```

---

## Project Conventions

### Architecture boundaries

The project is divided into four layers. Contributions must respect the
dependency rules between them.

```
data (JSON) --> content/ --> engine/ + components/ --> systems/ --> ui/
```

- `engine/` and `components/` must not import from `systems/`, `ui/`,
  or `content/`.
- `systems/` may import from `engine/` and `components/` only.
- `ui/` may import from `engine/`, `components/`, and `systems/`.
- `game_bootstrap.py` is the only module permitted to import from all
  layers simultaneously.

### Entity-Component-System rules

- Components are plain dataclasses. They hold data; they do not contain
  game logic or cross-component references.
- Systems are stateless functions or event-subscribed closures. All
  shared state is read from and written to components.
- New behaviour should be added as a new component plus a new system
  rather than by modifying existing components.

### Adding content vs. adding code

If you can express the change in the JSON data files (`data/`), do so.
New rooms, enemies, items, and quests do not require code changes. See
the "Adding Content" section in `README.md` for the exact schemas.

### Code style

- Follow PEP 8. Line length limit is 100 characters.
- Use `from __future__ import annotations` in every module.
- Use `TYPE_CHECKING` guards for imports that exist only for type hints,
  to avoid circular imports at runtime.
- Public functions and classes require docstrings. Internal helpers
  (prefixed with `_`) should have a docstring when their behaviour is
  not immediately obvious.
- Avoid bare `except` clauses. Catch specific exception types.
- No mutable default arguments. Use `field(default_factory=...)` in
  dataclasses and `None` with an `if` guard in regular functions.

### Event-driven communication

Systems must not call each other directly. If system A needs to trigger
behaviour owned by system B, system A should publish an event on the
bus and system B should subscribe to it. This keeps systems decoupled
and testable in isolation.

---

## Submitting Changes

1. Fork the repository and create a feature branch from `main`.
2. Make your changes, following the conventions above.
3. Add or update tests for any new system or engine behaviour.
4. Run the full test suite and confirm all tests pass.
5. Update `CHANGELOG.md` under the `[Unreleased]` heading.
6. Open a pull request with a clear description of what changed and why.

### Commit message format

```
<type>: <short summary>

<optional body explaining the why, not the what>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

Examples:

```
feat: add dialogue system for NPC interactions
fix: resolve loot drop quantity rolling off-by-one
docs: expand data schema reference in README
test: add coverage for status effect expiry
```

---

## Reporting Issues

Please include:

- The Python version you are running (`python --version`).
- The full traceback if the issue is a crash.
- The sequence of commands that triggered the issue.
- The contents of your save file if the issue is save/load related.
