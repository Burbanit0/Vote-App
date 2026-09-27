# Polity — tech radar

A recurring log of anything in the LLM-serving / open-model / agent-simulation space that could
matter for `polity` (the 30-year, population-500 election-history goal: autonomous citizens,
chambers, multiple voting methods, leader-countering mechanisms — currently a single Qwen model
served locally through vLLM in Docker), plus anything that's just worth knowing to keep up with a
fast-moving field even when it doesn't apply here yet. Machine-appended roughly every two days by
a scheduled session, always as a PR — nothing in here is ever adopted by the entry itself; only a
human merging real code (a compose-file pin, a config default) makes that call.

**Rules for an entry**

- Written for a reader with no prior context: no unexplained jargon. If a term like "batch
  invariance" or "speculative decoding" is used, it's explained in a sentence first.
- Every **For this project** finding has four parts: *What it is*, *Why it matters here* (which
  watch item or goal it touches), *How to test it* (a concrete, runnable check — reusing this
  project's own harnesses where they fit, naming the actual metric that would confirm or deny the
  effect), and a **verdict**: `watch` (nothing actionable yet) / `worth a probe` (cheap enough to
  try) / `adopt candidate` (probed and looks good — still needs a human to actually merge it).
- **AI/LLM culture** findings skip the test plan (there's nothing to adopt) but keep the
  plain-language "what it is" and add "why it's worth knowing".
- Entries are append-only, oldest watch-items list at the top stays static, dated log entries go
  at the bottom in order, sourced and dated. Nothing here is ever deleted or rewritten after the
  fact — a stale verdict gets a new entry saying it's stale, same as `observations.md`'s status model.

## Watch items

Seeded from this project's own explicitly-written "reopening conditions" — the things the project
has already decided are worth revisiting later, plus a general-purpose slot for anything else:

1. **Deterministic ("batch-invariant") concurrent serving cost.** Today, running vLLM with more
   than one worker at once makes `vote_cast` outcomes diverge by about 4% between runs of the
   *same* config — unacceptable for a reproducible 30-year history. The fix that exists today
   (`VLLM_BATCH_INVARIANT=1`) removes the divergence but makes generation about 11x slower, which
   is why the flagship 30-year run is currently planned strictly sequential (~22.5h). Any serving
   engine or vLLM release that gets cheaper determinism directly unblocks running this project's
   simulations in parallel instead of one at a time.
2. **AWQ-vs-bf16 reliability re-verification.** The model's weights were quantized (AWQ, 4-bit) to
   fit VRAM; several reliability tunings (thinking-token budgets, chunk sizes) were originally
   measured on the unquantized weights and haven't all been re-checked against the quantized ones.
   Not itself "new tech", but a newer/cleaner quantization format could make the question moot.
3. **NVFP4 precision probe / EAGLE-3 speculative decoding.** Both already tried as probes (not
   switched to production): NVFP4 keeps a known behavioural issue ("the collapse") but shifts which
   citizens end up as candidates; EAGLE-3 measured about 1/3 faster on real runs. Watch for either
   maturing enough in a new vLLM release to be worth a real production switch, not just a probe.
4. **New Qwen releases.** The model family currently in use is `Qwen3-8B-AWQ`. Watch for a
   quantized (AWQ/GGUF), `enable_thinking`-capable build of a newer generation to actually ship and
   get vLLM support — a bigger/better base model is only useful once it's actually servable on this
   project's hardware.
5. **Decision-quality techniques for the still-"unverified" decision types.** `representative_response`
   and `coalition_decision` are flagged as still not reliably answering based on their real input,
   and about 40% of citizens declare candidacy at every election (likely too high). Watch for
   prompting/serving techniques (structured output grammars, decision-specific fine-tunes, etc.)
   that could plausibly help with either.
6. **General radar (broad scope).** Anything else notable for long-horizon, high-determinism,
   many-agent simulation — a new serving engine (e.g. SGLang, TensorRT-LLM), a new open-weight
   model family, or an agent-simulation technique from an unrelated field — even without a specific
   tie to items 1–5 above.

## Index

| ID | Date | Category | Title | Verdict |
|---|---|---|---|---|
| [TR-001](#tr-001) | 2026-09-26 | project | Baseline snapshot of the six watch items | watch |
| [TR-002](#tr-002) | 2026-09-26 | project | Qwen4 preview family announced (Max/Flash/Plus/27B) | watch |
| [TR-003](#tr-003) | 2026-09-26 | culture | Jev: a non-generative "decision" model, not an LLM | — |

## Log

### TR-001

**What it is.** This is the seed entry, not a new finding — it restates where each of the six
watch items above stands today, so the next real radar pass has a documented "before" to diff
against, instead of silently assuming everyone remembers the current state.

**Why it matters here.** Without a documented baseline, a future entry saying "no change on item 1"
is unverifiable. This entry is that baseline: item 1 (batch invariance) unresolved, 11x cost;
item 2 (AWQ reliability) partly unresolved; item 3 (NVFP4/EAGLE-3) both probe-only; item 4 (Qwen
releases) currently on Qwen3-8B-AWQ; item 5 (decision quality) two decision types still flagged;
item 6 open by definition.

**How to test it.** Not applicable — nothing to test, this is a status restatement sourced from
the project's own docs (`docs/plan/polity/plan-flagship-30y-run.md`,
`docs/claude-memory/project_polity_vllm_switch.md`, `docs/plan/polity/observations.md` OBS-007 and
OBS-011).

**Verdict:** `watch` — no action, reference point only.

### TR-002

**What it is.** Alibaba previewed a new generation of its open Qwen model family — "Qwen4", in
four sizes (Max, Flash, Plus, and a 27-billion-parameter model) — on 2026-09-22. It builds on an
architecture first previewed in late August via "Qwen3.8-Flash-Next", an open-weight model. In
plain terms: this is a newer, presumably more capable version of the same model family this
project already runs (`Qwen3-8B-AWQ`), from the same source.

**Why it matters here.** Ties to watch item 4. A better base model is only useful once it's
actually servable here — as of this entry (4 days after the preview), there's no confirmed
quantized (AWQ/GGUF) build and no confirmed vLLM support for it, so it isn't switchable yet.

**How to test it.** Not yet testable. Once (if) a quantized 8B-or-smaller variant with
`enable_thinking` support and vLLM compatibility ships, run it through
`fast_api_voter/scripts/check_llm_stack_versions.py --discover` (already gates a candidate on VRAM
fit and `enable_thinking` support before recommending it), then — only if it passes — run the
project's own `scripts/bakeoff_request_arms_results.md`-style bake-off against the current
`Qwen3-8B-AWQ` baseline before considering any switch, exactly as the AWQ-vs-bf16 change was
treated as a confounding variable requiring its own re-verification.

**Verdict:** `watch` — nothing servable yet.

### TR-003

**What it is.** "Jev" is a proprietary model from a startup (TypeSafe AI), released mid-September
2026. It is *not* a chat/text-generating LLM: instead of writing sentences, it outputs a typed
decision (e.g. a category) with a confidence score, directly — the company calls this a "System 1"
model, after the fast/intuitive half of human thinking. The pitch is that this makes it far cheaper
and faster than a full LLM for tasks that are really just classification, at the cost of not
producing readable text.

**Why it's worth knowing.** It's a useful concept to know even though it doesn't fit `polity`
directly: this project's core value is the deliberation text itself (citizens reasoning, taking
positions, reacting to events), which a decision-only model can't produce — it could, in principle,
only replace a narrow sub-step that's already just a single categorical output (e.g. the final
yes/no of `vote_cast` once the deliberation text already exists). Jev itself is proprietary and not
free, so it isn't a real option here regardless — but the general category ("skip full generation,
output a typed decision with a confidence score, for the sub-steps that are really just
classification") is a pattern worth recognizing if it ever shows up in a free/open form.

**Verdict:** — (culture note, not project-actionable; no test plan)
