"""GET /console/agents and GET /console/agents/{agent_id}."""

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.db import load_console
from app.ui.console import (
    card,
    console_page,
    drawer,
    empty_state,
    error_state,
    loading_state,
    status_dot,
)

router = APIRouter()

_LIST_PATH = "/console/agents"
_ACCENTS = frozenset({"supervisor", "atlas", "vault", "pixel", "probe", "scribe", "reviewer"})
_FIELDS = (
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
_LIST_FIELDS = frozenset({"writes", "never", "activity"})


def _snapshot(source: str | None) -> dict:
    payload = load_console(force_seed=source == "seed")
    if not isinstance(payload, dict):
        return {"mode": "seed", "agents": []}
    return payload


def _mode(snapshot: dict) -> str:
    mode = snapshot.get("mode")
    if mode in ("live", "seed"):
        return mode
    return "seed"


def _agents(snapshot: dict) -> list[dict]:
    raw = snapshot.get("agents")
    if not isinstance(raw, list):
        return []
    agents: list[dict] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            agents.append(item)
    return agents


def _page(title: str, body: str, mode: str, path: str, status_code: int = 200) -> HTMLResponse:
    html = console_page(title=title, active="agents", mode=mode, path=path, body=body)
    return HTMLResponse(html, status_code=status_code)


def _ticket(value: object) -> str:
    if value is None:
        return "None"
    return str(value)


def _rounds(value: object) -> str:
    if value is None:
        return "n/a"
    return str(value)


def _items(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "<p>None</p>"
    rows = "".join("<li>" + escape(str(item)) + "</li>" for item in values)
    return "<ul>" + rows + "</ul>"


def _stats(agent: dict) -> str:
    rows = (
        ("Tickets done", agent.get("tickets_done")),
        ("PRs opened", agent.get("prs_opened")),
        ("Average review rounds", _rounds(agent.get("avg_review_rounds"))),
        ("Needs-human", agent.get("needs_human_count")),
    )
    lines = ["<li>" + escape(label) + ": " + escape(str(value)) + "</li>" for label, value in rows]
    return "<ul>" + "".join(lines) + "</ul>"


def _identify(markup: str, agent_id: str) -> str:
    safe_id = escape(agent_id, quote=True)
    style = ""
    if agent_id in _ACCENTS:
        style = f' style="border-left:4px solid var(--accent-{agent_id})"'
    # card() takes no id. The roster contract needs id="agent-<slug>" on the card.
    opener = '<a class="card"'
    if markup.startswith(opener):
        return f'<a id="agent-{safe_id}" class="card"{style}' + markup[len(opener) :]
    return f'<div id="agent-{safe_id}">{markup}</div>'


def _agent_card(agent: dict) -> str:
    agent_id = str(agent["id"])
    body = (
        "<p>" + escape(str(agent.get("summary") or "")) + "</p>"
        "<h3>Write fence</h3>"
        + _items(agent.get("writes"))
        + "<h3>Never</h3>"
        + _items(agent.get("never"))
        + "<p>Current ticket: "
        + escape(_ticket(agent.get("current_ticket")))
        + "</p>"
        + status_dot(str(agent.get("status") or ""))
        + _stats(agent)
    )
    href = f"{_LIST_PATH}/{agent_id}"
    return _identify(card(str(agent.get("role") or agent_id), body, href), agent_id)


def _roster(agents: list[dict]) -> str:
    return "\n".join(_agent_card(agent) for agent in agents)


def _field_value(agent: dict, field: str) -> str:
    value = agent.get(field)
    if field == "status":
        return status_dot(str(value or ""))
    if field in _LIST_FIELDS:
        return _items(value)
    if field == "current_ticket":
        return escape(_ticket(value))
    if field == "avg_review_rounds":
        return escape(_rounds(value))
    if value is None:
        return ""
    return escape(str(value))


def _drawer_body(agent: dict) -> str:
    rows = [
        "<dt>" + escape(field) + "</dt><dd>" + _field_value(agent, field) + "</dd>"
        for field in _FIELDS
    ]
    return (
        "<dl>" + "".join(rows) + "</dl>"
        "<h3>Write fence</h3>"
        + _items(agent.get("writes"))
        + "<h3>Never</h3>"
        + _items(agent.get("never"))
    )


def _find(agents: list[dict], agent_id: str) -> dict | None:
    for agent in agents:
        if agent.get("id") == agent_id:
            return agent
    return None


@router.get(_LIST_PATH, response_class=HTMLResponse)
def list_agents(state: str | None = None, source: str | None = None) -> HTMLResponse:
    snapshot = _snapshot(source)
    mode = _mode(snapshot)
    if state == "loading":
        body = loading_state("Loading agents.")
    elif state == "empty":
        body = empty_state("No agents to show.")
    elif state == "error":
        body = error_state("Agents could not be loaded.")
    else:
        body = _roster(_agents(snapshot))
    return _page("Agents", body, mode, _LIST_PATH)


@router.get("/console/agents/{agent_id}", response_class=HTMLResponse)
def agent_detail(agent_id: str, source: str | None = None) -> HTMLResponse:
    snapshot = _snapshot(source)
    mode = _mode(snapshot)
    path = f"{_LIST_PATH}/{agent_id}"
    agent = _find(_agents(snapshot), agent_id)
    if agent is None:
        return _page("Agent", error_state("No such agent."), mode, path, status_code=404)
    title = str(agent.get("role") or agent_id)
    body = _roster(_agents(snapshot)) + drawer(title, _drawer_body(agent), open=True)
    return _page(title, body, mode, path)
