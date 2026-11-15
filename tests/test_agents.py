import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parent.parent / "agents"
NAMES = ["explorer", "implementer", "test-runner", "reviewer"]
OMIT_CLAUDE_MD = {"explorer", "test-runner"}


def frontmatter(name):
    lines = (AGENTS / (name + ".md")).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", name + ": no frontmatter"
    end = lines.index("---", 1)
    # ponytail: flat "key: value" lines only; no YAML lib in stdlib
    return dict(l.split(": ", 1) for l in lines[1:end])


class TestAgents(unittest.TestCase):
    def test_frontmatter(self):
        for name in NAMES:
            with self.subTest(agent=name):
                fm = frontmatter(name)
                self.assertEqual(fm["name"], name)
                self.assertEqual(fm["model"], "sonnet")
                self.assertLess(len(fm["description"]), 250)
                self.assertIn(fm["effort"], {"low", "medium"})
                self.assertEqual(fm.get("omitClaudeMd") == "true", name in OMIT_CLAUDE_MD)

    def test_implementer_can_call_skills(self):
        # tools is a strict allowlist: without Skill the criticality gate is unreachable
        self.assertIn("Skill", [t.strip() for t in frontmatter("implementer")["tools"].split(",")])


if __name__ == "__main__":
    unittest.main()
