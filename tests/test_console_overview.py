"""GET /console renders the harness landing page from the console snapshot."""

from html import escape

import pytest

from app.db import load_console

TILE_IDS = (
    "stat-open-issues",
    "stat-open-prs",
    "stat-merged-today",
    "stat-avg-rounds",
    "stat-ci-pass",
    "stat-needs-human",
)

TILE_LABELS = (
    "Open issues",
    "Open PRs",
    "Merged today",
    "Average review rounds",
    "CI pass rate",
    "Needs human",
)


@pytest.fixture(autouse=True)
def seed_console(monkeypatch):
    monkeypatch.setenv("CONSOLE_SOURCE", "seed")


def _payload() -> dict:
    return {
        "mode": "seed",
        "stats": {
            "open_issues": 4,
            "open_prs": 2,
            "merged_today": 1,
            "avg_review_rounds": 1.5,
            "ci_pass_rate": 0.92,
            "needs_human": 0,
        },
        "events": [
            {"actor": "PR", "text": "older item", "at": "2026-11-20T00:00:00Z"},
            {"actor": "Issue", "text": "newer <script>", "at": "2026-11-22T00:00:00Z"},
        ],
        "merges_by_day": [
            {"date": "2026-11-17", "count": 0},
            {"date": "2026-11-18", "count": 1},
            {"date": "2026-11-19", "count": 0},
            {"date": "2026-11-20", "count": 2},
            {"date": "2026-11-21", "count": 0},
            {"date": "2026-11-22", "count": 0},
            {"date": "2026-11-23", "count": 3},
        ],
    }


def _install(monkeypatch, payload):
    def fake_load(*, force_seed: bool = False, runner=None):
        fake_load.calls.append(force_seed)
        return payload

    fake_load.calls = []
    monkeypatch.setattr("app.features.console_overview.router.load_console", fake_load)
    return fake_load


def _tile_value(html: str, element_id: str) -> str:
    start = html.index(f'id="{element_id}"')
    open_p = html.index("<p>", start)
    close_p = html.index("</p>", open_p)
    return html[open_p + 3 : close_p]


def _expected_average(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".") or "0"
    return str(value)


def _expected_rate(value) -> str:
    if value is None:
        return "n/a"
    return f"{round(value * 100)}%"


def test_seed_overview_renders_tiles_timeline_and_chart(client):
    snapshot = load_console(force_seed=True)
    response = client.get("/console")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "<title>Overview · Harness Console</title>" in html
    assert '<a href="/console" aria-current="page">Overview</a>' in html
    assert 'id="source-badge" data-mode="seed" href="/console">Offline (seed data)</a>' in html
    for element_id, label in zip(TILE_IDS, TILE_LABELS, strict=True):
        assert f'id="{element_id}"' in html
        assert f"<h2>{label}</h2>" in html
    stats = snapshot["stats"]
    assert _tile_value(html, "stat-open-issues") == str(stats["open_issues"])
    assert _tile_value(html, "stat-open-prs") == str(stats["open_prs"])
    assert _tile_value(html, "stat-merged-today") == str(stats["merged_today"])
    assert _tile_value(html, "stat-avg-rounds") == _expected_average(stats["avg_review_rounds"])
    assert _tile_value(html, "stat-ci-pass") == _expected_rate(stats["ci_pass_rate"])
    assert _tile_value(html, "stat-needs-human") == str(stats["needs_human"])
    events = sorted(snapshot["events"], key=lambda event: event["at"], reverse=True)
    assert events
    start = html.index('<ol id="activity-timeline">')
    block = html[start : html.index("</ol>", start)]
    found = []
    cursor = 0
    for event in events:
        marker = f'data-at="{escape(event["at"], quote=True)}"'
        found.append(block.index(marker, cursor))
        cursor = found[-1] + 1
        assert escape(event["text"]) in block
        assert escape(event["actor"]) in block
    assert found == sorted(found)
    assert html.count("<tr><td>") == 7
    assert html.count("<rect ") == 7
    assert 'id="merges-chart"' in html
    assert "<th>Date</th><th>Merges</th>" in html
    assert 'id="merges-chart-bars"' in html
    for day in snapshot["merges_by_day"]:
        row = f"<tr><td>{day['date']}</td><td>{day['count']}</td></tr>"
        assert row in html
        assert f"<title>{day['count']}</title>" in html
    assert 'id="loading-state"' not in html
    assert 'id="empty-state"' not in html
    assert 'id="error-state"' not in html


def test_source_seed_forces_the_loader(client, monkeypatch):
    fake_load = _install(monkeypatch, load_console(force_seed=True))
    response = client.get("/console", params={"source": "seed"})
    assert response.status_code == 200
    assert fake_load.calls == [True]
    assert "Offline (seed data)" in response.text
    assert 'data-mode="seed"' in response.text


def test_plain_request_does_not_force_seed(client, monkeypatch):
    fake_load = _install(monkeypatch, load_console(force_seed=True))
    response = client.get("/console")
    assert response.status_code == 200
    assert fake_load.calls == [False]


def test_live_mode_shows_the_live_badge(client, monkeypatch):
    payload = _payload()
    payload["mode"] = "live"
    _install(monkeypatch, payload)
    html = client.get("/console").text
    assert 'id="source-badge" data-mode="live" href="/console?source=seed">Live</a>' in html


def test_null_average_and_ci_rate_render_as_na(client, monkeypatch):
    payload = _payload()
    payload["stats"]["avg_review_rounds"] = None
    payload["stats"]["ci_pass_rate"] = None
    _install(monkeypatch, payload)
    html = client.get("/console").text
    assert _tile_value(html, "stat-avg-rounds") == "n/a"
    assert _tile_value(html, "stat-ci-pass") == "n/a"


def test_ci_pass_rate_renders_as_percent(client, monkeypatch):
    _install(monkeypatch, _payload())
    html = client.get("/console").text
    assert _tile_value(html, "stat-ci-pass") == "92%"
    assert _tile_value(html, "stat-avg-rounds") == "1.5"
    assert _tile_value(html, "stat-open-issues") == "4"


def test_timeline_is_newest_first_and_escaped(client, monkeypatch):
    _install(monkeypatch, _payload())
    html = client.get("/console").text
    start = html.index('<ol id="activity-timeline">')
    block = html[start : html.index("</ol>", start)]
    newer = block.index("newer")
    older = block.index("older item")
    assert newer < older
    assert "&lt;script&gt;" in block
    assert "<script>" not in block


def test_other_state_is_the_success_view(client, monkeypatch):
    _install(monkeypatch, _payload())
    html = client.get("/console", params={"state": "ready"}).text
    assert 'id="stat-open-issues"' in html
    assert 'id="loading-state"' not in html
    assert 'id="empty-state"' not in html
    assert 'id="error-state"' not in html


@pytest.mark.parametrize(
    ("state", "element_id"),
    [("loading", "loading-state"), ("empty", "empty-state"), ("error", "error-state")],
)
def test_state_query_hides_tiles(client, state, element_id):
    response = client.get("/console", params={"state": state})
    assert response.status_code == 200
    html = response.text
    assert f'id="{element_id}"' in html
    for tile_id in TILE_IDS:
        assert f'id="{tile_id}"' not in html
    assert 'id="activity-timeline"' not in html
    assert 'id="merges-chart"' not in html


def test_missing_snapshot_key_renders_error_state(client, monkeypatch):
    _install(monkeypatch, {"mode": "seed"})
    response = client.get("/console")
    assert response.status_code == 200
    html = response.text
    assert 'id="error-state"' in html
    assert 'id="stat-open-issues"' not in html
    assert 'id="activity-timeline"' not in html


def test_notes_and_pages_routes_stay_available(client, make_note):
    note_id = make_note("Kept", "still here")
    note = client.get(f"/notes/{note_id}")
    assert note.status_code == 200
    assert note.json()["title"] == "Kept"
    pages = client.get("/pages")
    assert pages.status_code == 200
    assert 'id="index"' in pages.text
