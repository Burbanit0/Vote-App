---
description: Check that the branch does what was asked (fast-gate + the spec-checker agent) and prepare the PR's "Evidence" section
argument-hint: "<the original request, verbatim>"
---

Check the current branch before opening its PR.

0. **What gets checked is what is committed.**
   - fast-gate and spec-checker both compare the base with `HEAD`.
   - If `git status --porcelain` shows uncommitted tracked changes, stop: say so and offer to commit first.
   - Otherwise the check would cover other code than the PR's, and a fast-gate "no changes" would pass for a success.
   - **The base**, written `<base>` below, is the future PR's: `origin/polity` by default, or `origin/develop` for a sync. Both checks get the same one.
1. **The request.**
   - Take `$ARGUMENTS` as the original request, verbatim.
   - With no argument, take the user's message that started this work, as is, without summarising or rewording it.
   - If it is no longer available, ask for it. A paraphrase written by the change's author is not evidence.
2. **The fast checks.**
   - Run `scripts/fast-gate.sh <base>` and keep its summary.
   - A `SKIPPED` section is not a pass: note it.
3. **Does it do what was asked.**
   - Run the `spec-checker` agent with the exact request and the same `<base>`.
   - Give it neither your own summary of the change nor the commit messages.
   - Show its report as is.
4. **The "Evidence" block.** Print a block ready to paste into the PR template's `## Evidence` section:
   - the commands actually run, with their output (the useful last lines);
   - the spec-checker's verdict and its criteria (C1, C2…);
   - a **Not verified** line, required and never empty: write "nothing" only when true.

If the verdict is `FAIL`, or a criterion is missing, do not open the PR. Say what is missing and suggest the next step.

If the verdict is `GAPS`, open it only if the gaps are written in the PR.

Do not fix anything on the report's word alone.
