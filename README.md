# Factwise — Team Project Planner

A Django-powered team project planner tool with file-based persistence.

---

## Architecture

```
factwise-python/
├── planner/
│   ├── settings.py      # Standalone Django config
│   ├── setup.py         # Django initialisation (idempotent)
│   ├── models.py        # User, Team, TeamMembership, Board, Task
│   ├── user_impl.py     # Implements UserBase
│   ├── team_impl.py     # Implements TeamBase
│   └── board_impl.py    # Implements ProjectBoardBase
├── db/                  # SQLite database lives here (auto-created)
├── out/                 # Exported board .txt files
```

---

## Tech Choices

| Choice | Reason |
|--------|--------|
| **Django ORM (standalone)** | Clean, battle-tested ORM for relational data; used without the web stack via `django.setup()` |
| **SQLite in `db/`** | File-based persistence as required; zero configuration, no separate server |
| **UUID primary keys** | Avoids sequential id leakage; portable across environments |
| **`TeamMembership` explicit through-table** | Enables clean 50-member cap enforcement and timestamped joins |

---

## Usage

```python
from planner.user_impl import UserImpl
from planner.team_impl import TeamImpl
from planner.board_impl import ProjectBoardImpl

users  = UserImpl()
teams  = TeamImpl()
boards = ProjectBoardImpl()

uid = users.create_user('{"name": "alice", "display_name": "Alice"}')
tid = teams.create_team('{"name": "backend", "description": "Backend squad", "admin": "<user_id>"}')
bid = boards.create_board('{"name": "Sprint 1", "description": "Q1 Sprint", "team_id": "<team_id>"}')
```

The database tables are created automatically on first import — no migrations to run manually.

---

## Assumptions

1. **`add_task` requires `board_id`** — the base docstring omits it, but a task cannot be created without knowing its board. The field is added to the JSON contract as `"board_id"`.

2. **`describe_user` returns `display_name` as `"description"`** — the base docstring uses the key `"description"` where the rest of the API uses `"display_name"`. Since there is no separate description field on User, `display_name` is returned under the `"description"` key.

3. **Team members cap (50) is a total cap**, not a per-call cap. Adding users that would push total members above 50 raises a `ValueError`.

4. **`creation_time` in `create_board` / `add_task`** — accepted if provided; defaults to `now()` if absent.

5. **`update_user` with `"name"` key present raises `ValueError`** — username is immutable by constraint.

---

## Constraints Enforced

| Entity | Constraint |
|--------|-----------|
| User | `name` unique, ≤ 64 chars; `display_name` ≤ 64 (create) / 128 (update) |
| Team | `name` unique, ≤ 64; `description` ≤ 128; max 50 members |
| Board | `name` unique per team, ≤ 64; `description` ≤ 128; must be OPEN to accept tasks |
| Task | `title` unique per board, ≤ 64; `description` ≤ 128; board must be OPEN |
| Close board | All tasks must be `COMPLETE` |

---

## Board Export

`export_board` writes a formatted ASCII report to `out/<board_slug>_<id>.txt`:

```
╔══════════════════════════════════════════════════════════════════╗
║  BOARD: Sprint 1                                                 ║
║  Team: backend   Status: OPEN ○                                  ║
║  Created: 2024-06-01 09:00   Closed: —                          ║
╠══════════════════════════════════════════════════════════════════╣
║  SUMMARY                                                         ║
║  Total: 3   Open: 1   In Progress: 1   Complete: 1              ║
║  Progress: [████████░░░░░░░░░░░░] 33%                           ║
╠══════════════════════════════════════════════════════════════════╣
║  TASKS                                                           ║
╠══════════════════════════════════════════════════════════════════╣
║  ● [01] Setup CI pipeline                                        ║
║         Status:   COMPLETE                                       ║
║         Assignee: alice                                          ║
║         Created:  2024-06-01 10:00                              ║
╟──────────────────────────────────────────────────────────────────╢
║  ◑ [02] Implement auth                                           ║
║         Status:   IN PROGRESS                                    ║
║         Assignee: bob                                            ║
║         Created:  2024-06-02 11:00                              ║
╚══════════════════════════════════════════════════════════════════╝

Generated: 2024-06-05 14:22:00
```
