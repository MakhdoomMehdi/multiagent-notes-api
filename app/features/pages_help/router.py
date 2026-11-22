"""Static help page. Success is the page itself (ADR-0008)."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Notes help</title>
<style>
  body { font-family: Georgia, serif; margin: 24px auto; max-width: 40rem;
         padding: 0 16px; background: #f6f4ef; color: #1c1915; line-height: 1.5; }
  h1, h2, h3 { font-weight: normal; }
  code { font-family: Consolas, monospace; }
  a { color: #1c1915; }
</style>
</head>
<body>
<header>
  <h1>Help</h1>
  <p>This page is the help screen. Opening it is the success state. It explains
  the notes API and the other four screens. The API has no list, update, or
  delete route.</p>
</header>
<main>
  <section>
    <h2>Notes API</h2>
    <p>The browser calls only these two endpoints.</p>
    <h3><code>POST /notes</code></h3>
    <p>Creates one note. Send a title and an optional body. Success returns
    <strong>201</strong> with the stored note: id, title, body, created_at, and
    tags. A missing title, an empty title, or a title longer than 200 characters
    returns <strong>422</strong>.</p>
    <h3><code>GET /notes/{note_id}</code></h3>
    <p>Returns that note. The id is an integer. An unknown id returns
    <strong>404</strong> with detail "Note not found".</p>
  </section>
  <section>
    <h2>Screens</h2>
    <nav aria-label="Other screens">
      <ul>
        <li><a href="/pages"><code>/pages</code></a></li>
        <li><a href="/pages/new"><code>/pages/new</code></a></li>
        <li><code>/pages/notes/{note_id}</code></li>
        <li><a href="/pages/find"><code>/pages/find</code></a></li>
      </ul>
    </nav>
    <h3><code>/pages</code></h3>
    <p>The index links to <code>/pages/new</code>, <code>/pages/find</code>, and
    this help page. It has a form that asks for an id and opens
    <code>/pages/notes/{note_id}</code>. With no id entered, that is the empty
    state. Success is the index showing.</p>
    <h3><code>/pages/new</code></h3>
    <p>A form with a required title and a body. The browser sends
    <code>POST /notes</code>. Success shows the created note (id, title, body,
    created_at, and tags) and a link to <code>/pages/notes/{note_id}</code>.
    An empty title stays on the form and shows the 422 detail. The blank form
    is the empty state.</p>
    <h3><code>/pages/notes/{note_id}</code></h3>
    <p>The browser sends <code>GET /notes/{note_id}</code>. Success shows the
    title, body, created_at, and tags. An unknown id shows the 404 detail
    "Note not found". The page shows loading while the request is in flight.</p>
    <h3><code>/pages/find</code></h3>
    <p>The page stays empty until an id is submitted. The browser then sends
    <code>GET /notes/{note_id}</code>, the same call as the note screen.
    Success shows the title, body, created_at, and tags on this page. An unknown
    id shows the 404 detail "Note not found" on this page.</p>
  </section>
</main>
</body>
</html>
"""


@router.get("/pages/help", response_class=HTMLResponse)
def help_page() -> HTMLResponse:
    return HTMLResponse(PAGE)
