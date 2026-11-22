# ADR-0008: Notes frontend is server-rendered pages

- Status: Accepted
- Date: 2026-11-23
- Deciders: Human lead, Supervisor agent
- Ticket / PR: #3
- Supersedes: nothing

## Context

The notes API creates one note and fetches one note. `app/features/notes/router.py` exposes `POST /notes` and `GET /notes/{note_id:int}` and no other note route. `POST /notes` accepts a title and an optional body and returns 201 with the stored note: `id`, `title`, `body`, `created_at`, and `tags`. A missing title, an empty title, or a title longer than 200 characters returns 422. `GET /notes/{note_id:int}` returns that same note, or 404 with detail `Note not found`. There is no list, update, or delete route. These page routes do not exist yet.

The repository has no `web/`, `ui/`, or `src/` directory. ADR-0002 keeps the stack to FastAPI and SQLite. ADR-0003 puts each feature in `app/features/<name>/`, mounts every router by auto-discovery, and keeps features from importing each other. ADR-0005 says Pixel writes a UI directory only after one exists, and a Pixel ticket stops until then. ADR-0006 serves `GET /board` as HTML from `app/features/board/router.py`. ADR-0007 keeps that page and still adds no standalone `ui/` directory. ADR-0005, ADR-0006, and ADR-0007 are Accepted. This ADR does not rewrite ADR-0001 through ADR-0007.

Later tickets need a written place for the notes screens. The Supervisor has already chosen server-rendered pages inside this app. This ADR records that choice.

## Options considered

- A standalone `ui/` directory, assigned to Pixel. Rejected. ADR-0005 and ADR-0007 forbid inventing one, and Pixel stops until a UI directory already exists. A `web/` or `src/` tree is the same kind of new directory.
- A second SPA toolchain, with its own framework and build. Rejected. ADR-0002 is FastAPI and SQLite only.
- Five server-rendered FastAPI features, one HTML page each, mounted by auto-discovery, the same HTML-in-a-feature pattern as the board. This is the option we took.

## Decision

We will not add `web/`, `ui/`, or `src/`.

We will build the notes frontend as five server-rendered FastAPI features, one HTML page each. Auto-discovery mounts them (ADR-0003). Each page is HTML returned from that feature, the same HTML-in-a-feature pattern as the board (ADR-0006).

Pages do not import each other or `app.features.notes`. The paths do not overlap. The browser calls only `POST /notes` and `GET /notes/{note_id:int}`.

Atlas owns the five features. Pixel is not assigned. This ADR supersedes nothing.

We will use semantic HTML, put a label on every control, and keep the text readable. We will not add a shared stylesheet, because that file would belong to more than one ticket. Inline styles are allowed. A screen has only the states named for it below.

- `GET /pages` is `app/features/pages_index/`. The page links to `/pages/new`, `/pages/find`, and `/pages/help`, and it has a form that asks for an id and navigates to `/pages/notes/{id}`. Empty state: no id entered. Success: the index is showing.
- `GET /pages/new` is `app/features/pages_new/`. The page is a form with title (required) and body. The browser POSTs `/notes`. Success shows the created note (`id`, `title`, `body`, `created_at`, and `tags`) and a link to `/pages/notes/{id}`. An empty title stays on the page and shows the 422 detail. Empty state: the blank form.
- `GET /pages/notes/{note_id:int}` is `app/features/pages_note/`. The browser GETs `/notes/{id}`. Success shows title, body, created_at, and tags. An unknown id shows the 404 detail "Note not found". The page shows loading while the request is in flight.
- `GET /pages/find` is `app/features/pages_find/`. The page stays empty until an id is submitted. The browser then GETs `/notes/{id}`, the same call as `/pages/notes/{note_id:int}`. Success shows title, body, created_at, and tags on this page. An unknown id shows the 404 detail "Note not found" on this page.
- `GET /pages/help` is `app/features/pages_help/`. The page states the two endpoints, status codes 201, 422, and 404, and the other four paths. Success is the page itself.

Out of scope: list, update, delete, tag editing, auth, a `ui/` directory, and any change to `app/features/notes/`, `app/db.py`, or `app/models.py`.

## Consequences

The Supervisor files the five Atlas tickets only after this ADR merges. Each ticket owns one of the feature folders above, so the pull requests stay disjoint.

Page chrome is duplicated. Features cannot import each other, and there is no shared stylesheet.

The UI cannot list notes until a later API ticket adds a list route. Update, delete, tag editing, and auth wait for their own decisions. The notes feature, `app/db.py`, and `app/models.py` stay as they are.

Pixel stays blocked for a standalone frontend. This ADR adds no UI directory, so a Pixel ticket still stops (ADR-0005).

Shipping the screens is easier inside the FastAPI app that already exists: one mount path, no second toolchain, and five Atlas sessions that do not share files.
