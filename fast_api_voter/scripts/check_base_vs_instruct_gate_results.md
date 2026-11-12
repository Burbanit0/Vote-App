# §2bis prerequisite gate — does the collapse reproduce on Qwen3-4B instruct?

## Why this gate exists

§2bis chose a bf16 `Qwen3-4B` / `Qwen3-4B-Base` pair as the only base-vs-instruct bench that
fits this hardware without confounding the variable under test (no official quantized Qwen3
base model exists at any size; the literal 8B-base form needs ~16GB of weights on a 16.3GB
card). That pair only answers §2's question **if the collapse reproduces on the 4B instruct arm
in the first place** — otherwise there is nothing there for a base arm to explain. This is that
gate, run before the base arm was ever started.

Method: the three §5.C probes, unmodified, pointed at the bench arm via `POLITY_PROBE_MODEL`.
Same prompts, same schemas, same `think=False`, same probe geometry as the measurements already
recorded against the shipped 8B.

## Result: 2 of 3 reproduce

| decision type | shipped 8B instruct (AWQ) | 4B instruct (bf16) | reproduces? |
|---|---|---|---|
| `pressure_action` | flat, P(act=4) ≥0.976 everywhere, separation **+0.004** | flat, P(act=4) ≈0 everywhere, separation **−0.029**, r = −0.117 | **yes** |
| `coalition_decision` | flat, P(action=1) 0.965–0.999, spread **0.035** | flat, P(action=1) ≈1.0, spread **0.00043** | **yes** |
| `representative_response` | flat, P(stance=1) = 1.0 ± **0.000001** | **not flat** — pole-to-pole **+1.000000** | **no** |

### `pressure_action` and `coalition_decision`: collapsed on both

Both are flat in the sense that matters — no gradient tracking the signal the decision is
supposed to depend on. `coalition_decision` is if anything *flatter* at 4B (spread 0.00043 vs
0.035). The bench is valid for these two.

One detail worth recording rather than smoothing over: `pressure_action` collapses to the
**opposite constant** at 4B (always `act=0`/NOTHING) from the shipped 8B (always
`act=4`/WAIT_FOR_ELECTION). The flatness reproduces; the pole does not.

### `representative_response`: does NOT collapse at 4B

At the no-problem pole (L=0.95, street=0.00) the 4B instruct model chose `stance=3` (SILENCE),
P(stance=1)=0.000000. At every point carrying real pressure it chose CONCESSION with
P(stance=1)=1.000000. That is a sharp, correctly-directed discrimination between exactly the
two poles the original diagnostic used — where the shipped 8B is flat at 1.0 ± 0.000001 across
the whole interpolation, conceding identically to a healthy officeholder and one in crisis.

**The 4B bench cannot answer §2's question for this decision type** — there is no collapse there
to attribute to anything. Per §2bis's own pre-registration, that non-reproduction is itself the
finding.

## What the non-reproduction constrains

§2's hypothesis is that the collapses are **alignment-induced** (instruct tuning pushing the
model to a safe fixed attractor when asked to commit an act that lands on another agent).
`Qwen3-4B` and `Qwen3-8B` are **both instruct-tuned**. If alignment tuning alone caused
`representative_response`'s collapse, it should appear on both. It does not. So for this
decision type, pure alignment is not sufficient as an explanation — something that differs
between these two models (scale, post-training recipe, or quantization — see the confound
below) is load-bearing.

That does not refute §2's hypothesis for the other two types; it narrows where it can apply.

## The confound this comparison carries, stated plainly

**The 8B-vs-4B contrast conflates at least three variables: parameter count, post-training
recipe, and quantization** (shipped 8B is AWQ 4-bit; the 4B arms are bf16). Nothing here
licenses reading these differences as a clean "scale effect". They are recorded as *observed
differences between two concretely-specified configurations*, nothing more.

The experiment this gate exists to enable is the one that is *not* confounded: `Qwen3-4B` vs
`Qwen3-4B-Base`, identical in family, size, precision, template and serving flags, differing
only in instruction tuning.

## A pattern now visible across three measurements

`pressure_action`'s collapse *constant* has now moved three times while its *flatness* never
did:

| configuration | collapses to |
|---|---|
| 8B-AWQ instruct, JSON prompt | `act=4` (WAIT_FOR_ELECTION), P≈1.0 |
| 8B-AWQ instruct, TOON prompt | `act=0` (NOTHING), every point <0.5 |
| 4B-bf16 instruct, JSON prompt | `act=0` (NOTHING), P≈0.0 |

Surface form and model identity both move *which* constant is chosen; neither restores
sensitivity to `self_gap`. Whatever drives this collapse appears to be robust to changes that
readily flip its output — which is a stronger constraint on the mechanism than any single
measurement gives.

## Criterion for the base arm, restated against the correct baseline

§2bis pre-registered "base arm shows ≥0.10 spread on at least one probe where instruct showed
<0.05", calibrated against the *8B* instruct spreads. With the bench now characterized, the
correct comparison baseline is the **4B instruct** arm, and one statistic needs replacing:
max−min spread is fragile to a single outlier (4B instruct `pressure_action` shows spread 0.2227
driven entirely by one point at self_gap=0.42, while every other point sits below 0.007). The
primary discrimination statistics for the base arm are therefore the two the probes already
report and that actually measure signal-tracking:

- **separation** (mean P above vs below the decision-relevant threshold), and
- **Pearson correlation** between the varied signal and P,

with max−min spread reported as secondary. Restated threshold, fixed before the base arm runs:
**the base arm counts as materially more content-sensitive if, on `pressure_action` or
`coalition_decision`, it shows |separation| ≥ 0.10 with the correct sign, where the 4B instruct
arm showed |separation| ≤ 0.03.** Worse format compliance on the base arm is expected and is
reported separately from the gradient reading, never conflated with it.

## Disposition

Gate **passes for two of three** decision types. The base arm is worth running, and will be
read only against `pressure_action` and `coalition_decision`;
`representative_response` is out of scope for the 4B bench, with its non-reproduction recorded
above as a finding in its own right.
