# multiagent-notes-api

A small Notes API (FastAPI + SQLite) built by a team of Cursor agents:

- **Supervisor**: plans, writes ADRs and tickets, dispatches, unblocks, merges. Never writes code.
- **Builders** (5+ in parallel): one ticket = one git worktree = one branch = one pull request.
- **Reviewer**: review-and-fix loop, at most 3 rounds.

Tickets are GitHub Issues, and a pull request merges only when tests pass, the Reviewer has
approved, and a feature-run output is attached. See [AGENTS.md](AGENTS.md) and
[docs/adr/](docs/adr/).

## Run locally

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
```

## Start a session

Open this folder in Cursor and tell the main chat:

> Act as the Supervisor in `.cursor/agents/supervisor.md`. Goal: <feature goal>.
