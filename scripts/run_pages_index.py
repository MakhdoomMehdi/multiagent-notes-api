from scripts.feature_run import serve, show


def main() -> None:
    with serve() as client:
        show(client.get("/pages"))
        show(client.post("/pages"))
        show(client.get("/pages", params={"note_id": "4"}))


if __name__ == "__main__":
    main()
