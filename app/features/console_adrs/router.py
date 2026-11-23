"""List and read architecture decisions from docs/adr."""

import os
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.db import load_console
from app.ui.console import console_page, empty_state, error_state, loading_state

router = APIRouter()

_TEMPLATE_NAME = "0000-template.md"
_KEY_NUMBERS = {3, 4, 9}
_KEY_0005 = "0005-specialized-builder-roles.md"
_FILENAME = re.compile(r"^(\d{4})-(.+)\.md$")
_TITLE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_STATUS = re.compile(r"^-\s*Status:\s*(.*?)\s*$", re.IGNORECASE)
_DATE = re.compile(r"^-\s*Date:\s*(.*?)\s*$", re.IGNORECASE)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BULLET = re.compile(r"^[-*]\s+(.+)$")
_NUMBERED = re.compile(r"^\d+\.\s+(.+)$")
_ADR_LINK = re.compile(r"ADR-(\d{4})\b")
_LIST_PATH = "/console/adrs"

_STYLE = """
<style>
.adr-filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; }
.adr-filters label { display: flex; flex-direction: column; gap: 4px; color: var(--muted); }
.adr-filters input, .adr-filters button {
  font: inherit; color: var(--text); background: var(--bg);
  border: 1px solid var(--border); border-radius: 8px; padding: 6px 8px;
}
#adr-list {
  list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px;
}
#adr-list a { color: var(--text); text-decoration: none; font-weight: 600; }
#adr-list li {
  padding: 12px 16px; background: var(--card); border: 1px solid var(--border); border-radius: 12px;
}
#adr-list li.adr-key { box-shadow: inset 3px 0 0 var(--accent-scribe); }
#adr-reader h1, #adr-reader h2, #adr-reader h3 { font-weight: 600; margin: 0 0 8px; }
#adr-reader p, #adr-reader ul, #adr-reader ol { margin: 0 0 12px; }
#adr-reader pre {
  overflow: auto; margin: 0 0 12px; padding: 12px; background: var(--bg); border-radius: 8px;
}
</style>
"""


@dataclass(frozen=True)
class Adr:
    number: int
    slug: str
    filename: str
    title: str
    status: str
    date: str
    body: str


def adr_directory() -> Path | None:
    """Honor CONSOLE_ADR_DIR, then parents of this file, then the working directory."""
    override = os.environ.get("CONSOLE_ADR_DIR")
    if override is not None and override.strip():
        path = Path(override.strip())
        return path if path.is_dir() else None
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "adr"
        if candidate.is_dir():
            return candidate
    candidate = Path.cwd() / "docs" / "adr"
    if candidate.is_dir():
        return candidate
    return None


def _parse_adr(path: Path, number: int, slug: str, body: str) -> Adr:
    title = ""
    status = ""
    recorded = ""
    for line in body.splitlines():
        if not title:
            heading = _TITLE.match(line)
            if heading:
                title = heading.group(1).strip()
        if not status:
            found = _STATUS.match(line)
            if found:
                status = found.group(1).strip()
        if not recorded:
            found = _DATE.match(line)
            if found:
                recorded = found.group(1).strip()
    if not title:
        title = slug.replace("-", " ")
    return Adr(number, slug, path.name, title, status, recorded, body)


def load_adrs(directory: Path) -> list[Adr] | None:
    """Read ADR files. None means the directory could not be listed."""
    try:
        paths = list(directory.iterdir())
    except OSError:
        return None
    found: list[Adr] = []
    for path in paths:
        if not path.is_file() or path.name == _TEMPLATE_NAME:
            continue
        match = _FILENAME.match(path.name)
        if match is None:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found.append(_parse_adr(path, int(match.group(1)), match.group(2), body))
    found.sort(key=lambda adr: (adr.number, adr.filename))
    return found


def _is_key(adr: Adr) -> bool:
    if adr.number in _KEY_NUMBERS:
        return True
    return adr.filename == _KEY_0005


def _matches_query(adr: Adr, query: str) -> bool:
    needle = query.strip().casefold()
    if not needle:
        return True
    return needle in adr.title.casefold() or needle in adr.body.casefold()


def _matches_status(adr: Adr, status: str) -> bool:
    wanted = status.strip().casefold()
    if not wanted:
        return True
    actual = adr.status.strip().casefold()
    if actual == wanted:
        return True
    if not actual.startswith(wanted):
        return False
    return len(actual) == len(wanted) or not actual[len(wanted)].isalnum()


def _link_adrs(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        number = int(match.group(1))
        href = escape(f"/console/adrs/{number}", quote=True)
        return f'<a href="{href}">{match.group(0)}</a>'

    return _ADR_LINK.sub(replace, text)


def _starts_block(line: str) -> bool:
    return (
        line.startswith("```")
        or _HEADING.match(line) is not None
        or _BULLET.match(line) is not None
        or _NUMBERED.match(line) is not None
    )


def _list_block(lines: list[str], index: int) -> tuple[str, int]:
    kind = "ol" if _NUMBERED.match(lines[index]) else "ul"
    matcher = _NUMBERED if kind == "ol" else _BULLET
    items: list[str] = []
    while index < len(lines):
        found = matcher.match(lines[index])
        if found is None:
            break
        item = found.group(1).strip()
        index += 1
        while index < len(lines) and lines[index].startswith((" ", "\t")) and lines[index].strip():
            item = item + " " + lines[index].strip()
            index += 1
        items.append("<li>" + _link_adrs(item) + "</li>")
    return "<" + kind + ">" + "".join(items) + "</" + kind + ">", index


def render_markdown(source: str) -> str:
    """Escape first, then headings, paragraphs, lists, fenced code, and ADR links."""
    text = escape(source, quote=False).replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            blocks.append("<pre><code>" + "\n".join(code) + "</code></pre>")
            continue
        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            blocks.append(f"<h{level}>" + _link_adrs(heading.group(2).strip()) + f"</h{level}>")
            index += 1
            continue
        if _BULLET.match(line) or _NUMBERED.match(line):
            block, index = _list_block(lines, index)
            blocks.append(block)
            continue
        if not line.strip():
            index += 1
            continue
        paragraph = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not _starts_block(lines[index]):
            paragraph.append(lines[index].strip())
            index += 1
        blocks.append("<p>" + _link_adrs(" ".join(paragraph)) + "</p>")
    return "\n".join(blocks)


def _console_mode(source: str | None) -> str:
    try:
        snapshot = load_console(force_seed=source == "seed")
    except Exception:
        return "seed"
    if isinstance(snapshot, dict) and snapshot.get("mode") in {"live", "seed"}:
        return str(snapshot["mode"])
    return "seed"


def _page(title: str, body: str, *, source: str | None, path: str) -> str:
    return console_page(
        title=title,
        active="adrs",
        mode=_console_mode(source),
        path=path,
        body=body,
    )


def _filters(query: str, status: str, source: str | None) -> str:
    hidden = ""
    if source == "seed":
        hidden = '<input type="hidden" name="source" value="seed">'
    return (
        '<form class="adr-filters" method="get" action="/console/adrs">'
        + hidden
        + '<label for="q">Search'
        + '<input id="q" name="q" type="search" value="'
        + escape(query, quote=True)
        + '"></label>'
        + '<label for="status">Status'
        + '<input id="status" name="status" type="text" value="'
        + escape(status, quote=True)
        + '"></label>'
        + '<button type="submit">Filter</button>'
        + "</form>"
    )


def _row(adr: Adr) -> str:
    key = ' class="adr-key"' if _is_key(adr) else ""
    href = escape(f"/console/adrs/{adr.number}", quote=True)
    label = escape(f"ADR-{adr.number:04d}")
    return (
        f"<li{key}>"
        + f'<a href="{href}">{label}</a> '
        + f"<span>{escape(adr.title)}</span> "
        + f"<span>{escape(adr.status)}</span> "
        + f"<span>{escape(adr.date)}</span>"
        + "</li>"
    )


def _list_body(query: str, status: str, source: str | None) -> str:
    directory = adr_directory()
    if directory is None:
        return error_state("The ADR directory is missing.")
    adrs = load_adrs(directory)
    if adrs is None:
        return error_state("The ADR directory could not be read.")
    visible = [adr for adr in adrs if _matches_query(adr, query) and _matches_status(adr, status)]
    if not visible:
        return _STYLE + _filters(query, status, source) + empty_state("No ADRs match.")
    rows = "".join(_row(adr) for adr in visible)
    return _STYLE + _filters(query, status, source) + f'<ul id="adr-list">{rows}</ul>'


@router.get(_LIST_PATH, response_class=HTMLResponse)
def list_adrs(
    q: str | None = None,
    status: str | None = None,
    state: str | None = None,
    source: str | None = None,
) -> HTMLResponse:
    if state == "loading":
        body = loading_state("Loading ADRs.")
    elif state == "error":
        body = error_state("The ADR list could not be loaded.")
    else:
        body = _list_body(q or "", status or "", source)
    return HTMLResponse(_page("ADRs", body, source=source, path=_LIST_PATH))


@router.get("/console/adrs/{number:int}", response_class=HTMLResponse)
def read_adr(number: int, source: str | None = None) -> HTMLResponse:
    path = f"/console/adrs/{number}"
    directory = adr_directory()
    adrs = load_adrs(directory) if directory is not None else None
    if directory is None or adrs is None:
        body = error_state("The ADR directory is missing.")
        return HTMLResponse(_page("ADRs", body, source=source, path=path))
    chosen = next((adr for adr in adrs if adr.number == number), None)
    if chosen is None:
        body = error_state("ADR not found.")
        return HTMLResponse(_page("ADR not found", body, source=source, path=path), status_code=404)
    reader = '<article id="adr-reader">' + render_markdown(chosen.body) + "</article>"
    title = chosen.title or f"ADR-{number:04d}"
    return HTMLResponse(_page(title, reader, source=source, path=path))
