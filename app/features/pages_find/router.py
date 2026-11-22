"""GET /pages/find. The browser loads the note; this router returns HTML only."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

# The note is loaded in the browser with GET /notes/{id}. This page never queries the database.
PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Find a note</title>
  <style>
    body {
      font-family: Georgia, serif;
      line-height: 1.5;
      margin: 2rem auto;
      max-width: 40rem;
    }
    label { display: block; font-weight: bold; }
    input, button { font: inherit; }
    input { padding: 0.25rem 0.5rem; }
    button { margin-top: 0.75rem; }
    dt { font-weight: bold; }
    [hidden] { display: none; }
  </style>
</head>
<body>
  <main>
    <h1>Find a note</h1>
    <form id="find-form">
      <label for="note-id">Note id</label>
      <input id="note-id" name="note_id" type="text" inputmode="numeric" required>
      <button type="submit">Find</button>
    </form>
    <div id="result" aria-live="polite">
      <p id="empty-state">No note is loaded yet.</p>
      <section id="note" hidden>
        <h2>Note</h2>
        <dl>
          <dt>Title</dt>
          <dd id="title"></dd>
          <dt>Body</dt>
          <dd id="body"></dd>
          <dt>Created</dt>
          <dd id="created_at"></dd>
          <dt>Tags</dt>
          <dd id="tags"></dd>
        </dl>
      </section>
      <p id="not-found" hidden>Note not found</p>
    </div>
  </main>
  <script>
    const form = document.getElementById("find-form");
    const noteIdInput = document.getElementById("note-id");
    const emptyState = document.getElementById("empty-state");
    const noteSection = document.getElementById("note");
    const notFound = document.getElementById("not-found");

    function showEmpty() {
      emptyState.hidden = false;
      noteSection.hidden = true;
      notFound.hidden = true;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const noteId = noteIdInput.value.trim();
      if (!/^[1-9][0-9]*$/.test(noteId)) {
        showEmpty();
        return;
      }
      try {
        const response = await fetch("/notes/" + noteId);
        if (response.status === 404) {
          let detail = "Note not found";
          try {
            const payload = await response.json();
            if (payload && typeof payload.detail === "string" && payload.detail) {
              detail = payload.detail;
            }
          } catch (_error) {
            detail = "Note not found";
          }
          notFound.textContent = detail;
          emptyState.hidden = true;
          noteSection.hidden = true;
          notFound.hidden = false;
          return;
        }
        if (!response.ok) {
          showEmpty();
          return;
        }
        const note = await response.json();
        document.getElementById("title").textContent = note.title;
        document.getElementById("body").textContent = note.body;
        document.getElementById("created_at").textContent = note.created_at;
        const tags = Array.isArray(note.tags) ? note.tags.join(", ") : "";
        document.getElementById("tags").textContent = tags;
        emptyState.hidden = true;
        notFound.hidden = true;
        noteSection.hidden = false;
      } catch (_error) {
        showEmpty();
      }
    });
  </script>
</body>
</html>
"""


@router.get("/pages/find", response_class=HTMLResponse)
def find_page() -> HTMLResponse:
    return HTMLResponse(PAGE_HTML)
