# Plugins and MCP servers for Claude Code and Antigravity

`install.py --yes` installs the shared rules, hooks and the skills in `skills/`. Everything else below is installed separately. Inventory taken 2026-11-14 on the work PC. Codex is no longer used.

## Skills
See `docs/SKILLS.md`.

## Claude Code

### Plugins
| Plugin | Add marketplace | Install | State on work PC |
|---|---|---|---|
| reflect-mod | `claude plugin marketplace add bayramannakov/claude-reflect` | `claude plugin install reflect-mod@claude-reflect-marketplace` | installed, disabled |
| cache-tax | `claude plugin marketplace add karanb192/claude-code-mods` | `claude plugin install cache-tax@claude-code-mods` | not installed |
| blast-radius | `claude plugin marketplace add ~/claude-code-playground/claude-code/mods` | `claude plugin install blast-radius@claude-code-playground-mods` | not installed; needs that local folder |

Not for Claude: `egm` (google/elephant-goldfish-model), removed 2026-11-13.

### MCP servers
- claude.ai connectors (come with the account): Claude Docs, Gmail, Meizo MCP K8s (`https://ai.meizoerp.com/mcp`).
- `rea`: `claude mcp add rea -- npx -y rea-agents@4.0.1 mcp` (disabled for hrms-project).
- hrms-project `.mcp.json`: AgentsRoom-Chrome, AgentsRoom-MCP, AgentsRoom-Test-Runner, AgentsRoom-QA-Tester; need env `AGENTSROOM_MCP_SESSION`.

## Antigravity
- Plugin: egm 0.1.0 (`~/.gemini/config/plugins/egm`), for design documents only.
- MCP servers: none.

## Order on a new machine
1. `python3 ~/ai-config-ccg/install.py --yes`
2. Skills: follow `docs/SKILLS.md`.
3. Claude marketplaces + plugins, `rea` MCP.
4. Antigravity: egm.
5. Check: `claude plugin list`; `claude mcp list`; `ls ~/.gemini/config/skills`; `grep -c "^# Global Rules" ~/.claude/CLAUDE.md` prints 1.
