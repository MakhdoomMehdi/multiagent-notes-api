# ADR-0009: Shared page chrome lives in app/ui

- Status: Accepted
- Date: 2026-11-23
- Deciders: Human lead, Supervisor agent
- Ticket / PR: #15
- Supersedes: in ADR-0008, the lines that assign the notes-page HTML to Atlas and that forbid a shared layout. The rest of ADR-0008 still stands.

## Context

ADR-0008 put each notes screen in its own feature and told Atlas to own the HTML. It also forbade a shared stylesheet so five pull requests would not touch one file. The pages now exist. A person moving between them has no single navigation control, and copying a sidebar into every feature repeats the same markup with no owner.

Pixel is the frontend role. Atlas owns HTTP handlers, validation, and feature tests. ADR-0003 still stops features from importing each other. Shared code that is not a feature can live beside `app.db` and `app.models`.

## Options considered

- Copy the same sidebar into each feature and leave Atlas as the editor. Rejected. That keeps UI work on the backend role and the copies drift apart.
- Add a top-level `web/` or `ui/` app. Rejected. ADR-0002 stays FastAPI, and the pages are already server-rendered.
- One shared chrome package, `app/ui/`, imported by the pages. Pixel owns it. This is the option we took.

## Decision

We will put shared page chrome in `app/ui/`. Page features may import `app.ui`. They still must not import each other.

Pixel owns `app/ui/` and the HTML that renders it, including edits to a page file that only insert that markup. Atlas does not write that markup.

The first chrome is one sidebar. It links to `/pages`, `/pages/new`, `/pages/find`, `/pages/help`, `/board`, and `/docs`. The note screen stays reached through Find, because that route needs an id.

## Consequences

A sidebar is one file, so the links stay the same on every page. Features take a dependency on `app.ui`, which ADR-0003 did not spell out for chrome. A page that wants different navigation has to live with the shared one or ask for a new ADR.

Pixel can create `app/ui/` when a ticket lists it. Atlas tickets that ask for a screen stop and go to Pixel.
