LINKS = (
    'href="/pages"',
    'href="/pages/new"',
    'href="/pages/find"',
    'href="/pages/help"',
    'href="/board"',
    'href="/docs"',
)

PAGES = ("/pages", "/pages/new", "/pages/find", "/pages/help", "/pages/notes/1")


def test_each_notes_page_renders_the_same_sidebar(client):
    for path in PAGES:
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        body = response.text
        assert 'id="app-nav"' in body
        for link in LINKS:
            assert link in body, path
