import ast
from pathlib import Path


def test_get_pages_new_returns_html(client):
    response = client.get("/pages/new")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_form_has_labeled_required_title_and_labeled_body(client):
    page = client.get("/pages/new").text
    assert '<label for="title">Title</label>' in page
    assert 'id="title"' in page
    assert "required" in page
    assert '<label for="body">Body</label>' in page
    assert 'id="body"' in page


def test_blank_form_is_the_empty_state(client):
    page = client.get("/pages/new").text
    assert 'id="empty-state"' in page
    assert "Blank form" in page
    assert 'id="created" hidden' in page
    assert "value=" not in page


def test_page_posts_notes_and_shows_the_created_note(client):
    page = client.get("/pages/new").text
    assert 'fetch("/notes"' in page
    assert '"POST"' in page
    assert "note.id" in page
    assert "note.title" in page
    assert "note.body" in page
    assert "note.created_at" in page
    assert "note.tags" in page
    assert '"/pages/notes/"' in page


def test_empty_title_stays_on_the_page_and_shows_422_detail(client):
    page = client.get("/pages/new").text
    assert "novalidate" in page
    assert "preventDefault" in page
    assert "422" in page
    assert ".detail" in page
    assert "window.location" not in page


def test_other_failures_stay_on_the_page(client):
    page = client.get("/pages/new").text
    assert "!response.ok" in page
    assert "window.location" not in page


def test_post_pages_new_is_not_allowed(client):
    response = client.post("/pages/new", json={"title": "Nope", "body": ""})
    assert response.status_code == 405


def test_feature_does_not_import_other_features():
    feature = Path(__file__).resolve().parents[1] / "app" / "features" / "pages_new"
    sources = list(feature.rglob("*.py"))
    assert sources
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for name in imported:
                assert not name.startswith("app.features"), name
