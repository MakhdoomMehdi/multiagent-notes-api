"""Exercise the console ADR reader against the real server."""

import os

from scripts.feature_run import serve, show


def main() -> None:
    os.environ["CONSOLE_SOURCE"] = "seed"
    with serve() as client:
        show(client.get("/console/adrs"))
        show(client.get("/console/adrs", params={"q": "auto-discovery", "status": "Accepted"}))
        show(client.get("/console/adrs/3"))
        show(client.get("/console/adrs/9999"))


if __name__ == "__main__":
    main()
