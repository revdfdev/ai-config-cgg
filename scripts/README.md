# Scripts

`test-hooks.sh` checks the guard, proof-gate and reminder hooks (set `PYTHON`
to pick the interpreter). `test-codex-rules.sh` checks `codex/guard.rules`
against the Codex binary. `validate-skills.sh` checks skill structure.
Installer tests live in `tests/` (`python3 -m unittest discover -s tests`).
