from fastapi import APIRouter, HTTPException, status

from app import db
from app.models import Note, NoteIn

router = APIRouter()


def _load_note(conn, note_id: int) -> Note | None:
    row = conn.execute(
        "SELECT id, title, body, created_at FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if row is None:
        return None
    tags = [
        r["tag"]
        for r in conn.execute(
            "SELECT tag FROM note_tags WHERE note_id = ? ORDER BY tag", (note_id,)
        )
    ]
    return Note(**dict(row), tags=tags)


@router.post("/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
def create_note(note: NoteIn) -> Note:
    with db.connect() as conn:
        note_id = conn.execute(
            "INSERT INTO notes (title, body) VALUES (?, ?)", (note.title, note.body)
        ).lastrowid
        return _load_note(conn, note_id)


@router.get("/notes/{note_id:int}", response_model=Note)
def get_note(note_id: int) -> Note:
    with db.connect() as conn:
        note = _load_note(conn, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note
