def test_get_note_page_returns_html_for_an_integer_id(client):
    response = client.get("/pages/notes/7")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    page = response.text
    assert "Loading" in page
    assert 'id="title"' in page
    assert 'id="body"' in page
    assert 'id="created_at"' in page
    assert 'id="tags"' in page
    assert "/notes/" in page
    assert "Note not found" in page
    assert 'data-note-id="7"' in page


def test_unknown_id_page_includes_not_found_detail(client):
    response = client.get("/pages/notes/9999")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Note not found" in response.text
    assert "/notes/" in response.text
    assert 'data-note-id="9999"' in response.text


def test_non_integer_id_is_not_captured(client):
    response = client.get("/pages/notes/abc")
    assert response.status_code == 404


def test_post_note_page_is_not_allowed(client):
    response = client.post("/pages/notes/7")
    assert response.status_code == 405
