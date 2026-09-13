# Shareable stories

Four standalone write-ups pulled out of
[`PLAN_SOLIDITE_TECHNIQUE.md`](../../PLAN_SOLIDITE_TECHNIQUE.md), the
technical-hardening plan for Vote Lab. The plan itself is French, internal,
and organized by work item ("Lot"); these are the opposite on purpose —
English, narrative, written for a reader who has never opened this repo, one
real investigation per file. Each one is meant to be linked and read on its
own, the way a blog post is, not as a chapter of a larger document.

Every number and quote in each story traces back to a specific test file, an
experience carnet under [`docs/exploration/`](../exploration/README.md), or
a dated section of the plan — cited at the bottom of each piece.

- **[Is 91% coverage lying to you?](is-91-percent-coverage-lying-to-you.md)**
  — a green coverage badge (91.56% backend, 87.05% frontend) turns out to
  answer "did a test execute this line," not "does a real user ever reach
  it." Measuring coverage under the actual end-to-end suite instead of unit
  tests drops the backend to 34.4% and finds a fully-tested 2,813-line
  subsystem with zero routes wired to it — plus a page invisible to every
  existing signal at once.

- **[25 quality tools — the verdicts table nobody else publishes](25-tools-the-verdicts-table.md)**
  — most "we adopted tool X" posts never mention what got rejected. This one
  tracks rejections with the same rigor as adoptions: a tool dropped
  because its maintainers joined a competitor, a technically-better tool
  disqualified by license, a documented feature confirmed not to actually
  exist, an overlap measured instead of assumed.

- **[Testing a mathematical theory the way you test code](testing-a-mathematical-theory-like-code.md)**
  — social-choice theory's own axioms (Condorcet, monotonicity, independence
  of clones…) as executable assertions against 26 voting methods, an
  under-sampled search that misclassified four methods until a real
  shrinking search caught it, an independent academic library that
  exposed real bugs (and one of its own), and a formal solver proof that
  caught a mistake in its own first encoding.

- **[How many of my own written rules were already being broken?](how-many-written-rules-were-already-broken.md)**
  — turning four documented-but-unenforced conventions into blocking gates.
  The deepest architectural rule turned out to already hold; the rules
  written in direct response to a real incident immediately caught real,
  unfixed debt — three routers with no rate limit, eighteen silently
  swallowed exceptions.
