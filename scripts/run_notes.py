from scripts.feature_run import serve, show


def main() -> None:
    with serve() as client:
        created = show(client.post("/notes", json={"title": "Groceries", "body": "milk, eggs"}))
        show(client.post("/notes", json={"title": "", "body": "empty title"}))
        show(client.post("/notes", json={"body": "missing title"}))
        show(client.get(f"/notes/{created.json()['id']}"))
        show(client.get("/notes/9999"))


if __name__ == "__main__":
    main()
