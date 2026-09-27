# pressure_action is never told the criterion — and a wrong conclusion my own control caught

## The observation that started this

`simple_rules.deterministic_pressure_action` — the proxy every `pressure_action` measurement in
this project is scored against — decides by comparing `gap < citizen.blank_threshold`.

`PressureContext.to_payload()` sends `{self_gap, mandate_dev, neighbors_acting,
ticks_to_election}`. **`blank_threshold` is never sent, and no decision rule is ever stated.**
The model is asked to judge "is this citizen discontented enough to act" while being given a raw
`self_gap` number with no per-citizen scale reference and no criterion.

The contrast with `vote_cast` — the one type this project rates reliable (23/24 against real
ground truth) — is sharp. Its prompt supplies all three ingredients: the quantity (`distances`,
pre-computed), the per-voter threshold (`blank_threshold`), **and** the rule stated explicitly:
*"Un candidat est ACCEPTABLE si et seulement si sa distance est INFERIEURE OU EGALE au
'blank_threshold' de l'electeur."*

## Four arms, shipped model, same 17-citizen geometry as every prior measurement

| arm | what was added | mean P(act=4) | separation | proxy-agreement |
|---|---|---|---|---|
| A baseline | nothing (production prompts) | 0.9982 | +0.0038 | 9/17 |
| B +threshold | `blank_threshold` in each ctx (data only) | 0.9781 | +0.0462 | 9/17 |
| C +rule | B + a rule from `self_gap` to *acceptability* | 0.0035 | +0.0004 | 8/17 |
| D +act mapping | B + the rule stated through to the act choice | 0.9999 | +0.0001 | 9/17 |

Read carefully, this refutes the hypothesis it was built to test:

- **Supplying the missing data barely helps** (A→B: proxy-agreement unchanged at 9/17, which is
  exactly the majority-class baseline).
- **Stating a rule flips the constant rather than inducing tracking** (C: the whole distribution
  moves to always-`act=0`, still flat).
- **Stating the full mapping flips it back** (D: always-`act=4`), still flat — even though arm D
  supplies both numbers and says, in plain terms, `self_gap > blank_threshold → act=4`,
  and includes citizens at `self_gap=0.02` where the stated rule unambiguously says `act=0`.

Arm C and D together add a fourth entry to this session's growing list of things that move
*which* constant is chosen without restoring sensitivity — after prompt format (TOON), model
identity (4B vs 8B), and probe geometry.

## The solo control, which changes everything

The same arm-D prompt, one citizen per call:

| self_gap | threshold | P(act=4) | chose | rule says | |
|---|---|---|---|---|---|
| 0.02 | 0.5 | 0.007346 | `act=0` | `act=0` | correct |
| 2.20 | 0.5 | 1.000000 | `act=4` | `act=4` | correct |

**Solo separation: +0.992654.** Against +0.0001 for the identical prompt at batch 17.

So the model *can* execute the stated comparison, essentially perfectly, one citizen at a time.
Whatever fails at batch size does not fail for lack of capability or lack of instruction.

## Where a confident, wrong conclusion nearly got written up

The obvious follow-up was to sweep batch size and find the cliff. That sweep
(`check_pressure_batch_size_sweep.py`) built each batch by **alternating** clearly-below /
clearly-above values, and produced a dramatic result: 1/1 at size 1, then at or below the 50%
blind-guess baseline at *every* larger size — including 0/12 with separation **−0.9157**, i.e.
confidently inverted. The natural reading was "per-record attention collapses at batch 2", and it
would have made a tidy story alongside `cast_votes`'s own documented batching finding.

A control in the same script re-ran every size with the order permuted. The picture inverted:
**2/2, 8/8, 12/12, 17/17, 24/25** — near-perfect at exactly the sizes that had just "collapsed".

The model had been pattern-completing on the alternation instead of reading values, and the
0/12 inversion was that completion landing one position out of phase. **The first sweep measured
the regularity of my own input, not the model's batch capacity.** Only the control stopped it
being reported as a finding.

## The properly randomized sweep, and what it actually shows

The predecessor's "shuffle" was a single fixed permutation that barely disturbs alternation at
small n (at n=3 it is simply a reversal). `check_pressure_batch_order_randomized.py` re-does it
with genuinely random orders, several per size, RNG seeded from `(run_seed, batch_size, trial)`
so the sweep replays identically:

| batch | per-trial accuracy | mean |
|---|---|---|
| 1 | 100% · 100% · 100% | **100%** |
| 3 | 100% · 67% · 100% | 89% |
| 5 | 20% · 80% · 100% | 67% |
| 8 | 50% · 50% · 50% | 50% |
| 12 | 0% · 100% · 83% | 61% |
| 17 | 88% · 94% · 53% | 78% |
| 25 | 92% · 92% · 92% | 92% |

There is **no clean cliff and no monotonic decline**. Within a single batch size accuracy swings
enormously (size 5: 20–100%; size 12: 0–100%), and size 25 outperforms size 8. What is robust:

- **batch 1 is reliably correct** (3/3 trials at 100%);
- **every size above 1 is unstable**, driven by the specific composition and order of the batch
  rather than by its size.

So batch size alone does not characterise this, and any recommendation phrased purely as a chunk
size would be overfitting to whichever composition happened to be tested. That is as far as the
evidence goes.

## What is actually established

1. **The production prompt does not contain the information its own scoring proxy uses.** No
   `blank_threshold`, no stated criterion. This is not in dispute — it is visible in
   `PressureContext.to_payload()` and `build_pressure_system_prompt`.
2. **Given the criterion, at batch 1, the model is essentially perfect** (separation +0.993).
3. **Given the criterion at larger batches, accuracy is unstable** in a way governed by batch
   composition, not size — not characterised further here.
4. **Without the criterion, nothing else moves the needle**: adding the data alone leaves
   proxy-agreement at the majority-class baseline, and adding rules only relocates the constant.

## The design question this raises, which is not mine to settle

There is a reason the criterion is absent, and it is deliberate. `build_coalition_system_prompt`'s
own docstring states the principle: *"No coalition-theory framing anywhere in this prompt (§3.3 —
no 'prefer a minimal winning coalition', no strategy hint of any kind): only the rules of the game
and the closed code tables."* The project withholds decision rules on purpose, to measure **free
arbitration** rather than rule-following.

These measurements suggest that when a model is given a bare scalar with no scale reference and
no criterion, "free arbitration" does not produce a distribution of judgements — it produces a
constant, and which constant is highly labile. That is a real tension between the experimental
design and what the instrument can deliver, and resolving it is a modelling decision:

- supply the per-citizen threshold as **data** without stating a rule (arm B) — closest to the
  design's intent, but measured here as nearly inert;
- supply the rule and accept that the LLM is then executing a specification rather than
  arbitrating (arm D at batch 1 — accurate, but it makes the model a slow reimplementation of a
  two-line function);
- keep the current design and treat `pressure_action`'s output as unusable for any claim that
  depends on per-citizen variation.

## Disposition

No production change made. The three scripts are diagnostic. The most concrete actionable item
is item 1 above — a prompt that omits the quantity its own proxy compares against is a defect
independent of any collapse hypothesis, and it is cheap to fix. Whether fixing it is *desirable*
depends on the §3.3 design question, which is the project owner's call.
