# Plugins and MCP servers for Claude Code and Antigravity

`install.py --yes` installs the shared rules, hooks and the skills in `skills/`. Everything else below is installed separately. Inventory taken 2026-11-14 on the work PC. Codex is no longer used.

## Skills
See `docs/SKILLS.md`.

## Claude Code

### Plugins
| Plugin | Add marketplace | Install | State on work PC |
|---|---|---|---|
| taste-skill | `claude plugin marketplace add Leonxlnx/taste-skill` | `claude plugin install taste-skill@taste-skill` | installed |
| frontend-design | `claude plugin marketplace add anthropics/claude-code` | `claude plugin install frontend-design@claude-code-plugins` | installed |
| reflect-mod | `claude plugin marketplace add bayramannakov/claude-reflect` | `claude plugin install reflect-mod@claude-reflect-marketplace` | installed, disabled |
| cache-tax | `claude plugin marketplace add karanb192/claude-code-mods` | `claude plugin install cache-tax@claude-code-mods` | not installed |
| blast-radius | `claude plugin marketplace add ~/claude-code-playground/claude-code/mods` | `claude plugin install blast-radius@claude-code-playground-mods` | not installed; needs that local folder |

Not used: `egm` (google/elephant-goldfish-model), removed from Claude 2026-11-13 and from Antigravity 2026-11-14.

### MCP servers
- claude.ai connectors (come with the account): Claude Docs, Gmail, Meizo MCP K8s (`https://ai.meizoerp.com/mcp`).
- `rea`: `claude mcp add rea -- npx -y rea-agents@4.0.1 mcp` (disabled for hrms-project).
- hrms-project `.mcp.json`: AgentsRoom-Chrome, AgentsRoom-MCP, AgentsRoom-Test-Runner, AgentsRoom-QA-Tester; need env `AGENTSROOM_MCP_SESSION`.

## Antigravity
- Plugins: none.
- Skills copied from the Claude plugins (run after the Claude plugins are installed):
  ```bash
  cp -r ~/.claude/plugins/cache/taste-skill/taste-skill/*/skills/taste-skill ~/.gemini/config/skills/
  cp -r ~/.claude/plugins/cache/claude-code-plugins/frontend-design/*/skills/frontend-design ~/.gemini/config/skills/
  ```
- On a machine that still has egm: `claude plugin uninstall egm@egm; claude plugin marketplace remove egm; rm -rf ~/.gemini/config/skills/egm-* ~/.gemini/config/plugins/egm`
- MCP servers: none.

## Order on a new machine
1. `python3 ~/ai-config-ccg/install.py --yes`
2. Skills: follow `docs/SKILLS.md`.
3. Claude marketplaces + plugins, `rea` MCP.
4. Check: `claude plugin list`; `claude mcp list`; `ls ~/.gemini/config/skills`; `grep -c "^# Global Rules" ~/.claude/CLAUDE.md` prints 1.
