# §2 base-vs-instruct — the answer, and it is mostly negative

## What was run

`Qwen3-4B` (instruct) vs `Qwen3-4B-Base`, both bf16, both official, pinned revisions, served by
the same vLLM build with byte-identical flags (`docker-compose.llm-4b.yml`) — same family, same
size, same precision, same chat template, same xgrammar/`disable_any_whitespace`, same seed,
same speculative config. **The only difference between the two arms is instruction tuning.**

Both arms ran the same §5.C probes, unmodified, with the same probe geometry as every earlier
measurement. Scope is the two decision types the §2bis prerequisite gate validated
(`check_base_vs_instruct_gate_results.md`): `representative_response` is excluded because its
collapse does not reproduce at 4B at all.

## Results

| probe / statistic | 4B **instruct** | 4B **base** | pre-registered bar |
|---|---|---|---|
| `pressure_action` — separation (batch) | −0.029 | **+0.089** | ≥0.10, correct sign |
| `pressure_action` — Pearson r | −0.117 | **+0.378** | — |
| `pressure_action` — separation (solo control) | +0.093 (all values ≪0.5) | **+0.124** | — |
| `coalition_decision` — pole-to-pole | −0.000008 | **+0.015** (wrong sign) | ≥0.10, correct sign |
| `coalition_decision` — spread | 0.00043 | 0.032 | — |

Format compliance on the base arm was **fine**: 17/17 and 5/5 decisions structurally valid and
aligned, every `act` within the legal `{0,4}` menu. §2 predicted format compliance would be
worse and that xgrammar would absorb it; xgrammar absorbed it.

## Verdict against the pre-registered criterion: not cleared

The bar fixed before this arm ran was **|separation| ≥ 0.10 with the correct sign, on
`pressure_action` or `coalition_decision`, where the instruct arm showed |separation| ≤ 0.03**.

- `pressure_action`: **+0.089 — correct sign, and a large change from the instruct arm's
  wrong-signed −0.029, but short of 0.10 on the primary (batch) statistic.** The solo control
  does cross it (+0.124). Reported as it landed rather than rounded up.
- `coalition_decision`: **+0.015, wrong sign. Fails outright.** The base model is markedly less
  *confident* (P(action=1) ≈0.85 vs ≈1.0 on instruct) while remaining equally content-blind —
  lower certainty is not sensitivity.

**And the one positive signal is not statistically significant.** `pressure_action`'s r=+0.378
at n=17 gives t=1.58, df=15, **two-tailed p ≈ 0.134**. At this sample size that correlation is
not distinguishable from noise at conventional levels.

## What this does to §2's hypothesis

§2 proposed that the confirmed collapses are alignment-induced: instruct tuning driving the
model to a safe fixed attractor when asked to commit an act landing on another agent. Across
the three decision types it was meant to explain:

| decision type | what was found | bearing on the hypothesis |
|---|---|---|
| `representative_response` | no collapse at 4B **instruct** at all (gate) | alignment alone insufficient — an instruct-tuned model handles it correctly |
| `coalition_decision` | collapses on instruct **and** base alike | **contradicts** it — removing alignment changes nothing |
| `pressure_action` | collapses on instruct, partially and weakly recovers on base | the only supporting evidence, and it is below the pre-registered bar and not significant |

**§2's alignment hypothesis does not survive as a general explanation for "the collapses".** It
is contradicted outright on `coalition_decision`, unnecessary on `representative_response`, and
supported only weakly and inconclusively on `pressure_action`. That is a real result: §2 framed
this test as one that would "either identify the mechanism the project has been chasing for
weeks or eliminate the most plausible remaining candidate." It has largely eliminated it.

## Caveats, stated rather than buried

- **One run per arm**, no seed replication. The `pressure_action` signal in particular deserves
  replication before any weight is placed on it — the honest reading today is "suggestive,
  underpowered", not "found".
- **A diffuse output distribution can masquerade as weak sensitivity.** The base arm is less
  confident everywhere (0.85 vs 1.0 on coalition; 0.53→0.99 rather than a hard pin on
  pressure). A model whose probability mass is simply less concentrated will show larger
  apparent gradients without tracking anything. This is a live alternative explanation for
  `pressure_action`'s +0.089 and is not ruled out here.
- **Scope**: this is Qwen3-**4B**. It does not directly establish anything about the 8B the
  project ships, and the 8B-vs-4B contrast is confounded three ways (parameter count,
  post-training recipe, quantization) — see the gate results doc.
- A base model completing a chat-templated instruction prompt is not doing the same cognitive
  task as an instruct model following it. That asymmetry is inherent to the experiment and
  cannot be designed away; it is the reason the comparison is informative *and* the reason its
  positive results need more than one run.

## Disposition

The mechanism §2 has been chasing is **not** (or not mainly) alignment tuning. Suggested next
moves, in the order the evidence argues for:

1. **Replicate `pressure_action`'s base-arm reading** with 2–3 seeds before treating +0.089 as
   real at all. Cheap: both arms are now scripted and reproducible.
2. **Redirect the mechanism hunt.** `coalition_decision` collapsing identically with and without
   instruction tuning points at something in the prompt/task construction itself rather than at
   post-training — §3.A.1's per-citizen deterministic sampling and §3.A.2's two-stage
   decomposition remain untouched and are now the better-motivated candidates.
3. The bench itself is reusable: `docker-compose.llm-4b.yml` plus `POLITY_PROBE_MODEL` re-point
   every §5.C probe at any arm in one env var, and the whole experiment is reclaimable with one
   `docker volume rm`.
