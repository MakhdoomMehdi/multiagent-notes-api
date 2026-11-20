# ADR-0001: Record architecture decisions as ADRs

- Status: Accepted
- Date: 2026-11-20
- Deciders: Human lead, Supervisor agent

## Context
Several agents work on this repository in parallel and none of them keeps memory between
sessions. Decisions that live only in a chat are lost, and a builder that cannot see why the code
is shaped a certain way will undo it. See
[Martin Fowler, Architecture Decision Record](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html).

## Decision
We will record every decision that affects structure, dependencies, interfaces, or process as an
ADR in `docs/adr/`, numbered sequentially, using `0000-template.md`.

- Every ticket lists the ADRs it must follow. Every pull request lists the ADRs it followed or added.
- The Supervisor writes ADRs during planning. A Builder that has to make a new structural decision
  inside its ticket adds a new ADR in its own pull request with status `Proposed`; the Reviewer
  checks it and the Supervisor marks it `Accepted`.
- ADRs are never rewritten after acceptance. A changed decision gets a new ADR that supersedes it.

## Consequences
Agents can be given the ADR folder as context instead of a long prompt. Reviews have a written
standard to check against. Writing an ADR is a small cost on each structural change.
