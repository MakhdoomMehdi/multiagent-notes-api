def _note_id_tag(html: str) -> str:
    start = html.index('id="note-id"')
    tag_start = html.rindex("<input", 0, start)
    tag_end = html.index(">", start)
    return html[tag_start : tag_end + 1]


def test_get_pages_returns_html(client):
    response = client.get("/pages")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_pages_links_to_new_find_and_help(client):
    html = client.get("/pages").text
    assert 'href="/pages/new"' in html
    assert 'href="/pages/find"' in html
    assert 'href="/pages/help"' in html


def test_pages_has_labeled_note_id_that_navigates(client):
    html = client.get("/pages").text
    assert '<label for="note-id">Note id</label>' in html
    tag = _note_id_tag(html)
    assert tag.startswith("<input")
    assert 'id="note-id"' in tag
    assert 'data-note-path="/pages/notes/"' in html
    assert "/pages/notes/" in html


def test_pages_starts_with_no_id_entered(client):
    html = client.get("/pages").text
    assert "No note id has been entered." in html
    assert "value=" not in _note_id_tag(html)


def test_pages_shows_the_index(client):
    html = client.get("/pages").text
    assert 'id="index"' in html
    assert "The index is showing." in html
    assert "hidden" not in html


def test_post_pages_is_not_allowed(client):
    response = client.post("/pages")
    assert response.status_code == 405


def test_query_note_id_stays_on_the_empty_index(client):
    response = client.get("/pages", params={"note_id": "4"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "No note id has been entered." in html
    assert "The index is showing." in html
    assert "value=" not in _note_id_tag(html)
    assert 'value="4"' not in html
