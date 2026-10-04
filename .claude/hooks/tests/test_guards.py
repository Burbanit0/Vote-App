"""Decision tests for the Claude Code guardrail hooks (stdlib only).

Run: python3 -m unittest discover -s .claude/hooks/tests -v
Each case feeds a real hook payload on stdin, the way Claude Code does, and
checks the decision printed (deny / ask / nothing).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))

import session_ci_status  # noqa: E402


def run(hook: str, payload: dict, env: dict | None = None) -> dict | None:
    res = subprocess.run([sys.executable, str(HOOKS / hook)], input=json.dumps(payload), capture_output=True,
                         text=True, timeout=60, env={**os.environ, **(env or {})})
    assert res.returncode == 0, res.stderr
    out = res.stdout.strip()
    return json.loads(out) if out else None


def decision(out: dict | None) -> str | None:
    if out is None:
        return None
    if "decision" in out:
        return out["decision"]
    spec = out.get("hookSpecificOutput", {})
    return spec.get("permissionDecision") or ("context" if "additionalContext" in spec else None)


# Built at runtime so this file's own source never reads as the commands it tests.
PUSH = "git " + "push"


class BashGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ok = Path(self.tmp.name, "ok.sh")
        self.ok.write_text("echo 'all good'; exit 0\n")
        self.bad = Path(self.tmp.name, "bad.sh")
        self.bad.write_text("echo 'F401 unused import'; exit 1\n")
        self.env = {"GUARD_FAST_GATE": str(self.ok)}

    def tearDown(self):
        self.tmp.cleanup()

    def bash(self, cmd: str, env: dict | None = None) -> str | None:
        return decision(run("bash_guard.py", {"tool_name": "Bash", "tool_input": {"command": cmd}}, env or self.env))

    def test_denies_history_rewrites_and_protected_pushes(self):
        for cmd in [f"{PUSH} --force origin feat/x", f"{PUSH} -f", f"{PUSH} origin +feat/x",
                    f"{PUSH} origin polity", f"{PUSH} origin HEAD:refs/heads/develop",
                    f"{PUSH} origin feat/x:main", f"{PUSH} --no-verify origin feat/x",
                    "git reset --hard HEAD~1", "git commit --no-verify -m x",
                    f"cd x && {PUSH} --force-with-lease"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), "deny")

    def test_denies_self_approval_and_merges(self):
        for cmd in ["gh pr merge 724 --merge", "gh pr comment 724 --body '/reviewed abc1234'",
                    "gh pr edit 724 --add-label reviewed",
                    "gh api repos/o/r/statuses/abc -f state=success -f context=human-review",
                    "gh api -X PUT repos/o/r/pulls/1/merge"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), "deny")

    def test_asks_before_oracle_regeneration_and_ratchet_updates(self):
        for cmd in ["PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py",
                    "cd fast_api_voter && python -m pytest --snapshot-update",
                    "npx playwright test --update-snapshots",
                    "./scripts/check_quality_ratchet.sh --update"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), "ask")

    def test_asks_before_shell_writes_to_guardrail_files(self):
        for cmd in ["echo x > .mergify.yml", "sed -i 's/a/b/' .github/workflows/e2e.yml",
                    "cat a | tee .claude/settings.json", "rm .claude/hooks/bash_guard.py",
                    "cp /tmp/x .github/quality-baseline.json",
                    "git checkout polity -- .github/workflows/audit.yml"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), "ask")

    def test_reads_and_unrelated_commands_pass(self):
        for cmd in ["cat .mergify.yml", "python3 scripts/check_mergify_protected_paths.py 2>/dev/null",
                    "grep -n x .github/workflows/e2e.yml > /tmp/out.txt", "git status", "npm run lint",
                    "cp .mergify.yml /tmp/backup.yml"]:
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.bash(cmd))

    def test_heredoc_bodies_are_data_not_commands(self):
        cmd = f"cat > /tmp/notes.txt <<'EOF'\n{PUSH} --force origin polity\nEOF\necho done"
        self.assertIsNone(self.bash(cmd))

    def test_review_findings_bypasses_are_closed(self):
        # Separators inside a quoted body, multi-line bodies, git global options,
        # background `&`, here-strings and unterminated heredocs.
        for cmd in ['gh pr comment 1 --body "ok; /reviewed abc1234"',
                    'gh pr comment 1 --body "looks good\n/reviewed abc1234"',
                    "gh pr comment 1 --body-file - <<'EOF'\n/reviewed abc1234\nEOF",
                    f"git -C . {PUSH[4:]} --force", f"git --no-pager -c x=y {PUSH[4:]} -f",
                    f"sleep 1 & {PUSH} --force", f'cat <<< "x"; {PUSH} --force',
                    f"cat <<EOF\nnot closed\n{PUSH} --force"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), "deny")

    def test_implicit_push_destination_is_the_current_branch(self):
        on_polity = {**self.env, "GUARD_CURRENT_BRANCH": "polity"}
        for cmd in [PUSH, f"{PUSH} origin", f"{PUSH} -u origin HEAD", f"git -C sub {PUSH[4:]}"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd, on_polity), "deny")
        on_feature = {**self.env, "GUARD_CURRENT_BRANCH": "feat/x"}
        self.assertIsNone(self.bash(f"{PUSH} -u origin HEAD", on_feature))
        self.assertIsNone(self.bash(f"{PUSH} origin feat/x", on_polity))  # explicit destination wins

    def test_mentioning_reviewed_in_prose_is_fine(self):
        msg = "git commit -q -F - <<'EOF'\nfix: deny /reviewed when a command calls gh or the API\nEOF"
        self.assertIsNone(self.bash(msg))
        self.assertIsNone(self.bash("grep -rn '/reviewed' .github/workflows/human-review.yml"))

    def test_redirections_stay_whole(self):
        self.assertEqual(self.bash("echo hi 2>&1 | tee .mergify.yml"), "ask")
        self.assertIsNone(self.bash("python3 x.py 2>&1 | tail -5"))

    def test_push_runs_the_fast_gate(self):
        self.assertIsNone(self.bash(f"{PUSH} -u origin feat/x"))
        out = run("bash_guard.py", {"tool_input": {"command": f"{PUSH} -u origin feat/x"}},
                  {"GUARD_FAST_GATE": str(self.bad)})
        self.assertEqual(decision(out), "deny")
        self.assertIn("F401", out["hookSpecificOutput"]["permissionDecisionReason"])


def edit(path: str, old: str, new: str) -> str | None:
    return decision(run("edit_guard.py", {"tool_name": "Edit", "tool_input": {
        "file_path": path, "old_string": old, "new_string": new}}))


class EditGuard(unittest.TestCase):
    def test_asks_on_added_silencers(self):
        cases = [("voter-app/src/lib/x.test.ts", "it('a', f)", "it.skip('a', f)"),
                 ("voter-app/src/lib/x.ts", "const a = b", "const a = b as any"),
                 ("fast_api_voter/api/x.py", "import os", "import os  # noqa: F401"),
                 ("fast_api_voter/api/tests/test_x.py", "def test_a():", "@pytest.mark.skip\ndef test_a():"),
                 ("voter-app/src/x.tsx", "f()", "// @ts-expect-error\nf()")]
        for path, old, new in cases:
            with self.subTest(path=path, new=new):
                self.assertEqual(edit(path, old, new), "ask")

    def test_removing_a_silencer_is_fine(self):
        self.assertIsNone(edit("fast_api_voter/api/x.py", "import os  # noqa: F401", "import os"))

    def test_asks_on_weakened_thresholds(self):
        self.assertEqual(edit("voter-app/package.json", '"atLeast": 99.76', '"atLeast": 99.5'), "ask")
        self.assertEqual(edit("fast_api_voter/api/tests/x.py", "FAST_CEILING_S = 0.5", "FAST_CEILING_S = 2.0"), "ask")
        self.assertIsNone(edit("voter-app/package.json", '"atLeast": 99.76', '"atLeast": 99.8'))

    def test_asks_on_guardrail_files(self):
        for path in [".mergify.yml", ".github/workflows/e2e.yml", ".claude/settings.json",
                     ".github/quality-baseline.json", "fast_api_voter/api/tests/golden/polity_golden.json",
                     "voter-app/vitest.config.ts"]:
            with self.subTest(path=path):
                self.assertEqual(edit(path, "a", "b"), "ask")

    def test_ordinary_edit_passes(self):
        self.assertIsNone(edit("voter-app/src/lib/x.ts", "const a = 1", "const a = 2"))


def gh(tool: str, tool_input: dict) -> str | None:
    return decision(run("github_guard.py", {"tool_name": f"mcp__github__{tool}", "tool_input": tool_input}))


class GithubGuard(unittest.TestCase):
    def test_denies_merges_direct_writes_and_self_approval(self):
        self.assertEqual(gh("merge_pull_request", {"pullNumber": 1}), "deny")
        self.assertEqual(gh("enable_pr_auto_merge", {"pullNumber": 1}), "deny")
        self.assertEqual(gh("push_files", {"files": []}), "deny")
        self.assertEqual(gh("add_issue_comment", {"issue_number": 1, "body": "/reviewed abc1234"}), "deny")
        self.assertEqual(gh("issue_write", {"method": "update", "labels": ["ci", "reviewed"]}), "deny")

    def test_ordinary_calls_pass(self):
        self.assertIsNone(gh("add_issue_comment", {"issue_number": 1, "body": "Fixed in abc1234, thanks."}))
        self.assertIsNone(gh("pull_request_read", {"method": "get", "pullNumber": 1}))


class StopGuard(unittest.TestCase):
    def test_loop_guard(self):
        self.assertIsNone(decision(run("stop_engine_parity.py", {"stop_hook_active": True})))

    def test_blocks_once_per_engine_state(self):
        import contextlib
        import io

        import stop_engine_parity as hook

        state = {"v": "state-1"}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(hook, "changed_files", return_value={next(iter(hook.ENGINE))}), \
                mock.patch.object(hook, "engine_state", side_effect=lambda _t: state["v"]), \
                mock.patch.dict(os.environ, {"GUARD_PARITY_ACK": str(Path(tmp, "ack"))}):
            def stop() -> str | None:
                buf = io.StringIO()
                with mock.patch.object(sys, "stdin", io.StringIO("{}")), contextlib.redirect_stdout(buf):
                    hook.main()
                return decision(json.loads(buf.getvalue())) if buf.getvalue().strip() else None

            self.assertEqual(stop(), "block")
            self.assertIsNone(stop())  # same state: already told, not re-blocked every turn
            state["v"] = "state-2"
            self.assertEqual(stop(), "block")  # a further engine edit blocks again
            with mock.patch.object(hook, "changed_files", return_value={next(iter(hook.ENGINE)), hook.FIXTURE}):
                state["v"] = "state-3"
                self.assertIsNone(stop())  # fixture regenerated alongside: fine


class CiStatus(unittest.TestCase):
    def run_(self, name, conclusion, attempt=1, status="completed"):
        return {"name": name, "conclusion": conclusion, "status": status, "run_attempt": attempt,
                "created_at": "2026-10-02T15:00:00Z", "html_url": f"https://x/{name}", "display_title": "t"}

    def test_red_when_latest_attempt_failed(self):
        text = session_ci_status.summarize("abc1234def", [self.run_("Frontend CI", "failure")], False)
        self.assertIn("RED", text)
        self.assertIn("https://x/Frontend CI", text)

    def test_a_green_rerun_supersedes_the_failed_attempt(self):
        runs = [self.run_("Frontend CI", "failure", 1), self.run_("Frontend CI", "success", 2)]
        self.assertIn("green", session_ci_status.summarize("abc1234def", runs, False))

    def test_no_runs_yet(self):
        self.assertIn("no CI runs yet", session_ci_status.summarize("abc1234def", [], False))


if __name__ == "__main__":
    unittest.main()
