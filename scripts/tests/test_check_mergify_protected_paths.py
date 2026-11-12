"""Tests for the review-hold path classifier (stdlib unittest).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_mergify_protected_paths as cmp  # noqa: E402

CONFIG = """
merge_protections:
  - name: hold
    if:
      - base ~= ^(polity|develop)$
      - or:
          # Engine.
          - files = voter-app/src/lib/playgroundVoting.ts
          - files ~= ^\\.github/workflows/  # trailing comment
          - and:
              - files = voter-app/package.json
              - -author = dependabot[bot]
          - files = .mergify.yml
    success_conditions:
      - check-success = human-review
"""


class Classify(unittest.TestCase):
    def test_rules_parse_exact_regex_and_author_exceptions(self):
        got = cmp.rules(CONFIG)
        self.assertEqual([(r.op, r.pattern) for r in got], [
            ("=", "voter-app/src/lib/playgroundVoting.ts"), ("~=", r"^\.github/workflows/"),
            ("=", "voter-app/package.json"), ("=", ".mergify.yml")])
        self.assertEqual(got[2].unless_author, frozenset({"dependabot[bot]"}))
        self.assertEqual(got[3].unless_author, frozenset())  # the block ended

    def test_held_paths(self):
        paths = ["voter-app/src/lib/playgroundVoting.ts", ".github/workflows/e2e.yml",
                 "voter-app/src/lib/other.ts", "docs/x.md", "voter-app/package.json"]
        self.assertEqual(cmp.held_paths(CONFIG, paths, "someone"),
                         ["voter-app/src/lib/playgroundVoting.ts", ".github/workflows/e2e.yml",
                          "voter-app/package.json"])
        self.assertEqual(cmp.held_paths(CONFIG, ["voter-app/package.json"], "dependabot[bot]"), [])
        self.assertEqual(cmp.held_paths(CONFIG, ["docs/x.md"]), [])

    def test_the_real_config_holds_its_own_safety_net(self):
        text = (cmp.ROOT / ".mergify.yml").read_text(encoding="utf-8")
        for path in [".mergify.yml", ".github/workflows/human-review.yml", ".claude/settings.json",
                     "scripts/check_mergify_protected_paths.py", "voter-app/src/lib/playgroundVoting.ts",
                     "voter-app/src/lib/__fixtures__/engineParity.json", "voter-app/package.json"]:
            with self.subTest(path=path):
                self.assertEqual(cmp.held_paths(text, [path], "Burbanit0"), [path])
        self.assertEqual(cmp.held_paths(text, ["voter-app/package.json"], "dependabot[bot]"), [])
        # The backend's pins are held for everyone, Dependabot included.
        pins = ["fast_api_voter/requirements.txt", "fast_api_voter/requirements-dev.lock.txt"]
        self.assertEqual(cmp.held_paths(text, pins, "dependabot[bot]"), pins)
        self.assertEqual(cmp.held_paths(text, ["fast_api_voter/requirements/notes.md"], "x"), [])
        self.assertEqual(cmp.held_paths(text, ["docs/journal/JOURNAL_DE_BORD.md", "voter-app/src/App.tsx"]), [])

    def run_cli(self, argv, stdin):
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin)), redirect_stdout(out):
            code = cmp.main(argv)
        return code, out.getvalue().split()

    def test_cli_classify(self):
        code, out = self.run_cli(["--classify", "--author", "x"], ".mergify.yml\ndocs/a.md\n")
        self.assertEqual((code, out), (0, [".mergify.yml"]))

    def test_cli_refuses_to_classify_with_an_unparseable_config(self):
        with mock.patch.object(cmp.Path, "read_text", return_value="queue_rules: []\n"):
            code, out = self.run_cli(["--classify"], ".mergify.yml\n")
        self.assertEqual((code, out), (2, []))


if __name__ == "__main__":
    unittest.main()
