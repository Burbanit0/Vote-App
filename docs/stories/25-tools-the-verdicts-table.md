# 25 quality tools on a real project — the table nobody else publishes

Search for engineering blog posts about adopting a tool and you will find no
shortage of them: "we added X to our pipeline," complete with a config
snippet and a victory lap. Search for posts about the tools a team tried and
threw away, with the real reason and the real evidence, and the shelf is
almost bare. Nobody publishes their rejects. Not because rejects aren't
interesting — the opposite, usually — but because keeping score of your own
"no" requires exactly the kind of bookkeeping that only pays off in
public later, long after the decision itself stopped being urgent.

Vote Lab, a small pedagogical voting-methods sandbox, kept that bookkeeping
anyway. Every tool trial that reached a real verdict — adopt, reject, or
suspend — got a same-template writeup: a starting hypothesis, the exact
protocol run, what was actually found (explicitly: "found nothing" counts as
a valid, interesting result), what it cost, and a closing "what would
transfer to another project." Fourteen of them, at last count, sit in
[`docs/exploration/`](../exploration/README.md) as EXP-001 through EXP-014,
indexed in a table anyone can scan in under a minute: tool, domain, verdict,
real findings, cost.

The honest gap is worth stating up front, because a project that audits its
own tools should be willing to audit its own claims about them: roughly
twenty-five tools were tried across the full hardening effort this table
comes from, but only fourteen got the full formal ritual. The other eleven
or so — GuardDog, TruffleHog, `madge`, `type-coverage`, `ccusage`,
`nbstripout`, a handful of minor Dependabot and CI calls — were short,
proportionate decisions written as a paragraph rather than a full carnet.
The index itself says so, plainly, rather than rounding the "~25" up to
match the marketing framing. That kind of correction, applied to your own
project's own claim about itself, is the same discipline the table exists
to document in the first place.

What makes the table worth reading isn't the count. It's that a rejection
gets exactly the same rigor as an adoption — verified against the real
state of the repo, not against the tool's marketing page. Four examples
carry the whole argument.

## Lost Pixel: rejected without a single test run

The plan's own candidate for visual regression testing was a choice between
Playwright's native `toHaveScreenshot` and Lost Pixel, a purpose-built visual
diffing service. Lost Pixel never got installed. On April 22, 2026, the
project publicly announced its team was joining Figma and archived the
repository — checked *before* any integration work started, not discovered
partway through one. Playwright's own screenshot comparison, pinned to a
Docker image for pixel-perfect reproducibility across machines, became a CI
gate instead. The rejection cost nothing because it happened at the research
step, which is the entire point of doing the research step.

## hypofuzz: rejected despite being the better technical fit

This is the more interesting shape of rejection, because the tool wasn't
weak — it was disqualified on a completely different axis. `hypofuzz` would
have reused the project's existing Hypothesis property-based strategies
directly, layering coverage-guided fuzzing on top of infrastructure already
in place — a real technical advantage over the alternative. It lost anyway,
to `atheris`, for two independent reasons found by checking rather than
assuming: its license is non-OSI and restricted to non-commercial use, on a
project that is itself MIT and public; and its PyPI release trailed roughly
six months behind the project's actual latest commit. `atheris` won on
license and freshness, not on technical merit — and said so plainly instead
of pretending the loser was worse at the thing it was actually good at.
(`atheris` then went on to find four real crashing bugs in the voting
engine and its LLM-response parsers in a few cumulative minutes of fuzzing —
a separate story worth telling on its own, but the selection process that
got it in the door is the point here.)

## `.claudeignore`: confirmed not to exist, before it got used as a plan

The plan drafted a concrete action item: add a `.claudeignore` file to keep
generated artifacts (a 155k-token `package-lock.json`, a 152k-token
notebook, a 116k-token generated OpenAPI schema) out of casual reads. Before
writing that file, the actual Claude Code permissions documentation got
checked for the word "claudeignore." Zero occurrences. What turned up
instead was an open upstream feature request for exactly this
(`anthropics/claude-code` issue #579) and several other issues confirming
that a `.claudeignore` file dropped into a repo today is simply ignored,
silently, by the tool that would need to read it. No such file was created.
The verification didn't kill the goal — it redirected it: a `PreToolUse`
hook, modeled on an existing guardrail already proven to fire in this repo,
now surfaces a warning on a full, untargeted read of any of the known
generated files. The one thing the plan assumed existed didn't; the thing
that actually solved the underlying problem was found by checking rather
than by trusting the first idea.

## OSV-Scanner vs. Trivy: a measured zero, not an assumed one

Two vulnerability scanners, checked for real overlap instead of picking one
on reputation. Before trusting a "0 vs 0" result on this repo's actual
dependencies, the detector itself was proven sensitive first: run against
two deliberately outdated packages (`urllib3==1.26.4`, `Jinja2==2.4.1`, 18
real CVEs apiece), both scanners caught all of it. Only then did the real
comparison run against this repo's real dependency tree — 0 findings from
each, cross-checked with a third independent tool (`pip-audit`, also 0).
The zero is meaningful specifically because the tool was shown capable of
producing a non-zero first. A "no findings" result that skips that step is
indistinguishable from a broken scanner; one that includes it is evidence.

## The pattern underneath the individual tools

Look across all fourteen formal writeups and the same move repeats: don't
trust a detector's silence until you've watched it make noise on something
it should catch. `EXP-004` (the Lost Pixel/Playwright decision) injected a
real visual regression — a mis-colored 0.07%-of-pixels marker — into a
screenshot test with an overly forgiving tolerance, watched it pass when it
shouldn't have, tightened the threshold, and watched the same injection fail
correctly. `EXP-006` (`pytest-benchmark`) injected a real O(n²) performance
regression into a voting method (3.7ms → 1,101.6ms, a 290x slowdown),
confirmed the gate caught it, then confirmed it went green again after the
regression was reverted. Even the custom `import-linter` and
`dependency-cruiser` architecture rules got the same treatment: a synthetic
violation injected, watched fail, removed, watched pass again — before
either was trusted as a real gate rather than a plausible-looking one.

That's the actual shareable artifact here, more than any single tool's name.
Anyone can list twenty-five tools they tried. Far fewer can show, tool by
tool, the moment they made each one lie on purpose, just to prove it was
capable of telling the truth.

---

*Sourced from [`PLAN_SOLIDITE_TECHNIQUE.md`](../../PLAN_SOLIDITE_TECHNIQUE.md)
(Lot 0.3's framing and Lot 13's own honest reconciliation of "~25 tried" vs.
"14 formal"), the [verdicts index](../exploration/README.md), and
[EXP-004](../exploration/EXP-004-regression-visuelle-playwright-screenshots.md),
[EXP-009](../exploration/EXP-009-osv-scanner-vs-trivy-overlap.md), and
[EXP-011](../exploration/EXP-011-atheris-coverage-fuzzing.md) for the Lost
Pixel, OSV-Scanner, and hypofuzz decisions respectively.*
