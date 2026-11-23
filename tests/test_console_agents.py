"""GET /console/agents roster and GET /console/agents/{agent_id} drawer."""

from html import escape

import pytest

from app import db

AGENT_IDS = (
    "supervisor",
    "atlas",
    "vault",
    "pixel",
    "probe",
    "scribe",
    "reviewer",
)
FIELDS = (
    "id",
    "role",
    "summary",
    "writes",
    "never",
    "status",
    "current_ticket",
    "tickets_done",
    "prs_opened",
    "avg_review_rounds",
    "needs_human_count",
    "activity",
)


@pytest.fixture(autouse=True)
def seed_console(monkeypatch):
    monkeypatch.setenv("CONSOLE_SOURCE", "seed")
    db.clear_console_cache()
    yield
    db.clear_console_cache()


def _rounds(value: float | None) -> str:
    if value is None:
        return "n/a"
    return str(value)


def _ticket(value: int | None) -> str:
    if value is None:
        return "None"
    return str(value)


def _card_html(page: str, agent_id: str) -> str:
    marker = f'id="agent-{agent_id}"'
    start = page.index(marker)
    rest = page[start:]
    end = len(rest)
    for token in ('id="agent-', 'id="detail-drawer"'):
        found = rest.find(token, len(marker))
        if found != -1:
            end = min(end, found)
    return rest[:end]


def _seed_agents() -> list[dict]:
    payload = db.load_console(force_seed=True)
    return payload["agents"]


def test_list_has_seven_cards_with_roster_fields(client):
    response = client.get("/console/agents")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    page = response.text
    assert page.startswith("<!DOCTYPE html>")
    assert 'href="/console/agents" aria-current="page"' in page
    assert 'id="source-badge" data-mode="seed" href="/console/agents"' in page
    assert page.count('class="card"') == 7

    agents = _seed_agents()
    assert [agent["id"] for agent in agents] == list(AGENT_IDS)
    for agent in agents:
        card = _card_html(page, agent["id"])
        assert f'href="/console/agents/{agent["id"]}"' in card
        assert escape(agent["role"]) in card
        assert escape(agent["summary"]) in card
        assert "Write fence" in card
        assert "Never" in card
        for path in agent["writes"]:
            assert escape(path) in card
        for path in agent["never"]:
            assert escape(path) in card
        assert f"Current ticket: {_ticket(agent['current_ticket'])}" in card
        assert f'data-status="{agent["status"]}"' in card
        assert f"Tickets done: {agent['tickets_done']}" in card
        assert f"PRs opened: {agent['prs_opened']}" in card
        assert f"Average review rounds: {_rounds(agent['avg_review_rounds'])}" in card
        assert f"Needs-human: {agent['needs_human_count']}" in card
        assert f"var(--accent-{agent['id']})" in card


def test_atlas_drawer_lists_every_field(client):
    response = client.get("/console/agents/atlas")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    page = response.text
    assert 'id="detail-drawer"' in page
    assert 'data-open="true"' in page
    drawer = page[page.index('id="detail-drawer"') :]
    agent = next(item for item in _seed_agents() if item["id"] == "atlas")
    for field in FIELDS:
        assert f"<dt>{field}</dt>" in drawer
    assert escape(agent["summary"]) in drawer
    assert "Write fence" in drawer
    assert "Never" in drawer
    for path in agent["writes"]:
        assert escape(path) in drawer
    for path in agent["never"]:
        assert escape(path) in drawer
    for line in agent["activity"]:
        assert f"<li>{escape(line)}</li>" in drawer
    assert "<dd>201</dd>" in drawer
    assert "<dd>1.33</dd>" in drawer
    assert 'data-status="needs-human"' in drawer
    assert 'href="/console/agents/atlas" aria-current="page"' in page or (
        'href="/console/agents" aria-current="page"' in page
    )


def test_unknown_agent_is_html_404(client):
    response = client.get("/console/agents/no-such")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    page = response.text
    assert page.startswith("<!DOCTYPE html>")
    assert 'id="app-nav"' in page
    assert 'id="error-state"' in page
    assert "No such agent." in page
    assert not page.lstrip().startswith("{")
    assert 'class="card"' not in page
    for agent_id in AGENT_IDS:
        assert f'id="agent-{agent_id}"' not in page


def test_empty_state_omits_cards(client):
    response = client.get("/console/agents", params={"state": "empty"})
    assert response.status_code == 200
    page = response.text
    assert 'id="empty-state"' in page
    assert 'class="card"' not in page
    assert 'id="loading-state"' not in page
    assert 'id="error-state"' not in page
    for agent_id in AGENT_IDS:
        assert f'id="agent-{agent_id}"' not in page


def test_loading_and_error_states_omit_cards(client):
    loading = client.get("/console/agents", params={"state": "loading"})
    assert loading.status_code == 200
    assert 'id="loading-state"' in loading.text
    assert 'class="card"' not in loading.text
    for agent_id in AGENT_IDS:
        assert f'id="agent-{agent_id}"' not in loading.text

    error = client.get("/console/agents", params={"state": "error"})
    assert error.status_code == 200
    assert 'id="error-state"' in error.text
    assert 'class="card"' not in error.text
    for agent_id in AGENT_IDS:
        assert f'id="agent-{agent_id}"' not in error.text


def test_source_query_forces_seed_without_github(client, monkeypatch):
    monkeypatch.delenv("CONSOLE_SOURCE", raising=False)

    def boom(args):
        raise AssertionError(args)

    monkeypatch.setattr(db, "_default_runner", boom)
    db.clear_console_cache()
    response = client.get("/console/agents", params={"source": "seed"})
    assert response.status_code == 200
    page = response.text
    assert 'data-mode="seed"' in page
    assert page.count('class="card"') == 7
    assert 'id="agent-atlas"' in page


def test_agent_id_stays_a_string_slug(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/console/agents/{agent_id}"]["get"]
    parameters = [item for item in operation["parameters"] if item["name"] == "agent_id"]
    assert len(parameters) == 1
    assert parameters[0]["schema"]["type"] == "string"
    assert client.get("/console/agents/atlas").status_code == 200


def test_card_text_is_escaped(client, monkeypatch):
    original = db.load_console

    def poisoned(**kwargs):
        payload = original(force_seed=True)
        payload["agents"][1]["summary"] = '<script>alert("x")</script>'
        payload["agents"][1]["writes"] = ["<fence>"]
        return payload

    monkeypatch.setattr("app.features.console_agents.router.load_console", poisoned)
    response = client.get("/console/agents")
    assert response.status_code == 200
    page = response.text
    assert "<script>alert" not in page
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in page
    assert "&lt;fence&gt;" in page


def test_broken_snapshot_stays_html(client, monkeypatch):
    monkeypatch.setattr(
        "app.features.console_agents.router.load_console",
        lambda **kwargs: {"mode": "seed"},
    )
    response = client.get("/console/agents")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'class="card"' not in response.text
    assert page_is_html(response.text)


def page_is_html(page: str) -> bool:
    return page.startswith("<!DOCTYPE html>") and 'id="app-nav"' in page
