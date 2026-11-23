"""SQLite access shared by every feature. Owned by the base; builders must not edit it."""

import copy
import json
import os
import re
import sqlite3
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta

from app.models import (
    ConsoleAgent,
    ConsoleChip,
    ConsoleDay,
    ConsoleEvent,
    ConsoleIssue,
    ConsoleMessage,
    ConsolePlan,
    ConsolePull,
    ConsoleSnapshot,
    ConsoleStats,
    ConsoleStrain,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag     TEXT    NOT NULL,
    PRIMARY KEY (note_id, tag)
);
"""

# In-memory console snapshot. No console table: nothing to lock, default, or roll back in SQL.
# Rollback is deleting the console models, CONSOLE_SEED, and the loader below.
_REPO = "https://github.com/MakhdoomMehdi/multiagent-notes-api"
_CACHE_SECONDS = 4.0
_ISSUE_ARGS = [
    "issue",
    "list",
    "--state",
    "all",
    "--limit",
    "50",
    "--json",
    "number,title,state,labels,url,body,updatedAt",
]
_PR_ARGS = [
    "pr",
    "list",
    "--state",
    "all",
    "--limit",
    "50",
    "--json",
    "number,title,state,labels,url,body,mergedAt,updatedAt,statusCheckRollup",
]
_FAIL_CONCLUSIONS = {"FAILURE", "CANCELLED", "TIMED_OUT"}
_OK_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
_PASS_ROLLUP = [{"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}]
_FAIL_ROLLUP = [{"name": "ci", "status": "COMPLETED", "conclusion": "FAILURE"}]
_PENDING_ROLLUP = [{"name": "ci", "status": "IN_PROGRESS", "conclusion": ""}]

_CLOSES_RE = re.compile(r"(?i)\bCloses\s+#(\d+)\b")
_TITLE_CLOSES_RE = re.compile(r"\(#(\d+)\)\s*$")
_ROUND_RE = re.compile(r"round:([123])\Z")
_FEATURE_HEADING_RE = re.compile(r"^## Feature run\s*$", re.MULTILINE)
_NEXT_H2_RE = re.compile(r"^## ", re.MULTILINE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE_RE = re.compile(r"^```[A-Za-z0-9_-]*$")

_cache_payload: dict | None = None
_cache_at = 0.0


def db_path() -> str:
    return os.environ.get("NOTES_DB_PATH", "notes.db")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _field(body: str, name: str) -> str | None:
    label = re.escape(name)
    found = re.search(rf"(?im)^{label}:\s*(.+?)\s*$", body)
    if found:
        return found.group(1).strip()
    heading = re.search(rf"(?im)^##\s*{label}\s*\n+\s*(.+?)\s*$", body)
    if heading:
        return heading.group(1).strip()
    return None


def slug_from_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > 40:
        slug = slug[:40].rstrip("-")
    return slug


def _normalize_state(value: object) -> str:
    key = str(value or "").strip().upper()
    return {"OPEN": "open", "CLOSED": "closed", "MERGED": "merged"}.get(key, "closed")


def _label_names(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    names: list[str] = []
    for item in raw:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and item.get("name") is not None:
            names.append(str(item["name"]))
    return names


def _round_of(labels: list[str]) -> int:
    found = 0
    for label in labels:
        match = _ROUND_RE.fullmatch(label.strip())
        if match:
            found = max(found, int(match.group(1)))
    return found


def _feature_run_filled(body: str) -> bool:
    match = _FEATURE_HEADING_RE.search(body or "")
    if not match:
        return False
    section = body[match.end() :]
    nxt = _NEXT_H2_RE.search(section)
    if nxt:
        section = section[: nxt.start()]
    section = _HTML_COMMENT_RE.sub("", section)
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or _FENCE_RE.fullmatch(stripped):
            continue
        return True
    return False


def ci_from_rollup(rollup: object) -> str:
    """Map a gh statusCheckRollup to pass, fail, pending, or missing."""
    if not isinstance(rollup, list):
        return "missing"
    conclusions: list[str] = []
    incomplete = False
    for item in rollup:
        if not isinstance(item, dict):
            incomplete = True
            continue
        conclusion = str(item.get("conclusion") or "").strip().upper()
        status = str(item.get("status") or "").strip().upper()
        if conclusion in _FAIL_CONCLUSIONS:
            conclusions.append(conclusion)
            continue
        if not conclusion or (status and status != "COMPLETED"):
            incomplete = True
            continue
        conclusions.append(conclusion)
    if any(item in _FAIL_CONCLUSIONS for item in conclusions):
        return "fail"
    if incomplete:
        return "pending"
    if all(item in _OK_CONCLUSIONS for item in conclusions):
        return "pass"
    return "fail"


def linked_issue(pull: dict) -> int | None:
    closes = pull.get("closes")
    if isinstance(closes, int) and not isinstance(closes, bool):
        return closes
    match = _CLOSES_RE.search(pull.get("body") or "")
    if match:
        return int(match.group(1))
    title_match = _TITLE_CLOSES_RE.search((pull.get("title") or "").strip())
    if title_match:
        return int(title_match.group(1))
    return None


def _group_pulls(pulls: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for pull in pulls:
        number = linked_issue(pull)
        if number is None:
            continue
        grouped.setdefault(number, []).append(pull)
    return grouped


def _column(issue: dict, linked: list[dict]) -> str:
    labels = set(issue.get("labels") or [])
    open_labels: set[str] = set()
    all_labels: set[str] = set()
    for pull in linked:
        pull_labels = set(pull.get("labels") or [])
        all_labels.update(pull_labels)
        if pull.get("state") == "open":
            open_labels.update(pull_labels)
    if "needs-human" in labels or "needs-human" in open_labels:
        return "needs-human"
    if any(pull.get("state") == "merged" for pull in linked):
        return "merged"
    if "review:approved" in open_labels:
        return "approved"
    if "status:in-review" in labels or "status:in-review" in all_labels:
        return "in-review"
    if "status:in-progress" in labels or "status:blocked" in labels:
        return "in-progress"
    return "planned"


def _preferred_pull(linked: list[dict]) -> dict | None:
    for state in ("open", "merged", "closed"):
        for pull in linked:
            if pull.get("state") == state:
                return pull
    return None


def _on_board(issue: dict, linked: list[dict]) -> bool:
    if issue.get("state") == "open":
        return True
    return any(pull.get("state") == "merged" for pull in linked)


def _rounded_mean(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def merges_by_day(pulls: list[dict], today: date) -> list[dict]:
    """Seven UTC days ending on today, oldest first, with zero days kept."""
    days: list[dict] = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        iso = day.isoformat()
        count = 0
        for pull in pulls:
            if isinstance(pull, dict):
                stamp = pull.get("merged_at") or ""
            else:
                stamp = getattr(pull, "merged_at", None) or ""
            if str(stamp).startswith(iso):
                count += 1
        days.append({"date": iso, "count": count})
    return days


def _pull_model(pull: dict) -> ConsolePull:
    labels = list(pull.get("labels") or [])
    merged_at = pull.get("merged_at")
    return ConsolePull(
        number=int(pull["number"]),
        title=str(pull.get("title") or ""),
        state=pull.get("state") or "closed",
        labels=labels,
        url=str(pull.get("url") or ""),
        body=str(pull.get("body") or ""),
        closes=linked_issue(pull),
        feature_run_filled=_feature_run_filled(str(pull.get("body") or "")),
        ci=ci_from_rollup(pull.get("status_check_rollup")),
        review_approved="review:approved" in labels,
        needs_human="needs-human" in labels,
        round=_round_of(labels),
        merged_at=str(merged_at) if merged_at else None,
        updated_at=str(pull.get("updated_at") or ""),
    )


def _issue_model(issue: dict, linked: list[dict]) -> ConsoleIssue:
    labels = list(issue.get("labels") or [])
    review_round = _round_of(labels)
    for pull in linked:
        review_round = max(review_round, _round_of(list(pull.get("labels") or [])))
    chosen = _preferred_pull(linked)
    ci = ci_from_rollup(chosen.get("status_check_rollup")) if chosen else "missing"
    state = issue.get("state") if issue.get("state") in {"open", "closed"} else "closed"
    return ConsoleIssue(
        number=int(issue["number"]),
        title=str(issue.get("title") or ""),
        state=state,
        labels=labels,
        url=str(issue.get("url") or ""),
        body=str(issue.get("body") or ""),
        specialist=str(issue.get("specialist") or ""),
        wave=int(issue.get("wave") or 0),
        slug=str(issue.get("slug") or ""),
        branch=str(issue.get("branch") or ""),
        column=_column(issue, linked),
        round=review_round,
        ci=ci,
        updated_at=str(issue.get("updated_at") or ""),
    )


def _owns(issue: dict, agent_id: str) -> bool:
    return str(issue.get("specialist") or "").strip().lower() == agent_id


def _reviewer_status(pulls: list[dict]) -> str:
    open_pulls = [pull for pull in pulls if pull.get("state") == "open"]
    if any("needs-human" in (pull.get("labels") or []) for pull in open_pulls):
        return "needs-human"
    for pull in open_pulls:
        labels = list(pull.get("labels") or [])
        if "status:in-review" in labels or _round_of(labels) > 0:
            return "working"
    return "idle"


def _specialist_status(agent_id: str, issues: list[dict], grouped: dict[int, list[dict]]) -> str:
    owned = [issue for issue in issues if _owns(issue, agent_id) and issue.get("state") == "open"]

    def open_pulls(issue: dict) -> list[dict]:
        return [pull for pull in grouped.get(issue["number"], []) if pull.get("state") == "open"]

    for issue in owned:
        labels = list(issue.get("labels") or [])
        if "needs-human" in labels:
            return "needs-human"
        if any("needs-human" in (pull.get("labels") or []) for pull in open_pulls(issue)):
            return "needs-human"
    if any("status:blocked" in (issue.get("labels") or []) for issue in owned):
        return "blocked"
    for issue in owned:
        labels = list(issue.get("labels") or [])
        if "status:in-progress" in labels or "status:in-review" in labels:
            return "working"
    return "idle"


def _reviewer_ticket(pulls: list[ConsolePull], status: str) -> int | None:
    open_pulls = sorted(
        (pull for pull in pulls if pull.state == "open"),
        key=lambda pull: pull.number,
    )
    if status == "needs-human":
        matched = [pull for pull in open_pulls if pull.needs_human]
    elif status == "working":
        matched = [
            pull for pull in open_pulls if "status:in-review" in pull.labels or pull.round > 0
        ]
    else:
        return None
    if not matched:
        return None
    return matched[0].closes


def _activity(agent_id: str, issues: list[dict]) -> list[str]:
    owned = [issue for issue in issues if _owns(issue, agent_id)]
    owned.sort(
        key=lambda issue: (issue.get("updated_at") or "", issue.get("number") or 0),
        reverse=True,
    )
    titles = [str(issue.get("title") or "") for issue in owned[:3]]
    if titles:
        return titles
    if agent_id == "supervisor":
        return ["Planning and merging"]
    if agent_id == "reviewer":
        return ["Waiting for a pull request"]
    return ["No open ticket"]


_AGENT_CATALOG = (
    {
        "id": "supervisor",
        "role": "Supervisor",
        "summary": "Plans, files tickets, dispatches builders, and merges.",
        "writes": ["GitHub Issues, labels, and merges"],
        "never": ["app/", "tests/", "scripts/", "docs/"],
    },
    {
        "id": "atlas",
        "role": "Atlas",
        "summary": "Implements one HTTP feature, including that view's HTML response.",
        "writes": ["app/features/<name>/", "tests/test_<name>.py", "scripts/run_<name>.py"],
        "never": ["app/db.py", "app/models.py", "app/ui/", "another feature"],
    },
    {
        "id": "vault",
        "role": "Vault",
        "summary": "Changes shared models and the seed loader.",
        "writes": ["app/db.py", "app/models.py", "the named schema test"],
        "never": ["route handlers", "app/ui/", "scripts/"],
    },
    {
        "id": "pixel",
        "role": "Pixel",
        "summary": "Builds shared page chrome.",
        "writes": ["app/ui/"],
        "never": ["route handlers", "app/db.py", "app/models.py", ".github/"],
    },
    {
        "id": "probe",
        "role": "Probe",
        "summary": "Adds break tests only.",
        "writes": ["tests/test_<name>_probe.py"],
        "never": ["app/", "scripts/", "docs/"],
    },
    {
        "id": "scribe",
        "role": "Scribe",
        "summary": "Writes ADRs, the README, and the changelog.",
        "writes": ["docs/", "README.md", "CHANGELOG.md"],
        "never": ["app/", "tests/", "scripts/"],
    },
    {
        "id": "reviewer",
        "role": "Reviewer",
        "summary": "Reviews one pull request and sets labels.",
        "writes": ["a review comment and labels"],
        "never": ["files", "commits", "pushes"],
    },
)


def _agents(
    issues: list[dict],
    pulls: list[dict],
    board: list[ConsoleIssue],
    pull_models: list[ConsolePull],
    grouped: dict[int, list[dict]],
) -> list[ConsoleAgent]:
    agents: list[ConsoleAgent] = []
    for spec in _AGENT_CATALOG:
        agent_id = spec["id"]
        if agent_id == "reviewer":
            status = _reviewer_status(pulls)
            current = _reviewer_ticket(pull_models, status)
        else:
            status = _specialist_status(agent_id, issues, grouped)
            open_numbers = sorted(
                int(issue["number"])
                for issue in issues
                if _owns(issue, agent_id) and issue.get("state") == "open"
            )
            current = open_numbers[0] if open_numbers else None
        owned_ids = {int(issue["number"]) for issue in issues if _owns(issue, agent_id)}
        owned_pulls = [pull for pull in pull_models if pull.closes in owned_ids]
        needs_human_count = sum(
            1
            for issue in board
            if issue.state == "open"
            and issue.column == "needs-human"
            and issue.specialist.strip().lower() == agent_id
        )
        agents.append(
            ConsoleAgent(
                id=agent_id,
                role=spec["role"],
                summary=spec["summary"],
                writes=list(spec["writes"]),
                never=list(spec["never"]),
                status=status,
                current_ticket=current,
                tickets_done=sum(
                    1
                    for issue in issues
                    if _owns(issue, agent_id) and issue.get("state") == "closed"
                ),
                prs_opened=len(owned_pulls),
                avg_review_rounds=_rounded_mean(
                    [pull.round for pull in owned_pulls if pull.round > 0]
                ),
                needs_human_count=needs_human_count,
                activity=_activity(agent_id, issues),
            )
        )
    return agents


def _stats(
    issues: list[dict],
    pull_models: list[ConsolePull],
    board: list[ConsoleIssue],
    today: date,
) -> ConsoleStats:
    passed = sum(1 for pull in pull_models if pull.ci == "pass")
    failed = sum(1 for pull in pull_models if pull.ci == "fail")
    today_iso = today.isoformat()
    return ConsoleStats(
        open_issues=sum(1 for issue in issues if issue.get("state") == "open"),
        open_prs=sum(1 for pull in pull_models if pull.state == "open"),
        merged_today=sum(1 for pull in pull_models if (pull.merged_at or "").startswith(today_iso)),
        avg_review_rounds=_rounded_mean([pull.round for pull in pull_models if pull.round > 0]),
        ci_pass_rate=round(passed / (passed + failed), 2) if passed + failed else None,
        needs_human=sum(1 for issue in board if issue.column == "needs-human"),
    )


def _filled_body(issue: int) -> str:
    return f"Closes #{issue}\n\n## Feature run\npytest -q passed\n"


def _empty_comment_body(issue: int) -> str:
    return f"Closes #{issue}\n\n## Feature run\n<!-- empty -->\n"


def _empty_fence_body(issue: int) -> str:
    return f"Closes #{issue}\n\n## Feature run\n```\n```\n"


def _issue_record(
    number: int,
    title: str,
    state: str,
    labels: list[str],
    specialist: str,
    wave: int,
    slug: str,
    branch: str,
    updated_at: str,
    body: str = "",
    url: str | None = None,
) -> dict:
    return {
        "number": number,
        "title": title,
        "state": state,
        "labels": labels,
        "url": url or f"{_REPO}/issues/{number}",
        "body": body,
        "specialist": specialist,
        "wave": wave,
        "slug": slug,
        "branch": branch,
        "updated_at": updated_at,
    }


def _pull_record(
    number: int,
    title: str,
    state: str,
    labels: list[str],
    closes: int,
    body: str,
    merged_at: str | None,
    updated_at: str,
    rollup: list[dict],
) -> dict:
    return {
        "number": number,
        "title": title,
        "state": state,
        "labels": list(labels),
        "url": f"{_REPO}/pull/{number}",
        "body": body,
        "closes": closes,
        "merged_at": merged_at,
        "updated_at": updated_at,
        "status_check_rollup": [dict(item) for item in rollup],
    }


def _plan(title: str, owner: str, branch: str) -> dict:
    return {
        "title": title,
        "owner": owner,
        "branch": branch,
        "status": "planned",
        "issue_url": "",
        "pr_url": "",
    }


def _build_seed() -> dict:
    # issue, pull, merged_at, specialist, wave, slug, branch, title
    merged_rows = (
        (1, 2, "2026-11-20T13:48:25Z", "Atlas", 2, "notes", "ticket/1-notes", "Create a note"),
        (
            3,
            4,
            "2026-11-22T19:44:41Z",
            "Scribe",
            1,
            "notes-frontend",
            "adr/0008-notes-frontend",
            "Notes frontend",
        ),
        (
            5,
            13,
            "2026-11-22T20:21:10Z",
            "Atlas",
            2,
            "pages-index",
            "ticket/5-pages-index",
            "Notes index",
        ),
        (
            6,
            11,
            "2026-11-22T20:34:46Z",
            "Atlas",
            2,
            "pages-new",
            "ticket/6-pages-new",
            "New note page",
        ),
        (
            7,
            14,
            "2026-11-22T20:24:25Z",
            "Atlas",
            2,
            "pages-note",
            "ticket/7-pages-note",
            "Note page",
        ),
        (
            8,
            12,
            "2026-11-22T20:18:31Z",
            "Atlas",
            2,
            "pages-find",
            "ticket/8-pages-find",
            "Find notes",
        ),
        (
            9,
            10,
            "2026-11-22T20:14:59Z",
            "Atlas",
            2,
            "pages-help",
            "ticket/9-pages-help",
            "Notes help",
        ),
        (
            15,
            16,
            "2026-11-23T07:46:04Z",
            "Scribe",
            1,
            "shared-page-chrome",
            "adr/0009-shared-page-chrome",
            "Shared page chrome",
        ),
        (17, 18, "2026-11-23T07:52:12Z", "Pixel", 2, "app-nav", "ticket/17-app-nav", "App nav"),
        (
            19,
            20,
            "2026-11-23T07:57:19Z",
            "Probe",
            3,
            "nav-probe",
            "ticket/19-nav-probe",
            "Nav probe",
        ),
    )
    issues = []
    pulls = []
    for number, pull_number, merged_at, specialist, wave, slug, branch, title in merged_rows:
        labels = ["status:in-progress"] if number == 1 else []
        issues.append(
            _issue_record(
                number, title, "closed", labels, specialist, wave, slug, branch, merged_at
            )
        )
        pulls.append(
            _pull_record(
                pull_number,
                title,
                "merged",
                ["review:approved", "round:1"],
                number,
                _filled_body(number),
                merged_at,
                merged_at,
                _PASS_ROLLUP,
            )
        )

    samples = (
        (
            201,
            "Atlas",
            2,
            "export",
            "ticket/201-export",
            ["status:ready"],
            "Sample: export notes",
            None,
        ),
        (
            202,
            "Atlas",
            2,
            "health",
            "ticket/202-health",
            ["status:in-progress"],
            "Sample: health check",
            None,
        ),
        (
            203,
            "Atlas",
            2,
            "tag-search",
            "ticket/203-tag-search",
            ["status:in-review"],
            "Sample: tag search",
            301,
        ),
        (
            204,
            "Atlas",
            2,
            "share-links",
            "ticket/204-share-links",
            [],
            "Sample: share links",
            302,
        ),
        (
            205,
            "Atlas",
            2,
            "bulk-delete",
            "ticket/205-bulk-delete",
            [],
            "Sample: bulk delete",
            303,
        ),
        (
            206,
            "Probe",
            3,
            "webhook",
            "ticket/206-webhook",
            ["status:in-review"],
            "Sample: webhook",
            304,
        ),
        (
            207,
            "Vault",
            1,
            "seed-schema",
            "ticket/207-seed-schema",
            ["status:blocked"],
            "Sample: seed schema",
            None,
        ),
        (
            208,
            "Scribe",
            3,
            "demo-guide",
            "ticket/208-demo-guide",
            ["status:in-progress"],
            "Sample: demo guide",
            None,
        ),
    )
    sample_pulls = {
        301: (["status:in-review", "round:2"], _filled_body(203), _PENDING_ROLLUP),
        302: (["review:approved", "round:1"], _filled_body(204), _PASS_ROLLUP),
        303: (
            ["needs-human", "round:3", "status:in-review"],
            _empty_comment_body(205),
            _FAIL_ROLLUP,
        ),
        304: (["review:approved", "round:1"], _empty_fence_body(206), _PASS_ROLLUP),
    }
    for index, row in enumerate(samples, start=1):
        number, specialist, wave, slug, branch, labels, title, pull_number = row
        updated_at = f"2026-11-23T10:{index:02d}:00Z"
        issues.append(
            _issue_record(
                number, title, "open", list(labels), specialist, wave, slug, branch, updated_at
            )
        )
        if pull_number is None:
            continue
        pull_labels, body, rollup = sample_pulls[pull_number]
        pulls.append(
            _pull_record(
                pull_number,
                title,
                "open",
                pull_labels,
                number,
                body,
                None,
                updated_at,
                rollup,
            )
        )

    events = [
        {"actor": "PR", "text": f"#{pull_number} {title}", "at": merged_at}
        for _number, pull_number, merged_at, _specialist, _wave, _slug, _branch, title in sorted(
            merged_rows, key=lambda row: row[2], reverse=True
        )
    ]
    notes_message = "I want these features in my app: list notes, tags, and search."
    return {
        "issues": issues,
        "pulls": pulls,
        "events": events,
        "strains": [
            {
                "id": "role-maps",
                "title": "Conflicting role maps",
                "detail": (
                    "ADR-0005 and the harness README still describe Pixel as blocked until a UI "
                    "directory exists, while ADR-0009 and the Pixel prompt say Pixel owns app/ui/."
                ),
                "evidence": [
                    "docs/adr/0005-specialized-builder-roles.md",
                    "docs/harness/README.md",
                    "docs/adr/0009-shared-page-chrome.md",
                    ".cursor/agents/pixel.md",
                ],
                "proposed_fix": (
                    "Restate Pixel's paths in a new ADR and update the harness role table."
                ),
            },
            {
                "id": "agents-unowned",
                "title": "Nobody owns .cursor/agents/.",
                "detail": "Prompt files under .cursor/agents/ have no specialist in ADR-0005.",
                "evidence": [
                    "docs/adr/0005-specialized-builder-roles.md",
                    ".cursor/agents/",
                ],
                "proposed_fix": "Name an owner in an ADR before the next prompt edit.",
            },
            {
                "id": "five-vs-waves",
                "title": "Five tickets at once versus real waves",
                "detail": (
                    "The harness README and the supervisor prompt still describe five tickets "
                    "at once, while the console plan is grouped into waves."
                ),
                "evidence": [
                    "docs/harness/README.md",
                    ".cursor/agents/supervisor.md",
                ],
                "proposed_fix": (
                    "Allow wave planning when the human asks for it, and leave dependents "
                    "unlabelled until the previous wave merges."
                ),
            },
            {
                "id": "board-outside-github",
                "title": "The board lives outside GitHub state",
                "detail": (
                    "ADR-0007 stores the live tree outside GitHub, so a down board must stay "
                    "a warning rather than a second ticket store."
                ),
                "evidence": [
                    "docs/adr/0007-live-harness-tree.md",
                    "scripts/harness_event.py",
                ],
                "proposed_fix": (
                    "Keep GitHub as the source of truth and treat a down board as a warning, "
                    "not a second ticket store."
                ),
            },
        ],
        "chips": [
            {
                "id": "console",
                "label": "Build the Harness Console",
                "message": (
                    "I want these features in my app: a harness console with chat intake, "
                    "an agent roster, a pipeline, a merge gate, an ADR reader, and a strains page."
                ),
            },
            {
                "id": "notes",
                "label": "Notes, tags, and search",
                "message": notes_message,
            },
            {
                "id": "health",
                "label": "Export and health",
                "message": "I want these features in my app: export notes and a health check.",
            },
        ],
        "transcript": [
            {"role": "user", "text": notes_message},
            {"role": "supervisor", "text": "The plan is grouped by wave."},
        ],
        "demo_plan": {
            "summary": "The console work is grouped into three waves.",
            "waves": [
                {
                    "wave": 1,
                    "tickets": [
                        _plan("Harness console ADR", "Scribe", "adr/0010-harness-console"),
                        _plan("Console seed", "Vault", "ticket/pending-console-seed"),
                        _plan("Console chrome", "Pixel", "ticket/pending-console-chrome"),
                    ],
                },
                {
                    "wave": 2,
                    "tickets": [
                        _plan("Console chat", "Atlas", "ticket/pending-console-chat"),
                        _plan("Console agents", "Atlas", "ticket/pending-console-agents"),
                        _plan("Console pipeline", "Atlas", "ticket/pending-console-pipeline"),
                        _plan("Console merge", "Atlas", "ticket/pending-console-merge"),
                        _plan("Console ADRs", "Atlas", "ticket/pending-console-adrs"),
                        _plan("Console strains", "Atlas", "ticket/pending-console-strains"),
                        _plan("Console overview", "Atlas", "ticket/pending-console-overview"),
                    ],
                },
                {
                    "wave": 3,
                    "tickets": [
                        _plan("Console tests", "Probe", "ticket/pending-console-tests"),
                        _plan("Demo guide", "Scribe", "ticket/pending-demo-guide"),
                    ],
                },
            ],
        },
    }


CONSOLE_SEED = _build_seed()


def _seed_events() -> list[ConsoleEvent]:
    events = [
        ConsoleEvent(actor=event["actor"], text=event["text"], at=event["at"])
        for event in CONSOLE_SEED["events"]
    ]
    events.sort(key=lambda event: event.at, reverse=True)
    return events[:12]


def _live_events(issues: list[dict], pulls: list[dict]) -> list[ConsoleEvent]:
    rows: list[tuple[str, int, str, str]] = []
    for issue in issues:
        rows.append(
            (
                str(issue.get("updated_at") or ""),
                int(issue["number"]),
                "Issue",
                f"#{issue['number']} {issue['title']}",
            )
        )
    for pull in pulls:
        rows.append(
            (
                str(pull.get("updated_at") or ""),
                int(pull["number"]),
                "PR",
                f"#{pull['number']} {pull['title']}",
            )
        )
    rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
    if not rows:
        return _seed_events()
    return [
        ConsoleEvent(at=stamp, actor=actor, text=text) for stamp, _number, actor, text in rows[:8]
    ]


def _utc_today() -> date:
    return datetime.now(UTC).date()


def derive_console(
    issues: list[dict],
    pulls: list[dict],
    *,
    mode: str,
    today: date | None = None,
) -> ConsoleSnapshot:
    """Derive columns, rounds, CI, stats, agents, events, and merges for both modes."""
    today = today or _utc_today()
    grouped = _group_pulls(pulls)
    pull_models = [_pull_model(pull) for pull in pulls]
    pull_models.sort(key=lambda pull: pull.number)
    board = [
        _issue_model(issue, grouped.get(int(issue["number"]), []))
        for issue in issues
        if _on_board(issue, grouped.get(int(issue["number"]), []))
    ]
    board.sort(key=lambda issue: issue.number)
    events = _seed_events() if mode == "seed" else _live_events(issues, pulls)
    return ConsoleSnapshot(
        mode=mode,
        issues=board,
        pulls=pull_models,
        agents=_agents(issues, pulls, board, pull_models, grouped),
        events=events,
        merges_by_day=[ConsoleDay.model_validate(day) for day in merges_by_day(pulls, today)],
        stats=_stats(issues, pull_models, board, today),
        strains=[ConsoleStrain.model_validate(item) for item in CONSOLE_SEED["strains"]],
        chips=[ConsoleChip.model_validate(item) for item in CONSOLE_SEED["chips"]],
        transcript=[ConsoleMessage.model_validate(item) for item in CONSOLE_SEED["transcript"]],
        demo_plan=ConsolePlan.model_validate(CONSOLE_SEED["demo_plan"]),
    )


def _from_seed() -> ConsoleSnapshot:
    return derive_console(CONSOLE_SEED["issues"], CONSOLE_SEED["pulls"], mode="seed")


def _slug_and_branch(body: str, number: int, title: str) -> tuple[str, str]:
    slug = slug_from_title(title)
    branch = _field(body, "Branch")
    if not branch:
        branch = f"ticket/{number}-{slug}" if slug else f"ticket/{number}"
    return slug, branch


def _parse_wave(body: str) -> int:
    raw = _field(body, "Wave")
    if raw is None:
        return 0
    token = raw.split()[0]
    return int(token) if token.isdigit() else 0


def _normalize_issue(raw: dict) -> dict:
    number = int(raw["number"])
    title = str(raw.get("title") or "")
    body = str(raw.get("body") or "")
    slug, branch = _slug_and_branch(body, number, title)
    state = _normalize_state(raw.get("state"))
    if state != "open":
        state = "closed"
    return _issue_record(
        number,
        title,
        state,
        _label_names(raw.get("labels")),
        _field(body, "Specialist") or "",
        _parse_wave(body),
        slug,
        branch,
        str(raw.get("updatedAt") or raw.get("updated_at") or ""),
        body=body,
        url=str(raw.get("url") or "") or None,
    )


def _normalize_pull(raw: dict) -> dict:
    body = str(raw.get("body") or "")
    title = str(raw.get("title") or "")
    merged = raw.get("mergedAt", raw.get("merged_at"))
    record = {
        "number": int(raw["number"]),
        "title": title,
        "state": _normalize_state(raw.get("state")),
        "labels": _label_names(raw.get("labels")),
        "url": str(raw.get("url") or ""),
        "body": body,
        "closes": None,
        "merged_at": str(merged) if merged else None,
        "updated_at": str(raw.get("updatedAt") or raw.get("updated_at") or ""),
        "status_check_rollup": raw.get("statusCheckRollup", raw.get("status_check_rollup")),
    }
    record["closes"] = linked_issue(record)
    return record


def _from_live(raw_issues: list, raw_pulls: list) -> ConsoleSnapshot:
    issues = []
    for raw in raw_issues:
        if isinstance(raw, dict) and "number" in raw:
            issues.append(_normalize_issue(raw))
    pulls = []
    for raw in raw_pulls:
        if isinstance(raw, dict) and "number" in raw:
            pulls.append(_normalize_pull(raw))
    return derive_console(issues, pulls, mode="live")


def clear_console_cache() -> None:
    global _cache_payload, _cache_at
    _cache_payload = None
    _cache_at = 0.0


def _read_cache() -> dict | None:
    if _cache_payload is None:
        return None
    if time.monotonic() - _cache_at >= _CACHE_SECONDS:
        return None
    return copy.deepcopy(_cache_payload)


def _write_cache(payload: dict) -> None:
    global _cache_payload, _cache_at
    _cache_payload = copy.deepcopy(payload)
    _cache_at = time.monotonic()


def _default_runner(args: list[str]) -> str:
    completed = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=8,
    )
    if completed.returncode != 0:
        error = completed.stderr or f"gh exited {completed.returncode}"
        raise RuntimeError(error)
    return completed.stdout


def _emergency() -> dict:
    try:
        return derive_console([], [], mode="seed").model_dump()
    except Exception:
        return {"mode": "seed"}


def load_console(
    *,
    force_seed: bool = False,
    runner: Callable[[list[str]], str] | None = None,
) -> dict:
    """Return a console snapshot. A GitHub failure falls back to the seed and does not raise."""
    try:
        if force_seed or os.environ.get("CONSOLE_SOURCE") == "seed":
            return _from_seed().model_dump()
        use_cache = runner is None
        if use_cache:
            cached = _read_cache()
            if cached is not None:
                return cached
        active = _default_runner if runner is None else runner
        try:
            raw_issues = json.loads(active(_ISSUE_ARGS))
            raw_pulls = json.loads(active(_PR_ARGS))
            if not isinstance(raw_issues, list) or not isinstance(raw_pulls, list):
                raise ValueError("gh JSON must be a list")
            snapshot = _from_live(raw_issues, raw_pulls)
        except Exception:
            snapshot = _from_seed()
        payload = snapshot.model_dump()
        if use_cache:
            _write_cache(payload)
        return payload
    except Exception:
        return _emergency()
