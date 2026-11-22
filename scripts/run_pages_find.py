from scripts.feature_run import serve, show


def main() -> None:
    with serve() as client:
        show(client.get("/pages/find"))
        created = show(client.post("/notes", json={"title": "Groceries", "body": "milk, eggs"}))
        show(client.get(f"/notes/{created.json()['id']}"))
        show(client.get("/notes/9999"))


if __name__ == "__main__":
    main()
