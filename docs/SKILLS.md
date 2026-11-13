# Skills for Claude Code and Antigravity

Follow this on a new machine. Inventory from the work PC, 2026-11-14. Codex is no longer used.

Where agents load skills:
- Claude: `~/.claude/skills`
- Antigravity: `~/.gemini/config/skills` (also `~/.gemini/skills`, `~/.gemini/antigravity/skills`)


| Skill | Source | Claude | Antigravity |
|---|---|---|---|
| bug-triage, diagnosing-bugs, e2e, e2e-analysis, grill-me, grilling, handoff, memory, pattern, plan, review, simplify, tdd, teach, to-questionnaire, writing-for-agents | this repo `skills/` (`install.py` links them) | yes | yes |
| design-taste-frontend | skills CLI: Leonxlnx/taste-skill | yes | yes |
| premium-3d-website, shader-programming-glsl, threejs-lighting, threejs-materials, threejs-postprocessing, threejs-shaders, threejs-skills | skills CLI: sickn33/antigravity-awesome-skills | yes | yes (linked from `~/.claude/skills`) |
| impeccable | impeccable npm CLI (`npx impeccable update` refreshes) | yes | yes |
| mobile-responsive-analyzer | copied folder (source not recorded) | yes | yes |

Installed in `~/.agents/skills` but not linked into Claude or Antigravity: find-skills (vercel-labs/skills), leanrea (aicodeking/leanrea), openui (thesysdev/skills), ponytail + ponytail-audit/-debt/-gain/-help/-review (DietrichGebert/ponytail), reverse-engineer-anything (source not recorded). Skills CLI install: `npx skills add <source>` (lock file `~/.agents/.skill-lock.json`).

Note: 7 repo skills are not committed yet (diagnosing-bugs, grill-me, grilling, handoff, teach, to-questionnaire, writing-for-agents); commit them or a new machine will not get them.

## Steps
1. `python3 ~/ai-config-ccg/install.py --yes` links the repo skills into both agents.
2. Skills CLI: `npx skills add Leonxlnx/taste-skill` and `npx skills add sickn33/antigravity-awesome-skills` (lands in `~/.agents/skills`).
3. Link into Claude: `ln -s ~/.agents/skills/<name> ~/.claude/skills/<name>` for design-taste-frontend, premium-3d-website, shader-programming-glsl, threejs-*.
4. Link into Antigravity: `ln -s ~/.claude/skills/<name> ~/.gemini/config/skills/<name>` for the same names, and `ln -s ~/.gemini/skills/impeccable ~/.gemini/config/skills/impeccable`.
5. impeccable: install with the impeccable npm CLI into `~/.claude/skills` and `~/.gemini/skills`.
6. mobile-responsive-analyzer: copy the folder into `~/.claude/skills` and `~/.gemini/skills`.
7. Check: `ls ~/.claude/skills | wc -l` (27 on the work PC, incl. `synced`) and `ls ~/.gemini/config/skills | wc -l` (25).
