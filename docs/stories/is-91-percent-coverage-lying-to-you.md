# Is 91% coverage lying to you?

A voting-methods sandbox called Vote Lab carries a coverage badge that most
teams would be happy to show off: **91.56% on the backend, 87.05% on the
frontend**, under `pytest-cov` and Vitest respectively. Both numbers are
real, both are reproducible, and both answer a much narrower question than
the badge implies. They tell you that some test, somewhere, called a
function with synthetic data and every line lit up green. They say nothing
about whether a real user clicking through the real app ever reaches that
line at all.

That gap — between "a test executes this" and "a user's journey executes
this" — is exactly what two existing signals in this codebase are
structurally unable to see, and it's worth being precise about why, because
the blind spot is not a tooling gap that a better linter fixes.

**Static dead-code detection** (`vulture`, `knip`, `dependency-cruiser`) sees
what's referenced by *nothing*. It cannot tell that a function referenced
only by its own unit test — imported nowhere else in the entire source tree
— is never triggered by an actual route. To a reachability graph, a test
file importing something is a perfectly legitimate edge.

**Unit coverage** sees what a test reaches by calling a function directly,
with hand-built inputs, often exercising a code path deeper or stranger than
any real click ever would — and sometimes completely disconnected from
whether that function is wired into anything the running application
actually serves.

Both signals were already at "green" on the file that turned out to be the
most interesting exhibit in the whole exercise. Green wasn't wrong. Green
just wasn't the whole story.

## A third signal: what the real app actually touches

The fix was conceptually simple: measure coverage under the real end-to-end
suite — a real browser, against a real backend process, driving real HTTP
and WebSocket traffic, not synthetic function calls. On the backend, that
meant wrapping the actual `uvicorn` process Playwright talks to with
`coverage.py`. On the frontend, it meant instrumenting the real Vite build
with Istanbul and reading `window.__coverage__` back out of the browser
after each spec.

Getting there took two debugging detours that are worth recounting on their
own, because both are the kind of failure that looks like success.

The first attempt to capture backend coverage produced *nothing*: the
server logged a perfectly clean shutdown — "Shutting down… Application
shutdown complete… Finished server process" — and yet no `.coverage` file
ever appeared on disk, verified three times over before it was believed.
The cause lived in `uvicorn`'s own signal handling: on a clean stop,
`Server.capture_signals()` restores the *original* signal handler and then
re-raises the same signal against itself, by design, so that a process
supervisor sees the real exit code in the process's termination status. That
second, self-inflicted signal kills the process via the kernel's default
action *after* Python has already finished cleaning up — which completely
bypasses `atexit`, the exact mechanism `coverage.py`'s save-on-exit depends
on. The fix was to install a custom SIGTERM/SIGINT handler *before* uvicorn
installs its own, so that uvicorn captures that handler as "the original"
and hands control back to it — at exactly the moment its self-signal fires —
in time to call `coverage.Coverage.current().save()` before the default
kernel action takes over.

The second detour was quieter and arguably scarier: an early "complete" run
produced coverage numbers that looked entirely plausible — reasonable
percentages against real files — while measuring nothing that had actually
happened. A third-party process, unrelated to this work, was already
squatting on the default port the instrumented server was supposed to bind
to. The health-check probe used to confirm the server was up happily
answered against that other process instead, the e2e suite passed, and a
coverage report was dutifully generated from a server that had never
started. The address-already-in-use error was sitting in the log the entire
time; nobody had grepped for it, because a passing suite and a generated
report looked like enough evidence. The fix was mechanical (a dedicated
port), but the lesson generalizes past this one script: a plausible-looking
report is not proof it measured what you think it measured.

## The numbers, once the plumbing was trustworthy

Two independent runs, reproducible to the line:

| | Unit tests | Real e2e | Delta |
|---|---|---|---|
| Backend — lines | 91.56% (13,687 / 14,949) | **34.4%** (5,149 / 14,949) | −57 pts |
| Frontend — statements | 87.05% (9,125 / 10,482) | **63.15%** (6,211 / 9,835)* | −24 pts |

*(Denominators differ slightly between Vitest's native-V8 coverage provider
and Istanbul's Babel-based instrumentation — two legitimate ways of counting
a "statement" that don't land on exactly the same total. The comparison
holds in direction and magnitude, not to the exact digit.)*

The backend's drop is far steeper than the frontend's, and that asymmetry
makes sense once you think about the shapes of the two codebases: the
frontend shares one component tree across a handful of real routes, so
visiting even a few pages exercises a large slice of shared UI, hooks, and
stores. The backend exposes dozens of independent worker functions behind
dozens of independent routes, and the e2e suite only walks a handful of
them.

## Two findings the numbers made impossible to ignore

**An entire, unreachable subsystem.** `api/domain/polity/` — 2,813 lines
across twenty files, roughly 19% of the whole backend — sits at **0%**
execution under e2e while running at **~99%** under unit tests (ten of its
files even hit exactly 100%, appearing in the unit report's own "fully
covered" list). This wasn't a bug hiding in plain sight; it was a research
subsystem that never had a reason to be one. A direct check confirms it:
`api/main.py` registers exactly seven routers — health, election, export,
public, simulations, tech, theory — and grepping the entire route layer for
the string "polity" returns nothing. The frontend has zero references to it
either. The code is real, it's tested, and it's driven instead by a
separate harness of research scripts that import it as a library, entirely
outside the HTTP app a user's browser ever talks to. Not a defect — but
exactly the kind of architectural boundary that should be written down
explicitly rather than left for someone to rediscover by accident.

**A page nobody visits anymore, but that both layers still swear is fine.**
`/simulation/compare` is a legacy redirect now — `routes.ts` sends it
straight to `/playground`, and the page component is mounted by nothing but
its own test. And yet the backend keeps `POST /compare` alive and fully
wired (`_compare_methods_worker`, 457 lines, already the lowest unit
coverage in the entire backend at 65%, and it falls to **7%** under e2e).
On the frontend, `useDebouncedSimulation.ts` — the hook that calls this same
now-orphaned endpoint — sits at **100%** of its own functions covered by its
own unit test, and is referenced *nowhere else* in the entire `src/` tree.
`knip` does not flag it as dead code, and it isn't behaving incorrectly by
its own rules: an import from a test file is, by knip's own design, a
legitimate reason for a file to exist. But that legitimate design choice is
precisely what creates the blind spot — "statically referenced" and
"100% unit-covered" can both be true of code that no real route has mounted
in months. Neither signal, alone or combined, could have surfaced this. It
took a third question neither tool is built to ask: does a route actually
mount this component, for real, right now?

## What this is (and isn't) worth to a project

This measurement was adopted as a **diagnostic tool, run on demand — not a
CI gate**, and the reasons are concrete rather than a vague "it's too
slow." Under Istanbul instrumentation, the heaviest single test in the
frontend suite (a client-side spatial simulation) slowed from 2.7s to 4.3s
in isolation — tolerable — but under the suite's normal 8-way parallelism,
that same test **failed on a 30-second timeout on Firefox, reproducibly, on
two independent runs out of two**. That's real instability introduced by
the measurement itself, not a regression in the product, and shipping it as
a recurring nightly signal would manufacture exactly the kind of
unreproducible red the project's separate flake-hunting effort had
otherwise worked to eliminate. The second reason is about what kind of
question this even is: it's a photograph taken after a major cleanup
("what, concretely, is unreachable in real usage right now"), not a trend
to watch commit over commit the way unit coverage or a mutation score are.

Coverage isn't lying, exactly. It's answering a real question honestly —
"did some test execute this line" — while a badge on a README quietly lets
readers assume it answered a different one: "does this code do anything for
a real user." The 91% was never false. It just wasn't, on its own, the
number that mattered.

## Related signals this project also runs

Runtime reachability is one axis of "does the test suite actually mean
something." Two others, run alongside it here, ask a different pair of
uncomfortable questions and are worth naming for completeness:

- **Mutation testing** (`mutmut` on the backend's voting engine, floored at
  70%; Stryker on the client engine, floored at 80%, both gating in CI) asks
  whether the assertions inside an already-green, already-reachable line
  would even notice if the logic were subtly broken — a check on the
  *meaning* of a passing test, not just whether it ran.
- **`pytest-randomly`**, randomizing test order on every run, plus a
  purpose-built flake hunter that reruns the full 1,974-test backend suite
  three times with a different random order each time and diffs the
  results, asks whether tests are secretly coupled to each other through
  shared state. Three real runs during this work found zero flakes — a
  clean result, reported as exactly that rather than dressed up.

None of the three signals — runtime reachability, mutation score, or
order-independence — replaces the other two. Each catches a different way a
coverage number can tell the truth about the wrong question.

---

*Sourced from [`PLAN_SOLIDITE_TECHNIQUE.md`](../../PLAN_SOLIDITE_TECHNIQUE.md)
(Lot 5 and Lot 6.5) and
[`docs/exploration/EXP-003-couverture-runtime-e2e.md`](../exploration/EXP-003-couverture-runtime-e2e.md),
which carries the full protocol, both debugging detours in detail, and the
per-file numbers.*
