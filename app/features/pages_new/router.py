"""GET /pages/new. The page script POSTs /notes and renders the result (ADR-0008)."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>New note</title>
<style>
  body {
    font-family: Georgia, serif;
    margin: 24px;
    background: #f6f4ef;
    color: #1c1915;
  }
  h1 { font-weight: normal; }
  form {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 36rem;
  }
  label { font-size: 14px; }
  input, textarea {
    font: inherit;
    padding: 8px;
    border: 1px solid #d9d3c8;
    background: white;
  }
  textarea { min-height: 8rem; }
  button { font: inherit; width: fit-content; padding: 8px 14px; }
  .empty { color: #6b645c; }
  #error { color: #a33b32; }
  a { color: #1c1915; }
</style>
</head>
<body>
<main>
<h1>New note</h1>
<p id="empty-state" class="empty">Blank form. Enter a title and an optional body.</p>
<form id="note-form" novalidate>
  <label for="title">Title</label>
  <input id="title" name="title" type="text" required autocomplete="off">
  <label for="body">Body</label>
  <textarea id="body" name="body"></textarea>
  <button type="submit">Create note</button>
</form>
<p id="error" role="alert" hidden></p>
<section id="created" hidden>
  <h2>Created note</h2>
  <dl>
    <dt>id</dt><dd id="note-id"></dd>
    <dt>title</dt><dd id="note-title"></dd>
    <dt>body</dt><dd id="note-body"></dd>
    <dt>created_at</dt><dd id="note-created-at"></dd>
    <dt>tags</dt><dd id="note-tags"></dd>
  </dl>
  <a id="note-link" href="/pages/notes/">View note</a>
</section>
</main>
<script>
function text(value) {
  return String(value ?? "");
}
function formatDetail(detail) {
  if (typeof detail === "string") {
    return detail;
  }
  if (!Array.isArray(detail)) {
    return text(detail);
  }
  return detail.map((item) => {
    const parts = Array.isArray(item.loc) ? item.loc : [];
    const loc = parts.filter((part) => part !== "body").join(".");
    const msg = item.msg || text(item);
    return loc ? loc + ": " + msg : msg;
  }).join("; ");
}
function showError(message) {
  const error = document.getElementById("error");
  error.hidden = false;
  error.textContent = message;
}
document.getElementById("note-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = document.getElementById("title").value;
  const body = document.getElementById("body").value;
  document.getElementById("error").hidden = true;
  document.getElementById("created").hidden = true;
  document.getElementById("empty-state").hidden = false;
  let response;
  try {
    response = await fetch("/notes", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({title, body}),
    });
  } catch (_err) {
    showError("The note was not created.");
    return;
  }
  if (response.status === 422) {
    const payload = await response.json();
    showError(formatDetail(payload.detail));
    return;
  }
  if (!response.ok) {
    showError("The note was not created.");
    return;
  }
  const note = await response.json();
  document.getElementById("note-id").textContent = text(note.id);
  document.getElementById("note-title").textContent = text(note.title);
  document.getElementById("note-body").textContent = text(note.body);
  document.getElementById("note-created-at").textContent = text(note.created_at);
  document.getElementById("note-tags").textContent = text((note.tags || []).join(", "));
  const link = document.getElementById("note-link");
  link.href = "/pages/notes/" + note.id;
  document.getElementById("created").hidden = false;
  document.getElementById("empty-state").hidden = true;
});
</script>
</body>
</html>
"""


@router.get("/pages/new", response_class=HTMLResponse)
def new_note_page() -> HTMLResponse:
    return HTMLResponse(PAGE)
