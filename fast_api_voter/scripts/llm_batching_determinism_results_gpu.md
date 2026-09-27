# LLM batching determinism — protocol result (GPU)

Verification protocol for design doc §15bis.5 / DEMARRAGE-polity-v0.md §5.
Run 2026-08-17, immediately after recreating `ollama-polity` with
`--gpus=all` (RTX 5070 Ti, driver 591.86) — the first time this exact
protocol has been run against a GPU-backed Ollama instance. Directly
comparable to `llm_batching_determinism_results.md` (CPU, run 2026-07-31):
same script, same model, same options, same batch sizes. **This document
does not replace or invalidate the CPU one** — both measurements stand,
each describing the backend it was run against.

**Setup**: Ollama, GPU (`--gpus all`, RTX 5070 Ti), `OLLAMA_FLASH_ATTENTION=false`
(disabled as a separate, already-applied fix earlier this session — see the
`campaign_positioning` reliability investigation for why), `OLLAMA_NUM_PARALLEL=8`
(matching the CPU protocol's concurrency setup so the comparison is
apples-to-apples), model `qwen2.5:0.5b` (pinned, not `:latest`),
`temperature=0`, fixed `seed=42`, one fixed prompt (the same mock
citizen-vote-factors prompt), `num_predict=64`.
Script: `fast_api_voter/scripts/check_llm_batching_determinism.py` (reused
unmodified — no new tooling needed).

## Result: the B2 concern reproduces on GPU too, unchanged in kind

| Check | CPU (2026-07-31) | GPU (2026-08-17) |
|---|---|---|
| batch_size=1, 10 consecutive runs | identical | **identical** |
| batch_size=1, before vs. after a full container restart | identical | **identical** |
| batch_size=5 | NOT identical | **NOT identical** |
| batch_size=25 | NOT identical | **NOT identical** |
| batch_size=50 | NOT identical | **NOT identical** |
| **Overall** | FAIL | **FAIL** |

**The non-determinism does not disappear on GPU, and it does not change in
kind** — sequential, unbatched calls (`batch_size=1`) remain perfectly
reproducible, including across a cold container restart; concurrent
batching (`batch_size>=5`) still produces divergent completions from
otherwise-identical requests. This is the same qualitative shape as the CPU
result, on the same script, same model, same seed.

What is new information this run, not available from the CPU doc alone —
the **degree** of divergence, measured as distinct outputs per batch:

| Batch size | Distinct outputs (of N) |
|---|---|
| 5 | 4 |
| 25 | 5 |
| 50 | 12 |

Divergence does not scale linearly with batch size (12/50 is a *smaller*
fraction than 4/5), consistent with batching-induced numerical
non-associativity being a property of *how many requests happen to land in
the same forward pass together*, not a fixed per-request corruption rate.

Example (batch_size=5, same prompt, same options, only the batch differs —
first ~180 characters of each):

```
[0] "1. **Political Beliefs and Values**: Candidates A and B represent
     different political ideologies and values. Understanding the
     candidates' positions on issues such as social justic"
[1] "1. **Political Beliefs and Values**: Candidates A and B represent
     different political ideologies and values. Understanding these
     differences can help the voter make an informed dec"
[2] (identical to [1])
[3] (identical to [1])
[4] "1. **Political Beliefs and Values**: Candidates A and B represent
     different political ideologies and values. If the voter is
     influenced by their beliefs and values, they might be m"
```

Likely cause: unchanged from the CPU finding — floating-point
non-associativity in batched matrix multiplication, where concurrent
requests change the numerical reduction order inside the same forward
pass. This is a documented property of batched inference generally
(llama.cpp/Ollama on either backend), not a CPU-specific artifact and not
something the GPU switch introduced. Flash attention was disabled for this
run (see Setup); whether flash attention *on* changes the degree of
batching divergence was not tested here — this protocol tests concurrent
identical-content batching, a different mechanism from the single-call
content-degeneracy issue flash attention was disabled to fix.

## Consequence for the design

Unchanged from the CPU result — both decisions in `polity_config.yaml`
remain correctly conservative, now confirmed on the backend the project
actually runs on:

- `batch_sharding: static` (§15bis.4a) — still correct; this result shows
  *any* concurrent batching breaks reproducibility on GPU too, not just
  dynamic reassignment.
- `parallel.intra_run_workers: 1` (§15bis.3) — still correct; intra-run LLM
  call parallelism would still break byte-for-byte reproducibility (Lot 8)
  on GPU, exactly as it would on CPU.

**Open question, still not resolved by this run** (carried over verbatim
from the CPU doc, unchanged): whether a *fixed-size* static batch (same
citizens, same batch composition, called the same way every run) is
internally deterministic even though *concurrent* calls aren't. This run,
like the CPU one, only tested identical-content concurrent batches — it
does not test the actual v2+ scenario (same composition, different
per-citizen content, called the same way run over run).

## Reproducing this check

```bash
docker exec ollama-polity ollama pull qwen2.5:0.5b   # if not already present
python fast_api_voter/scripts/check_llm_batching_determinism.py --save before.json
docker restart ollama-polity   # wait for it to come back up
python fast_api_voter/scripts/check_llm_batching_determinism.py --compare before.json
```

Requires `ollama-polity` running with `--gpus=all` and
`OLLAMA_NUM_PARALLEL=8` (the shipped production container does not set
`NUM_PARALLEL`, which defaults to 1 — that's correct for production, where
`intra_run_workers: 1` means only one request is ever in flight at a time,
but it would mask this protocol's batching test, which needs the server
able to accept concurrent requests to exercise the failure mode at all).

## Cold start vs. warm: a second, distinct determinism gap (2026-08-18)

Everything above tests `qwen2.5:0.5b`, `num_predict=64`, no `think`, no
structured output — a materially different regime from what production
actually runs (`qwen3:8b`, `think=True` for most decision types, long
chain-of-thought before the JSON answer, `response_format` strict). This
section covers a gap the protocol above never exercised: is a single,
**isolated, non-concurrent** production call — the "batch_size=1: identical"
case above — actually reproducible for the real model and the real
`think=True` request shape? It is not, but only for the first call after a
cold model load.

**How this was found**: the v6b acceptance run failed a third time in
`cast_votes` with the same `finish_reason='length'` signature already fixed
once for `decide_campaign_positioning` (§A.3 of the working session), this
time exhausting all `max_batch_replays` attempts on the same chunk. An
attempt to replay the chunk that had originally failed — 170 attempts across
the 34 real dumped chunks, 3 reps each plus a fresh single pass — reproduced
it zero times. Investigating why turned up something more fundamental:
running the identical config twice from a fresh process and hashing every
`complete_json` call showed that **call 1 — the very first LLM call of the
pipeline (`candidacy_considered`) — has byte-identical system/user prompt
hashes between the two runs, but a different raw response.** Calls 2-5
(other citizens' independent candidacy decisions) then matched exactly
between both runs; from call 6 (`decide_campaign_positioning`) onward the
two runs had genuinely diverged in both prompt content and outcome —
consistent with call 1's differing decision changing the final nominee
count (observed directly: one fresh run produced 4 nominees, another
produced 5, for the same seed/config).

**Isolated confirmation** (`test_isolated_think_determinism.py`, ad hoc,
not committed as a script — reused two already-dumped real production
prompts, `decide_campaign_positioning`'s and `cast_votes`'s, called 8×
sequentially with `think=True`, raw output hashed each time):

| Prompt | Model state at rep 1 | Result |
|---|---|---|
| positioning | cold (`ollama ps` empty just before) | rep 1 differs; reps 2-8 all identical to each other |
| vote_chunk0 | already warm (positioning's own reps just ran) | 8/8 identical |
| positioning, re-run | already warm (from the run above) | 8/8 identical, and the stable hash matches reps 2-8 of the cold run exactly |

Once warm, the model is perfectly, repeatedly deterministic for identical
input — 16/16 matched hashes across every warm call observed. Only the
first call after a genuinely cold model load diverges. This is a known
class of GPU-inference behavior (kernel-selection/autotuning heuristics
that can pick a different execution path on the first invocation of a
freshly loaded model), not a general property of the model or of `think=True`
generation.

**Two follow-up checks, both load-bearing for the fix:**

1. **Is `keep_alive` honored on `/v1/chat/completions` (the endpoint every
   `think=True` call uses)?** No. Sending `"keep_alive": "90s"` in the
   request body left `ollama ps`'s `UNTIL` at the ~5-minute default
   afterward — silently ignored, the same failure mode already documented
   for `num_ctx` on this endpoint
   (`scripts/ollama_context_window_results.md`). A per-request fix on this
   endpoint is not available; server-side default (`OLLAMA_KEEP_ALIVE`,
   container-level) is the only lever, same pattern as the `num_ctx` fix.
2. **Does a fixed warm-up call, applied after a forced-cold state, reliably
   stabilize the following real call?** Yes, but not by reproducing the
   same hash as an unrelated warm history — "warm" is path-dependent on
   what specifically warmed the model, not one universal state. What
   matters for reproducibility is a *consistent procedure*, which this
   does provide: 4 independent forced-cold cycles (unload via `keep_alive=0`
   on the native endpoint, confirmed empty via `ollama ps`, then one
   throwaway `think=True` warm-up call, then the real positioning call)
   produced the **same** hash (`fe47e16836476287`) all 4 times — distinct
   from, but just as stable as, the same-prompt-repeated warm reference
   above.

## Consequence for the design (this section)

- `_warm_up_llm_client` (`run_polity_simulation.py`) issues one throwaway
  call through each endpoint shape (`think=True` and `think=False` are
  genuinely different Ollama request paths — see `llm_client.py`'s own
  module docstring) inside `_llm_client_scope`, before any real decision
  runs, on a real owned client only (never on an injected test client).
  Best-effort: any failure is logged and swallowed, never allowed to abort
  a run. This closes the start-of-run cold-start case, confirmed above.
- **Mid-run cold start — closed separately, by a container-level env var,
  not by `_warm_up_llm_client`.** A real run's own gaps between calls (a
  quiet tick, unusual latency) could in principle exceed Ollama's idle
  `keep_alive` timeout (~5 min default) at any point after the start-of-run
  warm-up, and since per-request `keep_alive` is confirmed silently ignored
  on the endpoint that matters (above), no application-side fix reaches
  this case. `ollama-polity` was recreated (2026-08-18) with
  `OLLAMA_KEEP_ALIVE=60m` added to its existing env vars (image, port,
  named volume, GPU device request, `OLLAMA_FLASH_ATTENTION=false`, and
  `OLLAMA_CONTEXT_LENGTH=16384` from the `num_ctx` fix all preserved
  unchanged — same recreate procedure as that fix). `60m` chosen over `-1`
  (never unload) deliberately: comfortably covers any realistic inter-call
  gap in a real run (15-90s in normal operation) while still releasing the
  ~8.4GB of VRAM after a genuine pause (end of run, an interrupted dev
  session) rather than pinning it indefinitely against a GPU that may run
  other workloads later. Verified directly: `docker exec ollama-polity
  ollama ps` showed `CONTEXT 16384` and `UNTIL 59 minutes from now` after a
  real request — both fixes active simultaneously, model weights confirmed
  intact post-recreation (`ollama list`, all three pulled models present).

  **This is complementary to the warm-up call, not redundant with it — the
  two protect different risk windows.** `_warm_up_llm_client` protects
  exactly one moment: the very first LLM call of a run, when the container
  (or the model within it) may be genuinely cold. `OLLAMA_KEEP_ALIVE=60m`
  protects every moment *after* that: it prevents the model from ever
  going cold again mid-run purely from an idle gap, which the warm-up call
  — a one-shot action taken once at start — cannot do anything about on
  its own. Neither one covers the other's window: a long `keep_alive`
  alone does nothing for a container that was *just* started or recreated
  (the model still has to load and take its one non-deterministic pass for
  the first time); a warm-up call alone does nothing to stop a real idle
  timeout from reintroducing the exact same problem an hour into an
  8-hour acceptance run.
- Every downstream failure this project has chased under a "budget
  shortfall" framing (`_POSITIONING_THINK_TOKEN_ALLOWANCE`,
  `_VOTE_THINK_TOKEN_ALLOWANCE`) may have been partly measuring this
  cold-start effect rather than (or in addition to) genuine content-driven
  token-budget insufficiency — a longer, non-terminating cold-start
  generation would present with the identical `finish_reason='length'`
  signature. Those allowance increases are not wrong (a real generation
  running long is still worth budgeting for), but the warm-up fix should
  be evaluated on its own before recalibrating any allowance further.

## A third mechanism, found live: cross-request prompt-cache reuse (2026-08-18)

With both fixes above in place, a fresh dump attempt of the v6b acceptance
config still failed — `decide_campaign_positioning` hit
`finish_reason='length'` 3/3 times in a row on the same prompt shape
already fixed once (task tokens=3989, decoding to 9775/9836, right at the
already-raised ceiling), exhausting `max_batch_replays`. The model was
confirmed warm throughout (`ollama ps`), so this is not the cold-start case
above. Docker logs showed the failing attempts preceded by
`srv load: - looking for better prompt, base f_keep = 0.290, sim = 1.000` —
a low-confidence partial match against Ollama's cross-request prompt cache
(a pool of recently-run, *unrelated* prompts, logged elsewhere as
`cache state: 11 prompts`). Every subsequent clean/fast rep of the exact
same prompt showed a high `f_keep` (0.7-1.0). Replaying the same known
prompt immediately after: rep 1 reproduced the failure, reps 2-8 all
converged to one stable, fast, clean output — `vote_chunk0` was 8/8 stable
throughout. This raised the hypothesis that a low-quality cache match
corrupts the generation into a long, non-terminating trajectory.

**Two follow-ups, before spending more GPU cycles chasing this:**

1. **Source-checked, not speculated**: does Ollama expose any per-request
   way to control prompt-cache reuse? No. `api/types.go`'s `Options`
   struct has no `cache_prompt`/`no_cache`/`cache_reuse`-shaped field
   anywhere. More decisively, `llm/llama_server.go` — Ollama's own internal
   call to the underlying llama.cpp server — sets `CachePrompt: true`
   (completion) and `"cache_prompt": true` (chat) **hardcoded**, with no
   configuration path from the public API. There is no flag to test or
   use; the mechanism is unconditionally on for every request, by design,
   with no override available short of bypassing Ollama's own wrapper
   entirely.
2. **Causality test, not just correlation, at near-zero GPU cost**: since
   `cache_prompt` can't be disabled, tested instead whether a deliberately
   *low* `f_keep` alone is sufficient to corrupt a generation, using cheap
   `think=False`, `max_tokens=50` calls (3 independent trials, each priming
   the cache with a distinct real long prompt, then immediately sending a
   never-before-seen short call: one sharing the prime's exact system-
   prompt text as a genuine prefix — mirroring production's real shape,
   where successive calls share large common system-prompt boilerplate —
   and one an unrelated control). **Result: all 6 trials (3 shared-prefix,
   3 control) finished cleanly at `done_reason='stop'` in 1.3-1.7s, with no
   distinguishable difference between the shared-prefix and control arms.**
   A low `f_keep` alone does **not** reproduce the failure on a cheap,
   short, `think=False` call. The trigger requires an interaction with long
   `think=True` reasoning generation — `f_keep` is a correlated symptom
   (both track "how novel is this exact token sequence"), not, on its own,
   the causal mechanism. The precise condition under which a long-reasoning
   generation fails to terminate naturally remains unisolated after this
   round; further narrowing would need controlled think=True trials, which
   are the expensive kind this test was designed to avoid pending a
   decision on whether that investment is worth it.

**Pragmatic mitigation, applied now, documented explicitly as mitigation,
not a fix**: the next relaunch uses `--max-batch-replays 5` (6 total
attempts per batch) rather than the `2` used in the run that failed.
Reasoning: the worst streak actually observed in production was 3
consecutive failures on one chunk; the settling behavior observed above
(a bad attempt is very often followed immediately by a stable, clean one)
suggests recovery typically happens within 1-2 extra tries once triggered
at all. `5` extra replays is roughly double the worst observed streak —
deliberately generous margin, not a guess at the minimum, and still
strictly bounded per `LlmResponseError`'s own design philosophy (a
malformed/misaligned response is never silently retried forever; every
replay is logged to `replays.log`, never journaled). This absorbs the
known risk while the root mechanism stays open — it does not claim the
problem is resolved.

**Open, unresolved question this round surfaces rather than answers**:
this is the third distinct Ollama/GPU-level reliability issue found in one
investigation (context-shift from a silently-dropped `num_ctx`, cold-start
non-determinism, and now this cache-interaction effect) — each traced to a
different mechanism, two of them (context-shift, cache reuse) specific to
behavior inside Ollama's own wrapper layer around llama.cpp, not the model
or GPU themselves. Whether Ollama, as currently configured, remains the
right serving layer for this specific workload (`think=True`, long
reasoning, prompts that are never exactly repeated within a run) — versus
a native `llama-server` (which exposes `cache_prompt` as a genuine,
documented per-request option) or the vLLM switch already scoped in this
project's own roadmap (§15bis.6) — is a real question this investigation
raises but does not settle, and is a call for the project owner to make,
not an engineering conclusion to smuggle into a bug-fix commit.

## Correction (2026-08-18, later same day): the "settling" claim above is demonstrated false

**The section above's own reasoning for `--max-batch-replays 5`
("a bad attempt is very often followed immediately by a stable, clean
one" / "recovery typically happens within 1-2 extra tries once triggered
at all") is empirically wrong, not just unconfirmed.** Left in place above,
struck through nowhere, exactly as written — this note corrects it rather
than silently rewriting the history of what was believed at the time.

**What actually happened**: the `--max-batch-replays 5` relaunch (real
acceptance run, `sortition-llm-8y`, 2026-08-18 ~20:25) failed 6/6 on
`campaign_positioning` — every one of the 5 replays hit the identical
`finish_reason='length'` error, never once recovering. Root-caused
directly, not inferred: `_complete_and_decode_with_replay` retries the
**byte-identical** request. A controlled, isolated replay of the exact
failing prompt (reconstructed from the failed run's own journal —
`test_4_vs_5_nominees.py`, then `test_prompt_variation_mitigation.py`,
both under this repo's scratchpad discipline) shows the real pattern:

```
call 1: prompt A (fresh)               -> OK
call 2: prompt A (identical repeat)    -> FAIL, finish_reason='length'
call 3: prompt A (identical repeat)    -> FAIL, finish_reason='length'
call 4: prompt B (fresh, different)    -> OK
call 5: prompt B (identical repeat)    -> FAIL, finish_reason='length'
call 6: prompt B (identical repeat)    -> FAIL, finish_reason='length'
```

Two independently-content-different prompts (4-nominee and 5-nominee
positioning batches) show the **identical** OK/FAIL/FAIL shape. The
variable is not prompt content, not nominee count, not the warm-up (a
dedicated causality test — restart the container, vary only whether a
truncated `think=True` warm-up call precedes the positioning call —
found the positioning call succeeds 3/3 regardless of warm-up state,
exonerating it). The variable is **repetition of byte-identical input
within one session**: a fresh prompt succeeds; the same prompt resubmitted
right after does not recover, it degenerates further and stays degenerate.

**Direct consequence for the shipped mitigation**: a bounded replay of the
*exact same request* is not a bet on independent-trial recovery — for
this specific failure class, it is a near-certain repeat of the same
degenerate cache-match condition. `--max-batch-replays N` does not
meaningfully improve the odds for this bug once triggered, regardless of
`N`. This does not retract the replay mechanism itself (it remains sound,
bounded, and logged — and it does help for genuinely stochastic
misalignment failures, a different, real failure class this project has
also observed) — it retracts the *specific justification* given above for
why it should work against this one.

**Tested as a live mitigation, same investigation — result: inconclusive,
and the reason why is itself informative.** `test_prompt_variation_mitigation.py`
restarted the Ollama container fresh, then ran 5 calls: prompt A (fresh),
prompt A (identical repeat, meant as the control reproducing the bug),
prompt A + a trivial inert marker, the same marker repeated, then a fresh
second marker. **All 5 succeeded, including the identical-repeat control**
— so the test never reproduced the failure it was meant to test a fix
against, and nothing can be concluded about whether the marker helped.

This failure to reproduce, on a freshly restarted container with only 5
calls total, contrasts with the run above that DID reproduce OK/FAIL/FAIL
twice in a row — which ran immediately after ~9 other calls on the same
still-warm container (the warm-up causality test's own 3 arms). This
suggests, as an untested hypothesis and nothing more, that the trigger
may depend on **how many distinct prompts are already sitting in
llama.cpp's own prompt-cache pool** (more entries -> higher chance of a
partial-match collision against one of them) rather than purely on
"is this call byte-identical to the immediately preceding one." A clean
test of the trivial-variation mitigation needs a reliable way to first
put the server into the degenerate state, then test whether variation
recovers it — which this attempt did not achieve. Not yet re-attempted;
per the project owner's own standing instruction, no further acceptance
relaunch happens until either this mitigation is actually confirmed
working (which it isn't yet) or the llama-server spike is conclusive.

**Spike outcome and the decision it fed (2026-08-19)**: the timeboxed
`llama-server` spike ran (3h budget, concluded in 14 min) and came back
**inconclusive on its own central question** — it never reproduced this
bug at all, under two separate loaded-cache protocols (4 prompts light,
then 10 prompts heavy with substantial per-prompt generation), using the
exact same GGUF weights copied out of Ollama's own blob store and the
exact real failing prompt rebuilt from the failed run's own journal.
6/6 identical submissions succeeded cleanly on `llama-server` where the
same prompt reproducibly fails on Ollama. Because the bug never
manifested, `cache_prompt: false` — the whole reason to look at
`llama-server` — was never actually tested as a fix. What the spike does
weakly suggest, without proving: the failure may be specific to Ollama's
own orchestration layer around llama.cpp (its own prompt-cache pool
management, batching internals) rather than a property of llama.cpp or
Qwen3 generically — consistent with the fact that two of the three bugs
found in this whole investigation were already traced to that same
wrapper layer. **Decision: stay on Ollama with the shipped mitigations,
do not switch serving layer** — recorded, with the full reasoning and the
alternatives rejected, in `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md`.
The spike's own protocol, logs and script live on branch
`spike/llama-server-cache-prompt` (`fast_api_voter/scripts/llama_server_spike/`),
deliberately not merged into the main line.

**This document remains the full source of truth for the problem itself;
the ADR above records only the architecture decision that followed from
it.** The operational gap this section leaves open, stated plainly so the
next person does not rediscover it the expensive way: **there is
currently no mitigation that protects against this specific failure
mode.** A bounded `--max-batch-replays` resubmits byte-identical bytes,
which is precisely the condition under which the degenerate pattern was
observed; the trivial-variation idea is untested; and the serving-layer
switch that would have provided a real per-request lever is not being
taken. Any further acceptance relaunch has to say what it is doing about
that, rather than assume a larger replay count covers it.

## Mitigation nonce — validation du banc, puis test de stationnarité (2026-08-19)

**Étape 1 — fiabiliser la reproduction avant de tester quoi que ce soit
contre elle.** La recette historique reconstituée exactement (redémarrage
à froid du conteneur, un seul appel d'amorçage à contenu distinct — le
prompt à 5 nominés — puis le prompt réel à 4 nominés soumis 3 fois de
suite : frais, identique, identique) a été rejouée 3 fois indépendantes.
**Résultat : `[OK, FAIL, FAIL]` reproduit 3/3, avec des temps d'échec
quasi identiques (97-104s) à chaque essai.** La recette est fiable — le
banc n'était pas le problème.

**Étape 2 — tester le nonce contre ce banc validé.** Chaque resoumission
(rangs 2 et 3) reçoit un marqueur JSON inerte différent au lieu d'octets
identiques. 3 essais courts : `[OK,OK,FAIL]`, `[OK,FAIL,FAIL]`,
`[OK,OK,OK]` — 3 échecs sur 6 resoumissions (~50%). Un effet réel (mieux
que 6/6 sans variation) mais pas fiable sur cet échantillon.

**Étape 3 — test de stationnarité, séquences longues avec rang
enregistré**, pour trancher si ce taux est stable par tentative
(l'indépendance tiendrait, l'extrapolation `p^N` serait fiable) ou
dérive avec la position (confirmerait l'hypothèse "volume de cache
accumulé"). 2 essais de 8 resoumissions consécutives chacun, même banc,
un nonce frais à chaque rang :

| Rang | Essai 1 | Essai 2 |
|---|---|---|
| 0 (frais, sans nonce) | OK | OK |
| 1 | OK | OK |
| 2 | OK | OK |
| 3 | **FAIL** | OK |
| 4 | OK | OK |
| 5 | OK | OK |
| 6 | **FAIL** | OK |
| 7 | **FAIL** | OK |
| 8 | OK | OK |
| **Total (rangs 1-8)** | 5/8 | 8/8 |

**Regroupé sur les deux essais : 13/16 resoumissions avec nonce réussies
(~81%)** — nettement au-dessus de l'estimation à petit échantillon de
l'étape 2 (~50%), mais ce chiffre agrégé masque un problème plus
important que le taux lui-même.

**Interprétation, sans arrondir vers l'hypothèse la plus pratique à
déployer** :
- **Pas de tendance monotone par rang** dans l'essai 1 : les échecs
  (rangs 3, 6, 7) ne sont pas concentrés en fin de séquence — les rangs 4,
  5 et 8 (dont le plus élevé) réussissent. Ça ne confirme PAS l'hypothèse
  "le taux augmente avec la position/le volume de cache accumulé" de
  façon simple et monotone.
- **Mais la variance entre les deux essais est énorme et n'est pas
  expliquée par le rang** : protocole strictement identique (même
  redémarrage à froid, même amorce, même prompt), 3 échecs sur 8 dans un
  essai contre 0 sur 9 dans l'autre. Si l'hypothèse d'indépendance/taux
  fixe par tentative était correcte, une telle divergence entre deux
  essais de taille comparable serait très improbable — les échecs de
  l'essai 1 se comportent comme groupés dans une session "mauvaise"
  plutôt que dispersés comme des tirages indépendants d'un taux commun.
- **Conclusion : ni l'hypothèse de stationnarité/indépendance, ni
  l'hypothèse d'un effet de rang monotone, ne sont proprement confirmées
  par cet échantillon.** Un troisième facteur, non identifié et non
  capturé par le rang seul, semble déterminer si une session entière
  tend à échouer ou non. Deux essais restent un échantillon fin pour
  isoler ce facteur.

**Décision : ne pas déployer la combinaison nonce + `--max-batch-replays`
sur la base d'un calcul de probabilité (`p^N`).** Ce calcul suppose des
tentatives indépendantes ; les données le contredisent. Le risque réel
n'est pas mesuré par ce chiffre agrégé — une session "comme l'essai 1"
pourrait épuiser un budget de tentatives borné même à un taux moyen de
81%, si les échecs se groupent au mauvais moment plutôt que de se
répartir uniformément.

Pas encore identifié : ce qui distingue une session "essai 1" d'une
session "essai 2" au-delà du rang. Candidats non testés : l'horloge
réelle/le calendrier des requêtes (pas juste leur ordre), un état GPU
résiduel non capturé par un simple redémarrage de conteneur, une
variance véritablement stochastique du kernel CUDA sous-jacent
(cohérent avec le fait que le mode déterministe upstream de llama.cpp,
`GGML_DETERMINISTIC`, existe justement pour fermer cette classe de
non-déterminisme — voir `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md`
et `docs/adr/BACKLOG-alternatives.md` pour son statut, non mergé en
amont et non exposé par Ollama).

## Décision d'architecture qui en découle

Voir `docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md` : rester
sur Ollama avec les mitigations déjà en place, ne pas basculer vers
`llama-server` ni accélérer vLLM — le spike n'a jamais reproduit le bug 4
(donc n'a jamais pu tester `cache_prompt=false` comme correctif), et la
piste `GGML_DETERMINISTIC` n'est pas disponible aujourd'hui (PR amont non
mergée). L'état opérationnel reste donc inchangé : **aucune mitigation
validée ne protège actuellement ce mode d'échec de façon fiable.**

## Coût réel du relaunch qui a échoué, et recherche du facteur de session (2026-08-19)

**Coût réel confirmé — l'échec est bon marché pour CE bug précis.** Le
journal du relaunch à `--max-batch-replays 5` (`sortition-llm-8y`) s'arrête
au **tick 0** : 112 événements, tous antérieurs à la première élection,
zéro `elected`/`legislative_result`. Le run est mort sur le tout premier
appel LLM de la simulation entière. Temps réel écoulé entre le début du
run et la dernière tentative de replay : **9 minutes 11 secondes**
(20:25:43 → 20:34:54, horodatages fichiers). Ce n'est pas juste "tôt dans
le run" — c'est le point le plus précoce possible. Pour ce mode d'échec
spécifique, un relaunch coûte réellement quelques minutes, pas des
heures.

**Recherche du facteur de session (budget fixé à 1h, ~20 min utilisées) —
signal partiel trouvé, pas une explication complète.** Chronologie des
deux essais du test de stationnarité reconstituée précisément (horodatages
des fichiers de log + propre journal de redémarrage d'Ollama, `Listening
on`) : **Essai 1 (3 échecs, rangs 3/6/7) : 11:45:29-11:55:29 UTC. Essai 2
(0 échec) : 11:55:29-12:00:12 UTC**, immédiatement à la suite, même
protocole de redémarrage à froid pour les deux.

Vérifié dans l'ordre demandé :
1. **État du conteneur avant chaque essai** — identique pour les deux
   (redémarrage à froid systématique). Écarté comme facteur différenciant.
2. **Activité GPU concurrente** — deux événements réels et vérifiés dans
   le journal système Windows, aucun ne fournissant une explication
   complète :
   - La session Windows était **verrouillée** pendant la quasi-totalité
     des deux essais (le poste était sans surveillance depuis la longue
     pause précédente) ; un événement `SessionUnlock` (Kernel-Power,
     ID 566) survient à 11:59:54 UTC, dans les 18 dernières secondes de
     l'essai 2 — ne favorise clairement ni l'un ni l'autre essai, et
     n'explique pas pourquoi l'essai 1 (verrouillé sur toute sa durée)
     a échoué davantage que l'essai 2 (verrouillé presque toute sa
     durée aussi).
   - Un scan Windows Defender (événements 1000/1001, 11:49:25-11:49:49
     UTC) chevauche précisément la fenêtre d'appel du **rang 3**,
     premier échec de l'essai 1. **Corrélation temporelle réelle pour 1
     échec sur 3** — mais aucun événement Defender/mise à jour Windows
     ne coïncide avec les rangs 6 ou 7 (les deux autres échecs de
     l'essai 1), et aucun scan n'a eu lieu pendant la fenêtre propre de
     l'essai 2 non plus (donc rien à comparer côté essai 2). Recherche
     Docker Desktop/WSL2 (compaction mémoire, `vmmem`) : aucun journal
     couvrant cette fenêtre horaire trouvé.
3. **Ordre chronologique** — reconstitué précisément (voir ci-dessus) ;
   aucune anomalie identifiée au-delà des deux points précédents.

**Conclusion, sans arrondir vers l'hypothèse la plus pratique** : un
signal réel a été trouvé (le scan Defender coïncide avec un échec précis),
mais il ne couvre qu'un tiers des échecs observés et ne différencie pas
les deux essais dans leur ensemble (0 vs 3 échecs sur des durées et des
conditions par ailleurs quasi identiques). **La cause de la variance
inter-session reste non identifiée** au sens propre du terme — pas
"rien trouvé du tout", mais rien d'assez complet pour être qualifié de
facteur de confusion contrôlable avec confiance à ce stade. Piste de
contrôle réelle pour un futur test, si cette question est reprise :
désactiver l'analyse en temps réel de l'antivirus (ou au minimum
journaliser les événements système en continu pendant le test, plutôt que
de les reconstituer après coup) pour isoler ou écarter cette piste
proprement.

## Risque résiduel accepté consciemment — relaunch du 2026-08-19

**Décision : relancer l'acceptance run sans mitigation validée contre le
bug 4, en acceptant le risque résiduel.** Consignée ici explicitement pour
qu'une relecture future n'ait pas à reconstruire le raisonnement :

- **Aucune mitigation confirmée n'existe** pour ce mode d'échec au moment
  du relaunch. `--max-batch-replays` (byte-identique) ne protège pas
  contre une resoumission qui rejoue la condition dégénérée (section
  "Correction" ci-dessus). Le nonce par tentative a un effet réel mais non
  fiable (81% agrégé sur 16 resoumissions, non stationnaire entre essais —
  section "test de stationnarité"), et n'a **pas** été câblé dans le code
  de production : le déployer sans l'avoir validé de façon fiable aurait
  répété l'erreur méthodologique déjà commise une fois avec
  `--max-batch-replays 5` lui-même.
- **Le facteur de session reste non identifié** — budget d'investigation
  d'1h dépensé (section précédente), un signal réel trouvé (scan antivirus
  coïncidant avec 1 échec sur 3) mais couvrant au mieux un tiers du
  pattern observé. Le rendement marginal de continuer à creuser est jugé
  décroissant à ce stade.
- **Le calcul coût/bénéfice justifie le relaunch malgré tout** : l'échec
  précédent (`sortition-llm-8y`, `--max-batch-replays 5`) est mort au
  **tick 0** en **9 minutes 11 secondes** — le point le plus précoce
  possible dans un run de 33 ticks / ~4h prévues. Un nouvel échec dans les
  mêmes conditions coûterait quelques minutes, pas des heures.
- **Ce calcul repose entièrement sur l'hypothèse que l'échec, s'il se
  reproduit, reste précoce.** C'est la condition qui rend le risque
  accepté raisonnable — pas une garantie que le bug est résolu ou
  compris. Si un futur run échoue significativement plus tard dans la
  séquence (après plusieurs ticks ou plusieurs heures, pas au tick 0),
  cette hypothèse serait invalidée et le calcul de risque devrait être
  refait en profondeur, pas juste noté comme un deuxième échec de plus.
- **Action gratuite prise avant ce relaunch** : l'antivirus (protection en
  temps réel Windows Defender) a été désactivé pour la durée de ce run
  spécifique, afin d'éliminer d'office le seul facteur de bruit confirmé
  (même partiel) identifié dans la section précédente — pas parce qu'il
  est jugé être LA cause, mais parce que le désactiver ne coûte rien et
  retire une hypothèse candidate de la liste si le run échoue à nouveau
  avec l'antivirus hors-jeu.

## Bug 4 résolu (partiellement) — mécanisme composite identifié, mitigation déployée (2026-08-19/20)

Le relaunch accepté ci-dessus s'est effectivement interrompu au tick 0
(`sortition-llm-8y`, exclusion Windows Defender configurée entre-temps sur
les chemins Docker + le process `ollama.exe`, confirmée via les logs
Microsoft-Windows-Windows Defender/Operational faute de droits admin pour
lire la config directement). Reste mort tôt, cohérent avec le risque
accepté. Ce qui suit documente l'investigation qui a suivi, harnais de
test en main (`fast_api_voter/scripts/llm_test_harness/`), et qui a
finalement produit une mitigation testée et déployée — la piste
"resoumission d'octets identiques" qui a occupé la majeure partie de ce
document s'avère n'avoir jamais été la bonne variable.

### Le taux de base (hors resoumission) est déjà significatif

Avant de tester le nonce contre le critère pré-enregistré (n=97 calculé
par le harnais pour un IC à 95%), un contrôle bon marché : 10 appels
**frais et distincts** (jamais resoumis), un seul redémarrage à froid.
**5/10 échecs (50%, IC de Wilson [24%, 76%])** — largement au-dessus du
seuil de 20-30% qui aurait permis de continuer le protocole nonce tel que
conçu. Ce résultat, à lui seul, invalide la prémisse "seule la
resoumission dégrade" : un appel jamais resoumis a déjà un taux d'échec
substantiel.

### Le pattern est déterministe, pas stochastique — la piste cache-volume confirmée

Expérience de suivi : 4 sessions indépendantes (redémarrage à froid à
chaque fois), 15 appels à contenu **strictement identique** (mêmes
groupes de nominés, même ordre) à chaque session. **Le pattern exact
d'échecs (rangs 1, 4, 8, 10, 11 sur 15) se reproduit à l'identique sur
les 4 sessions**, sans exception. Ceci contredit directement la
"variance énorme entre essais" du test de stationnarité du nonce
(section précédente) — ce test-là variait le contenu (un nonce distinct
à chaque rang), celui-ci ne varie rien : le déterminisme apparaît
seulement quand rien ne varie, ce qui suggère que le nonce lui-même
introduisait le bruit qu'il était censé neutraliser, plutôt que
d'observer une variance intrinsèque du système.

Croisement (gratuit, aucun appel GPU supplémentaire) entre les timestamps
des essais et les lignes `cache state: N prompts` des logs Docker du
conteneur `ollama-polity`, avec un bornage correct par redémarrage
(un bug du script d'analyse initial incluait par erreur des entrées
résiduelles d'une session précédente — les logs Docker persistent au
travers d'un `docker restart`, corrigé en calculant le plancher temporel
depuis `container_uptime_seconds`) :

| Niveau de cache au démarrage de l'appel | Résultat |
|---|---|
| 0, 2, 4, 5, 6 | 0 échec sur 24 |
| 7 | 8 échecs sur 20 (40%) |
| 8 (capacité max observée) | 4 échecs sur 8 (50%) |

Critère pré-enregistré (ratio taux d'échec cache≥8 / taux d'échec
cache<8 ≥ 2x) : **satisfait, ratio = 2.00 exactement.** 80% de tous les
échecs par troncature se concentrent aux deux derniers niveaux avant/à
saturation. Capacité mesurée : ~8 prompts sur ce conteneur, bornée par
la limite mémoire du pool de cache llama.cpp (8192 MiB, visible dans le
même log). Réserve : le design confond contenu, rang et niveau de cache
(séquence identique à chaque session) — corrélation nette, pas une
preuve causale isolée du niveau de cache en tant que tel.

### Un second bug distinct, identifié comme déjà connu et déjà corrigé

Le tout premier appel de chaque session échouait systématiquement (5/5
sur les expériences précédentes) selon un mode d'échec jamais documenté
jusque-là : `cid` renvoyés strictement égaux aux valeurs de `motif`
(`CampaignMotif` 601-604) au lieu des vrais `citizen_id` attendus — une
confusion de champs par le modèle, syntaxiquement valide, pas une
troncature. Relecture de ce document : ce phénomène correspond très
probablement à la section "Cold start vs. warm" ci-dessus — le tout
premier passage d'inférence après un chargement de modèle à froid
emprunte un chemin d'exécution GPU différent. `_warm_up_llm_client`
(`run_polity_simulation.py`) existe déjà en production pour absorber cet
effet, mais **les scripts de diagnostic de cette investigation ne
l'appelaient jamais**, contrairement au pipeline réel. Test direct (6
redémarrages à froid, `_warm_up_llm_client` appelé cette fois) :
corruption cid=motif disparue, **0/6**. Confirmé sur données réelles :
dans `sortition-llm-8y`, `candidacy_considered` et
`party_nomination_choice` utilisent tous deux `think=False` (vérifié
dans le code), donc `campaign_positioning` était bien le tout premier
appel `think=True` de ce run, juste après le warm-up de démarrage — et
`replays.log` montre qu'il a échoué à sa première tentative avant de
réussir au retry, exactement le pattern trouvé sur le banc synthétique.

### La synthèse qui unifie les deux pistes

Avec le warm-up appliqué, l'appel réel qui suit immédiatement échouait
maintenant 6/6, systématiquement par troncature — déplacé, pas éliminé.
Hypothèse "le warm-up de production (32 tokens, garanti de tronquer sous
`think=True`) laisse une entrée corrompue" testée et **réfutée** : un
warm-up à budget généreux (1500 tokens, se termine proprement 6/6)
produit le même 6/6 d'échecs sur l'appel suivant. En revanche, un
warm-up dont le **prompt a une taille/forme réaliste** (un vrai prompt
`campaign_positioning` complet, peu importe qu'il réussisse ou échoue
lui-même) élimine la contamination : **6/6 de réussite** sur l'appel qui
suit.

Ces deux pistes — volume de cache et forme du prompt précédent — ne sont
probablement pas deux mécanismes séparés mais une seule et même cause vue
sous deux angles : une correspondance partielle de faible confiance
contre une entrée de cache dissemblable en taille/forme (le mécanisme
"cross-request prompt-cache reuse" déjà documenté plus haut dans ce
fichier, jamais confirmé jusqu'ici). Plus le cache contient d'entrées,
plus la probabilité qu'un nouveau prompt matche par erreur contre une
entrée petite/dissemblable augmente mécaniquement — pas besoin de deux
explications distinctes pour les deux résultats.

### Mitigation déployée : recyclage du modèle par nombre d'appels

`llm.recycle_after_n_calls` (`polity_config.yaml`, `LlmConfig`,
`OllamaJsonClient`) — nouveau champ, `null` par défaut (désactivé). Force
un unload/reload du modèle Ollama (`keep_alive: 0` sur l'endpoint natif,
**vérifié en direct** : réinitialise bien `cache state` à 0, même effet
qu'un redémarrage complet du conteneur, sans son coût — pas de perte de
connexion TCP, pas de relance du process conteneur) tous les N appels
`complete_json`, de façon préemptive (avant l'appel qui ferait entrer le
pool dans sa zone de risque mesurée, pas après).

**Un bug réel trouvé en testant le mécanisme en conditions réelles, pas
seulement en mock** : la première implémentation réutilisait le prompt
trivial `"{}"` du warm-up de production pour le re-warm après recyclage —
exactement la forme dont la section précédente vient de prouver qu'elle
casse l'appel suivant. Vérifié en direct (seuil=2, 5 appels) : **2/5
seulement**, pire que sans mitigation. Corrigé en remplaçant ce prompt
trivial par un prompt rempli de contenu inerte, dimensionné pour
approcher la taille d'un vrai prompt de production (~6000 caractères) —
revérifié en direct sur le même protocole difficile : **4/5**, nette
amélioration (le seul échec restant suit directement le tout premier
recyclage, lui-même consécutif au warm-up de démarrage qui utilise
toujours le stub trivial de `_warm_up_llm_client`, volontairement hors
périmètre de cette modification).

**Honnêteté sur ce qui reste non résolu** :
- Le seuil mesuré (~8 prompts, capacité de risque à partir de 7) l'est
  pour UN prompt shape précis (`campaign_positioning`, `think=True`,
  grand budget de tokens) sur LA mémoire de CE conteneur — pas prouvé
  général à tout mélange de types de décision. `recycle_after_n_calls`
  reste `null` par défaut pour cette raison ; une valeur de 5-6 reste
  prudente sous le seuil mesuré si activée.
- `_warm_up_llm_client` (le warm-up de tout début de run) utilise encore
  le stub trivial `"{}"` — non corrigé dans ce changement, périmètre
  volontairement restreint au recyclage. C'est la piste la plus évidente
  pour une prochaine amélioration si le taux d'échec au tout début d'un
  run reste un problème.
- La vérification live du recyclage corrigé porte sur n=5 appels, un seul
  passage — une amélioration mesurée et crédible (2/5 → 4/5 sur le même
  protocole difficile), pas une garantie statistique à ce niveau
  d'échantillon.
- Le mécanisme causal exact (correspondance partielle contre une entrée
  de cache dissemblable) reste une hypothèse bien étayée, pas une preuve
  formelle — Ollama n'expose aucun moyen de désactiver ou d'inspecter
  directement ce comportement (confirmé plus haut, section "cross-request
  prompt-cache reuse").

**Décision : bug 4 est considéré clos pour ce projet.** Pas "résolu" au
sens d'une preuve causale complète, mais suffisamment compris et
mitigé : le mécanisme composite est identifié, une mitigation testée et
mesurée existe et est disponible (`recycle_after_n_calls`), et le
rendement marginal d'investiguer davantage est jugé décroissant face au
travail de fond du projet (retour à v6, contagion sociale). Voir
`docs/adr/ADR-001-serving-layer-ollama-vs-llama-server.md` pour la
clôture formelle de la décision d'architecture correspondante.

## Un septième mode de défaillance, distinct de bug 4 — le conteneur meurt sans laisser de trace (2026-08-22)

Le second run d'acceptance v6b (`recall_floor=0.0`, cf. le plan de session) a
crashé au tick 32/32 — la toute dernière élection présidentielle du run,
après ~4h16 d'exécution — avec une `LlmTransportError` (`WinError 10054`,
connexion fermée par l'hôte distant), pas une erreur de schéma/décodage. Ce
mode est **distinct des six déjà documentés dans ce fichier** (B2 batching,
l'écart cold-start, la réutilisation cross-request du prompt-cache, bug 4
lui-même, l'incohérence déterministe `blank`/`ranking` de `cast_votes`
consignée dans `cache_recycle_chunk_size_tension_findings.md`, et le
chunk_size de `chamber_deliberation` v6b Lot 3) : ici, le **conteneur
`ollama-polity` lui-même est mort** (`docker inspect` : `exitCode=255`,
`OOMKilled=false`), pas une réponse du modèle qui échoue une validation.

**Preuve directement lue dans les logs du conteneur** (préservés à travers
le restart — même `container Id`, seul le process a été redémarré, pas
recréé) : deux rechargements successifs de `llama-server` à 70s d'intervalle
(22:20:03 puis 22:21:13 UTC — vraisemblablement `recycle_after_n_calls`
faisant son travail normal pendant les batches denses de la dernière
élection), puis **plus aucune ligne de log pendant 68 secondes**, jusqu'à la
mort du process à 22:21:54 (horodatage `docker inspect` lui-même) — ni panic,
ni erreur, ni message OOM. GPU sain au moment du diagnostic (1.5/16 GiB
utilisés, 46°C), 385 GiB de disque libre.

**Cause confirmée, pas seulement plausible** : l'utilisateur a exécuté
`wsl --shutdown` dans l'autre worktree (`Vote-App`) pendant que ce run
tournait. `wsl --list --verbose` montre la distro `docker-desktop` (celle
qui héberge TOUS les conteneurs Docker Desktop de la machine, quel que soit
le worktree/dépôt depuis lequel `docker` est invoqué) à seulement 10 minutes
d'uptime au moment du diagnostic — cohérent avec un redémarrage de la VM
vers 22:22, exactement la fenêtre du crash puis de mon propre `docker start`
de récupération. `wsl --shutdown` coupe la VM légère sous-jacente
brutalement, depuis l'extérieur de Docker — ce qui explique exactement le
silence total dans les logs (le process n'a pas eu l'occasion d'écrire quoi
que ce soit avant de mourir, contrairement à un OOM-kill du noyau qui
laisserait au moins une trace côté hôte) et le `WinError 10054` côté client
(la connexion TCP a été coupée sous ses pieds, pas refusée).

**Conséquence pour l'hypothèse "instabilité liée à la durée d'uptime"** :
elle est **révisée à la baisse, pas retenue comme l'explication de cet
incident précis**. Les deux rechargements `llama-server` juste avant le
crash sont vraisemblablement une coïncidence de timing (le run traitait
justement les batches les plus denses de tout le run, la dernière
élection), pas un facteur causal — `wsl --shutdown` explique le crash
entièrement, indépendamment de la durée pendant laquelle le conteneur avait
tourné (26h ici, mais ç'aurait été identique à 2h). La mitigation de
redémarrage préventif toutes les 12h (`ollama_uptime_guard.py`, déployée le
même jour) reste déployée — elle répond à un risque réel et indépendamment
documenté (instabilité WSL2/Docker Desktop après une longue durée,
cf. recherche bornée ci-dessous) — mais **elle n'aurait pas empêché cet
incident précis**, puisque son déclencheur n'a rien à voir avec l'uptime du
conteneur.

**Recherche bornée (pas une investigation complète), pour situer le
contexte général sans lui faire porter la responsabilité de cet incident** :
- Plusieurs issues GitHub documentées et actives sur `docker/for-win` et
  `microsoft/WSL` décrivent une dégradation de la connectivité
  conteneur↔hôte après une durée d'exécution prolongée sous le backend
  WSL2 de Docker Desktop (ex. `docker/for-win#10745` : timeout après ~1h
  environ ; `docker/for-win#12105` : perte de connexion après un certain
  temps, résolue seulement par une réinitialisation de Docker Desktop ;
  `microsoft/WSL#13124` : crashs aléatoires de la VM WSL en usage prolongé
  avec Docker Desktop). Ces symptômes (perte de connexion réseau, VM WSL
  instable) sont dans la même famille que le `WinError 10054` observé ici,
  mais **aucune de ces issues ne correspond exactement** à ce cas précis
  (déclenchement confirmé par `wsl --shutdown`, pas une dégradation
  spontanée).
- Un pattern bien documenté côté Ollama (ex. `ollama/ollama#6682`, cité
  dans plusieurs sources secondaires) lie des crashs de conteneur à un
  parallélisme de requêtes non contraint (`OLLAMA_NUM_PARALLEL` par défaut)
  épuisant la VRAM sur des GPU grand public — **non applicable ici** :
  `OLLAMA_NUM_PARALLEL` est resté à sa valeur par défaut tout du long sans
  incident jusqu'à ce jour, et le GPU était sain (1.5/16 GiB) au diagnostic.
  Mentionné pour mémoire, pas retenu comme piste.

**Conclusion, honnête sur ce qui reste incertain** : la cause immédiate de
*cet* incident est confirmée (`wsl --shutdown` externe) — pas un mode de
défaillance à investiguer davantage pour lui-même. Ce qui reste ouvert,
plus large que cet incident : ce projet n'a pas de mécanisme de
checkpoint/reprise (rejeté explicitement lors de la planification v4 Lot 8,
pour ne pas réintroduire de non-déterminisme) — donc n'importe quelle
coupure externe de la VM WSL2/Docker Desktop, quelle qu'en soit la cause
future, coûte l'intégralité d'un run multi-heures en cours. C'est un risque
opérationnel du poste de travail, pas un bug du code applicatif de ce
projet — noté ici pour que la prochaine session qui voit un run planté sans
message d'erreur applicatif pense à vérifier `wsl --list --verbose` et
`docker inspect --format '{{.State}}'` avant de suspecter le modèle ou le
code.

Sources (recherche bornée, 2026-08-22) :
- [Docker Windows and WSL2 timeout · Issue #10745 · docker/for-win](https://github.com/docker/for-win/issues/10745)
- [Unable to connect to WSL2 from a docker container after some time · Issue #12105 · docker/for-win](https://github.com/docker/for-win/issues/12105)
- [WSL randomly crashes and won't restart easily when using it with Docker Desktop · Issue #13124 · microsoft/WSL](https://github.com/microsoft/WSL/issues/13124)
