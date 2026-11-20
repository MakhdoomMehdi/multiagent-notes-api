"""Helper for per-feature run scripts (scripts/run_<feature>.py).

Starts the real app with uvicorn on a free port against a throwaway database, then lets the
script call endpoints and print each request and response. The printed output is what builders
paste into the "Feature run" section of their pull request.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def serve() -> Iterator[httpx.Client]:
    port = _free_port()
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "NOTES_DB_PATH": os.path.join(tmp, "run.db")}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    httpx.get(f"{base}/openapi.json", timeout=0.5)
                    break
                except httpx.TransportError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("server did not start")
            with httpx.Client(base_url=base, timeout=5) as client:
                yield client
        finally:
            proc.terminate()
            proc.wait(timeout=10)


def show(response: httpx.Response) -> httpx.Response:
    request = response.request
    print(f"> {request.method} {request.url.raw_path.decode()}")
    if request.content:
        print(f"> {request.content.decode()}")
    try:
        body = json.dumps(response.json(), indent=2)
    except ValueError:
        body = response.text
    print(f"< {response.status_code}\n{body}\n")
    return response
