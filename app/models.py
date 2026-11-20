"""Shared API models. Owned by the base; feature-specific models live in the feature folder."""

from pydantic import BaseModel, Field


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = ""


class Note(NoteIn):
    id: int
    created_at: str
    tags: list[str] = []
