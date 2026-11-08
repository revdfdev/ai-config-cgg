# Decisions

Record durable configuration decisions here, including their date and reason.

- 2026-11-08 — Trackers removed; bigger changes use the `plan` skill (one file, steps ticked only with proof, deleted when done). Reason: tracker upkeep cost more than it saved.
- 2026-11-08 — Bash guard matches subcommands after global flags (`kubectl -n x delete`, `helm -n x upgrade`) and covers split `rm` flags, DB writes, image removal and terraform. Reason: a real prod `helm -n … upgrade` passed the old guard.
- 2026-11-08 — Forced `effortLevel: low` removed from Claude settings. Reason: too shallow for incident and infra work; set per session instead.
