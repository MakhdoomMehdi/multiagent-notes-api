# ADR-0004: Agent roles, GitHub as the source of truth, and the merge gate

- Status: Accepted
- Date: 2026-11-20
- Deciders: Human lead, Supervisor agent

## Context
A Supervisor, five or more Builders, and a Reviewer work on this repository together. They need
clear boundaries, shared state that survives sessions, and a merge rule that does not rely on any
one agent being right.

## Decision
- **Roles.** The Supervisor plans, writes tickets and ADRs, dispatches Builders, and unblocks them;
  it never edits code. Each Builder implements exactly one ticket on one branch in its own git
  worktree and opens exactly one pull request. The Reviewer reviews and never edits code.
- **State.** GitHub is the only shared state: tickets are Issues, work is pull requests, status is
  labels, and questions and answers are comments. Agents do not rely on each other's chat history.
- **Branches.** `ticket/<issue-number>-<slug>`, cut from `main`, squash-merged back to `main`.
- **Review loop.** At most three rounds, tracked with `round:1`, `round:2`, `round:3`. If round 3
  still requests changes, the pull request gets `needs-human` and goes back to the Supervisor.
- **Merge gate.** A pull request can merge only when all of these hold, enforced by branch
  protection on `main` and the `ci` workflow:
  1. `lint-and-test` passes (ruff and pytest).
  2. `merge-gate` passes: the pull request has `review:approved`, does not have `needs-human`,
     links an issue with `Closes #N`, and has a filled-in "Feature run" section. A pull request
     that only changes `docs/adr/` needs only the approval label.
- **Approval label.** All agents act through one GitHub account, which cannot approve its own pull
  requests, so the Reviewer's approval is recorded as a review comment plus the `review:approved`
  label. Any push after approval removes the label (enforced by the workflow), forcing a re-review.

## Consequences
Every step is visible on GitHub and in the recording. A stuck pull request stops after three rounds
instead of looping. The approval label is weaker than a second account's review; with a second
account, switch the gate to GitHub's required approvals.
