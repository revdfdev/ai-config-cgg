# Plugins, MCP servers and skills to set up on a new machine

`install.py --yes` installs the shared rules, hooks and the skills in `skills/`. Everything else below is installed separately. Inventory taken 2026-11-14 on the work PC.

## Skills

### From this repo (`install.py` links them)
bug-triage, diagnosing-bugs, e2e, e2e-analysis, grill-me, grilling, handoff, memory, pattern, plan, review, simplify, tdd, teach, to-questionnaire, writing-for-agents.
Linked into `~/.claude/skills` and `~/.codex/skills`. Antigravity does not get them today.

### From GitHub via the skills CLI (`~/.agents/skills`, lock file `~/.agents/.skill-lock.json`)
Install with the skills CLI (vercel-labs/skills), one source at a time: `npx skills add <source>`.

| Skill | Source |
|---|---|
| design-taste-frontend | Leonxlnx/taste-skill |
| find-skills | vercel-labs/skills |
| leanrea | aicodeking/leanrea |
| openui | thesysdev/skills |
| ponytail, ponytail-audit, ponytail-debt, ponytail-gain, ponytail-help, ponytail-review | DietrichGebert/ponytail |
| premium-3d-website, shader-programming-glsl, threejs-lighting, threejs-materials, threejs-postprocessing, threejs-shaders, threejs-skills | sickn33/antigravity-awesome-skills |

### Other skills
- `impeccable` (UI design): impeccable npm CLI; `npx impeccable update` refreshes it. Present in `~/.agents/skills`, `~/.claude/skills`, `~/.gemini/skills`.
- `mobile-responsive-analyzer`: plain folder copied into `~/.claude/skills`, `~/.codex/skills`, `~/.gemini/skills` (source not recorded).
- `reverse-engineer-anything`: in `~/.agents/skills` (source not recorded).

## Claude Code

### Plugins
| Plugin | Add marketplace | Install | State on work PC |
|---|---|---|---|
| reflect-mod | `claude plugin marketplace add bayramannakov/claude-reflect` | `claude plugin install reflect-mod@claude-reflect-marketplace` | installed, disabled |
| cache-tax | `claude plugin marketplace add karanb192/claude-code-mods` | `claude plugin install cache-tax@claude-code-mods` | not installed (was listed in `claude/settings.json`) |
| blast-radius | `claude plugin marketplace add ~/claude-code-playground/claude-code/mods` | `claude plugin install blast-radius@claude-code-playground-mods` | not installed; needs that local folder |

Not for Claude or Codex: `egm` (google/elephant-goldfish-model), removed 2026-11-13.

### MCP servers
- claude.ai connectors (come with the claude.ai account, no install): Claude Docs, Gmail, Meizo MCP K8s (`https://ai.meizoerp.com/mcp`).
- `rea`: `claude mcp add rea -- npx -y rea-agents@4.0.1 mcp` (disabled for hrms-project).
- hrms-project `.mcp.json`: AgentsRoom-Chrome, AgentsRoom-MCP, AgentsRoom-Test-Runner, AgentsRoom-QA-Tester; need env `AGENTSROOM_MCP_SESSION` (missing on the work PC, so they don't start).

## Codex
Plugins (OpenAI curated, installed from the Codex plugin menu): Figma, Sites, Pets, Plugin Management, Default templates, Hatchable, Indeed Job Search, Chessvia Openings. No MCP servers configured.

## Antigravity
| Item | Where | Notes |
|---|---|---|
| egm 0.1.0 plugin | `~/.gemini/config/plugins/egm` | keep for design documents only |

## Order on a new machine
1. `python3 ~/ai-config-ccg/install.py --yes`
2. Skills CLI sources above, then impeccable.
3. Claude marketplaces + plugins, `rea` MCP.
4. Codex curated plugins you want.
5. Antigravity: egm.
6. Check: `claude plugin list`; `claude mcp list`; `grep -c "^# Global Rules" ~/.claude/CLAUDE.md` prints 1.
