def test_create_note_returns_201_and_note(client):
    response = client.post("/notes", json={"title": "Groceries", "body": "milk, eggs"})
    assert response.status_code == 201
    note = response.json()
    assert isinstance(note["id"], int)
    assert note["title"] == "Groceries"
    assert note["body"] == "milk, eggs"
    assert note["created_at"]
    assert note["tags"] == []


def test_create_note_without_body_defaults_to_empty(client):
    response = client.post("/notes", json={"title": "Only title"})
    assert response.status_code == 201
    assert response.json()["body"] == ""


def test_create_note_with_empty_title_returns_422(client):
    response = client.post("/notes", json={"title": "", "body": "x"})
    assert response.status_code == 422


def test_create_note_with_missing_title_returns_422(client):
    response = client.post("/notes", json={"body": "x"})
    assert response.status_code == 422


def test_get_note_returns_200_with_sorted_tags(client, make_note):
    note_id = make_note("Tagged", body="b", tags=("zeta", "alpha", "mid"))
    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 200
    note = response.json()
    assert note["id"] == note_id
    assert note["title"] == "Tagged"
    assert note["body"] == "b"
    assert note["created_at"]
    assert note["tags"] == ["alpha", "mid", "zeta"]


def test_get_created_note_round_trips(client):
    created = client.post("/notes", json={"title": "Round", "body": "trip"}).json()
    response = client.get(f"/notes/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_note_returns_404(client):
    response = client.get("/notes/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}
