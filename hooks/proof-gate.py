"""Stop (Claude Code, Codex, Antigravity): if this turn edited files, require a check
after the last edit and a reported result, or an explicit "not verified"."""
import json
import os
import re
import sys

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
# Markdown edits (plans, notes, memory) have no build or test to run.
DOC_SUFFIXES = (".md", ".markdown")
REPORTED = re.compile(r"(?i)\b(checks?|tests?|verified|verification|ran)\b[^\n]*[:`]")
NOT_VERIFIED = re.compile(r"(?i)not verified")


def blocks(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def is_user_prompt(entry):
    if entry.get("type") != "user" or entry.get("isSidechain"):
        return False
    return not any(b.get("type") == "tool_result" for b in blocks(entry))


def claude_turn(entries):
    start = max((i for i, e in enumerate(entries) if is_user_prompt(e)), default=-1)
    steps, final_text = [], ""
    for entry in entries[start + 1:]:
        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        for b in blocks(entry):
            if b.get("type") == "tool_use":
                name = b.get("name")
                path = str((b.get("input") or {}).get("file_path") or "").lower()
                if name in EDIT_TOOLS and path.endswith(DOC_SUFFIXES):
                    steps.append("doc")
                else:
                    steps.append("edit" if name in EDIT_TOOLS else "run" if name == "Bash" else "other")
                final_text = ""
            elif b.get("type") == "text":
                final_text += b.get("text", "")
    return steps, final_text


def codex_turn(entries):
    def kind(entry):
        return entry.get("type"), (entry.get("payload") or {}).get("type")
    start = max((i for i, e in enumerate(entries) if kind(e) == ("event_msg", "user_message")), default=-1)
    steps, final_text = [], ""
    for entry in entries[start + 1:]:
        payload = entry.get("payload") or {}
        if kind(entry) == ("event_msg", "patch_apply_end"):
            steps.append("edit")
        elif kind(entry) == ("event_msg", "agent_message"):
            final_text = payload.get("message") or ""
        elif entry.get("type") == "response_item" and payload.get("type") in ("custom_tool_call", "function_call"):
            call = "%s %s %s" % (payload.get("name"), payload.get("input"), payload.get("arguments"))
            if re.search(r"exec_command|\bshell\b|local_shell", call):
                steps.append("run")
            final_text = ""
    return steps, final_text


def antigravity_turn(entries):
    start = max((i for i, e in enumerate(entries) if e.get("type") == "USER_INPUT"), default=-1)
    steps, final_text = [], ""
    for entry in entries[start + 1:]:
        if entry.get("type") != "PLANNER_RESPONSE":
            continue
        calls = entry.get("tool_calls") or []
        for call in calls:
            name = call.get("name") or ""
            steps.append("edit" if name in ("edit_file", "write_file") else "run" if name == "run_command" else "other")
        final_text = "" if calls else entry.get("content") or ""
    return steps, final_text


def verdict(entries, last_message=None):
    if any(e.get("type") == "USER_INPUT" for e in entries):
        turn = antigravity_turn
    elif any(e.get("type") in ("event_msg", "response_item") for e in entries):
        turn = codex_turn
    else:
        turn = claude_turn
    steps, final_text = turn(entries)
    if last_message:
        final_text = last_message
    edits = [i for i, step in enumerate(steps) if step == "edit"]
    if not edits or NOT_VERIFIED.search(final_text):
        return None
    if "run" not in steps[edits[-1] + 1:]:
        return ("You edited files but ran no check after the last edit. Run the "
                "relevant test/build/check, or say \"not verified\" and why.")
    if not REPORTED.search(final_text):
        return ("Report the check you ran and its result (e.g. \"Checks: <command> "
                "-> <result>\"), or say \"not verified\".")
    return None


def main():
    payload = json.load(sys.stdin)
    antigravity = "transcriptPath" in payload
    if payload.get("stop_hook_active") or payload.get("executionNum", 1) > 1:
        return
    if antigravity and payload.get("terminationReason") != "NO_TOOL_CALL":
        return
    path = payload.get("transcript_path") or payload.get("transcriptPath")
    if not path or not os.path.isfile(path):
        return
    entries = []
    with open(path) as transcript:
        for line in transcript:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    reason = verdict(entries, payload.get("last_assistant_message"))
    if reason:
        json.dump({"decision": "continue" if antigravity else "block", "reason": reason}, sys.stdout)


if __name__ == "__main__":
    main()
