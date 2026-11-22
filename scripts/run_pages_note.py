from scripts.feature_run import serve, show


def main() -> None:
    with serve() as client:
        created = show(client.post("/notes", json={"title": "Groceries", "body": "milk, eggs"}))
        note_id = created.json()["id"]
        show(client.get(f"/pages/notes/{note_id}"))
        show(client.get(f"/notes/{note_id}"))
        show(client.get("/notes/9999"))
        show(client.get("/pages/notes/9999"))


if __name__ == "__main__":
    main()
