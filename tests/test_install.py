"""Installer tests. Run: python3 -m unittest discover -s tests"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.py"
START = "<!-- ai-config-ccg:start -->"
sys.path.insert(0, str(ROOT))

USER_SETTINGS = {
    "theme": "dark",
    "permissions": {"allow": ["Bash(ls)"], "deny": ["Bash(rm -rf /)"]},
    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]},
}


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="aiccg-home-"))
        self.addCleanup(shutil.rmtree, self.home, True)
        for d in (".claude", ".codex", ".gemini"):
            (self.home / d).mkdir()

    def run_install(self, *args, env=None, ok=True, answers=None):
        e = dict(os.environ, AI_CONFIG_CCG_HOME=str(self.home), NO_COLOR="1")
        e.update(env or {})
        kw = {"input": answers} if answers is not None else {"stdin": subprocess.DEVNULL}
        p = subprocess.run([sys.executable, str(INSTALL), *args], env=e,
                           capture_output=True, text=True, **kw)
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def write(self, rel, text):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def settings(self):
        return json.loads((self.home / ".claude/settings.json").read_text(encoding="utf-8"))

    def snapshot(self):
        return sorted(str(p.relative_to(self.home)) for p in self.home.rglob("*"))


class DryRun(Base):
    def test_dry_run_writes_nothing(self):
        before = self.snapshot()
        out = self.run_install("--yes", "--dry-run").stdout
        self.assertEqual(self.snapshot(), before)
        self.assertIn("settings.json", out)
        self.assertIn("nothing changed", out.lower())


class Merge(Base):
    def test_settings_keeps_user_keys_and_adds_ours_once(self):
        self.write(".claude/settings.json", json.dumps(USER_SETTINGS, indent=2))
        self.run_install("--yes")
        s = self.settings()
        self.assertEqual(s["theme"], "dark")
        self.assertIn("Bash(ls)", s["permissions"]["allow"])
        self.assertIn("Bash(rm -rf /)", s["permissions"]["deny"])
        self.assertIn("Bash(git push --force *)", s["permissions"]["deny"])
        stop = [h["command"] for g in s["hooks"]["Stop"] for h in g["hooks"]]
        self.assertIn("echo mine", stop)
        ours = [c for c in stop if "proof-gate.py" in c]
        self.assertEqual(len(ours), 1)
        self.assertIn(ROOT.as_posix(), ours[0])
        self.assertNotIn("$HOME", ours[0])
        self.assertTrue(list((self.home / ".claude").glob("settings.json.bak-*")))

    def test_second_run_changes_nothing(self):
        self.write(".claude/settings.json", json.dumps(USER_SETTINGS, indent=2))
        self.write(".claude/CLAUDE.md", "my rules\n")
        self.run_install("--yes")
        first = {p: (self.home / p).read_bytes() for p in (".claude/settings.json", ".claude/CLAUDE.md")}
        self.run_install("--yes")
        for p, b in first.items():
            self.assertEqual((self.home / p).read_bytes(), b, p)

    def test_rules_block_appended_not_replaced(self):
        self.write(".claude/CLAUDE.md", "my rules\n")
        self.run_install("--yes")
        text = (self.home / ".claude/CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("my rules\n"))
        self.assertEqual(text.count("<!-- ai-config-ccg:start -->"), 1)
        self.assertIn("# Global Rules", text)

    def test_gemini_and_codex_hooks_merged(self):
        self.write(".gemini/config/hooks.json", json.dumps({"my-group": {"Stop": []}}))
        self.write(".codex/hooks.json", json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo c"}]}]}}))
        self.run_install("--yes")
        g = json.loads((self.home / ".gemini/config/hooks.json").read_text())
        self.assertIn("my-group", g)
        self.assertIn("ai-config-ccg-guard", g)
        c = json.loads((self.home / ".codex/hooks.json").read_text())
        cmds = [h["command"] for grp in c["hooks"]["Stop"] for h in grp["hooks"]]
        self.assertIn("echo c", cmds)
        self.assertTrue(any("proof-gate.py" in x for x in cmds))
        self.assertTrue((self.home / ".codex/rules/ai-config-ccg.rules").exists())


class Skills(Base):
    def test_clash_skipped_by_default_others_linked(self):
        mine = self.write(".claude/skills/tdd/SKILL.md", "my tdd\n")
        self.run_install("--yes")
        self.assertEqual(mine.read_text(), "my tdd\n")
        self.assertFalse((self.home / ".claude/skills/tdd").is_symlink())
        self.assertTrue((self.home / ".claude/skills/plan/SKILL.md").exists())

    def test_copy_fallback(self):
        self.run_install("--yes", env={"AI_CONFIG_CCG_FORCE_COPY": "1"})
        p = self.home / ".claude/skills/plan"
        self.assertTrue(p.is_dir() and not p.is_symlink())
        self.run_install("--uninstall", "--yes", env={"AI_CONFIG_CCG_FORCE_COPY": "1"})
        self.assertFalse(p.exists())

    def test_only_skills(self):
        self.run_install("--yes", "--only", "skills")
        self.assertTrue((self.home / ".claude/skills/plan").exists())
        self.assertFalse((self.home / ".claude/settings.json").exists())
        self.assertFalse((self.home / ".claude/CLAUDE.md").exists())


class Uninstall(Base):
    def test_restores_untouched_files_exactly(self):
        orig_s = json.dumps(USER_SETTINGS, indent=2)
        self.write(".claude/settings.json", orig_s)
        self.write(".claude/CLAUDE.md", "my rules\n")
        self.write(".claude/skills/tdd/SKILL.md", "my tdd\n")
        self.run_install("--yes")
        self.run_install("--uninstall", "--yes")
        self.assertEqual((self.home / ".claude/settings.json").read_text(), orig_s)
        self.assertEqual((self.home / ".claude/CLAUDE.md").read_text(), "my rules\n")
        self.assertFalse((self.home / ".claude/skills/plan").exists())
        self.assertEqual((self.home / ".claude/skills/tdd/SKILL.md").read_text(), "my tdd\n")
        self.assertFalse((self.home / ".ai-config-ccg/state.json").exists())

    def test_keeps_edits_made_after_install(self):
        self.write(".claude/settings.json", json.dumps(USER_SETTINGS, indent=2))
        self.run_install("--yes")
        s = self.settings()
        s["model"] = "sonnet"
        self.write(".claude/settings.json", json.dumps(s, indent=2))
        self.run_install("--uninstall", "--yes")
        s = self.settings()
        self.assertEqual(s["model"], "sonnet")
        self.assertEqual(s["permissions"]["deny"], ["Bash(rm -rf /)"])
        cmds = [h["command"] for g in s["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(cmds, ["echo mine"])

    def test_check(self):
        self.run_install("--yes")
        self.assertEqual(self.run_install("--check").returncode, 0)
        os.unlink(self.home / ".claude/skills/plan") if (self.home / ".claude/skills/plan").is_symlink() \
            else shutil.rmtree(self.home / ".claude/skills/plan")
        self.assertEqual(self.run_install("--check", ok=False).returncode, 1)


class NoTerminal(Base):
    def test_no_input_uses_defaults_instead_of_crashing(self):
        p = self.run_install("--dry-run", ok=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_uninstall_removes_dirs_it_created(self):
        self.run_install("--yes")
        self.run_install("--uninstall", "--yes")
        self.assertFalse((self.home / ".claude/skills").exists())
        self.assertFalse((self.home / ".gemini/config").exists())
        self.assertTrue((self.home / ".claude").is_dir())


class Questions(Base):
    def test_pick_agents_by_number_then_yes_no_per_part(self):
        # 1 = Claude, 4 = Cline. Claude: rules y, skills y, safety n, checks y. Cline: rules y, skills n. Confirm y.
        out = self.run_install(answers="1 4\ny\ny\nn\ny\ny\nn\ny\n").stdout
        self.assertIn("Cline", out)
        s = self.settings()
        cmds = [h["command"] for ev in s["hooks"].values() for g in ev for h in g["hooks"]]
        self.assertTrue(any("proof-gate.py" in c for c in cmds))
        self.assertFalse(any("guard-bash.py" in c for c in cmds))
        self.assertNotIn("permissions", s)
        self.assertIn(START, (self.home / ".claude/CLAUDE.md").read_text())
        cline_rules = self.home / "Documents/Cline/Rules/ai-config-ccg.md"
        self.assertIn("# Global Rules", cline_rules.read_text())
        self.assertFalse((self.home / ".cline/skills").exists())
        self.assertFalse((self.home / ".gemini/GEMINI.md").exists())
        self.run_install("--uninstall", "--yes")
        self.assertFalse(cline_rules.exists())

    def test_enter_takes_defaults_and_final_no_writes_nothing(self):
        before = self.snapshot()
        out = self.run_install(answers="\n" * 30, ok=False).stdout
        self.assertIn("Go ahead?", out)
        self.assertEqual(self.snapshot(), before)

    def test_rules_default_no_when_file_has_own_text(self):
        self.write(".claude/CLAUDE.md", "my rules\n")
        # Claude only; rules Enter (default No), skills/safety/checks Enter (Yes), confirm y
        self.run_install(answers="1\n\n\n\n\ny\n")
        self.assertEqual((self.home / ".claude/CLAUDE.md").read_text(), "my rules\n")
        self.assertTrue((self.home / ".claude/skills/plan").exists())


class MoreAgents(Base):
    def test_kimi_gets_skills_only(self):
        self.run_install("--yes", "--agents", "kimi")
        self.assertTrue((self.home / ".kimi-code/skills/plan/SKILL.md").exists())
        self.assertFalse((self.home / ".claude/skills").exists())

    def test_opencode_rules_and_skills(self):
        self.run_install("--yes", "--agents", "opencode")
        self.assertIn(START, (self.home / ".config/opencode/AGENTS.md").read_text())
        self.assertTrue((self.home / ".config/opencode/skills/plan").exists())

    def test_windsurf_skips_rules_over_char_limit(self):
        big = "x" * 5000 + "\n"
        p = self.write(".codeium/windsurf/memories/global_rules.md", big)
        out = self.run_install("--yes", "--agents", "windsurf").stdout
        self.assertEqual(p.read_text(), big)
        self.assertIn("6000", out)

    def test_found_agents_only_under_yes(self):
        (self.home / ".cursor").mkdir()
        self.run_install("--yes")
        self.assertTrue((self.home / ".cursor/skills/plan").exists())
        self.assertFalse((self.home / ".copilot").exists())
        self.assertFalse((self.home / ".kimi-code").exists())


if __name__ == "__main__":
    unittest.main()
