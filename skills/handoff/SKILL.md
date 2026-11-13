---
name: handoff
description: Write a short, verified handoff so a new thread or another agent (Claude, Codex, Antigravity) can continue the work without the old chat. Use when the user asks for a handoff, ends a session, or the thread is long, looping or cut off.
---

# Handoff

Write the handoff from live evidence, not memory of the chat. Check repo state
(`git -C <repo> status --short`, `git log --oneline -5`) and the active tracker
`STATE.md` before writing.

1. If a tracker is active, update its `STATE.md` first (checklist, blockers,
   next step). The handoff points to it instead of repeating it.
2. Output one block the user can paste into the next thread:

```
Handoff — <date>
Goal: <one line: what the user wants>
State: <done / in progress / blocked, one line each>
Facts: <verified facts the next agent needs: commits, environments, test
        employees, commands that prove things; mark anything unverified>
Next step: <the single next action, and whether it needs user approval>
Files: <tracker STATE.md, register, key source files, uncommitted changes>
Don't: <traps already hit, e.g. wrong BASE_URL, others' uncommitted files>
```

Rules:

- Keep it under ~25 lines; detail belongs in the tracker.
- Only facts you checked this session; say "not verified" otherwise.
- Name exact commits, branches and unpushed work. Never include secrets.
- List other agents' uncommitted files as "not ours, leave alone".
- If the user wants it saved, write durable facts with the `memory` skill;
  the handoff itself stays in chat.
