# ADR-0003: One folder per feature, mounted by auto-discovery

- Status: Accepted
- Date: 2026-11-20
- Deciders: Human lead, Supervisor agent

## Context
Five or more builders work at the same time, each on its own branch. If every feature had to
register itself in a shared file, every pull request would conflict with every other one.

## Decision
- Each feature lives in `app/features/<name>/` and exposes `router = APIRouter()` in `router.py`.
  `app/main.py` imports and mounts every such router automatically, in alphabetical order.
- A feature's files are: `app/features/<name>/`, `tests/test_<name>.py`, and
  `scripts/run_<name>.py`. A ticket owns exactly these paths and nothing else.
- Features must not import from each other. Shared code goes into the base (`app/db.py`,
  `app/models.py`) through a separate ticket.
- Integer path parameters use the `:int` converter (for example `/notes/{note_id:int}`), so
  literal routes such as `/notes/search` from another feature are never captured by a path
  parameter regardless of mount order.
- Route paths must not overlap another feature's paths with the same HTTP method; the
  Supervisor assigns path prefixes in the ticket.

## Consequences
Parallel pull requests touch disjoint files and merge without conflicts. Features cannot reuse
each other's helpers, which leads to some duplication.
