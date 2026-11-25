import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_seeded as c  # noqa: E402
from checkpoint_reminder import IN_PROGRESS  # noqa: E402

SCRIPT = ROOT / "scripts" / "check_seeded.py"
TEMPLATES = ROOT / "templates"


class CheckSeededTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for rel in c.REQUIRED_FILES:
            self.write(rel, "ok\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        f = self.dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)

    def cli(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.dir)], capture_output=True, text=True)

    def test_complete_tree_passes(self):
        self.assertEqual(c.problems(self.dir), [])

    def test_leftover_marker_reported(self):
        self.write("docs/README.md", "Seeded on {{date}} and {{project_name}}\n")
        found = c.problems(self.dir)
        self.assertEqual(len(found), 1)
        self.assertIn("docs/README.md", found[0])

    def test_any_marker_name_in_a_required_file_reported(self):
        self.write("CLAUDE.md", "x = '{{not_a_known_name}}'\n")
        found = c.problems(self.dir)
        self.assertEqual(len(found), 1)
        self.assertIn("CLAUDE.md", found[0])

    def test_marker_under_docs_projects_reported_once(self):
        self.write("docs/projects/x/README.md", "Status ({{date}}): in progress\n")
        self.write("docs/projects/README.md", "{{date}}\n")  # required file inside docs/projects: still one problem
        found = c.problems(self.dir)
        self.assertEqual(len(found), 2)
        self.assertTrue(any("docs/projects/x/README.md" in f for f in found))
        self.assertTrue(any(f.startswith("docs/projects/README.md") for f in found))

    def test_users_own_files_are_not_scanned(self):
        self.write(".github/workflows/ci.yml", "token: ${{ secrets.X }}\n")
        self.write("src/app.py", "x = '{{date}}'\n")
        self.write(".git/COMMIT_EDITMSG", "{{date}}\n")
        self.assertEqual(c.problems(self.dir), [])

    def test_binary_file_under_docs_projects_skipped(self):
        (self.dir / "docs/projects/x").mkdir(parents=True)
        (self.dir / "docs/projects/x/logo.png").write_bytes(b"\x89PNG\xff\xfe\x00{{date}}")
        self.assertEqual(c.problems(self.dir), [])

    def test_missing_file_reported(self):
        (self.dir / ".claude/agents/reviewer.md").unlink()
        found = c.problems(self.dir)
        self.assertEqual(len(found), 1)
        self.assertIn(".claude/agents/reviewer.md", found[0])

    def test_cli_exit_codes(self):
        self.assertEqual(self.cli().returncode, 0)
        self.write("CLAUDE.md", "{{one_line_purpose}}\n")
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("CLAUDE.md", result.stdout)

    def git(self, *args):
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
        subprocess.run(["git", "-C", str(self.dir), *args], check=True, capture_output=True, env=env)

    def config(self, value):
        self.write(".claude/project-base.json", json.dumps({"parallel": value}))

    def test_parallel_marker_left_in_claude_md_reported(self):
        self.write("CLAUDE.md", "x\n<!-- parallel:start -->\nline\n")
        found = c.problems(self.dir)
        self.assertEqual(len(found), 1)
        self.assertIn("CLAUDE.md", found[0])

    def test_unignored_worktrees_dir_reported(self):
        self.git("init", "-q")
        self.config({})
        found = c.problems(self.dir)
        self.assertEqual(len(found), 1)
        self.assertIn(".claude/worktrees", found[0])

    def test_ignored_worktrees_dir_passes(self):
        self.git("init", "-q")
        self.write(".gitignore", "/.claude/worktrees/\n")
        self.config({})
        self.assertEqual(c.problems(self.dir), [])

    def test_custom_worktrees_dir_checked(self):
        self.git("init", "-q")
        self.write(".gitignore", "/.claude/worktrees/\n")
        self.config({"worktrees_dir": "wt"})
        self.assertIn("wt", c.problems(self.dir)[0])

    def test_invalid_worktrees_dir_falls_back_to_default(self):
        self.git("init", "-q")
        for bad in ("", 5):
            self.config({"worktrees_dir": bad})
            found = c.problems(self.dir)
            self.assertEqual(len(found), 1)
            self.assertIn(".claude/worktrees", found[0])

    def test_not_a_git_repo_skips_check(self):
        self.config({})
        self.assertEqual(c.problems(self.dir), [])

    def test_no_parallel_key_skips_check(self):
        self.git("init", "-q")
        self.write(".claude/project-base.json", "{}")
        self.assertEqual(c.problems(self.dir), [])


class TemplateTests(unittest.TestCase):
    def text(self, rel):
        return (TEMPLATES / rel).read_text()

    def test_markers_are_all_documented(self):
        used = set()
        for f in TEMPLATES.rglob("*"):
            if f.suffix in (".md", ".json"):
                used.update(c.MARKER.findall(f.read_text()))
        self.assertTrue(used)
        self.assertLessEqual(used, set(c.PLACEHOLDERS))

    def test_claude_md_fits_budget(self):
        self.assertLessEqual(len(self.text("CLAUDE.md").splitlines()), 120)

    def test_project_config_keeps_trimming_enabled(self):
        cfg = json.loads(self.text("project-base.json"))
        self.assertEqual(cfg["test_command"], "{{test_command}}")
        self.assertEqual(cfg["docs_root"], "docs")
        self.assertEqual(cfg["test_command_patterns"], ["{{test_command_regex}}"])

    def test_settings_fragment(self):
        cfg = json.loads(self.text("settings.fragment.json"))
        self.assertEqual(cfg["env"], {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"})
        self.assertEqual(set(cfg["enabledPlugins"]),
                         {"superpowers@claude-plugins-official", "ponytail@ponytail", "project-base@project-base"})
        self.assertEqual(set(cfg["extraKnownMarketplaces"]), {"claude-plugins-official", "ponytail", "project-base"})
        for entry in cfg["extraKnownMarketplaces"].values():
            self.assertEqual(entry["source"]["source"], "github")

    def test_task_template_is_an_open_checkpoint(self):
        task = self.text("task.md")
        self.assertTrue(IN_PROGRESS.search(task))
        for section in ("Status", "Goal", "Done so far", "Files touched", "Next step", "How to verify",
                        "Open questions"):
            self.assertRegex(task, r"(?m)^## " + section + r"$")

    def test_project_readme_has_dated_status_line(self):
        self.assertRegex(self.text("project/README.md"), r"(?m)^Status \(\{\{date\}\}\): ")

    def test_embedded_templates_match_their_source(self):
        self.assertIn(self.text("adr.md").strip(), self.text("adr-README.md"))
        self.assertIn(self.text("topic-card.md").strip(), self.text("topics-README.md"))


if __name__ == "__main__":
    unittest.main()
