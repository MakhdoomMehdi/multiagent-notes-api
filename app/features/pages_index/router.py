"""GET /pages: links to the other notes pages and a form that opens one note."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Notes</title>
<style>
  body {
    font-family: Georgia, serif;
    margin: 24px;
    background: #f6f4ef;
    color: #1c1915;
    line-height: 1.5;
  }
  h1, h2 { font-weight: normal; }
  a { color: #1c4f73; }
  label { display: block; margin-top: 16px; }
  input, button { font: inherit; }
  input { padding: 6px 8px; margin-top: 4px; }
  button { margin-top: 12px; padding: 6px 12px; }
  .empty { color: #6b645c; }
  nav ul { padding-left: 1.2rem; }
</style>
</head>
<body>
<main>
  <h1>Notes</h1>
  <p class="empty" id="empty-state">No note id has been entered.</p>
  <section id="index" aria-label="Notes index">
    <h2>Index</h2>
    <p>The index is showing.</p>
    <nav aria-label="Pages">
      <ul>
        <li><a href="/pages/new">Create a note</a></li>
        <li><a href="/pages/find">Find a note</a></li>
        <li><a href="/pages/help">Help</a></li>
      </ul>
    </nav>
    <form id="open-note" action="/pages/notes/" method="get" data-note-path="/pages/notes/">
      <label for="note-id">Note id</label>
      <input id="note-id" name="note_id" type="text"
        inputmode="numeric" autocomplete="off" required>
      <button type="submit">Open note</button>
    </form>
  </section>
</main>
<script>
var form = document.getElementById("open-note");
var input = document.getElementById("note-id");
input.addEventListener("input", function () {
  input.setCustomValidity("");
});
form.addEventListener("submit", function (event) {
  event.preventDefault();
  var noteId = input.value.trim();
  if (!/^[1-9][0-9]*$/.test(noteId)) {
    input.setCustomValidity("Enter a whole note id.");
    input.reportValidity();
    return;
  }
  input.setCustomValidity("");
  window.location.assign(form.getAttribute("data-note-path") + noteId);
});
</script>
</body>
</html>
"""


@router.get("/pages", response_class=HTMLResponse)
def pages_index() -> HTMLResponse:
    return HTMLResponse(PAGE)
