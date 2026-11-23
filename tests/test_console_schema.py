"""Schema and seed-loader coverage for the harness console. No HTTP feature."""

import json
from datetime import date

import pytest

from app import db
from app.models import ConsoleSnapshot, Note, NoteIn

ISSUE_ARGS = [
    "issue",
    "list",
    "--state",
    "all",
    "--limit",
    "50",
    "--json",
    "number,title,state,labels,url,body,updatedAt",
]
PR_ARGS = [
    "pr",
    "list",
    "--state",
    "all",
    "--limit",
    "50",
    "--json",
    "number,title,state,labels,url,body,mergedAt,updatedAt,statusCheckRollup",
]

MERGED_ISSUES = (1, 3, 5, 6, 7, 8, 9, 15, 17, 19)
PIPELINE = {"planned", "in-progress", "in-review", "approved", "merged", "needs-human"}
NOTES_MESSAGE = "I want these features in my app: list notes, tags, and search."


@pytest.fixture(autouse=True)
def _reset_console_state(monkeypatch):
    db.clear_console_cache()
    monkeypatch.delenv("CONSOLE_SOURCE", raising=False)
    yield
    db.clear_console_cache()


def test_note_models_and_notes_tables_stay(make_note):
    assert set(NoteIn.model_fields) == {"title", "body"}
    assert set(Note.model_fields) == {"title", "body", "id", "created_at", "tags"}
    assert "CREATE TABLE IF NOT EXISTS notes" in db.SCHEMA
    assert "CREATE TABLE IF NOT EXISTS note_tags" in db.SCHEMA
    assert "console" not in db.SCHEMA.lower()

    note_id = make_note("Kept", body="still", tags=("x",))
    with db.connect() as conn:
        names = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        title = conn.execute("SELECT title FROM notes WHERE id = ?", (note_id,)).fetchone()[0]
    assert {"notes", "note_tags"} <= names
    assert title == "Kept"


def test_seed_validates_and_covers_the_board():
    payload = db.load_console(force_seed=True)
    assert isinstance(payload, dict)
    snap = ConsoleSnapshot.model_validate(payload)
    assert snap.mode == "seed"

    by_issue = {issue.number: issue for issue in snap.issues}
    assert set(MERGED_ISSUES).issubset(by_issue)
    for number in range(201, 209):
        assert number in by_issue
        assert by_issue[number].title.startswith("Sample:")
    assert "note" in by_issue[1].title.lower()
    assert by_issue[1].column == "merged"
    assert "status:in-progress" in by_issue[1].labels
    assert {issue.column for issue in snap.issues} == PIPELINE
    assert by_issue[201].column == "planned"
    assert by_issue[202].column == "in-progress"
    assert by_issue[203].column == "in-review"
    assert by_issue[203].round == 2
    assert by_issue[203].ci == "pending"
    assert by_issue[204].column == "approved"
    assert by_issue[205].column == "needs-human"
    assert by_issue[205].round == 3
    assert by_issue[206].column == "approved"
    assert by_issue[207].column == "in-progress"
    assert by_issue[207].specialist == "Vault"
    assert by_issue[208].column == "in-progress"
    assert by_issue[3].branch == "adr/0008-notes-frontend"
    assert by_issue[15].specialist == "Scribe"
    assert by_issue[17].branch == "ticket/17-app-nav"
    assert by_issue[19].wave == 3
    assert by_issue[201].ci == "missing"
    assert all(by_issue[number].column == "merged" for number in MERGED_ISSUES)

    by_pull = {pull.number: pull for pull in snap.pulls}
    assert by_pull[2].state == "merged"
    assert by_pull[2].closes == 1
    assert by_pull[2].ci == "pass"
    assert by_pull[2].review_approved is True
    assert by_pull[2].round == 1
    assert by_pull[2].feature_run_filled is True
    assert "Closes #1" in by_pull[2].body
    assert by_pull[301].ci == "pending"
    assert by_pull[301].round == 2
    assert by_pull[301].review_approved is False
    assert by_pull[301].feature_run_filled is True
    assert by_pull[302].ci == "pass"
    assert by_pull[303].ci == "fail"
    assert by_pull[303].needs_human is True
    assert by_pull[303].feature_run_filled is False
    assert by_pull[303].round == 3
    assert by_pull[304].feature_run_filled is False
    assert by_pull[304].review_approved is True

    assert [agent.id for agent in snap.agents] == [
        "supervisor",
        "atlas",
        "vault",
        "pixel",
        "probe",
        "scribe",
        "reviewer",
    ]
    agents = {agent.id: agent for agent in snap.agents}
    assert agents["supervisor"].status == "idle"
    assert agents["supervisor"].activity == ["Planning and merging"]
    assert "app/" in agents["supervisor"].never
    assert agents["atlas"].status == "needs-human"
    assert agents["atlas"].current_ticket == 201
    assert agents["atlas"].tickets_done == 6
    assert agents["atlas"].prs_opened == 9
    assert agents["atlas"].needs_human_count == 1
    assert agents["atlas"].avg_review_rounds == 1.33
    assert agents["atlas"].activity == [
        "Sample: bulk delete",
        "Sample: share links",
        "Sample: tag search",
    ]
    assert agents["vault"].status == "blocked"
    assert agents["vault"].current_ticket == 207
    assert agents["vault"].writes[0] == "app/db.py"
    assert agents["pixel"].status == "idle"
    assert agents["pixel"].tickets_done == 1
    assert agents["pixel"].writes == ["app/ui/"]
    assert agents["pixel"].activity == ["App nav"]
    assert agents["probe"].status == "working"
    assert agents["probe"].current_ticket == 206
    assert agents["probe"].prs_opened == 2
    assert agents["scribe"].status == "working"
    assert agents["scribe"].current_ticket == 208
    assert agents["scribe"].tickets_done == 2
    assert agents["reviewer"].status == "needs-human"
    assert agents["reviewer"].current_ticket == 205
    assert agents["reviewer"].activity == ["Waiting for a pull request"]
    assert agents["reviewer"].prs_opened == 0

    assert [strain.id for strain in snap.strains] == [
        "role-maps",
        "agents-unowned",
        "five-vs-waves",
        "board-outside-github",
    ]
    role_maps = snap.strains[0]
    assert "docs/adr/0005-specialized-builder-roles.md" in role_maps.evidence
    assert ".cursor/agents/pixel.md" in role_maps.evidence
    assert role_maps.proposed_fix

    assert [chip.id for chip in snap.chips] == ["console", "notes", "health"]
    assert snap.chips[1].message == NOTES_MESSAGE
    assert snap.transcript[0].role == "user"
    assert snap.transcript[0].text == NOTES_MESSAGE
    assert snap.transcript[1].role == "supervisor"
    assert "wave" in snap.transcript[1].text.lower()

    assert "three waves" in snap.demo_plan.summary.lower()
    assert [wave.wave for wave in snap.demo_plan.waves] == [1, 2, 3]
    wave_branches = [[ticket.branch for ticket in wave.tickets] for wave in snap.demo_plan.waves]
    assert wave_branches[0] == [
        "adr/0010-harness-console",
        "ticket/pending-console-seed",
        "ticket/pending-console-chrome",
    ]
    assert wave_branches[1] == [
        "ticket/pending-console-chat",
        "ticket/pending-console-agents",
        "ticket/pending-console-pipeline",
        "ticket/pending-console-merge",
        "ticket/pending-console-adrs",
        "ticket/pending-console-strains",
        "ticket/pending-console-overview",
    ]
    assert wave_branches[2] == [
        "ticket/pending-console-tests",
        "ticket/pending-demo-guide",
    ]
    assert {ticket.owner for ticket in snap.demo_plan.waves[1].tickets} == {"Atlas"}
    assert all(
        ticket.status == "planned" and ticket.issue_url == "" and ticket.pr_url == ""
        for wave in snap.demo_plan.waves
        for ticket in wave.tickets
    )

    assert len(snap.events) >= 6
    assert all(event.actor == "PR" for event in snap.events)
    assert [event.at for event in snap.events] == sorted(
        (event.at for event in snap.events), reverse=True
    )
    assert snap.events[0].text.startswith("#20 ")
    assert len(snap.merges_by_day) == 7


def test_explicit_today_drives_merge_stats():
    snap = db.derive_console(
        db.CONSOLE_SEED["issues"],
        db.CONSOLE_SEED["pulls"],
        mode="seed",
        today=date(2026, 11, 23),
    )
    assert snap.stats.open_issues == 8
    assert snap.stats.open_prs == 4
    assert snap.stats.merged_today == 3
    assert snap.stats.needs_human == 1
    assert snap.stats.avg_review_rounds == 1.21
    assert snap.stats.ci_pass_rate == 0.92
    assert [(day.date, day.count) for day in snap.merges_by_day] == [
        ("2026-11-17", 0),
        ("2026-11-18", 0),
        ("2026-11-19", 0),
        ("2026-11-20", 1),
        ("2026-11-21", 0),
        ("2026-11-22", 6),
        ("2026-11-23", 3),
    ]
    days = db.merges_by_day(
        [
            {"merged_at": "2026-11-23T07:57:19Z"},
            {"merged_at": "2026-11-20T13:48:25Z"},
            {"merged_at": None},
        ],
        date(2026, 11, 23),
    )
    assert len(days) == 7
    assert days[0] == {"date": "2026-11-17", "count": 0}
    assert days[-1] == {"date": "2026-11-23", "count": 1}


def test_forced_seed_and_env_do_not_call_gh(monkeypatch):
    def boom(args):
        raise AssertionError(args)

    payload = db.load_console(force_seed=True, runner=boom)
    assert payload["mode"] == "seed"
    assert any(issue["number"] == 1 for issue in payload["issues"])

    monkeypatch.setenv("CONSOLE_SOURCE", "seed")
    again = db.load_console(runner=boom)
    assert again["mode"] == "seed"


def test_raising_runner_and_invalid_json_fall_back_to_seed():
    def boom(args):
        raise TimeoutError("timed out")

    assert db.load_console(runner=boom)["mode"] == "seed"

    def invalid(args):
        if args == ISSUE_ARGS:
            return "[]"
        return "not-json"

    fallback = db.load_console(runner=invalid)
    assert fallback["mode"] == "seed"
    assert any(issue["number"] == 1 for issue in fallback["issues"])


def test_failed_gh_process_returns_seed(monkeypatch):
    def fake_run(command, *, capture_output, text, timeout):
        assert command[0] == "gh"
        assert command[1:] == ISSUE_ARGS
        assert capture_output is True
        assert text is True
        assert timeout == 8

        class Completed:
            returncode = 1
            stdout = ""
            stderr = "nope"

        return Completed()

    monkeypatch.setattr(db.subprocess, "run", fake_run)
    payload = db.load_console()
    assert payload["mode"] == "seed"
    assert any(issue["number"] == 1 for issue in payload["issues"])


def test_live_overlay_merged_wins_over_stale_in_progress():
    calls = []

    def runner(args):
        calls.append(list(args))
        if args == ISSUE_ARGS:
            return json.dumps(
                [
                    {
                        "number": 50,
                        "title": "Stale progress",
                        "state": "CLOSED",
                        "labels": [{"name": "status:in-progress"}],
                        "url": "https://example.test/issues/50",
                        "body": "Specialist: Atlas\nWave: 2\nBranch: ticket/50-stale\n",
                        "updatedAt": "2026-11-23T08:00:00Z",
                    },
                    {
                        "number": 49,
                        "title": "Closed without a merge",
                        "state": "CLOSED",
                        "labels": [],
                        "url": "https://example.test/issues/49",
                        "body": "Specialist: Atlas\nWave: 2\n",
                        "updatedAt": "2026-11-23T07:00:00Z",
                    },
                ]
            )
        assert args == PR_ARGS
        return json.dumps(
            [
                {
                    "number": 51,
                    "title": "Stale progress",
                    "state": "MERGED",
                    "labels": ["review:approved", "round:1"],
                    "url": "https://example.test/pull/51",
                    "body": "Closes #50\n\n## Feature run\npytest ok\n",
                    "mergedAt": "2026-11-23T09:00:00Z",
                    "updatedAt": "2026-11-23T09:00:00Z",
                    "statusCheckRollup": [
                        {"status": "COMPLETED", "conclusion": "SUCCESS"},
                    ],
                }
            ]
        )

    seed = db.load_console(force_seed=True)
    live = db.load_console(runner=runner)
    assert calls == [ISSUE_ARGS, PR_ARGS]
    assert live["mode"] == "live"
    assert {issue["number"] for issue in live["issues"]} == {50}
    issue = live["issues"][0]
    assert issue["column"] == "merged"
    assert issue["specialist"] == "Atlas"
    assert issue["branch"] == "ticket/50-stale"
    assert issue["ci"] == "pass"
    assert live["stats"]["open_issues"] == 0
    assert live["pulls"][0]["state"] == "merged"
    assert live["pulls"][0]["closes"] == 50
    assert live["events"][0]["actor"] == "PR"
    assert live["events"][0]["text"].startswith("#51 ")
    assert live["events"][1]["actor"] == "Issue"
    assert live["strains"] == seed["strains"]
    assert live["chips"] == seed["chips"]
    assert live["transcript"] == seed["transcript"]
    assert live["demo_plan"] == seed["demo_plan"]
    assert len(live["merges_by_day"]) == 7
    assert [agent["id"] for agent in live["agents"]] == [agent["id"] for agent in seed["agents"]]


def test_empty_live_lists_stay_live_and_reuse_seed_events():
    seed = db.load_console(force_seed=True)

    def runner(args):
        assert args in (ISSUE_ARGS, PR_ARGS)
        return "[]"

    live = db.load_console(runner=runner)
    assert live["mode"] == "live"
    assert live["issues"] == []
    assert live["pulls"] == []
    assert live["events"] == seed["events"]
    assert live["strains"] == seed["strains"]
    assert live["stats"]["open_issues"] == 0
    assert live["stats"]["ci_pass_rate"] is None
    assert live["stats"]["avg_review_rounds"] is None


def test_live_slug_branch_and_check_rollup():
    def runner(args):
        if args[0] == "issue":
            return json.dumps(
                [
                    {
                        "number": 77,
                        "title": "Hello, World!",
                        "state": "OPEN",
                        "labels": ["status:ready"],
                        "url": "https://example.test/77",
                        "body": "Specialist: Probe\nWave: 3\n",
                        "updatedAt": "2026-11-23T12:00:00Z",
                    },
                    {
                        "number": 78,
                        "title": "A" * 50,
                        "state": "open",
                        "labels": [],
                        "url": "https://example.test/78",
                        "body": (
                            "## Specialist\nScribe\n\nWave: 4\nBranch: adr/0010-harness-console\n"
                        ),
                        "updatedAt": "2026-11-23T12:05:00Z",
                    },
                ]
            )
        return json.dumps(
            [
                {
                    "number": 90,
                    "title": "Checks (#77)",
                    "state": "OPEN",
                    "labels": ["status:in-review", "round:2"],
                    "url": "https://example.test/90",
                    "body": "No closes line\n\n## Feature run\n```\nonly fences around this\n```\n",
                    "mergedAt": None,
                    "updatedAt": "2026-11-23T12:06:00Z",
                    "statusCheckRollup": [
                        {"status": "COMPLETED", "conclusion": "SUCCESS"},
                        {"status": "COMPLETED", "conclusion": "NEUTRAL"},
                    ],
                },
                {
                    "number": 91,
                    "title": "Cancelled",
                    "state": "OPEN",
                    "labels": [],
                    "url": "https://example.test/91",
                    "body": "Closes #78\n\n## Feature run\n```\n```\n",
                    "mergedAt": None,
                    "updatedAt": "2026-11-23T12:07:00Z",
                    "statusCheckRollup": [
                        {"status": "IN_PROGRESS", "conclusion": ""},
                        {"status": "COMPLETED", "conclusion": "CANCELLED"},
                    ],
                },
            ]
        )

    live = db.load_console(runner=runner)
    by_issue = {issue["number"]: issue for issue in live["issues"]}
    assert by_issue[77]["slug"] == "hello-world"
    assert by_issue[77]["branch"] == "ticket/77-hello-world"
    assert by_issue[77]["specialist"] == "Probe"
    assert by_issue[77]["wave"] == 3
    assert by_issue[77]["column"] == "in-review"
    assert by_issue[77]["round"] == 2
    assert by_issue[77]["ci"] == "pass"
    assert by_issue[78]["slug"] == "a" * 40
    assert by_issue[78]["branch"] == "adr/0010-harness-console"
    assert by_issue[78]["specialist"] == "Scribe"
    assert by_issue[78]["wave"] == 4
    assert by_issue[78]["column"] == "planned"
    assert by_issue[78]["ci"] == "fail"
    pulls = {pull["number"]: pull for pull in live["pulls"]}
    assert pulls[90]["closes"] == 77
    assert pulls[90]["feature_run_filled"] is True
    assert pulls[90]["ci"] == "pass"
    assert pulls[91]["closes"] == 78
    assert pulls[91]["feature_run_filled"] is False
    assert pulls[91]["ci"] == "fail"


def test_default_path_caches_and_injected_runner_bypasses_it(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(db.time, "monotonic", lambda: clock["now"])
    calls = {"default": 0, "injected": 0}

    def default(args):
        calls["default"] += 1
        return "[]"

    def injected(args):
        calls["injected"] += 1
        if args[0] == "issue":
            return json.dumps(
                [
                    {
                        "number": 60,
                        "title": "Injected",
                        "state": "OPEN",
                        "labels": ["status:ready"],
                        "url": "https://example.test/60",
                        "body": "Specialist: Vault\nWave: 1\nBranch: ticket/60-injected\n",
                        "updatedAt": "2026-11-23T12:00:00Z",
                    }
                ]
            )
        return "[]"

    monkeypatch.setattr(db, "_default_runner", default)
    first = db.load_console()
    second = db.load_console()
    assert first["mode"] == "live"
    assert second["issues"] == []
    assert calls["default"] == 2

    overlay = db.load_console(runner=injected)
    assert calls["injected"] == 2
    assert overlay["issues"][0]["number"] == 60

    third = db.load_console()
    assert calls["default"] == 2
    assert third["issues"] == []

    clock["now"] += 4.1
    db.load_console()
    assert calls["default"] == 4

    seeded = db.load_console(force_seed=True)
    assert seeded["mode"] == "seed"
    assert calls["default"] == 4
