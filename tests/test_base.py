from app import db


def test_app_starts_and_serves_openapi(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Multi-agent Notes API"


def test_make_note_fixture_writes_note_and_tags(make_note):
    note_id = make_note("Hello", tags=("a", "b"))
    with db.connect() as conn:
        assert (
            conn.execute("SELECT title FROM notes WHERE id = ?", (note_id,)).fetchone()[0]
            == "Hello"
        )
        tags = {
            r[0] for r in conn.execute("SELECT tag FROM note_tags WHERE note_id = ?", (note_id,))
        }
    assert tags == {"a", "b"}
