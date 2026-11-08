"""Per-prompt reminder. Default output suits Claude Code/Codex UserPromptSubmit;
--antigravity suits Antigravity PreInvocation."""
import json
import sys

TEXT = ('Reminder: stay inside this request; read the owning code before editing; '
        'end with checks run and results, or say "not verified". Suggest a new thread when context is long.')

if "--antigravity" in sys.argv[1:]:
    json.dump({"injectSteps": [{"ephemeralMessage": TEXT}]}, sys.stdout)
else:
    json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": TEXT}}, sys.stdout)
