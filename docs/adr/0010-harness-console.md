# ADR-0010: Harness Console

- Status: Accepted
- Date: 2026-11-23
- Deciders: Human lead, Supervisor agent
- Ticket / PR: #21, #39
- Supersedes: nothing
- Extends: ADR-0003, ADR-0009

## Context

The notes API is one FastAPI app. `app/main.py` discovers every package under `app/features/` that exposes `router` and mounts it, so a new feature does not edit that file (ADR-0003). Shared page chrome already lives in `app/ui/`. `app/ui/nav.py` is the notes sidebar: `sidebar` and `with_sidebar` link Index, Create, Find, Help, Board, and API docs (ADR-0009). A feature may import `app.ui`. A feature must not import another feature.

The next demo is a Harness Console inside this same app: HTML views over this repository's issues, pull requests, agents, pipeline, merge gate, ADRs, and strains. Several builders will own those views at once. GitHub stays the shared state (ADR-0004), and the pages still have to render when `gh` fails, times out, or returns a payload the reader cannot use. The harness board is a separate surface. A console page must not depend on it.

This ADR supersedes nothing. It extends ADR-0003 and ADR-0009. It does not rewrite them.

## Options considered

- A separate frontend toolchain, with its own framework and build. Rejected. ADR-0002 keeps the stack on FastAPI and SQLite. A build step and a new top-level frontend would sit outside auto-discovery.
- One shared feature for every view. Rejected. ADR-0003 puts each feature in its own folder so parallel pull requests do not edit the same files. One folder would put overview, chat, agents, pipeline, merge, ADRs, and strains on the same paths.
- Server-rendered HTML in this FastAPI app, one feature folder per view, new chrome modules under `app/ui/`, and one GitHub reader that falls back to seed data. This is the option we took.

## Decision

We will add the Harness Console as server-rendered HTML inside the existing FastAPI app. There is no build step and no new top-level frontend. `app/main.py` stays untouched. Auto-discovery mounts the new features (ADR-0003).

We will use one feature folder per view. The folders are `app/features/console_overview/`, `app/features/console_chat/`, `app/features/console_agents/`, `app/features/console_pipeline/`, `app/features/console_merge/`, `app/features/console_adrs/`, and `app/features/console_strains/`. A feature may import `app.db`, `app.models`, and `app.ui`. A feature must not import another feature.

We will keep shared chrome in `app/ui/` (ADR-0009). Pixel owns that package. The console chrome is new modules under `app/ui/` and does not replace the notes sidebar in `app/ui/nav.py`. Atlas owns each view, including the HTML response of that view's router, and calls the console chrome. Atlas does not edit `app/ui/`.

We will read Issues, pull requests, labels, and CI from GitHub with `gh`. `app.db.load_console` is the only reader. On any failure, timeout, or invalid payload it returns seed data stored in `app/db.py` and sets `mode` to `seed`. It never raises. The console does not read the harness board and does not call `/board/events`. A down board must not break a console page.

We will serve these routes: `GET /console`, `GET /console/chat`, `POST /console/chat`, `GET /console/agents`, `GET /console/agents/{agent_id}`, `GET /console/pipeline`, `GET /console/pipeline/board`, `GET /console/merge`, `GET /console/merge/{number:int}`, `GET /console/adrs`, `GET /console/adrs/{number:int}`, and `GET /console/strains`. Integer parameters use the `:int` converter. `GET /console` is the landing page.

We will show a header badge, "Live" or "Offline (seed data)", from `mode`. `CONSOLE_SOURCE=seed` and `?source=seed` force the seed. The pipeline polls `GET /console/pipeline/board` every 5 seconds. We will not add a websocket.

We will not add `app/integrations/`, `app/security/`, or a JavaScript build.

## Consequences

Adding a view does not touch `app/main.py`, and the seven folders can land in separate pull requests. The notes sidebar stays where ADR-0009 put it. A console page can still render when GitHub is unreachable, because the reader returns seed data.

Features cannot import each other. A helper that two views need has to land in `app.db`, `app.models`, or `app.ui` through a ticket that owns that path (ADR-0003, ADR-0009). A view cannot import another view's helpers, so some markup is duplicated.

Atlas owns each view's HTML response and calls the console chrome from that view's router. Atlas does not edit `app/ui/`. Pixel owns the new modules under `app/ui/`. A view ticket that needs a chrome change stops for Pixel. This extends ADR-0009 for these views: Atlas writes the page response, and Pixel still owns the shared chrome. ADR-0009 is not rewritten, and `app/ui/nav.py` is not replaced.

A live GitHub call must never be required for a page to render. `load_console` is the only reader of Issues, pull requests, labels, and CI. Failure, timeout, and an invalid payload all return the seed data in `app/db.py`, set `mode` to `seed`, and do not raise. The console does not read the harness board and does not call `/board/events`. A down board must not break a console page.

The badge, the seed switch (`CONSOLE_SOURCE=seed` and `?source=seed`), and the five-second poll of `GET /console/pipeline/board` are part of the contract. There is no websocket, no `app/integrations/`, and no `app/security/`. Later tickets add the folders, the chrome modules, and `load_console`. This ADR does not add them.
