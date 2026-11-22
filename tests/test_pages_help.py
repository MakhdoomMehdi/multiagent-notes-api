def test_get_pages_help_returns_html(client):
    response = client.get("/pages/help")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()


def test_help_page_states_notes_endpoints_and_status_codes(client):
    text = client.get("/pages/help").text
    assert "POST /notes" in text
    assert "GET /notes/{note_id}" in text
    assert "201" in text
    assert "422" in text
    assert "404" in text


def test_help_page_states_the_other_four_paths(client):
    text = client.get("/pages/help").text
    assert "/pages" in text
    assert "/pages/new" in text
    assert "/pages/notes/{note_id}" in text
    assert "/pages/find" in text


def test_post_pages_help_returns_405(client):
    response = client.post("/pages/help")
    assert response.status_code == 405


def test_delete_pages_help_returns_405(client):
    response = client.delete("/pages/help")
    assert response.status_code == 405
