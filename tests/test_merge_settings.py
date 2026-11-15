import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "merge_settings.py"

FRAGMENT = {
    "env": {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"},
    "enabledPlugins": {"ponytail@ponytail": True, "project-base@project-base": True},
}


class MergeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.fragment = self.dir / "fragment.json"
        self.fragment.write_text(json.dumps(FRAGMENT), encoding="utf-8")
        self.target = self.dir / ".claude" / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.fragment), str(self.target), *extra],
            capture_output=True, text=True, encoding="utf-8",
        )

    def put(self, data, raw=None):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(raw if raw is not None else json.dumps(data), encoding="utf-8")

    def merged(self):
        return json.loads(self.target.read_text(encoding="utf-8"))

    def test_absent_target_gets_the_fragment(self):
        r = self.run_script("--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.merged(), FRAGMENT)

    def test_missing_keys_are_added(self):
        self.put({"permissions": {"allow": ["Bash(ls)"]}})
        self.assertEqual(self.run_script("--apply").returncode, 0)
        self.assertEqual(self.merged(), {"permissions": {"allow": ["Bash(ls)"]}, **FRAGMENT})

    def test_existing_value_is_kept_and_reported(self):
        self.put({"env": {"CLAUDE_CODE_SUBAGENT_MODEL": "opus"}})
        r = self.run_script("--apply")
        self.assertEqual(self.merged()["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "opus")
        self.assertIn("env.CLAUDE_CODE_SUBAGENT_MODEL", r.stdout)

    def test_nested_dicts_are_merged(self):
        self.put({"enabledPlugins": {"ponytail@ponytail": False, "other@x": True}})
        self.run_script("--apply")
        self.assertEqual(
            self.merged()["enabledPlugins"],
            {"ponytail@ponytail": False, "other@x": True, "project-base@project-base": True},
        )

    def test_non_ascii_is_preserved(self):
        self.put(None, raw='{"note": "café über"}')
        self.run_script("--apply")
        self.assertIn("café über", self.target.read_text(encoding="utf-8"))

    def test_no_write_without_apply(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.target.exists())
        self.assertIn("+", r.stdout)  # the diff is printed
        self.put({"a": 1})
        before = self.target.read_text(encoding="utf-8")
        self.run_script()
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)

    def test_invalid_target_is_left_alone(self):
        self.put(None, raw="{not json")
        r = self.run_script("--apply")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "{not json")


if __name__ == "__main__":
    unittest.main()
