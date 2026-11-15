import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_neutral as c  # noqa: E402

SCRIPT = ROOT / "scripts" / "check_neutral.py"
TERMS = ["acmecorp", "Widget Pro"]


class CheckNeutralTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        f = self.dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def test_clean_tree_passes(self):
        self.write("README.md", "A neutral plugin.\n")
        self.assertEqual(c.problems(self.dir, TERMS), [])

    def test_term_reported_with_file_line_and_term(self):
        self.write("docs/a.md", "fine\nstill fine\nbuilt for acmecorp only\n")
        found = c.problems(self.dir, TERMS)
        self.assertEqual(len(found), 1)
        self.assertIn("docs/a.md:3", found[0])
        self.assertIn("acmecorp", found[0])

    def test_match_is_case_insensitive_substring(self):
        self.write("a.md", "ACMECORP\nthe widget pro line\nxAcmeCorpx\n")
        found = c.problems(self.dir, TERMS)
        self.assertEqual(len(found), 3)

    def test_each_term_on_a_line_reported(self):
        self.write("a.md", "acmecorp and Widget Pro\n")
        self.assertEqual(len(c.problems(self.dir, TERMS)), 2)

    def test_empty_denylist_and_blank_terms_match_nothing(self):
        self.write("a.md", "anything at all\n")
        self.assertEqual(c.problems(self.dir, []), [])
        self.assertEqual(c.problems(self.dir, ["", "  "]), [])

    def test_license_skipped(self):
        self.write("LICENSE", "Copyright acmecorp\n")
        self.assertEqual(c.problems(self.dir, TERMS), [])

    def test_denylist_file_skipped_by_the_scan(self):
        self.write(".neutral-denylist", "# terms\nacmecorp\n")
        self.assertEqual(c.problems(self.dir, TERMS), [])

    def test_only_the_root_license_is_skipped(self):
        self.write("docs/LICENSE", "acmecorp\n")
        self.assertEqual(len(c.problems(self.dir, TERMS)), 1)

    def test_skipped_directories(self):
        for d in (".git", ".superpowers", "__pycache__", "scripts/__pycache__"):
            self.write(f"{d}/x.txt", "acmecorp\n")
        self.assertEqual(c.problems(self.dir, TERMS), [])

    def test_binary_file_skipped(self):
        (self.dir / "img.png").write_bytes(b"\x89PNG\xff\xfe acmecorp \x00\x01")
        (self.dir / "nul.dat").write_bytes(b"acmecorp\x00 valid utf-8 with a NUL")
        self.assertEqual(c.problems(self.dir, TERMS), [])

    def test_manifest_author_and_owner_lines_skipped_rest_scanned(self):
        plugin = {"name": "p", "author": {"name": "acmecorp", "url": "https://acmecorp.example"}, "description": "ok"}
        market = {"name": "m", "owner": {"name": "acmecorp"}, "plugins": []}
        self.write(".claude-plugin/plugin.json", json.dumps(plugin, indent=2) + "\n")
        self.write(".claude-plugin/marketplace.json", json.dumps(market, indent=2) + "\n")
        self.assertEqual(c.problems(self.dir, TERMS), [])
        plugin["description"] = "for acmecorp"
        self.write(".claude-plugin/plugin.json", json.dumps(plugin, indent=2) + "\n")
        found = c.problems(self.dir, TERMS)
        self.assertEqual(len(found), 1)
        self.assertIn(".claude-plugin/plugin.json:", found[0])

    def test_manifest_line_numbers_stay_accurate_after_author_block(self):
        text = '{\n  "author": {\n    "name": "acmecorp"\n  },\n  "description": "acmecorp"\n}\n'
        self.write(".claude-plugin/plugin.json", text)
        found = c.problems(self.dir, TERMS)
        self.assertEqual(len(found), 1)
        self.assertIn(".claude-plugin/plugin.json:5", found[0])

    def test_author_key_in_other_files_is_not_special(self):
        self.write("docs/x.json", '{"author": "acmecorp"}\n')
        self.assertEqual(len(c.problems(self.dir, TERMS)), 1)

    def test_this_script_is_not_flagged_by_its_own_denylist(self):
        # the denylist lives in the script, so the terms the owner fills in must not fail the check itself
        found = c.problems(ROOT, ["DENYLIST"])
        self.assertFalse([f for f in found if f.startswith("scripts/check_neutral.py")], found)

    def test_shipped_denylist_is_a_list_of_strings(self):
        self.assertIsInstance(c.DENYLIST, list)
        self.assertTrue(all(isinstance(t, str) for t in c.DENYLIST))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "a.md").write_text("built for acmecorp\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, denylist, root=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(c, "DENYLIST", denylist), redirect_stdout(out), redirect_stderr(err):
            code = c.main([str(root or self.dir)])
        return code, out.getvalue(), err.getvalue()

    def write_denylist(self, text):
        (self.dir / ".neutral-denylist").write_text(text, encoding="utf-8")

    def test_exit_1_and_prints_problems_when_a_term_matches(self):
        code, out, err = self.run_main(["acmecorp"])
        self.assertEqual(code, 1)
        self.assertIn("a.md:1", out)
        self.assertNotIn("denylist empty", err)

    def test_exit_0_when_clean(self):
        code, out, err = self.run_main(["nothing-here"])
        self.assertEqual((code, out), (0, ""))

    def test_empty_denylist_warns_on_stderr_but_exits_0(self):
        code, out, err = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn("denylist empty", err)
        self.assertIn("not meaningful", err)

    def test_terms_from_the_denylist_file_are_applied(self):
        self.write_denylist("acmecorp\n")
        code, out, err = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn("a.md:1", out)
        self.assertNotIn("denylist empty", err)

    def test_the_denylist_file_itself_is_not_reported(self):
        self.write_denylist("acmecorp\n")
        code, out, err = self.run_main([])
        self.assertNotIn(".neutral-denylist", out)

    def test_file_comments_blank_lines_and_padding_ignored(self):
        self.write_denylist("# a comment\n\n   \n  # indented comment\n  acmecorp  \n")
        self.assertEqual(c.read_denylist_file(self.dir), ["acmecorp"])

    def test_file_terms_add_to_the_module_denylist(self):
        (self.dir / "b.md").write_text("generic-term here\n", encoding="utf-8")
        self.write_denylist("acmecorp\n")
        code, out, err = self.run_main(["generic-term"])
        self.assertEqual(code, 1)
        self.assertIn("a.md:1", out)
        self.assertIn("b.md:1", out)

    def test_missing_file_reads_as_no_terms(self):
        self.assertEqual(c.read_denylist_file(self.dir), [])

    def test_comment_only_file_still_warns_and_exits_0(self):
        self.write_denylist("# nothing yet\n\n")
        code, out, err = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn("denylist empty", err)

    def test_unreadable_denylist_file_exits_2_instead_of_passing(self):
        (self.dir / ".neutral-denylist").write_bytes(b"\xff\xfe acmecorp")
        code, out, err = self.run_main([])
        self.assertEqual(code, 2)
        self.assertIn(".neutral-denylist", err)
        self.assertEqual(out, "")

    def test_root_that_does_not_exist_exits_2(self):
        code, out, err = self.run_main(["acmecorp"], root=self.dir / "nope")
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)
        self.assertEqual(out, "")

    def test_root_that_is_a_file_exits_2(self):
        code, out, err = self.run_main(["acmecorp"], root=self.dir / "a.md")
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)

    def test_denylist_file_is_git_ignored(self):
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
        self.assertIn(c.DENYLIST_FILE, lines)

    @unittest.skipIf(c.DENYLIST, "the owner has filled the denylist")
    def test_script_runs_as_a_program_on_the_shipped_empty_denylist(self):
        r = subprocess.run([sys.executable, str(SCRIPT), str(self.dir)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("denylist empty", r.stderr)


if __name__ == "__main__":
    unittest.main()
