from scripts.feature_run import serve, show


def main() -> None:
    with serve() as client:
        show(client.get("/pages/new"))
        show(client.post("/notes", json={"title": "Groceries", "body": "milk, eggs"}))
        show(client.post("/notes", json={"title": "", "body": "empty title"}))


if __name__ == "__main__":
    main()
