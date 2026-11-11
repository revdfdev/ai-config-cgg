# Proposal: Scope & Diagnosis Alignment Skill (`scope-check`)

## Proposed approach

Turn the 5-point alignment gate in `AGENTS.md` into an on-demand progressive-disclosure skill at `skills/scope-check/SKILL.md`, shared across Claude Code, Codex, and Gemini via `install.sh` (`scripts/sync-agents.sh`), and shorten the `AGENTS.md` line to a single context pointer (`stuck/complex flow -> scope-check`).

Draft `skills/scope-check/SKILL.md`:

```markdown
---
name: scope-check
description: >-
  Align on context, priority, scope boundaries, hotzones, and bottlenecks before
  proposing fixes or editing code. Use when diagnosing a complex flow, resetting
  a drifting task, or when asked for a 5-point alignment check.
---

# Scope & Diagnosis Alignment Check

Before proposing fixes or editing code, answer these 5 questions concisely using
live code and reproduction evidence. Label every point as **observed evidence**
vs **assumption**, and wait for user approval on any open decision before editing:

1. **Context & Desired Outcomes:** What exact flow/failure is in scope, what reproduced evidence do we have right now, and what measurable behavior defines "done"?
2. **Most Important Thing to Build:** What is the single highest-priority root cause or end-to-end slice to verify/fix first (no side fixes)?
3. **What We Are Not Building:** What adjacent modules, integrations, cleanups, or test shortcuts are explicitly out of scope right now?
4. **Building Hotzones:** Which exact files/endpoints/seams own the active failure across UI, backend, engine, and reproduction harness?
5. **Bottlenecks:** What is currently blocking proof or progress (uninspected payloads, missing API wiring, un-restarted services, ambiguous business rules, or stale context)?
```

## Acceptance criteria

- `skills/scope-check/SKILL.md` exists in `~/ai-config-ccg` with valid `name` and `description` frontmatter.
- `./install.sh --sync` links `scope-check` cleanly into Claude Code, Codex, and Gemini skill directories.
- `AGENTS.md` retains only a concise pointer under `## Skills` so the full 5-question prompt loads on demand without spending always-on context tokens.

## Risks and unchanged areas

- Modifying `AGENTS.md` affects Claude Code, Codex, and Gemini simultaneously (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md` are symlinks).
- Leave existing skills (`bug-triage`, `diagnosing-bugs`, `e2e-analysis`, etc.), hooks, and unrelated uncommitted files in `~/ai-config-ccg` unchanged.

## Proof

- `/home/rehan/ai-config-ccg/install.sh --check` exits `0` with no broken or missing symlinks for `AGENTS.md` and `skills/scope-check`.

Approval: pending
