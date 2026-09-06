# vLLM/AWQ vs Ollama — a severe, vLLM-specific truncation bug on `PressureDecision`

Found 2026-09-05 while directly comparing vLLM against Ollama on `pressure_action`'s real,
unmodified production schema (`PressureDecision`), following up on `plan-vllm-switch-readiness.md`'s
already-completed axis (a)/(b) checklist (`scripts/vllm_switch_results.md`) with a broader
head-to-head comparison across more decision types.

## What triggered the investigation

`check_vllm_pressure_action_open_menu_baseline.py` — the vLLM replay of the already-established
open-menu quality baseline — measured **60/70 (85.7%) truncations** (`finish_reason='length'`),
a rate with no precedent anywhere else in this session's vLLM testing (campaign_positioning and
chamber_deliberation, both axis-(b) hard cases, ran clean at 0/18 and 0/10 respectively). The 10
calls that did complete all returned the same act (`MOBILIZE`), including on cases where the
correct answer was clearly "don't act" — itself a red flag independent of the truncation rate.

## Root cause: `sort_keys=True` reordering `PressureDecision`'s fields

Direct inspection of a raw response (the same discipline that already found the `a_reasoning`
ordering mechanism in this investigation) showed the model emitting valid tokens through
`"motif": <n>` and then generating `\n   ` (newline + three spaces) repeated hundreds of times,
never reaching `target` or closing the JSON object — a non-terminating whitespace loop that burns
the entire token budget.

`llm_client.py`'s `json.dumps(body, sort_keys=True, ...)` — applied unconditionally to every
decision type, every provider, in production — reorders `PressureDecision`'s wire fields from
their natural declaration order (`cid, target, act, motif`) to alphabetical (`act, cid, motif,
target`). Isolated with a controlled A/B, both orderings, both providers, same 4 citizens, same
prompts, **exact production request shapes** (vLLM's OpenAI-compatible body via
`VllmJsonClient`; Ollama's native `/api/chat` body, matching
`pressure_action_harness.raw_pressure_call` exactly — an apples-to-apples comparison matters here,
since a first attempt against Ollama's `/v1/chat/completions` endpoint accidentally exercised a
*different*, already-documented Ollama bug, not this one):

| | vLLM | Ollama |
|---|---|---|
| `sort_keys=False` (natural order) | 4/4 clean | 4/4 clean |
| `sort_keys=True` (**shipped, production**) | **0/4 clean** — whitespace loop every time | 4/4 clean |

Deterministic (temperature=0, fixed seed) and fully reproducible via
`check_vllm_pressure_action_sort_keys_truncation.py`. **vLLM-specific**: the exact same reordering,
on the exact same schema and prompts, does not affect Ollama at all.

## What this is not

This is a **different, more severe** finding than
`plan-pressure-action-remediation.md`'s own `sort_keys` discovery (§3.4) — that one was about a
missing `a_reasoning` field being generated in the wrong position relative to `act`/`motif`, a
content-quality problem. This is complete non-termination on `PressureDecision`'s real,
already-shipped, unmodified schema — no reasoning field involved at all. Nor is the precise
xgrammar/vLLM-internal mechanism that makes this specific schema shape (four flat integer fields,
two `enum`-constrained) vulnerable investigated here — that would need vLLM-internals-level
tooling this project doesn't have; the finding is empirical, not mechanistic.

## Severity and scope

This directly blocks any future `provider: vllm` production switch as currently wired:
`pressure_action` is a real, currently-shipped decision type, and an 85.7% truncation rate is not
a tolerable degradation under any existing mitigation (`max_batch_replays` defaults to 0; even
raised, a deterministic 100% per-citizen failure at temperature=0 doesn't resolve via retry the
way `_VOTE_CAST_RETRY_TEMPERATURE`'s narrow exception does for a different bug).

This was not caught by `plan-vllm-switch-readiness.md`'s own axis (b) checklist
(`scripts/vllm_switch_results.md`) because that checklist's two named hard cases
(`campaign_positioning`, `chamber_deliberation`) don't happen to exercise this schema shape.
**`vllm_switch_results.md`'s "all clear" verdict needs this correction**: axis (b) passed on the
two cases it tested, but a third, untested decision type shows a severe, vLLM-specific failure —
the checklist was not exhaustive over every decision type in the engine, and this result is
evidence that it should be before any production switch is considered, not just evidence against
`pressure_action` specifically. Other decision types with similarly small, flat, `enum`-heavy
schemas (`ResponseDecision`, `CoalitionDecision`) are plausible candidates to check next but are
NOT tested here — flagged as a real gap, not assumed safe.

`sort_keys` is not touched here, deliberately — same standing discipline as every other mention
of it in this investigation: shared code across every decision type, needs its own separate
scoping decision, never a workaround folded into an unrelated investigation.

## Addendum: the `a_reasoning` schema (`check_vllm_pressure_action_reasoning_field_first.py`) avoids the truncation bug, but shows a different, opposite-direction quality problem

Curiosity check, same session: does the `a_reasoning`-first schema from
`check_pressure_action_reasoning_field_first.py` (Ollama) / its vLLM replay share this truncation
bug? Its wire order is `a_reasoning, act, cid, motif` — also alphabetically reordered, no `target`
field at all. **Result: 70/70 clean, 0 truncations, 0 order violations.** Whatever makes
`PressureDecision`'s specific `act, cid, motif, target` ordering vulnerable does not generalize to
every alphabetized 4-field schema — genuinely narrower than "any reordering breaks vLLM," and not
further isolated here (would need testing more orderings/field-count combinations to map the
actual boundary, out of scope for this comparison).

That said, the *content* result is a new, real finding of its own, and it does not favor vLLM:

| | Ollama | vLLM/AWQ |
|---|---|---|
| Pooled agreement | 81.4% (57/70) | 32.9% (23/70) |
| should-act (informative, n=17) | 23.5% (4/17) | 70.6% (12/17) |
| should-not-act (n=53) | 100% (53/53) | 20.8% (11/53) |

Both backends fail the pre-registered 80% bar on the informative subset, but in **opposite
directions**: Ollama systematically under-recommends action (collapses toward inaction); vLLM/AWQ
systematically over-recommends it — 41 of 42 wrongly-decided should-not-act cases got
`SIGN_PETITION` specifically, not a random spread across the other three legal codes.

The "70 distinct reasoning strings, therefore not content-blind" check
(`check_pressure_action_reasoning_field_first.py`'s own verdict logic) is too weak to catch this:
it only tests exact-string uniqueness, and every string embeds the citizen's own `self_gap` value,
making each one technically unique even when substantively templated. Direct inspection: **51 of
70 (73%) vLLM reasoning strings contain the identical verbatim phrase** ("suggère une opportunité
pour agir avant le scrutin" — roughly "suggests an opportunity to act before the election") — a
genuine content-blindness pattern by the qualitative standard already used elsewhere in this
investigation (`plan-pressure-action-remediation.md`'s own template-detection reading of §3.2/§3.4
traces), just not caught by that one script's distinct-string heuristic. Anyone re-running that
verdict logic on a new backend/model should check for template phrases directly, not rely on the
distinct-count proxy alone.

