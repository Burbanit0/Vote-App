# How many of my own written rules were already being broken?

Every project accumulates rules nobody enforces. They live in a
`CONTRIBUTING.md`, a `CLAUDE.md`, a skill file — "workers never import from
the routes layer," "no bare `except Exception` without a log line," "the
pure library code never imports from UI components." They're true the day
they're written. Nothing then checks whether they stay true, which means
the honest status of any such rule, six months on, is simply unknown until
someone goes looking. Vote Lab went looking, on purpose, and turned four
written-but-unenforced rules into blocking gates to find out.

The framing going in was blunt: *how many of my documented conventions were
already being violated, without me knowing?* The honest answer turned out
to be more interesting than a single number — because the rule that mattered
most was already clean, and the rules that caught real debt were the ones
written in direct response to incidents that had already happened.

## The deepest rule was already true

The architectural rule with the most riding on it — that the backend's
layering flows strictly `route → domain → engine`, documented as a
convention in the project's own API-conventions guide — got encoded as a
real `import-linter` contract and run as a blocking CI gate. The result:
**zero violations**. The layering the team had been holding to by discipline
alone actually held, verified rather than assumed. That's a valid, useful
result precisely because it wasn't guaranteed in advance — an unenforced
rule staying true for months is worth knowing with certainty, not just
believing.

The equivalent check on the frontend — a `dependency-cruiser` rule
forbidding the pure `src/lib` layer from ever importing UI components or
pages, a boundary the project's own architecture notes already state in
prose — came back just as clean: 287 modules, 1,558 dependencies, zero
violations. Before trusting either gate, both were tested the way this
project tests its own detectors elsewhere: a synthetic violation was
injected on purpose, confirmed to fail the gate, then removed and confirmed
green again. A rule that has never been proven capable of firing isn't a
gate yet, whatever its config file says.

## The rules born from real incidents found real debt

The picture flips entirely with the second kind of rule: custom Semgrep
checks written to encode three specific bug classes the team had already
been burned by, on a single day, in production code — "no worker imports
from the routes layer," "every v2 endpoint carries a rate limit," "no bare
`except Exception` swallowing an error without a log line." These weren't
abstract best practices; they were direct anti-recurrence rules for
incidents that had already cost real debugging time.

Writing them surfaced real, previously invisible debt immediately:

- **Three v2 routers with no rate limit at all** — a gap in exactly the
  protection the incident that inspired the rule was about. Fixed on the
  spot.
- **Eighteen bare `except Exception` blocks across nine files**, silently
  swallowing errors with no log line — meaning eighteen distinct places
  where something could fail with zero trace of it ever happening. All
  eighteen fixed, in the same pass, rather than filed as debt for later.

Neither finding was cosmetic. A missing rate limit and a silently swallowed
exception are both the specific shape of failure that's invisible until
someone hits it in production — which is exactly why the rule existed to
begin with, and exactly why it was worth checking immediately rather than
trusting that "we already fixed those" meant *all* of them were fixed.

## Smaller finds, same discipline

A cycle-detection pass with `madge` turned up one real import cycle between
a simulation Web Worker hook and a heatmap component — benign in this case
(a type-only import, erased entirely at compile time, so no runtime risk),
but real, and now visible instead of latent.

And in a small, almost self-referential twist: the plan document driving
this entire audit had, at one point, asserted as fact that the project's
Claude Code configuration had *zero* hooks in place. That claim was false —
guardrails already existed, protecting the generated engine-parity fixture
from accidental hand-edits — and the document corrected itself in the same
breath it made the claim, rather than letting an unverified assertion about
tooling stand uncorrected in a document specifically about not trusting
unverified assertions. Even the audit's own draft prose wasn't exempt from
the audit's own standard.

## What the exercise actually answered

The honest headline isn't a single scary number, and that's the more
useful result. The rule that would have been the most expensive to have
silently drifted — the layering that keeps the engine's boundaries
intentional — hadn't drifted at all, and now there's a CI gate proving it
stays that way instead of a paragraph asking people to remember. The rules
that *did* catch real, fixable debt were the ones written closest to an
actual incident, encoding a specific failure the team had already lived
through rather than a generic best practice borrowed from elsewhere — which
suggests a rule of thumb worth carrying to the next project: a convention
written down before anything ever went wrong is a hope; a convention written
down right after something went wrong, and then made mechanical, is where
the real debt turns out to be waiting.

---

*Sourced from [`PLAN_SOLIDITE_TECHNIQUE.md`](../../PLAN_SOLIDITE_TECHNIQUE.md),
Lot 2 ("Rendre les conventions exécutables"). The `import-linter` contract
lives in `fast_api_voter/pyproject.toml`; the custom Semgrep rules in
`.semgrep/vote-app-rules.yml`; the frontend boundary rule in
`.dependency-cruiser.json`.*
