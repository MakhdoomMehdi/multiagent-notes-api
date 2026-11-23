"""Shared API models. Owned by the base; feature-specific models live in the feature folder."""

from typing import Literal

from pydantic import BaseModel, Field


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = ""


class Note(NoteIn):
    id: int
    created_at: str
    tags: list[str] = []


ConsoleMode = Literal["live", "seed"]
IssueState = Literal["open", "closed"]
PullState = Literal["open", "merged", "closed"]
ConsoleColumn = Literal["planned", "in-progress", "in-review", "approved", "merged", "needs-human"]
CheckState = Literal["pass", "fail", "pending", "missing"]
AgentStatus = Literal["idle", "working", "blocked", "needs-human"]
MessageRole = Literal["user", "supervisor"]


class ConsolePull(BaseModel):
    number: int
    title: str
    state: PullState
    labels: list[str]
    url: str
    body: str
    closes: int | None = None
    feature_run_filled: bool
    ci: CheckState
    review_approved: bool
    needs_human: bool
    round: int
    merged_at: str | None = None
    updated_at: str


class ConsoleIssue(BaseModel):
    number: int
    title: str
    state: IssueState
    labels: list[str]
    url: str
    body: str
    specialist: str
    wave: int
    slug: str
    branch: str
    column: ConsoleColumn
    round: int
    ci: CheckState
    updated_at: str


class ConsoleAgent(BaseModel):
    id: str
    role: str
    summary: str
    writes: list[str]
    never: list[str]
    status: AgentStatus
    current_ticket: int | None = None
    tickets_done: int
    prs_opened: int
    avg_review_rounds: float | None = None
    needs_human_count: int
    activity: list[str]


class ConsoleEvent(BaseModel):
    actor: str
    text: str
    at: str


class ConsoleDay(BaseModel):
    date: str
    count: int


class ConsoleStats(BaseModel):
    open_issues: int
    open_prs: int
    merged_today: int
    avg_review_rounds: float | None = None
    ci_pass_rate: float | None = None
    needs_human: int


class ConsoleStrain(BaseModel):
    id: str
    title: str
    detail: str
    evidence: list[str]
    proposed_fix: str


class ConsolePlanTicket(BaseModel):
    title: str
    owner: str
    branch: str
    status: str
    issue_url: str
    pr_url: str


class ConsoleWave(BaseModel):
    wave: int
    tickets: list[ConsolePlanTicket]


class ConsolePlan(BaseModel):
    summary: str
    waves: list[ConsoleWave]


class ConsoleChip(BaseModel):
    id: str
    label: str
    message: str


class ConsoleMessage(BaseModel):
    role: MessageRole
    text: str


class ConsoleSnapshot(BaseModel):
    mode: ConsoleMode
    issues: list[ConsoleIssue]
    pulls: list[ConsolePull]
    agents: list[ConsoleAgent]
    events: list[ConsoleEvent]
    merges_by_day: list[ConsoleDay]
    stats: ConsoleStats
    strains: list[ConsoleStrain]
    chips: list[ConsoleChip]
    transcript: list[ConsoleMessage]
    demo_plan: ConsolePlan
