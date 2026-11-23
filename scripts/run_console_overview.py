"""Exercise GET /console against the real server with seed data."""

import os

from scripts.feature_run import serve, show


def main() -> None:
    os.environ["CONSOLE_SOURCE"] = "seed"
    with serve() as client:
        show(client.get("/console"))
        show(client.get("/console", params={"source": "seed"}))
        show(client.get("/console", params={"state": "loading"}))
        show(client.get("/console", params={"state": "empty"}))
        show(client.get("/console", params={"state": "error"}))
        show(client.get("/console", params={"state": "other"}))


if __name__ == "__main__":
    main()
