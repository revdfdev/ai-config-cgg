"""PreToolUse on shell commands (Claude Code Bash, Antigravity run_command):
deny forbidden commands, force a prompt for risky ones."""
import json
import re
import sys

# Global flags before a subcommand: -n x, --context prod, --namespace=x, --insecure.
FLAGS = r"(?:\s+--?[\w-]+(?:=\S+|\s+(?!-)\S+)?)*"

DENY = [
    (r"--no-verify\b", "Do not skip git hooks."),
    (r"(?i)co-authored-by", "No Co-Authored-By trailers."),
]
ASK = [
    (r"\bgit\b[^;&|\n]*\bpush\b", "Push needs your approval now."),
    (r"\bgit\b[^;&|\n]*\btag\s+(?!-l\b|--list\b)[^\s-]", "Tagging needs your approval now."),
    (r"\bgit\s+reset\s+--hard\b", "Discards uncommitted work."),
    (r"\bgit\s+checkout\s+(--\s|\.(\s|$))", "Discards uncommitted work."),
    (r"\bgit\s+restore\s+(?!--staged\b)", "Discards uncommitted work."),
    (r"\bgit\s+clean\s+-\w*f", "Deletes untracked files."),
    (r"\bgit\s+stash(?!\s+(list|show)\b)(\s|$)", "Stash hides others' work."),
    (r"\bgit\s+branch\s+-D\b", "Force-deletes a branch."),
    (r"\brm\b(?=[^;&|\n]*\s(-\w*[rR]\w*|--recursive)\b)(?=[^;&|\n]*\s(-\w*f\w*|--force)\b)", "Recursive force delete."),
    (r"\bkubectl" + FLAGS + r"\s+(apply|delete|rollout|scale|patch|edit|replace|create|drain|cordon|taint|label|annotate|set)\b", "Cluster change needs approval."),
    (r"\bhelm" + FLAGS + r"\s+(install|upgrade|uninstall|rollback|delete)\b", "Cluster change needs approval."),
    (r"\bmongo(sh)?\b[^\n]*\.(drop|dropDatabase|dropIndex(es)?|deleteMany|deleteOne|remove|updateMany|updateOne|replaceOne|findOneAndDelete|renameCollection)\s*\(", "Database write needs approval."),
    (r"(?i)\b(psql|mysql|mariadb|sqlite3)\b[^\n]*\b(drop\s+(table|database|schema)|truncate\b|delete\s+from)", "Database write needs approval."),
    (r"\bcrictl\s+(rmi|rmp|rm)\b|\bctr\b[^;&|\n]*\s(rm|remove|prune)\b", "Removes containers or images."),
    (r"\bdocker\s+((system|image|volume|container|builder)\s+prune|rmi?)\b", "Removes containers or images."),
    (r"\bterraform\s+(apply|destroy)\b", "Infrastructure change needs approval."),
    (r"\bdocker\s+push\b", "Publishing an image needs approval."),
    (r"\bgh\s+(pr\s+(create|merge)|release\s+create)\b", "Publishing needs approval."),
]


def decide(command):
    for pattern, reason in DENY:
        if re.search(pattern, command):
            return "deny", reason
    for pattern, reason in ASK:
        if re.search(pattern, command):
            return "ask", reason
    return None, None


def main():
    payload = json.load(sys.stdin)
    if "toolCall" in payload:
        args = payload["toolCall"].get("args") or {}
        decision, reason = decide(str(args.get("CommandLine") or ""))
        if decision:
            json.dump({"decision": "force_ask" if decision == "ask" else decision, "reason": reason}, sys.stdout)
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    decision, reason = decide(command)
    if decision:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }}, sys.stdout)


if __name__ == "__main__":
    main()
