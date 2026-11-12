# TOON input encoding, candidacy_considered — plan-llm-protocol-and-theory-program.md §5.E

## The two gates, per §5.E's own stated bar

§5.E's own Verification section: *"two gates, not one... (a) token count before/after via
`count_prompt_tokens`; (b) a decision-quality A/B, since token savings are worthless if
comprehension drops — run it on `candidacy_considered` first, which has real ground truth
(`simple_rules.decide_candidacy`) and no known collapse defect, so a quality regression is
attributable to the format rather than confounded with an existing failure."*

## Method

`check_toon_candidacy_ab.py`: 25 synthetic citizens (the shipped `llm.max_batch_size`, one real
full-size chunk), `ambition_score` evenly spanning both sides of the shipped
`ambition_threshold=0.3` (18 ground-truth "declare", 7 "decline"). Two new, diagnostic-only
prompt builders (`build_candidacy_system_prompt_toon`, `build_candidacy_user_prompt_toon`,
offline-tested to differ from the shipped JSON versions ONLY in an added format-explanation
paragraph with a worked example — everything else, including the motif table and the
expected-cid self-check, is byte-identical) run against the real production
`CANDIDACY_JSON_SCHEMA` (output stays JSON — §5.E's own hard input-only constraint), real
`think=False` (this decision type's own production value). Same 25 citizens, same seed, one
call per format.

## Result: real token savings, zero quality difference

| | JSON | TOON |
|---|---|---|
| prompt_tokens | 853 | 794 |
| decoded cleanly | 25/25 | 25/25 |
| correct vs ground truth | 16/25 | 16/25 |

**Token savings: 59 tokens, 6.9%.** Real, but modest relative to the plan's own rough
pre-estimate — expected, since candidacy's own prompt (3 keys, 25 records) is small to begin
with; the plan's own analysis named `pressure_action` (~8-12 keys, up to 25 citizens, "the
single highest-volume decision type in the project") as where TOON's key-repetition savings
should pay off more.

**Accuracy: identical, not just similar — 16/25 for both formats.** Both decoded every
decision cleanly (no format-induced parse/validation failures), and the exact same count
matched ground truth. This satisfies gate (b): the format change carries no measured quality
cost here.

## A separate finding, out of scope for this gate

16/25 = 64% accuracy is itself notably below this project's own established ≥80% reliability
bar — on BOTH formats identically, meaning this is a pre-existing property of
`candidacy_considered` under this specific test construction (ambition scores spanning the
threshold), not something TOON introduced or worsened. §1's earlier finding table recorded
`candidacy_considered` as "no collapse (5/5)" — a much smaller, structural-validity-only
sample, not a per-citizen ground-truth accuracy figure the way this test measures. Whether
64% here reflects a real, previously-uncharacterized `candidacy_considered` reliability gap
(distinct from the collapse question) or an artifact of this test's own citizen construction
is a genuinely open question this script surfaces but does not answer — worth a dedicated
follow-up, not conflated with the TOON verdict here.

## Disposition

**§5.E's own bar is cleared for `candidacy_considered`.** Per the plan's own ordering,
`pressure_action` was the next candidate tested (`check_toon_pressure_action_ab_results.md`) —
opposite result there: real token savings but a real quality regression (TOON flips which
constant the model collapses to), so it is NOT shipped. The two decisions are independent, not a
blanket "TOON everywhere" policy — see `check_pressure_shipped_wiring_results.md` for what
`pressure_action` shipped instead (calibration, not a format change).

**SHIPPED, 2026-09-10.** `decide_candidacies` now calls `build_candidacy_system_prompt_toon`/
`build_candidacy_user_prompt_toon` instead of the JSON pair — output stays JSON
(`CANDIDACY_JSON_SCHEMA`, unchanged), only the input encoding changed. Live-reconfirmed against
the actual wired function (not just the standalone builders) on a 20-citizen population spanning
the ambition range: 20/20 decoded cleanly, non-constant outcomes tracking ambition_score as
expected. Offline: `mypy api/` clean, `ruff check .` clean, full polity suite 1379/1379 (six
fake LLM clients across `test_polity_llm_behavior_engine.py`/`test_polity_run_simulation.py`
needed a small TOON-parsing fix, since `decide_candidacies`'s own user_prompt is no longer JSON —
mechanical, no behavior change). Still a single live A/B run at the diagnostic-builder level, not
yet replicated with a second seed — the risk this leaves open is narrow (a JSON-vs-TOON format
difference on a type with no known collapse, not a fresh quality question), but worth naming
rather than silently treating as fully closed.
