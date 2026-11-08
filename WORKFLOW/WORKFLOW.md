# Shared Agent Workflow

Long-form explanation of the rules in `AGENTS.md`. It is not loaded every
session; read it when a task needs more detail. If it conflicts with
`AGENTS.md`, `AGENTS.md` wins.

## 1. Start with context

1. Read the applicable global and repository `AGENTS.md` files.
2. Read relevant shared memory in
   `~/ai-config-ccg/MEMORIES/`, and relevant project memory through
   its `docs/agent-memory/INDEX.md` when present.
4. Inspect only the working-tree state, code, configuration, callers,
   consumers, tests, and persisted contracts required by the task before
   editing.
5. Treat live code and configuration as stronger evidence than memory or prior
   conversation. State conflicts instead of silently choosing one.

Before an edit, be able to name the owning file or component, the observed
behavior or contract, the relevant caller or consumer when there is one, and
the check that can prove the change. For documentation or configuration work,
inspect the existing documents or configuration instead of inventing a code
path. For bugs, reproduce the symptom or explicitly report that it is not yet
reproduced; do not guess at a fix. Keep this discovery proportional to the
task, and stop once it supports a bounded change.

## 2. Define the task

1. Identify the requested outcome and its boundary; communicate only decisions
   or risks the user needs to know.
2. For a small, contained change, proceed within that boundary.
3. For a change bigger than a few lines or spanning files or services, use
   `plan`: one short file of steps, each with its proof; wait for `proceed`.
4. Do not broaden the work because adjacent cleanup, an unrelated defect, or
   an alternative design looks attractive. Ask if a necessary change exceeds
   the approved scope.

Work with the user as a collaborator. Explain a material uncertainty and give
an evidence-based recommendation, but leave goals, priorities, and tradeoffs
to the user. Do not withhold a routine scoped implementation behind an
unnecessary approval step, and do not use a plan to overrule a newer
explicit instruction.

## 3. Implement deliberately

1. Make the smallest change that fulfills the approved request.
2. Preserve existing conventions and dependencies unless the request changes
   them.
3. Keep domain decisions in their proper layer and inspect real callers before
   changing a shared contract.
4. Never overwrite or discard unrelated user work. Confirm exact targets before
   destructive actions.
5. Use the relevant skill on demand: `bug-triage` for regressions, `tdd` for
   backend behavior, and `simplify` before a commit.

## 4. Prove the result

1. Choose checks that directly prove the requested behavior: focused tests,
   formatting, type checks, builds, and E2E flows where applicable. Verify
   deeply within scope, not broadly outside it.
2. For backend behavior, write and observe a failing test before production
   code, then make the smallest change that passes.
3. For changed frontend behavior, exercise the relevant user flow with the
   repository's test tooling when that flow is needed to prove the change.
4. Record the exact command and result. Never present an unrun check as passed;
   say `not verified` and why.
5. If the same approach fails twice, stop and report the evidence rather than
   retrying blindly.

For implementation tasks, the outcome is the requested working feature or
fix, not a finished plan. Use tests and checks to prove the
outcome; writing a test or ticking a plan step without a passing, relevant
result is not completion. For research-only tasks, the requested findings are
the outcome; do not implement merely to finish a plan.
If proof cannot run, keep the work open and report what remains unverified.

## Thread handoff

If a response is cut off, the same investigation repeats without new evidence,
or context has become too large to track the task reliably, stop the current
work. Tell the user to start a new thread. Give a short, copyable handoff with
the objective, plan file path if any, verified findings, remaining step, and
exact files to read. Tick proven plan steps first. Do not paste the transcript, reload
all earlier output, or keep resuming a cut-off response in the same thread.

## 5. Close the loop

1. Re-read the request and validate the delivered behavior against its
   acceptance criteria. Delete the plan file only after that proof, never to make
   the process look complete.
2. Report the outcome first, then relevant changed files, verification, and
   anything not verified.
3. Capture confirmed project facts in its `docs/agent-memory/`; use central
   `MEMORIES/` only for facts shared by all agents. Do not store secrets,
   transient logs, full transcripts, or assumptions.
4. Never push, deploy, restart, send, or otherwise create external state
   without explicit approval for that action.
