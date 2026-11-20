# Agent rules for this repository

Every agent reads this file first. Role prompts are in `.cursor/agents/`. Decisions are in
`docs/adr/`; read ADR-0003 and ADR-0004 before doing anything.

## Roles

| Role | Does | Never |
|---|---|---|
| Supervisor (`.cursor/agents/supervisor.md`) | Plans, writes ADRs and tickets, dispatches Builders and the Reviewer, unblocks, merges | Edits `app/`, `tests/`, or `scripts/` |
| Builder (`.cursor/agents/builder.md`) | Implements one ticket in its own worktree and opens one pull request | Touches files the ticket does not own, works on a second ticket |
| Reviewer (`.cursor/agents/reviewer.md`) | Reviews a pull request against the ticket and ADRs, labels the outcome | Edits code or pushes commits |

## Shared state is GitHub, not chat

- A ticket is a GitHub Issue created from the `Ticket` template.
- Work is a pull request that contains `Closes #<issue>`.
- Questions and answers are comments on the Issue or pull request.

## Labels

| Label | Meaning | Set by |
|---|---|---|
| `status:ready` | Ticket filed, waiting for a Builder | Supervisor |
| `status:in-progress` | A Builder is working on it | Builder |
| `status:blocked` | Builder needs an answer; question is in the last Issue comment | Builder |
| `status:in-review` | Pull request ready for the Reviewer | Builder |
| `round:1` / `round:2` / `round:3` | Current review round | Reviewer |
| `review:approved` | Reviewer approved the current commit | Reviewer |
| `needs-human` | Round 3 failed or a decision is above the Supervisor | Reviewer or Supervisor |

## Branches and pull requests

- Branch name: `ticket/<issue-number>-<short-slug>`, cut from the latest `main`.
- One ticket = one branch = one pull request. Squash-merge into `main`.
- Fill in every section of the pull request template, including "Feature run".

## Python environment

The project is not pip-installed, so each worktree imports its own `app/`. Use the shared
virtual environment of the main checkout; the Supervisor passes its absolute path as `PYTHON`
in every dispatch. Always run commands from the worktree root:

```
<PYTHON> -m pytest -q                     # all tests
<PYTHON> -m ruff check . ; <PYTHON> -m ruff format .
<PYTHON> -m scripts.run_<feature>         # feature run
```

New setup: `python -m venv .venv` then `.venv/Scripts/python -m pip install -r requirements-dev.txt`.

## Merge gate (ADR-0004)

A pull request merges only when the `ci` workflow's `lint-and-test` and `merge-gate` checks pass.
`merge-gate` needs `review:approved`, no `needs-human`, `Closes #N` in the body, and a filled
"Feature run" section. Pushing after approval removes `review:approved` automatically.

## Review loop

At most three rounds. Round N: the Reviewer sets `round:N` and either approves or requests
changes; the Builder fixes on the same branch and sets `status:in-review` again. If round 3
requests changes, the Reviewer sets `needs-human` and the loop stops.
