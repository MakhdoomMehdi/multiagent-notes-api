"""HTML shell for one note. The browser GETs /notes/{id}; this feature does not."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Note</title>
<style>
  body { font-family: Georgia, serif; margin: 24px auto; max-width: 40rem;
         background: #f6f4ef; color: #1c1915; line-height: 1.5; }
  h1 { font-weight: normal; }
  .loading { color: #6b645c; }
  .error { color: #a33b32; }
  dl { background: white; border: 1px solid #d9d3c8; border-radius: 8px;
       padding: 12px 16px; }
  dt { color: #6b645c; font-size: 14px; margin-top: 10px; }
  dd { margin: 0; white-space: pre-wrap; }
  [hidden] { display: none; }
</style>
</head>
<body>
<main data-note-id="__NOTE_ID__">
  <h1>Note</h1>
  <p id="loading" class="loading" role="status">Loading note…</p>
  <dl id="note" hidden>
    <dt><label for="title">Title</label></dt>
    <dd><output id="title"></output></dd>
    <dt><label for="body">Body</label></dt>
    <dd><output id="body"></output></dd>
    <dt><label for="created_at">Created at</label></dt>
    <dd><output id="created_at"></output></dd>
    <dt><label for="tags">Tags</label></dt>
    <dd><output id="tags"></output></dd>
  </dl>
  <p id="error" class="error" role="alert" hidden>Note not found</p>
</main>
<script>
const root = document.querySelector("main");
const noteId = root.dataset.noteId;
const loading = document.getElementById("loading");
const note = document.getElementById("note");
const error = document.getElementById("error");

function showError(message) {
  loading.hidden = true;
  note.hidden = true;
  error.textContent = message;
  error.hidden = false;
}

fetch("/notes/" + noteId).then(function (response) {
  if (response.status === 404) {
    return response.json().then(function (payload) {
      const detail = payload && typeof payload.detail === "string"
        ? payload.detail
        : "Note not found";
      showError(detail);
    });
  }
  if (!response.ok) {
    showError("Could not load this note.");
    return;
  }
  return response.json().then(function (data) {
    document.getElementById("title").textContent = data.title ?? "";
    document.getElementById("body").textContent = data.body ?? "";
    document.getElementById("created_at").textContent = data.created_at ?? "";
    const tags = Array.isArray(data.tags) ? data.tags : [];
    document.getElementById("tags").textContent = tags.length
      ? tags.join(", ")
      : "none";
    loading.hidden = true;
    error.hidden = true;
    note.hidden = false;
  });
}).catch(function () {
  showError("Could not load this note.");
});
</script>
</body>
</html>
"""


@router.get("/pages/notes/{note_id:int}", response_class=HTMLResponse)
def note_page(note_id: int) -> HTMLResponse:
    return HTMLResponse(_PAGE.replace("__NOTE_ID__", str(note_id)))
