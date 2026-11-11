"""scripts/fast-gate.sh must keep running on bash 3.2 (stdlib only).

macOS ships bash 3.2 and no `timeout`. The script once used `mapfile` (bash 4) and died on it
without failing: it printed "nothing to check" and exited 0, so the pre-push guard read green
having checked nothing. These tests keep that from coming back: one forbids the bash 4 / GNU-only
constructs, one runs the script under the system bash on a throwaway repo.

Run: python3 -m unittest discover -s .claude/hooks/tests -v
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "fast-gate.sh"

# Not in bash 3.2 (or not on a stock Mac): any of these in the script is a false pass waiting
# to happen on the maintainer's machine.
FORBIDDEN = {
    "mapfile": r"\bmapfile\b",
    "readarray": r"\breadarray\b",
    "associative array": r"\bdeclare\s+-A\b",
    "case-changing expansion": r"\$\{[A-Za-z_][A-Za-z_0-9]*(,,|\^\^)",
    "wait -n": r"\bwait\s+-n\b",
    "&>>": r"&>>",
    "coproc": r"\bcoproc\b",
}


def code_lines(text: str) -> list[tuple[int, str]]:
    return [(n, line) for n, line in enumerate(text.splitlines(), 1) if not line.lstrip().startswith("#")]


class FastGatePortability(unittest.TestCase):
    def test_no_bash4_or_gnu_only_constructs(self) -> None:
        offences = [
            f"line {n}: {name}"
            for n, line in code_lines(SCRIPT.read_text())
            for name, pattern in FORBIDDEN.items()
            if re.search(pattern, line)
        ]
        self.assertEqual(offences, [], "bash 4 / GNU-only construct in fast-gate.sh")

    def test_bare_timeout_is_not_called_directly(self) -> None:
        # `timeout` is absent on macOS; it goes through with_timeout, which falls back.
        direct = [n for n, line in code_lines(SCRIPT.read_text()) if re.match(r"\s*timeout\s", line)]
        self.assertEqual(direct, [], "call timeout through with_timeout")


@unittest.skipUnless(Path("/bin/bash").exists(), "no /bin/bash")
class FastGateRunsUnderSystemBash(unittest.TestCase):
    """A docs-only branch and an empty one, in a throwaway repo, under /bin/bash (3.2 on a Mac)."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "scripts").mkdir()
        shutil.copy(SCRIPT, self.tmp / "scripts" / "fast-gate.sh")
        (self.tmp / "fast_api_voter").mkdir()
        (self.tmp / "fast_api_voter" / "mypy.ini").write_text("[mypy]\npython_version = 3.14\n")
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.tmp / "README.md").write_text("one\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.tmp, check=True, capture_output=True)

    def gate(self, base: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/bash", "scripts/fast-gate.sh", base],
            cwd=self.tmp, capture_output=True, text=True, timeout=120,
        )

    def test_docs_only_change_is_counted_and_reported(self) -> None:
        (self.tmp / "docs.md").write_text("two\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "docs")
        res = self.gate("HEAD~1")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("unbound variable", res.stderr)
        self.assertNotIn("command not found", res.stderr)
        # The count is the proof it saw the diff at all (the false pass said nothing, with 0).
        self.assertIn("1 changed files", res.stdout)
        self.assertIn("nothing to check", res.stdout)

    def test_no_changes_says_so(self) -> None:
        res = self.gate("HEAD")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("unbound variable", res.stderr)
        self.assertIn("no committed changes", res.stdout)


if __name__ == "__main__":
    unittest.main()
