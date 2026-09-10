# Geometry-B replication — the §2 loose end, closed

## What this was for

`check_base_vs_instruct_results.md` left exactly one loose end: `pressure_action`'s base arm
showed separation +0.089 / r=+0.378, the only evidence supporting §2's alignment hypothesis,
and at n=17 it was not significant (p≈0.134). This replicates it under a different probe
geometry — **not** different seeds, which cannot vary anything at `temperature=0` (see that
doc's own correction).

Geometry B changes the incidental construction choices and nothing else: different cid block
(9000+ vs 4000+), 17 differently-placed `self_gap` values over the same span with the same
8-below/9-above split, a different fixed `mandate_dev` (0.25 vs 0.10), `ticks_to_election`
(6 vs 10), `target` (777 vs 999), and **descending** batch order. Same prompts, schema,
`think=False`, closed shipped menu, instrument and statistics.

Both arms were run under both geometries — the control that decides whether any effect is
base-vs-instruct or merely geometry.

## The full 2×2

`pressure_action`, P(act=4) tracking `self_gap`:

| | geometry A | geometry B |
|---|---|---|
| **4B instruct** | separation −0.029, r = −0.117 | separation +0.017, r = **+0.494** (p=0.044) |
| **4B base** | separation +0.089, r = +0.378 (p=0.135) | separation +0.073, r = **+0.685** (p=0.0024) |

## What replication actually showed

**The base-arm signal did not dissolve — it strengthened.** r rose from +0.378 (p=0.135) to
+0.685 (**p=0.0024**), now significant, with a visibly monotonic rise at the high end (0.007 at
mid-range self_gap climbing to 0.469 at self_gap=2.20).

**But the control removes the interpretation.** The *instruct* arm also produces a significant
positive correlation under geometry B (r=+0.494, **p=0.044**), where under geometry A it was
negative. So geometry B elicits gradient behaviour from **both** arms. "Base tracks `self_gap`,
instruct doesn't" is **not** supported.

What survives, consistently across both geometries: the base arm is **somewhat more** sensitive
than the instruct arm on both statistics (r: +0.378 vs −0.117, and +0.685 vs +0.494;
separation: +0.089 vs −0.029, and +0.073 vs +0.017). A real, repeatable, but small ordering.

**Neither arm, in either geometry, clears the pre-registered |separation| ≥ 0.10 bar** (base:
+0.089, +0.073).

**And in all four cells the decision output is fully collapsed** — every single threshold-call
is the same constant (act=0 in three cells, act=4 in geometry-A base). Only the underlying
probability moves at all; the decision never does.

## One built-in control worth naming

Geometry A batched ascending (high `self_gap` late in the chunk); geometry B batched descending
(high `self_gap` early). A positional artifact would therefore have **flipped sign** between
geometries. It did not — both arms show positive correlation in geometry B, and the base arm is
positive in both. So the correlation is a genuine `self_gap` effect, not a
position-within-chunk artifact. That is the one thing these two geometries jointly establish
cleanly.

## The more interesting finding, which was not what this was looking for

**The overall probability level is dominated by the call-level constants, not by the
per-citizen signal.** Base arm: P(act=4) ≈0.53–0.99 under geometry A, ≈0.007–0.47 under
geometry B. Instruct arm: ≈0.0001–0.12 under geometry B. Changing `mandate_dev`/
`ticks_to_election`/`target` moved the whole distribution by up to two orders of magnitude,
while `self_gap` — the per-citizen signal this decision is supposed to hinge on — moves it far
less within any single call.

Caveat on attribution: geometry B changed several call-level constants at once, so this cannot
be pinned to any one of them. What it does establish is that *something* in the shared,
call-level context overwhelms the individual citizen's own state. That is a sharper
characterisation of the failure than "collapse", and it is directly actionable — it points at
the same place §3.A.1 and §3.A.2 already point: at how the per-citizen signal is presented and
resolved, not at post-training.

## Disposition

§2's loose end is closed. The alignment hypothesis picks up a small, repeatable, but
bar-missing amount of support: the base arm is consistently somewhat more `self_gap`-sensitive
than the instruct arm, yet both track it, neither clears the pre-registered threshold, and the
committed decision is collapsed in every configuration tested. The overall §2 verdict from
`check_base_vs_instruct_results.md` — alignment tuning is not the mechanism — stands, now with
the one piece of contrary evidence properly bounded rather than left hanging.
