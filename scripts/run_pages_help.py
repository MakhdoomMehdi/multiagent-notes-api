from scripts.feature_run import serve, show


def main() -> None:
    with serve() as client:
        show(client.get("/pages/help"))


if __name__ == "__main__":
    main()
