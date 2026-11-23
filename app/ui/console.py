"""Harness Console chrome: dark layout, navigation, and shared elements.

Callers pass HTML they already built as ``body``. This module escapes titles,
messages, and attribute values only.
"""

from html import escape

ACCENTS = {
    "supervisor": "#7aa2ff",
    "atlas": "#2ec4b6",
    "vault": "#e6b325",
    "pixel": "#e879f9",
    "probe": "#fb923c",
    "scribe": "#a3e635",
    "reviewer": "#f87171",
}

NAV = (
    ("overview", "Overview", "/console"),
    ("chat", "Chat", "/console/chat"),
    ("agents", "Agents", "/console/agents"),
    ("pipeline", "Pipeline", "/console/pipeline"),
    ("merge", "Merge Gate", "/console/merge"),
    ("adrs", "ADRs", "/console/adrs"),
    ("strains", "Strains", "/console/strains"),
)

_KNOWN_STATUS = ("idle", "working", "blocked", "needs-human")

_STYLE_TEMPLATE = """
:root {
__ACCENTS__
  --bg: #12141a;
  --text: #e7e9ee;
  --muted: #9aa3b2;
  --card: #1c2030;
  --border: #2a3142;
  color-scheme: dark;
}
*, *::before, *::after { box-sizing: border-box; }
html { height: 100%; font-size: 18px; }
body {
  margin: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
  color: var(--text);
  font-family: "Segoe UI", "Source Sans 3", sans-serif;
  line-height: 1.5;
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  background: var(--card);
  border-bottom: 1px solid var(--border);
}
header h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
}
a {
  transition: color 160ms ease, background-color 160ms ease,
    border-color 160ms ease;
}
a:focus, .card:focus, .drawer:focus,
a:focus-visible, .card:focus-visible, .drawer:focus-visible {
  outline: 3px solid var(--accent-supervisor);
  outline-offset: 2px;
}
header a { color: var(--text); text-decoration: none; }
#source-badge {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 12px;
  color: var(--muted);
}
#source-badge[data-mode="live"] { color: var(--accent-scribe); }
.layout {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: stretch;
}
#app-nav {
  position: sticky;
  top: 0;
  width: 240px;
  flex: 0 0 240px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: auto;
  padding: 16px;
  background: var(--card);
  border-right: 1px solid var(--border);
}
#app-nav a {
  color: var(--text);
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 8px;
}
#app-nav a[aria-current="page"] {
  background: var(--border);
  box-shadow: inset 3px 0 0 var(--accent-supervisor);
}
main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}
main a:not(.card) { color: var(--accent-supervisor); }
.card {
  display: block;
  margin: 0;
  padding: 16px;
  background: var(--card);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 12px;
  text-decoration: none;
  transition: border-color 160ms ease, transform 160ms ease;
}
a.card:hover, a.card:focus-visible {
  border-color: var(--accent-supervisor);
}
.card h2, .drawer h2 { margin: 0 0 8px; font-size: 1.15rem; }
.badge {
  display: inline-block;
  margin-inline-end: 0.35rem;
  padding: 2px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--bg);
  color: var(--text);
  font-size: 1rem;
}
.badge[data-kind="pass"] { color: var(--accent-scribe); }
.badge[data-kind="fail"] { color: var(--accent-reviewer); }
.badge[data-kind="pending"] { color: var(--accent-vault); }
.badge[data-kind="missing"] { color: var(--muted); }
.status-dot {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-inline-end: 0.4rem;
}
.status-dot::before {
  content: "";
  width: 0.65em;
  height: 0.65em;
  border-radius: 50%;
  background: currentColor;
  flex: none;
}
.status-dot[data-status="idle"] { color: var(--muted); }
.status-dot[data-status="working"] { color: var(--accent-atlas); }
.status-dot[data-status="blocked"] { color: var(--accent-vault); }
.status-dot[data-status="needs-human"] { color: var(--accent-reviewer); }
#empty-state, #loading-state { color: var(--muted); margin: 0; }
#error-state { color: var(--accent-reviewer); margin: 0; }
.drawer {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 20;
  width: min(28rem, 100%);
  height: 100%;
  margin: 0;
  padding: 20px;
  overflow: auto;
  background: var(--card);
  color: var(--text);
  border-left: 1px solid var(--border);
  transform: translateX(100%);
  transition: transform 180ms ease;
}
.drawer[data-open="true"] { transform: translateX(0); }
[data-role="supervisor"] { color: var(--accent-supervisor); }
[data-role="atlas"] { color: var(--accent-atlas); }
[data-role="vault"] { color: var(--accent-vault); }
[data-role="pixel"] { color: var(--accent-pixel); }
[data-role="probe"] { color: var(--accent-probe); }
[data-role="scribe"] { color: var(--accent-scribe); }
[data-role="reviewer"] { color: var(--accent-reviewer); }
@media (max-width: 800px) {
  .layout { flex-direction: column; }
  #app-nav {
    position: static;
    width: auto;
    flex: 0 0 auto;
    flex-direction: row;
    flex-wrap: wrap;
    overflow: visible;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
}
@media (prefers-reduced-motion: reduce) {
  a, .card, .drawer { transition: none; }
}
"""


def _styles() -> str:
    accents = "\n".join(f"  --accent-{role}: {color};" for role, color in ACCENTS.items())
    return _STYLE_TEMPLATE.replace("__ACCENTS__", accents).strip()


def _source_badge(mode: str, path: str) -> str:
    if mode == "live":
        href = escape(f"{path}?source=seed", quote=True)
        return '<a id="source-badge" data-mode="live" href="' + href + '">Live</a>'
    href = escape(path, quote=True)
    return '<a id="source-badge" data-mode="seed" href="' + href + '">Offline (seed data)</a>'


def _nav(active: str) -> str:
    items: list[str] = []
    for key, label, href in NAV:
        current = ' aria-current="page"' if key == active else ""
        items.append(
            '<a href="' + escape(href, quote=True) + '"' + current + ">" + escape(label) + "</a>"
        )
    return '<nav id="app-nav" aria-label="Harness Console">\n' + "\n".join(items) + "\n</nav>"


def console_page(*, title: str, active: str, mode: str, path: str, body: str) -> str:
    safe_title = escape(title)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + safe_title + " · Harness Console</title>\n"
        "<style>\n" + _styles() + "\n</style>\n"
        "</head>\n"
        "<body>\n"
        "<header>\n"
        '<h1><a href="/console">Harness Console</a></h1>\n'
        + _source_badge(mode, path)
        + "\n</header>\n"
        '<div class="layout">\n' + _nav(active) + "\n<main>\n" + body + "\n</main>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def status_dot(status: str) -> str:
    if status in _KNOWN_STATUS:
        token = status
        word = status
    else:
        token = "idle"
        word = "unknown"
    return (
        '<span class="status-dot" data-status="'
        + escape(token, quote=True)
        + '">'
        + escape(word)
        + "</span>"
    )


def card(title: str, body: str, href: str | None = None) -> str:
    heading = "<h2>" + escape(title) + "</h2>"
    if href is None:
        return '<section class="card">' + heading + body + "</section>"
    return '<a class="card" href="' + escape(href, quote=True) + '">' + heading + body + "</a>"


def badge(text: str, kind: str = "neutral") -> str:
    return (
        '<span class="badge" data-kind="'
        + escape(kind, quote=True)
        + '">'
        + escape(text)
        + "</span>"
    )


def empty_state(message: str) -> str:
    return '<p id="empty-state">' + escape(message) + "</p>"


def error_state(message: str) -> str:
    return '<p id="error-state" role="alert">' + escape(message) + "</p>"


def loading_state(message: str) -> str:
    return '<p id="loading-state" role="status">' + escape(message) + "</p>"


def drawer(title: str, body: str, *, open: bool = False) -> str:
    flag = "true" if open else "false"
    return (
        '<aside id="detail-drawer" class="drawer" data-open="'
        + flag
        + '"><h2>'
        + escape(title)
        + "</h2>"
        + body
        + "</aside>"
    )
