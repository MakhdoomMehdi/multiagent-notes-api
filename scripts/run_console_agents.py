"""Exercise the agent roster, the Atlas drawer, the unknown id, and the empty state."""

import os

from scripts.feature_run import serve, show


def main() -> None:
    os.environ["CONSOLE_SOURCE"] = "seed"
    with serve() as client:
        show(client.get("/console/agents"))
        show(client.get("/console/agents/atlas"))
        show(client.get("/console/agents/no-such"))
        show(client.get("/console/agents", params={"state": "empty"}))
        show(client.get("/console/agents", params={"state": "loading"}))
        show(client.get("/console/agents", params={"state": "error"}))
        show(client.get("/console/agents", params={"source": "seed"}))


if __name__ == "__main__":
    main()
