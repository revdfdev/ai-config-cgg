#!/usr/bin/env python3
"""Interactive installer for ai-config-ccg (Linux, macOS, Windows; Python 3.8+, stdlib only).

Adds this repo's rules, skills and hooks to Claude Code, Codex and Gemini/Antigravity
without replacing your own config: JSON files are merged, rules files get one marked
block, skills are linked (copied where links are not allowed). Everything added is
recorded in ~/.ai-config-ccg/state.json so --check and --uninstall touch only that.

  python3 install.py              interactive
  python3 install.py --yes        accept defaults (detected agents, everything)
  python3 install.py --dry-run    show what would change
  python3 install.py --check      exit 1 if anything is missing or outdated
  python3 install.py --uninstall  remove only what this installer added
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
START, END = "<!-- ai-config-ccg:start -->", "<!-- ai-config-ccg:end -->"
GROUP_PREFIX = "ai-config-ccg-"

AGENTS = {a["key"]: a for a in json.loads((ROOT / "agents.json").read_text(encoding="utf-8"))["agents"]}
COMPONENTS = ["rules", "skills", "safety", "checks"]


def parts_of(agent):
    """The parts this agent supports, from its agents.json entry."""
    out = []
    if "rules" in agent:
        out.append("rules")
    if "skills" in agent:
        out.append("skills")
    if "hooks" in agent or "rulesfile" in agent:
        out.append("safety")
    if "hooks" in agent:
        out.append("checks")
    return out


# ---------- paths, io ----------

def home():
    return Path(os.environ.get("AI_CONFIG_CCG_HOME") or Path.home())


def state_path():
    return home() / ".ai-config-ccg" / "state.json"


def tilde(p):
    try:
        return "~/" + Path(p).relative_to(home()).as_posix()
    except ValueError:
        return str(p)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def read_json(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def dump_json(obj):
    return json.dumps(obj, indent=2) + "\n"


def python_cmd():
    py = Path(sys.executable).as_posix()
    return '"%s"' % py if " " in py else py


def render(obj):
    """Fill @PYTHON@ and @ROOT@ in every string of a parsed template."""
    if isinstance(obj, dict):
        return {k: render(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render(v) for v in obj]
    if isinstance(obj, str):
        return obj.replace("@PYTHON@", python_cmd()).replace("@ROOT@", ROOT.as_posix())
    return obj


def is_ours(command):
    return (ROOT.as_posix() + "/hooks/") in command


def component_of(command):
    return "safety" if "guard-bash.py" in command else "checks"


def skills_available():
    out = []
    for manifest in sorted((ROOT / "skills").glob("*/SKILL.md")):
        desc = ""
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip()
                break
        out.append((manifest.parent.name, desc))
    return out


# ---------- terminal UI ----------

class Style:
    on = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

    @classmethod
    def c(cls, code, text):
        return "\x1b[%sm%s\x1b[0m" % (code, text) if cls.on else text


def bold(t): return Style.c("1", t)
def dim(t): return Style.c("2", t)
def green(t): return Style.c("32", t)
def yellow(t): return Style.c("33", t)


def ask(prompt):
    """input() that treats a closed stdin (pipe, CI) as pressing Enter."""
    try:
        return input(prompt).strip()
    except EOFError:
        print()
        return ""


def yes(question, default):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = ask("%s %s " % (question, hint)).lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer y or n.")


def pick_agents(found):
    keys = list(AGENTS)
    print(bold("Agents"))
    for n, k in enumerate(keys, 1):
        print("  %d. %-22s %s" % (n, AGENTS[k]["label"], green("(found)") if k in found else ""))
    while True:
        answer = ask("Which agents? (numbers, e.g. 1 3 4; Enter = the found ones): ")
        if not answer:
            return found
        nums = answer.replace(",", " ").split()
        if all(x.isdigit() and 0 < int(x) <= len(keys) for x in nums):
            return [keys[int(x) - 1] for x in nums]
        print("  Use numbers from the list.")


def has_own_text(path):
    return path.exists() and path.read_text(encoding="utf-8").strip() and START not in path.read_text(encoding="utf-8")


def ask_parts(agent, allowed, skill_names):
    h = home()
    chosen = set()
    print("\n" + bold(agent["label"]))
    for part in parts_of(agent):
        if part not in allowed:
            continue
        if part == "rules":
            r = agent["rules"]
            p = h / r["path"]
            if r["mode"] == "file":
                q, d = "Add the shared working rules as %s?" % tilde(p), True
            elif has_own_text(p):
                q, d = "Add the shared working rules to %s? (it already has your own rules; this adds a second block)" % tilde(p), False
            else:
                q, d = "Add the shared working rules to %s?" % tilde(p), True
        elif part == "skills":
            q, d = "Add %d skills (%s)?" % (len(skill_names), ", ".join(skill_names)), True
        elif part == "safety":
            q, d = "Add the safety guard? It asks you before push, rm -rf, kubectl/helm changes, database drops.", True
        else:
            q, d = "Add the proof check? It stops the agent saying 'done' after edits without naming a check.", True
        if yes("  " + q, d):
            chosen.add(part)
    return chosen


# ---------- plan ----------

class Plan:
    def __init__(self):
        self.files = {}   # path -> new bytes
        self.links = []   # (src, dst, replace_existing)
        self.unlinks = []  # stale links
        self.notes = []
        self.summary = []
        self.deny_added = {}

    def empty(self):
        return not (self.files or self.links or self.unlinks)


def merge_events(target, ours, components):
    """Claude/Codex hook format: {"hooks": {event: [{matcher?, hooks: [..]}]}}."""
    added = 0
    hooks = target.setdefault("hooks", {})
    for event, groups in ours.get("hooks", {}).items():
        existing = [h.get("command") for g in hooks.get(event, []) for h in g.get("hooks", [])]
        for group in groups:
            mine = [h for h in group.get("hooks", []) if component_of(h["command"]) in components
                    and h["command"] not in existing]
            if mine:
                hooks.setdefault(event, []).append(dict(group, hooks=mine))
                added += len(mine)
    if not hooks:
        target.pop("hooks")
    return added


def merge_groups(target, ours, components):
    """Gemini format: {"ai-config-ccg-<name>": {event: [...]}}."""
    added = 0
    for name, body in ours.items():
        cmds = json.dumps(body)
        if component_of(cmds) in components and target.get(name) != body:
            target[name] = body
            added += 1
    return added


def build_plan(selection, skills, clash_choice):
    """selection: {agent_key: set of parts}."""
    plan = Plan()
    deny = render(read_json(ROOT / "claude/settings.json")).get("permissions", {}).get("deny", [])
    agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8").rstrip("\n").replace("~/ai-config-ccg/", ROOT.as_posix() + "/")
    block = "%s\n%s\n%s\n" % (START, agents_md, END)
    h = home()
    for key, components in selection.items():
        a = AGENTS[key]
        components = set(components) & set(parts_of(a))
        if "rules" in components:
            r = a["rules"]
            p = h / r["path"]
            old = p.read_text(encoding="utf-8") if p.exists() else ""
            if r["mode"] == "file":
                new = agents_md + "\n"
            elif START in old and END in old:
                before, rest = old.split(START, 1)
                new = before + block.rstrip("\n") + rest.split(END, 1)[1]
            else:
                new = old + ("\n" if old and not old.endswith("\n") else "") + ("\n" if old else "") + block
            if r.get("max_chars") and len(new) > r["max_chars"]:
                plan.notes.append("skipped rules for %s: %s would exceed its %d-character limit"
                                  % (a["label"], tilde(p), r["max_chars"]))
            elif new != old:
                plan.files[p] = new.encode("utf-8")
                verb = "write" if r["mode"] == "file" else ("update" if START in old else "add")
                plan.summary.append("%s: %s shared rules %s %s" % (a["label"], verb, "in" if r["mode"] == "block" else "as", tilde(p)))
        if components & {"safety", "checks"} and "hooks" in a:
            hk = a["hooks"]
            p = h / hk["path"]
            try:
                cur = read_json(p) or {}
            except ValueError:
                plan.notes.append("skipped %s: not valid JSON, left untouched" % tilde(p))
                cur = None
            if cur is not None:
                before = dump_json(cur)
                kept = len(cur)
                ours = render(read_json(ROOT / hk["template"]))
                n = merge_events(cur, ours, components) if hk["format"] == "events" else merge_groups(cur, ours, components)
                added_deny = []
                if hk.get("deny") and "safety" in components:
                    have = cur.setdefault("permissions", {}).setdefault("deny", [])
                    added_deny = [d for d in deny if d not in have]
                    have.extend(added_deny)
                after = dump_json(cur)
                if after != before:
                    plan.files[p] = after.encode("utf-8")
                    plan.deny_added[str(p)] = added_deny
                    extra = (", %d deny rule(s)" % len(added_deny)) if added_deny else ""
                    plan.summary.append("%s: add %d hook(s)%s to %s, keep your %d existing setting(s)"
                                        % (a["label"], n, extra, tilde(p), kept))
        if "safety" in components and "rulesfile" in a:
            dst = h / a["rulesfile"]["path"]
            data = (ROOT / a["rulesfile"]["source"]).read_bytes()
            if not dst.exists() or dst.read_bytes() != data:
                plan.files[dst] = data
                plan.summary.append("%s: write command rules %s" % (a["label"], tilde(dst)))
        if "skills" in components:
            sdir = h / a["skills"]
            new_skills = []
            for name in skills:
                src, dst = ROOT / "skills" / name, sdir / name
                if dst.is_symlink() and Path(os.path.realpath(dst)) == src.resolve():
                    continue
                if (dst.exists() or dst.is_symlink()) and str(dst) in load_state().get("links", {}):
                    if dst.is_symlink() or same_tree(src, dst):
                        continue
                    plan.links.append((src, dst, "refresh"))
                    plan.summary.append("%s: refresh skill %s" % (a["label"], name))
                    continue
                if dst.exists() or dst.is_symlink():
                    if not clash_choice(a["label"], name, dst):
                        plan.notes.append("kept your own %s (skill '%s' not installed for %s)" % (tilde(dst), name, a["label"]))
                        continue
                    plan.links.append((src, dst, "backup"))
                    plan.summary.append("%s: replace your skill %s (backed up)" % (a["label"], name))
                    continue
                plan.links.append((src, dst, None))
                new_skills.append(name)
            if new_skills:
                plan.summary.append("%s: add %d skill(s) to %s: %s" % (a["label"], len(new_skills), tilde(sdir), ", ".join(new_skills)))
            if sdir.is_dir():
                for p in sdir.iterdir():
                    if p.is_symlink() and os.path.realpath(p).startswith(str(ROOT / "skills")) \
                            and not (Path(os.path.realpath(p)) / "SKILL.md").exists():
                        plan.unlinks.append(p)
                        plan.summary.append("%s: remove stale skill link %s" % (a["label"], p.name))
    return plan


def same_tree(a, b):
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    return fa == fb and all((a / f).read_bytes() == (b / f).read_bytes() for f in fa)


# ---------- state ----------

def load_state():
    try:
        return json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(st):
    state_path().parent.mkdir(parents=True, exist_ok=True)
    state_path().write_text(dump_json(st), encoding="utf-8")


# ---------- apply ----------

def link_or_copy(src, dst):
    if not os.environ.get("AI_CONFIG_CCG_FORCE_COPY"):
        try:
            os.symlink(src, dst, target_is_directory=True)
            return "link"
        except (OSError, NotImplementedError):
            pass  # Windows without symlink rights: copy instead
    shutil.copytree(src, dst)
    return "copy"


def remove_path(p):
    if p.is_symlink() or p.is_file():
        p.unlink()
    elif p.is_dir():
        shutil.rmtree(p)


def make_dirs(d, created):
    missing = []
    while not d.exists():
        missing.append(d)
        d = d.parent
    for m in reversed(missing):
        m.mkdir()
        created.append(str(m))


def apply_plan(plan, selection, skills):
    st = load_state()
    st.update(root=ROOT.as_posix(), selection=selection, skills=skills)
    files, links = st.setdefault("files", {}), st.setdefault("links", {})
    created = st.setdefault("dirs", [])
    deny, backups = st.setdefault("deny_added", {}), st.setdefault("skill_backups", {})
    ts = stamp()
    for p, data in plan.files.items():
        make_dirs(p.parent, created)
        rec = files.get(str(p))
        if rec is None:
            backup = None
            if p.exists():
                backup = str(p.with_name("%s.bak-%s" % (p.name, ts)))
                shutil.copy2(p, backup)
            rec = files[str(p)] = {"backup": backup}
        p.write_bytes(data)
        rec["written"] = sha(data)
        if plan.deny_added.get(str(p)):
            deny.setdefault(str(p), []).extend(plan.deny_added[str(p)])
    for src, dst, mode in plan.links:
        make_dirs(dst.parent, created)
        if mode == "backup":
            bdir = home() / ".ai-config-ccg" / "backups" / ts
            bdir.mkdir(parents=True, exist_ok=True)
            target = bdir / ("%s-%s" % (dst.parent.parent.name.lstrip("."), dst.name))
            shutil.move(str(dst), str(target))
            backups[str(dst)] = str(target)
        elif mode == "refresh":
            remove_path(dst)
        links[str(dst)] = link_or_copy(src, dst)
    for p in plan.unlinks:
        p.unlink()
        links.pop(str(p), None)
    save_state(st)


# ---------- uninstall ----------

def strip_ours(p, deny_added):
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".md":
        if START in text and END in text:
            before, rest = text.split(START, 1)
            after = rest.split(END, 1)[1]
            before = before[:-1] if before.endswith("\n\n") else before
            text = before + after.lstrip("\n")
        return text
    if p.suffix == ".rules":
        return None
    try:
        obj = json.loads(text)
    except ValueError:
        return text
    for name in [k for k in obj if k.startswith(GROUP_PREFIX)]:
        del obj[name]
    hooks = obj.get("hooks")
    if isinstance(hooks, dict):
        for event in list(hooks):
            groups = []
            for g in hooks[event]:
                keep = [h for h in g.get("hooks", []) if not is_ours(h.get("command", ""))]
                if keep:
                    groups.append(dict(g, hooks=keep))
            if groups:
                hooks[event] = groups
            else:
                del hooks[event]
        if not hooks:
            del obj["hooks"]
    d = obj.get("permissions", {}).get("deny")
    if isinstance(d, list):
        obj["permissions"]["deny"] = [x for x in d if x not in deny_added]
    return dump_json(obj)


def uninstall(dry):
    st = load_state()
    if not st:
        print("Nothing to uninstall: no record of an install in %s." % tilde(state_path()))
        return 0
    lines = []
    for dst, kind in st.get("links", {}).items():
        p = Path(dst)
        if p.exists() or p.is_symlink():
            lines.append("remove skill %s" % tilde(p))
            if not dry:
                remove_path(p)
        b = st.get("skill_backups", {}).get(dst)
        if b and Path(b).exists():
            lines.append("put back your skill %s" % tilde(p))
            if not dry:
                shutil.move(b, dst)
    for path, rec in st.get("files", {}).items():
        p = Path(path)
        if not p.exists():
            continue
        backup = rec.get("backup")
        if sha(p.read_bytes()) == rec.get("written"):
            if backup and Path(backup).exists():
                lines.append("restore %s exactly as it was" % tilde(p))
                if not dry:
                    shutil.move(backup, path)
            else:
                lines.append("delete %s (created by the installer)" % tilde(p))
                if not dry:
                    p.unlink()
            continue
        new = strip_ours(p, st.get("deny_added", {}).get(path, []))
        lines.append("remove our entries from %s, keep your later edits" % tilde(p))
        if not dry:
            p.unlink() if new is None else p.write_text(new, encoding="utf-8")
    for line in lines:
        print("  - " + line)
    if dry:
        print("Dry run: nothing changed.")
    else:
        for d in sorted(st.get("dirs", []), key=len, reverse=True):
            try:
                Path(d).rmdir()  # only if empty: anything you added stays
            except OSError:
                pass
        state_path().unlink()
        try:
            state_path().parent.rmdir()
        except OSError:
            pass
        print(green("Uninstalled.") + " Your own files and skills were left in place.")
    return 0


# ---------- main ----------

def detect():
    return [k for k, a in AGENTS.items() if any((home() / d).is_dir() for d in a["detect"])]


def parse(argv):
    ap = argparse.ArgumentParser(description="Install ai-config-ccg rules, skills and hooks.")
    ap.add_argument("--yes", "-y", action="store_true", help="no questions: found agents, every part they support")
    ap.add_argument("--agents", help="comma list: " + ",".join(AGENTS))
    ap.add_argument("--only", help="comma list: " + ",".join(COMPONENTS))
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if anything is missing or outdated")
    mode.add_argument("--uninstall", action="store_true", help="remove only what this installer added")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse(argv)
    py = "py" if os.name == "nt" else "python3"
    if args.uninstall:
        if not args.yes and not yes("Remove everything ai-config-ccg added?", False):
            return 1
        return uninstall(args.dry_run)

    skills = [n for n, _ in skills_available()]
    if args.check:
        st = load_state()
        if not st.get("selection"):
            print("Not installed (no %s)." % tilde(state_path()))
            return 1
        plan = build_plan({k: set(v) for k, v in st["selection"].items()}, st.get("skills", skills), lambda *_: False)
        if plan.empty():
            print(green("Up to date."))
            return 0
        print(yellow("Out of date:"))
        for s in plan.summary:
            print("  - " + s)
        return 1

    allowed = {c.strip() for c in args.only.split(",")} if args.only else set(COMPONENTS)
    found = detect()
    if args.agents:
        agents = [a.strip() for a in args.agents.split(",") if a.strip() in AGENTS]
    elif args.yes:
        agents = found
    else:
        print(bold("ai-config-ccg installer") + dim("  (nothing is written until you confirm)\n"))
        agents = pick_agents(found)
    if not agents:
        print("No agents selected or found. Use --agents %s." % ",".join(AGENTS))
        return 1

    if args.yes:
        selection = {k: set(parts_of(AGENTS[k])) & allowed for k in agents}
    else:
        selection = {k: ask_parts(AGENTS[k], allowed, skills) for k in agents}

    def clash(label, name, path):
        if args.yes:
            return False
        return yes("  %s already has a skill called '%s' (%s). Replace it with this one? (yours is backed up)"
                   % (label, name, tilde(path)), False)

    plan = build_plan(selection, skills, clash)
    print("\n" + bold("Here's what will change"))
    for s in plan.summary:
        print("  + " + s)
    for n in plan.notes:
        print("  " + dim("· " + n))
    if plan.empty():
        print(green("Everything is already up to date."))
        return 0
    if args.dry_run:
        print("Dry run: nothing changed.")
        return 0
    if not args.yes and not yes("\nGo ahead?", False):
        print("Cancelled. Nothing changed.")
        return 1
    apply_plan(plan, {k: sorted(v) for k, v in selection.items()}, skills)
    print(green("\nDone.") + " Changed files were backed up next to themselves (*.bak-<time>).")
    print("Check:  %s install.py --check" % py)
    print("Undo:   %s install.py --uninstall" % py)
    return 0


if __name__ == "__main__":
    sys.exit(main())
