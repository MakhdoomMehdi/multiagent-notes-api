"""GET /console: stat tiles, activity, and the seven-day merge chart."""

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.db import load_console
from app.ui.console import card, console_page, empty_state, error_state, loading_state

router = APIRouter()

_TILES = (
    ("stat-open-issues", "Open issues", "open_issues", "count"),
    ("stat-open-prs", "Open PRs", "open_prs", "count"),
    ("stat-merged-today", "Merged today", "merged_today", "count"),
    ("stat-avg-rounds", "Average review rounds", "avg_review_rounds", "average"),
    ("stat-ci-pass", "CI pass rate", "ci_pass_rate", "rate"),
    ("stat-needs-human", "Needs human", "needs_human", "count"),
)

_ERROR = "The console overview could not be shown."


def _count(value: object) -> str:
    if type(value) is not int:
        raise TypeError("count")
    return str(value)


def _average(value: object) -> str:
    if value is None:
        return "n/a"
    if type(value) is int:
        return str(value)
    if type(value) is not float:
        raise TypeError("avg_review_rounds")
    rendered = f"{value:.2f}".rstrip("0").rstrip(".")
    return rendered or "0"


def _rate(value: object) -> str:
    if value is None:
        return "n/a"
    if type(value) is not float:
        raise TypeError("ci_pass_rate")
    return f"{round(value * 100)}%"


def _shown(value: object, kind: str) -> str:
    if kind == "average":
        return _average(value)
    if kind == "rate":
        return _rate(value)
    return _count(value)


def _tile(element_id: str, label: str, shown: str) -> str:
    markup = card(label, "<p>" + escape(shown) + "</p>")
    prefix = "<section "
    if not markup.startswith(prefix):
        raise TypeError("card")
    return '<section id="' + escape(element_id, quote=True) + '" ' + markup[len(prefix) :]


def _timeline(events: list) -> str:
    ordered = sorted(events, key=lambda event: event["at"], reverse=True)
    items: list[str] = []
    for event in ordered:
        at_attr = escape(str(event["at"]), quote=True)
        actor = escape(str(event["actor"]))
        text = escape(str(event["text"]))
        items.append(
            f'<li data-at="{at_attr}"><time datetime="{at_attr}">'
            f"{escape(str(event['at']))}</time> {actor}: {text}</li>"
        )
    return '<ol id="activity-timeline">\n' + "\n".join(items) + "\n</ol>"


def _chart(days: list) -> str:
    rows: list[str] = []
    for day in days:
        date = escape(str(day["date"]))
        count = escape(_count(day["count"]))
        rows.append(f"<tr><td>{date}</td><td>{count}</td></tr>")
    table = (
        '<table id="merges-chart">\n'
        "<thead><tr><th>Date</th><th>Merges</th></tr></thead>\n"
        "<tbody>\n" + "\n".join(rows) + "\n</tbody>\n"
        "</table>"
    )
    width = 420
    height = 140
    plot_height = height - 16
    count_days = len(days)
    gap = 8
    bar_width = max((width - gap * (count_days + 1)) // max(count_days, 1), 1)
    peak = max((_count_value(day) for day in days), default=0)
    peak = max(peak, 1)
    rects: list[str] = []
    for index, day in enumerate(days):
        value = _count_value(day)
        bar_height = round(value / peak * (plot_height - 4))
        x = gap + index * (bar_width + gap)
        y = plot_height - bar_height
        date = escape(str(day["date"]), quote=True)
        title = escape(str(value))
        rects.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" '
            f'data-date="{date}"><title>{title}</title></rect>'
        )
    svg = (
        f'<svg id="merges-chart-bars" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="Merges by day">\n' + "\n".join(rects) + "\n</svg>"
    )
    return table + "\n" + svg


def _count_value(day: dict) -> int:
    value = day["count"]
    if type(value) is not int:
        raise TypeError("count")
    return value


def _success(snapshot: dict) -> str:
    stats = snapshot["stats"]
    events = snapshot["events"]
    days = snapshot["merges_by_day"]
    if not isinstance(stats, dict) or not isinstance(events, list) or not isinstance(days, list):
        raise TypeError("snapshot")
    tiles = [
        _tile(element_id, label, _shown(stats[key], kind))
        for element_id, label, key, kind in _TILES
    ]
    return "\n".join(
        [
            *tiles,
            card("Activity", _timeline(events)),
            card("Merges", _chart(days)),
        ]
    )


def _mode(snapshot: object) -> str:
    if isinstance(snapshot, dict) and snapshot.get("mode") == "live":
        return "live"
    return "seed"


def _body(snapshot: object, state: str | None) -> str:
    if state == "loading":
        return loading_state("Loading the console overview.")
    if state == "empty":
        return empty_state("No console activity yet.")
    if state == "error":
        return error_state(_ERROR)
    try:
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot")
        return _success(snapshot)
    except (KeyError, TypeError, ValueError):
        return error_state(_ERROR)


def _page(snapshot: object, state: str | None) -> str:
    return console_page(
        title="Overview",
        active="overview",
        mode=_mode(snapshot),
        path="/console",
        body=_body(snapshot, state),
    )


@router.get("/console", response_class=HTMLResponse)
def console_overview(state: str | None = None, source: str | None = None) -> HTMLResponse:
    snapshot = load_console(force_seed=source == "seed")
    return HTMLResponse(_page(snapshot, state))
