---
name: tracker-control
description: Manage a research-first, file-backed work tracker. Use when a task needs research, spans sessions or agents, or has an active tracker.
---

# Tracker control

Use a tracker at `.atmar/trackers/<slug>/` only for work that needs durable
research, a multi-step delivery boundary, or explicit user tracking. Do not
create one for a small, self-contained task unless the user asks.

## Control mode

Before work, inspect `.atmar/trackers/*/STATE.md`. If exactly one tracker is
`active`, enter tracker-control mode: read its state, research, and proposal;
work only on its declared scope; and keep it active until the acceptance
criteria are proven or the user explicitly changes or drops it. Do not start
another tracker. Answer an unrelated question without silently switching the
implementation task; a newer explicit user instruction can change the tracker.
If more than one is active, stop and ask which one owns the work.

## Lifecycle

Create a tracker from the templates in `templates/tracker/`.

`research` → record each finding in `research.md` with source, evidence,
relevance, and open question. Stop researching once the evidence supports a
bounded proposal or reveals one concrete blocker; do not repeat searches that
add no new evidence. Inspect live code, configuration, callers, and tests
relevant to the outcome; a filled research file without source evidence is not
research. No implementation.

`proposed` → write the bounded approach in `proposal.md`, including in/out of
scope, acceptance criteria, risks, and proof. Wait for user approval.

`finalized` → proposal approved; preserve its acceptance boundary. An approval
that explicitly requests implementation also permits the move to `active`.
Otherwise wait for `proceed`, `go ahead`, or `implement`.

`active` → execute only finalized work. Gate each tracker item (epic, bug,
slice) separately: analyse and research it, report findings and the proposed
change, then wait for `proceed` or `go ahead` before editing; approval of one
item never carries to the next. Spend effort on the requested outcome,
not tracker upkeep; record only decisions, blockers, handoff state, and proof
needed to resume or verify it.

`completed` → the requested outcome meets its acceptance criteria. For an
implementation tracker, the feature or fix works and is proven by relevant
checks or observed behavior; for a research-only tracker, the requested
findings are delivered. Record exact evidence and release control mode. A
complete research file, approved proposal, passing test that does not prove
the outcome, or state transition alone is not completion. If outcome or proof
is blocked, keep the tracker active and report the blocker. `dropped` → user
abandons or changes the objective; record the reason and release control mode.
Do not require a second user instruction to mark proven work complete.

Read `references/schema.md` before creating or changing a tracker.
