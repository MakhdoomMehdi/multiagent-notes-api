import re


def _page(client) -> str:
    response = client.get("/pages/find")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    return response.text


def test_get_pages_find_returns_html(client):
    _page(client)


def test_labeled_note_id_and_empty_state(client):
    html = _page(client)
    label = re.search(r'<label\s+for="([^"]+)">\s*Note id\s*</label>', html)
    assert label, "expected a label asking for a note id"
    control_id = label.group(1)
    assert re.search(rf'<input[^>]*id="{control_id}"[^>]*>', html)
    assert re.search(r'<p id="empty-state">No note is loaded yet\.</p>', html)


def test_submit_fetches_note_and_stays_on_page(client):
    html = _page(client)
    assert 'fetch("/notes/"' in html
    assert "preventDefault()" in html
    assert "/pages/notes/" not in html
    for field in ("title", "body", "created_at", "tags"):
        assert f"note.{field}" in html


def test_unknown_id_shows_note_not_found(client):
    html = _page(client)
    assert "Note not found" in html
    assert "response.status === 404" in html


def test_invalid_id_stays_on_empty_state(client):
    html = _page(client)
    assert "/^[1-9][0-9]*$/" in html
    assert "required" in html


def test_server_does_not_render_a_note(client, make_note):
    note_id = make_note("Secret title", body="secret body", tags=("alpha",))
    response = client.get(f"/pages/find?id={note_id}")
    assert response.status_code == 200
    assert "No note is loaded yet." in response.text
    assert "Secret title" not in response.text


def test_post_pages_find_returns_405(client):
    response = client.post("/pages/find")
    assert response.status_code == 405
