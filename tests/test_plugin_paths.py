import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# A path the skills or hooks name relative to the plugin root, as <plugin>/x or ${CLAUDE_PLUGIN_ROOT}/x.
PATH_REF = re.compile(r"(?:<plugin>|\$\{CLAUDE_PLUGIN_ROOT\})/([\w./-]+)")


class TestPluginPaths(unittest.TestCase):
    def test_skill_references_exist(self):
        for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
            for ref in PATH_REF.findall(path.read_text(encoding="utf-8")):
                with self.subTest(skill=path.parent.name, ref=ref):
                    self.assertTrue((ROOT / ref.rstrip(".")).exists())

    def test_hook_commands_point_at_existing_scripts(self):
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        for event, groups in hooks.items():
            for group in groups:
                for hook in group["hooks"]:
                    refs = PATH_REF.findall(hook["command"])
                    with self.subTest(event=event, command=hook["command"]):
                        self.assertTrue(refs, "command names no plugin path")
                        for ref in refs:
                            self.assertTrue((ROOT / ref).is_file())


if __name__ == "__main__":
    unittest.main()
