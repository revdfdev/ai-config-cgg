# Skills to install at home (Claude Code + Antigravity)

Every skill installed on the work PC on 2026-11-14, with how to install it. Codex is no longer used.
Claude loads `~/.claude/skills`. Antigravity loads `~/.gemini/config/skills`, `~/.gemini/skills`, `~/.gemini/antigravity/skills`.

## 1. From this repo (16): `python3 ~/ai-config-ccg/install.py --yes`
Links each into `~/.claude/skills` and `~/.gemini/config/skills`.

bug-triage, diagnosing-bugs, e2e, e2e-analysis, grill-me, grilling, handoff, memory, pattern, plan, review, simplify, tdd, teach, to-questionnaire, writing-for-agents

## 2. From GitHub with the skills CLI (17), into `~/.agents/skills`

| Skill | Install | On work PC loaded by |
|---|---|---|
| design-taste-frontend | `npx skills add Leonxlnx/taste-skill` | Claude, Antigravity |
| premium-3d-website, shader-programming-glsl, threejs-lighting, threejs-materials, threejs-postprocessing, threejs-shaders, threejs-skills | `npx skills add sickn33/antigravity-awesome-skills` (pick these 7) | Claude, Antigravity |
| find-skills | `npx skills add vercel-labs/skills` | none (only in `~/.agents/skills`) |
| leanrea | `npx skills add aicodeking/leanrea` | none |
| openui | `npx skills add thesysdev/skills` | none |
| ponytail, ponytail-audit, ponytail-debt, ponytail-gain, ponytail-help, ponytail-review | `npx skills add DietrichGebert/ponytail` | none |

Then link the loaded ones into both agents:
```bash
for s in design-taste-frontend premium-3d-website shader-programming-glsl threejs-lighting threejs-materials threejs-postprocessing threejs-shaders threejs-skills; do
  ln -sfn ~/.agents/skills/$s ~/.claude/skills/$s
  ln -sfn ~/.agents/skills/$s ~/.gemini/config/skills/$s
done
```

## 3. Other installers

| Skill | Install | Loaded by |
|---|---|---|
| impeccable | impeccable npm CLI (`npx impeccable`; `npx impeccable update` refreshes). Copies into `~/.claude/skills` and `~/.gemini/skills`; link `~/.gemini/config/skills/impeccable` to `~/.gemini/skills/impeccable` | Claude, Antigravity |
| reverse-engineer-anything | REA, github.com/morluto/rea (`npx -y rea-agents`), into `~/.agents/skills` | none |
| mobile-responsive-analyzer | source not recorded: copy `~/.claude/skills/mobile-responsive-analyzer` from the work PC into `~/.claude/skills`, `~/.gemini/skills`, `~/.gemini/antigravity/skills` | Claude, Antigravity |

## 4. Come with the account (no install)
- Claude (claude.ai synced, `~/.claude/skills/synced`): built-in-browser, chrome-browser, computer-use, deep-research, docs, docx, google-workspace, import-memory, morning, pdf, pptx, skill-creator, xlsx.
- Antigravity built-ins: agy-customizations, antigravity_guide, automation, generative_ui, mcp-app-development, migrate-agent-settings, migrate-workflows, native_swarm, permissioned-github, plugin, run-workflow, swarm_monitor, swarm_narrator, ui-plugin-navigation.

## Check
- `ls ~/.claude/skills | wc -l` gives 27 on the work PC (16 repo + 8 skills CLI + impeccable + mobile-responsive-analyzer + `synced`).
- `ls ~/.gemini/config/skills | wc -l` gives 27 (16 repo + 8 skills CLI + impeccable + frontend-design + taste-skill).
- Not verified on a clean machine: the `npx skills add` and `npx impeccable` commands.
