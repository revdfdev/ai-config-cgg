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

AGENTS = {
    "claude": {"label": "Claude Code", "dir": ".claude", "rules": ".claude/CLAUDE.md",
               "skills": ".claude/skills", "hooks": (".claude/settings.json", "claude/settings.json", "events")},
    "codex": {"label": "Codex", "dir": ".codex", "rules": ".codex/AGENTS.md", "skills": ".codex/skills",
              "hooks": (".codex/hooks.json", "codex/hooks.json", "events"),
              "rulesfile": (".codex/rules/ai-config-ccg.rules", "codex/guard.rules")},
    "gemini": {"label": "Gemini / Antigravity", "dir": ".gemini", "rules": ".gemini/GEMINI.md",
               "skills": ".gemini/config/skills", "hooks": (".gemini/config/hooks.json", "gemini/hooks.json", "groups")},
}
COMPONENTS = [
    ("rules", "Rules", "Adds the shared working rules to each agent's rules file. Your own text stays."),
    ("skills", "Skills", "Links skills such as plan, tdd and review into each agent."),
    ("safety", "Safety guard", "Asks you first before push, rm -rf, kubectl/helm changes, database drops."),
    ("checks", "Proof check", "Agent can't say 'done' after edits without naming a check; short per-prompt reminder."),
]


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


def real_read_key():
    if os.name == "nt":
        import msvcrt
        c = msvcrt.getwch()
        if c in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        return {"\r": "enter", " ": "space", "\x03": "quit", "q": "quit", "a": "all"}.get(c, c)
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        c = sys.stdin.read(1)
        if c == "\x1b":
            return {"[A": "up", "[B": "down"}.get(sys.stdin.read(2), "")
        return {"\r": "enter", "\n": "enter", " ": "space", "\x03": "quit", "q": "quit",
                "k": "up", "j": "down", "a": "all"}.get(c, c)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def interactive():
    return sys.stdin.isatty() and sys.stdout.isatty()


def checkbox(title, items, read_key=None, plain_input=None, out=None, single=False):
    """items: (key, label, description, checked). Returns the checked keys in order."""
    out = out or sys.stdout
    checked = [bool(i[3]) for i in items]
    if read_key is None and plain_input is None:
        if interactive():
            read_key = real_read_key
            if os.name == "nt":
                os.system("")  # enables ANSI escapes in the Windows console
        else:
            plain_input = input
    if read_key:
        pos, drawn = 0, 0
        hint = "↑/↓ move · enter choose" if single else "↑/↓ move · space tick · a all · enter continue"
        while True:
            if drawn:
                out.write("\x1b[%dA\x1b[J" % drawn)
            lines = [bold(title), dim(hint)]
            for n, (key, label, desc, _) in enumerate(items):
                mark = ("(•)" if n == pos else "( )") if single else ("[x]" if checked[n] else "[ ]")
                cur = ">" if n == pos else " "
                lines.append("%s %s %s  %s" % (cur, green(mark) if checked[n] or single and n == pos else mark,
                                               bold(label) if n == pos else label, dim(desc)))
            out.write("\n".join(lines) + "\n")
            out.flush()
            drawn = len(lines)
            k = read_key()
            if k == "up":
                pos = (pos - 1) % len(items)
            elif k == "down":
                pos = (pos + 1) % len(items)
            elif k == "space" and not single:
                checked[pos] = not checked[pos]
            elif k == "all" and not single:
                checked = [not all(checked)] * len(items)
            elif k == "enter":
                if single:
                    return [items[pos][0]]
                return [i[0] for i, c in zip(items, checked) if c]
            elif k == "quit":
                raise SystemExit(130)
    while True:
        out.write(bold(title) + "\n")
        for n, (key, label, desc, _) in enumerate(items, 1):
            mark = "" if single else ("[x] " if checked[n - 1] else "[ ] ")
            out.write("  %d. %s%s  %s\n" % (n, mark, label, dim(desc)))
        prompt = "Pick a number: " if single else "Numbers to toggle (e.g. 1 3), Enter to continue: "
        out.flush()
        try:
            answer = plain_input(prompt).strip()
        except EOFError:  # no one to ask (piped/CI): keep the defaults
            out.write("\n")
            return [items[0][0]] if single else [i[0] for i, c in zip(items, checked) if c]
        nums = [int(x) - 1 for x in answer.replace(",", " ").split() if x.isdigit() and 0 < int(x) <= len(items)]
        if single:
            if nums:
                return [items[nums[0]][0]]
            continue
        if not answer:
            return [i[0] for i, c in zip(items, checked) if c]
        for n in nums:
            checked[n] = not checked[n]


def confirm(question):
    if not interactive():
        return False
    return input("%s [y/N] " % question).strip().lower() in ("y", "yes")


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


def build_plan(agents, components, skills, clash_choice):
    plan = Plan()
    deny = render(read_json(ROOT / "claude/settings.json")).get("permissions", {}).get("deny", [])
    agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8").rstrip("\n").replace("~/ai-config-ccg/", ROOT.as_posix() + "/")
    block = "%s\n%s\n%s\n" % (START, agents_md, END)
    for key in agents:
        a = AGENTS[key]
        h = home()
        if "rules" in components:
            p = h / a["rules"]
            old = p.read_text(encoding="utf-8") if p.exists() else ""
            if START in old and END in old:
                before, rest = old.split(START, 1)
                new = before + block.rstrip("\n") + rest.split(END, 1)[1]
            else:
                new = old + ("\n" if old and not old.endswith("\n") else "") + ("\n" if old else "") + block
            if new != old:
                plan.files[p] = new.encode("utf-8")
                plan.summary.append("%s: %s shared rules block in %s" % (a["label"], "update" if START in old else "add", tilde(p)))
        if components & {"safety", "checks"}:
            rel, tpl, fmt = a["hooks"]
            p = h / rel
            try:
                cur = read_json(p) or {}
            except ValueError:
                plan.notes.append("skipped %s: not valid JSON, left untouched" % tilde(p))
                cur = None
            if cur is not None:
                before = dump_json(cur)
                kept = len(cur)
                ours = render(read_json(ROOT / tpl))
                n = merge_events(cur, ours, components) if fmt == "events" else merge_groups(cur, ours, components)
                added_deny = []
                if key == "claude" and "safety" in components:
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
            dst, src = a["rulesfile"]
            dst = h / dst
            data = (ROOT / src).read_bytes()
            if not dst.exists() or dst.read_bytes() != data:
                plan.files[dst] = data
                plan.summary.append("%s: write command rules %s" % (a["label"], tilde(dst)))
        if "skills" in components:
            sdir = h / a["skills"]
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
                    choice = clash_choice(a["label"], name, dst)
                    if choice == "skip":
                        plan.notes.append("kept your own %s (skill '%s' not installed for %s)" % (tilde(dst), name, a["label"]))
                        continue
                    plan.links.append((src, dst, "backup"))
                    plan.summary.append("%s: replace your skill %s (backed up)" % (a["label"], name))
                    continue
                plan.links.append((src, dst, None))
                plan.summary.append("%s: add skill %s" % (a["label"], name))
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


def apply_plan(plan, selection):
    st = load_state()
    st.update(root=ROOT.as_posix(), selection=selection)
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
    return [k for k, a in AGENTS.items() if (home() / a["dir"]).is_dir()]


def parse(argv):
    ap = argparse.ArgumentParser(description="Install ai-config-ccg rules, skills and hooks.")
    ap.add_argument("--yes", "-y", action="store_true", help="accept defaults, no questions")
    ap.add_argument("--agents", help="comma list: " + ",".join(AGENTS))
    ap.add_argument("--only", help="comma list: " + ",".join(c[0] for c in COMPONENTS))
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if anything is missing or outdated")
    mode.add_argument("--uninstall", action="store_true", help="remove only what this installer added")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse(argv)
    if args.uninstall:
        if not args.yes and interactive() and not confirm("Remove everything ai-config-ccg added?"):
            return 1
        return uninstall(args.dry_run)

    if args.check:
        sel = load_state().get("selection")
        if not sel:
            print("Not installed (no %s)." % tilde(state_path()))
            return 1
        plan = build_plan(sel["agents"], set(sel["components"]), sel["skills"], lambda *_: "skip")
        if plan.empty():
            print(green("Up to date."))
            return 0
        print(yellow("Out of date:"))
        for s in plan.summary:
            print("  - " + s)
        return 1

    ask = not args.yes
    found = detect()
    if args.agents:
        agents = [a.strip() for a in args.agents.split(",") if a.strip() in AGENTS]
    elif ask:
        print(bold("ai-config-ccg installer") + dim("  (nothing is written until you confirm)\n"))
        items = [(k, a["label"], ("found " + tilde(home() / a["dir"])) if k in found else "not found", k in found)
                 for k, a in AGENTS.items()]
        agents = checkbox("Which agents?", items)
    else:
        agents = found
    if not agents:
        print("No agents selected or found. Use --agents claude,codex,gemini.")
        return 1

    if args.only:
        components = {c.strip() for c in args.only.split(",")}
    elif ask:
        components = set(checkbox("\nWhat to install?", [(k, l, d, True) for k, l, d in COMPONENTS]))
    else:
        components = {c[0] for c in COMPONENTS}

    skills = [n for n, _ in skills_available()]
    if "skills" in components and ask:
        skills = checkbox("\nWhich skills?", [(n, n, d[:70], True) for n, d in skills_available()])

    def clash(label, name, path):
        if not ask:
            return "skip"
        return checkbox("\n%s already has a skill called '%s' (%s). What to do?" % (label, name, tilde(path)),
                        [("skip", "Keep mine", "don't install this one", True),
                         ("replace", "Use the new one", "yours is backed up and restored on uninstall", False)],
                        single=True)[0]

    plan = build_plan(agents, components, skills, clash)
    print("\n" + bold("Review"))
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
    if ask and not confirm("\nApply these changes?"):
        print("Cancelled. Nothing changed.")
        return 1
    apply_plan(plan, {"agents": agents, "components": sorted(components), "skills": skills})
    print(green("\nDone.") + " Changed files were backed up next to themselves (*.bak-<time>).")
    print("Check:  %s install.py --check" % ("py" if os.name == "nt" else "python3"))
    print("Undo:   %s install.py --uninstall" % ("py" if os.name == "nt" else "python3"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
