---
name: plan
description: Use for any change that is more than a few lines or spans files/services. One short plan file whose steps are ticked only with proof; deleted when done. Replaces trackers.
---

# Plan

The reward is finished, proven work. The plan is scaffolding, not the deliverable.

## 1. Before writing it
Read the code. List what the change touches: callers, consumers, persisted data, API/event contracts. Trace real code, not file names.

## 2. Write `docs/plans/<slug>.md` in the repo being changed
(Cross-repo: the repo where the user-visible change lands.) One screen, no prose beyond this:

```markdown
# <title>
Problem: <2 lines: observed vs wanted>
Touches: <callers / consumers / contracts found in step 1>
Out of scope: <adjacent findings, not to be done>

- [ ] <step> — <file(s)> — proof: <test or command that will show it works>
- [ ] ...
```

Show it in chat. **Wait for "proceed".** Approval covers these steps only; new scope means asking again.

## 3. Work one step at a time
Implement → run the proof → tick → next step. A tick must carry what actually ran:

- `- [x] <step> — proof: go test ./internal/x -run TestY → PASS`
- `- [ ] <step> — not verified: <why it could not run>`

Never tick from intent ("looked at it", "should work"). No status sections, no progress prose, no summaries of what you plan to do.

## 4. Finish
Done = every step ticked with proof, typecheck/tests green. Then:
1. Move any durable fact learned into `docs/agent-memory/` (agent-memory skill).
2. Delete the plan file in the same commit. The commit and its tests are the record.

Report: files changed, behaviour changed, proof lines, anything not verified.
