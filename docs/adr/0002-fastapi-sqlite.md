# ADR-0002: FastAPI with SQLite and plain sqlite3

- Status: Accepted
- Date: 2026-11-20
- Deciders: Human lead, Supervisor agent

## Context
The service is a small Notes API used to demonstrate a multi-agent workflow. It must be quick to
set up on any machine and in CI, and easy for agents to read and test.

## Decision
- We will use Python 3.11+, FastAPI, and Pydantic models.
- We will store data in SQLite through the standard `sqlite3` module via `app/db.py`; no ORM.
- The database file comes from `NOTES_DB_PATH`. Tests and feature runs use a throwaway file.
- The schema (`notes`, `note_tags`) is owned by the base in `app/db.py`. A ticket that needs a
  schema change must say so explicitly; builders do not change the schema otherwise.
- Tests use `pytest` with the fixtures in `tests/conftest.py` (`client`, `make_note`).
  Lint and formatting use `ruff`.

## Consequences
No database server or migrations are needed. Raw SQL is visible in each feature, which keeps
features independent but repeats some query code; that duplication is acceptable at this size.
