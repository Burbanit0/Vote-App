"""Tests for the CI facts behind the generated doc counts (stdlib unittest).

Run: python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import ci_facts  # noqa: E402

CI_DOCS = ("CONTRIBUTING.md", ".claude/skills/voter-ci/SKILL.md")


def _generated_docs() -> list[str]:
    text = (ROOT / "scripts" / "check_generated_docs.sh").read_text(encoding="utf-8")
    block = re.search(r"^DOCS=\((.*?)^\)", text, re.S | re.M)
    assert block, "DOCS=( ... ) not found in check_generated_docs.sh"
    return block.group(1).split()


def _filters() -> dict[str, list[str]]:
    """openapi-contract.yml's paths-filter groups: {group: [patterns]}."""
    text = (ROOT / ".github" / "workflows" / "openapi-contract.yml").read_text(encoding="utf-8")
    groups: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if m := re.match(r"^ {12}(\w+):\s*$", line):
            current = groups.setdefault(m.group(1), [])
        elif (m := re.match(r'^\s+- "([^"]+)"', line)) and current is not None:
            current.append(m.group(1))
    return groups


class Wiring(unittest.TestCase):
    def test_every_generated_doc_triggers_the_check(self):
        # A doc outside the filter skips "Generated artifacts in sync" on the
        # very PR that drifts it.
        watched = [p for patterns in _filters().values() for p in patterns]
        missing = [d for d in _generated_docs() if d not in watched]
        self.assertEqual(missing, [], "add these to openapi-contract.yml's path filter")

    def test_the_facts_sources_trigger_the_check(self):
        for source in ("scripts/ci_facts.py", "scripts/check_ci_health.py",
                       "scripts/setup-branch-protection.sh",
                       ".github/workflows/*.yml", ".github/workflows/*.yaml", *CI_DOCS):
            self.assertIn(source, _filters()["docs"])

    def test_the_ci_docs_are_generated(self):
        for doc in CI_DOCS:
            self.assertIn(doc, _generated_docs())


class Facts(unittest.TestCase):
    def test_required_contexts_come_from_the_setup_script(self):
        polity = ci_facts.required_contexts("polity")
        self.assertIn("Workflow lint", polity)
        self.assertEqual(len(polity), len(set(polity)))
        self.assertNotIn("Workflow lint", ci_facts.required_contexts("main"))

    def test_contributing_table_is_in_sync(self):
        self.assertEqual(ci_facts.workflow_table_drift(ROOT / "CONTRIBUTING.md"), [])


class Table(unittest.TestCase):
    def drift(self, rows: list[str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("| Workflow | x |\n|---|---|\n" + "".join(f"| `{r}` (x) | y |\n" for r in rows)
                           + "Prose naming `ghost.yml` is not a row.\n", encoding="utf-8")
            return ci_facts.workflow_table_drift(doc)

    def test_in_sync(self):
        self.assertEqual(self.drift(ci_facts.workflow_files()), [])

    def test_a_workflow_without_a_row(self):
        files = ci_facts.workflow_files()
        self.assertEqual(self.drift(files[1:]), [f"no row for {files[0]}"])

    def test_a_row_for_a_deleted_workflow(self):
        self.assertEqual(self.drift([*ci_facts.workflow_files(), "ghost.yml"]),
                         ["a row for ghost.yml, which is not in .github/workflows/"])

    def test_a_workflow_with_two_rows(self):
        files = ci_facts.workflow_files()
        self.assertEqual(self.drift([*files, files[0]]), [f"two rows for {files[0]}"])

    def test_a_row_written_as_a_full_path(self):
        files = ci_facts.workflow_files()
        self.assertEqual(self.drift([f".github/workflows/{files[0]}", *files[1:]]), [])

    def test_require_raises_with_the_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("no table\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                ci_facts.require_workflow_table_in_sync(doc)
            self.assertIn("no row for", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
