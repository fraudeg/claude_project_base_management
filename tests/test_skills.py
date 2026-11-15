import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
KNOWLEDGE = {"project-workflow", "write-adr", "write-topic-card", "write-rule", "criticality-gate", "harness-ops"}


def frontmatter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", str(path) + ": no frontmatter"
    end = lines.index("---", 1)
    # ponytail: flat "key: value" lines only; no YAML lib in stdlib
    return dict(l.split(": ", 1) for l in lines[1:end])


def skill_files():
    return sorted(SKILLS.glob("*/SKILL.md"))


class TestSkills(unittest.TestCase):
    def test_knowledge_skills_exist(self):
        have = {p.parent.name for p in skill_files()}
        self.assertEqual(KNOWLEDGE - have, set())

    def test_frontmatter(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                fm = frontmatter(path)
                self.assertEqual(fm["name"], path.parent.name)
                self.assertLess(len(fm["description"]), 250)
                if path.parent.name in KNOWLEDGE:
                    self.assertTrue(fm["description"].startswith("Use when"), "description must say when")


if __name__ == "__main__":
    unittest.main()
