import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import create_app


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTES_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def make_note():
    """Insert a note directly, so a feature's tests don't depend on another feature's endpoints."""

    def _make(title: str = "Note", body: str = "", tags: tuple[str, ...] = ()) -> int:
        with db.connect() as conn:
            note_id = conn.execute(
                "INSERT INTO notes (title, body) VALUES (?, ?)", (title, body)
            ).lastrowid
            conn.executemany(
                "INSERT INTO note_tags (note_id, tag) VALUES (?, ?)",
                [(note_id, t) for t in tags],
            )
        return note_id

    return _make
