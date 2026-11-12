# §3.A.1's premise does not hold — per-citizen sampling cannot fix this collapse

## What was checked, and why before building

§3.A.1 is the plan's own "highest-value idea": everything runs at `temperature=0` (greedy
argmax), and *"content-blind collapse is, mechanically, what greedy decoding does to a
weakly-discriminated distribution"* — so drawing each citizen's decision from a per-citizen
deterministic seed should restore population variance while keeping exact reproducibility.

Two things needed checking first.

### The architectural problem

`seed` and `temperature` are per-**request** body fields (`llm_client.py`), and
`decide_pressure_actions` batches up to `llm.max_batch_size=25` citizens per request. **A
literal per-citizen seed therefore requires `chunk_size=1`** — 25× the call count, on the
highest-volume decision type in the project.

The zero-cost alternative is to sample **offline** from the logprobs §5.C already reads: one
greedy batched call yields P per citizen, then each citizen's outcome is drawn with its own
deterministic RNG (`blake2b(run_seed|citizen_id|tick|decision_type)` — not Python's `hash()`,
which is per-process randomized and would silently destroy the reproducibility this design
exists to preserve). Same result, no extra GPU work.

### The premise

Offline sampling **can only express signal already present in P. It cannot create any.** So the
question is whether the shipped model's P(act=4) carries enough spread for sampling to produce
real variance — or whether the distribution is itself already degenerate.

## Result: the distribution is not weakly-discriminated, it is confidently wrong

Live against the shipped `qwen3:8b`, same 17-citizen `pressure_action` geometry as every prior
measurement:

| | |
|---|---|
| act=4 rate, greedy (production today) | **17/17 = 100%** |
| act=4 rate, per-citizen deterministic draw | **17/17 = 100%** |
| act=4 rate, deterministic proxy says | 9/17 = 52.9% |
| mean P(act=4) | **0.998168** |
| mean Bernoulli variance p(1−p) | **0.001796** (max possible 0.25) |
| expected decisions changed by sampling | **0.03 of 17** |

**Per-citizen sampling would change 0.03 of 17 decisions in expectation — nothing.**

## And it fails in every other configuration measured too

Applying the same arithmetic to the P values recorded in every configuration measured this
session:

| configuration | mean P | mean p(1−p) | E[flips]/17 | % of decisions |
|---|---|---|---|---|
| shipped 8B (geometry A) | 0.9982 | 0.00180 | 0.03 | **0.2%** |
| 4B base (geometry A) | 0.9528 | 0.03249 | 0.80 | 4.7% |
| 4B base (geometry B) | 0.0563 | 0.04139 | 0.96 | **5.6%** |
| 4B instruct (geometry B) | 0.0091 | 0.00827 | 0.16 | 0.9% |

Even in the *most* favourable configuration ever measured, sampling flips ~6% of decisions. In
the shipped one — the only one that matters for a real run — it flips 0.2%.

## The correction this forces on our own reading

An earlier synthesis of this session's work claimed the logprob measurements were *"the
empirical proof of exactly the mechanism §3.A.1 describes — the signal exists in the
distribution and it is the argmax that throws it away."* **That overstated what was measured,
and this check refutes it.**

What is true: P **correlates** with `self_gap` (up to r=+0.685, p=0.0024 on the 4B base arm),
and that correlation survives reversing the batch order, so it is a genuine content effect.

What does not follow: that the correlation has enough **magnitude** to matter. Correlation is
scale-free; population variance is not. A distribution can track a signal faithfully in *shape*
while pinned so close to 0 or 1 that no draw from it ever changes an outcome. That is exactly
what these numbers show — P varies with `self_gap` while sitting at 0.998 (shipped) or 0.006–0.47
(4B base), so the realised Bernoulli variance stays near zero either way.

**The collapse is therefore not an argmax artifact of a weakly-discriminated distribution. It is
a confidently near-deterministic distribution that is simply wrong** — and the four
configurations differ mainly in *which* pole they are confident about, not in how confident they
are.

## Disposition

**§3.A.1 should not be built as specified.** Its mechanistic premise is false in every
configuration measured, and its literal form additionally costs 25× the calls for a decision
type that is already the project's highest-volume one.

This does not exhaust the idea's family. What it rules out is the cheap version — reading the
existing distribution and drawing from it. Anything that would actually work has to **change
the distribution itself**, not resample it:

- **§3.A.2 two-stage decomposition** — the remaining untouched candidate, and the one this
  result argues for most directly: if the model is confidently wrong on a compound judgement,
  splitting it into a narrower first stage changes what distribution is produced, rather than
  re-drawing from a bad one. §5.C's instrument already supplies that stage's read.
- **The call-level-context finding** (`check_pressure_gap_tracking_geometry_b_results.md`): the
  overall probability level is dominated by shared call context rather than the per-citizen
  signal. Making the per-citizen signal structurally harder to ignore is a distribution-changing
  intervention, and is untested.
- Raising temperature above 1 would flatten the distribution and manufacture variance, but that
  is noise, not signal — it would add population variance uncorrelated with each citizen's own
  state, which is worse than the current failure for an ABM, not better.
