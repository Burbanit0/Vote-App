# Réflexion — programme scientifique et programme LLM, comme un seul chantier

## Context

Two questions, asked together while the Phase 7 flagship run executes in the
background:

1. **La partie scientifique et théorique** — the theses this project has defined
   about how individuals behave with each other.
2. **Comment optimiser l'usage du LLM d'après les travaux de recherche** — long
   term, every available technique, not just the big obvious wins.

They turn out to be the same question, for a reason nobody has written down yet.
That finding is §1 below; everything after it is the program that follows from
it.

Two exhaustive inventories were built first (read-only, ~35 files each): the
behavioural theses embedded in the design doc + code, and every LLM technique
this project has already tried. Both are summarised inline where relevant.
Nothing here proposes re-treading ground already covered — the point of the
inventories was to avoid exactly that.

**Decisions taken before writing this**: all three theory angles are in scope
(audit / validity / extension); both topics run as one program with an explicit
dependency graph; the flagship run continues (its data stays useful, with the
`unverified` labelling Phase 1 already decided).

### Contrainte opérationnelle pendant l'exécution de Phase 7

**Rien de ce programme qui touche aux prompts ou au serveur ne peut démarrer
tant que le run flagship est en vol.** Two concrete hazards, both real:

- Changing any `build_*_user_prompt` (§5.B float precision, §5.E TOON) changes
  the bytes sent to the model. The run is checkpoint/resumable and *has already
  been resumed twice* this session — a resume after a prompt change would
  continue the same journal with a different prompt shape, and `config_hash`
  does **not** cover prompt-builder code, so the inconsistency would be silent.
- Restarting vLLM to change server flags (§3.B.6 speculative decoding, §3.B.7
  prefix-cache tuning) kills the in-flight run's connection.

What *is* safe while it runs: **§5.D** (read-only analysis of already-completed
journals) and documentation. That is where execution starts, and it is why the
ordering table's step 0 is gated below rather than started immediately.

---

## 1. The finding that binds the two topics

The project has 9 LLM decision types. Their measured reliability splits cleanly
— and the split runs exactly the wrong way for the science.

| Decision type | What it carries | Measured status |
|---|---|---|
| `pressure_action` (dt=10) | **Citizen chooses a lever against an officeholder** | **60,0 % agreement, bar is 80 %** — every remediation lever exhausted |
| `representative_response` (dt=6) | **Officeholder responds to citizen pressure** | **Collapse confirmed** (4/4 identical) |
| `coalition_decision` (dt=9) | **Party joins/refuses a coalition** | **Collapse confirmed** (6/6 identical) |
| `reaction_to_event` (dt=8, SCANDAL) | **Citizen reacts to a shared event** | **Collapse confirmed** (6/6 identical) |
| `chamber_deliberation` (dt=11) | Member adjusts own position | Non tranché |
| `campaign_positioning` (dt=5) | Nominee adjusts own platform | No collapse (separate 50-66 % failure defect) |
| `candidacy_considered` (dt=2) | Citizen evaluates own ambition | **No collapse** (5/5) |
| `party_nomination_choice` (dt=4) | Party compares its own aspirants | **No collapse** (4/5) |
| `vote_cast` (dt=1) | Citizen ranks candidates | **Reliable** — 23/24 at chunk=3, real ground truth |

**The four compromised types are precisely the four inter-individual ones.** The
three reliable ones are all self-referential or intra-group: *do I have enough
ambition*, *which of our own members is strongest*, *how far is each candidate
from me*.

The consequence is not abstract. §7bis.9's social-contagion thesis — the
project's most ambitious claim, the Granovetter threshold mechanism, the
"bandwagon moment" — is implemented as `neighbors_acting` lowering an awakening
threshold that gates **`pressure_action`**. The contagion channel's output stage
is the decision type sitting at 60 %. Same for the elected-vs-sortition
comparison: the elected side's behaviour comes from `representative_response`
(collapse confirmed), the sortition side from `chamber_deliberation` (non
tranché).

So: *"les comportements des individus entre eux"* is currently the least
instrumented part of the simulation, not because it wasn't built, but because
the LLM is measurably unreliable **exactly and only there**. That is why the two
topics are one program — LLM decision quality is not an engineering concern
sitting beside the science, it is the binding constraint *on* the science.

---

## 2. A refinement of the project's own collapse hypothesis

§3.6.0 currently records the hypothesis as: *act/response framing collapses,
self-evaluation-against-threshold does not*. The project itself flags one
genuine exception it could not absorb — `campaign_positioning` is act/response
by form and does **not** collapse — and downgraded the title from "4/4" to
"3/5 + 2 exceptions" rather than force it.

**Proposed refinement (hypothesis, not established): the discriminating axis is
not act-vs-evaluation, it is whether the decision commits an action that lands
on another agent.**

| Type | Lands on another agent? | Collapse? |
|---|---|---|
| `pressure_action` | Yes — acts against an officeholder | Yes (quality failure) |
| `representative_response` | Yes — responds to citizens | Yes |
| `coalition_decision` | Yes — binds with other parties | Yes |
| `reaction_to_event` | Yes — reacts to another's conduct | Yes |
| `campaign_positioning` | **No — adjusts own platform** | **No** |
| `chamber_deliberation` | **No — adjusts own position** | Non tranché (consistent) |
| `candidacy_considered` | No — own ambition | No |
| `party_nomination_choice` | No — comparative judgement, no act | No |

This absorbs all eight data points **including the exception that broke the
current formulation**, and it stops `campaign_positioning` being an anomaly.

### Why this matters beyond tidiness: a named mechanism, and a decisive test

The current hypothesis has no mechanism ("mécanisme réel non identifié", stated
repeatedly). The refined axis suggests one, and it comes from outside this
project's literature: **RLHF alignment training.** Instruct-tuned models are
optimised to avoid committing consequential actions on a person's behalf; asked
to *do something to someone*, they fall to a safe fixed attractor. Asked to
*compute a judgement*, no such pressure applies. The corroborating detail is
already in this project's own data and was never read this way: the
schema-embedded `a_reasoning` experiment found the reasoning **genuine and
content-sensitive** while the decision still collapsed — a reasoning-to-decision
translation failure, which is what an output-side alignment prior looks like,
not a comprehension failure. The cross-model check fits too: `mistral:7b`
collapsed to the *opposite* pole (always MOBILIZE) — a different attractor, same
attractor-shaped failure.

**Decisive, cheap test nobody has run: base vs instruct.** `Qwen3-8B-Base`
against the shipped instruct model, same prompts, same four collapsed types. If
the collapse is alignment-induced, the base model shows materially more
content-sensitivity. Format compliance will be worse — irrelevant, constrained
decoding (xgrammar, already shipped) handles format. This is one GPU afternoon
and it either identifies the mechanism the project has been chasing for weeks or
eliminates the most plausible remaining candidate.

---

## 3. Programme LLM

The inventory found **33 distinct avenues already explored**. Every one is
reactive: a bug fixed, a failure worked around, a constant recalibrated. There
is no proactive performance engineering anywhere, and **zero citations of LLM/ML
systems research** in a repo that cites political science meticulously. The
instinct behind the question is correct.

### 3.A — Décision: qualité (le goulot)

Ordered by expected value, all untried:

1. **Per-citizen deterministic sampling** — *the highest-value idea here.*
   Everything runs at `temperature=0`, i.e. greedy argmax. When prompt
   differences are small relative to the model's prior, greedy decoding gives
   *every citizen the same token* — content-blind collapse is, mechanically,
   what greedy decoding does to a weakly-discriminated distribution. The fix
   used everywhere in the silicon-sampling literature is temperature > 0 with
   multiple samples, which this project cannot afford and which breaks
   reproducibility. **But a per-citizen seed derived deterministically from
   `(run_seed, citizen_id, tick, decision_type)` at temperature > 0 gives
   variance across citizens while remaining exactly reproducible.** Same run,
   same seeds, same output — different citizens, different draws. This directly
   attacks the collapse without giving up the property the project has spent
   months defending. Tradeoff to state honestly: it adds noise to each
   *individual* decision while restoring *population* variance — for an ABM,
   population variance is the scientifically load-bearing quantity.
2. **Two-stage decomposition** — already named by the project for
   `pressure_action` (binary act/don't-act, then lever choice), never tested.
   The refined axis in §2 says it should generalise to all four
   lands-on-another-agent types. Research grounding: least-to-most and
   decomposed prompting.
3. **Grammar-level invariant enforcement** — `blank=1 ⟹ ranking=[]` (§3.6.1) is
   currently a Pydantic validator that *rejects after the fact*, and is the
   single most frequent `vote_cast` failure (~6,7 %, deterministic, and the
   reason `_VOTE_CAST_RETRY_SEED_BASE` had to be invented). Encoded into the
   xgrammar schema instead, the violation becomes **unreachable**. Kills a whole
   failure class rather than retrying it.
4. **Base vs instruct** — §2 above.
5. **DeepSeek-R1 distillations** — already on the backlog, flagged there for
   native explicit chain-of-thought; §2's reasoning-to-decision framing makes
   them a targeted candidate rather than a generic model swap.

### 3.B — Débit (levers jamais touchés)

6. **Speculative decoding** — **zero mentions anywhere in the repo.** vLLM
   supports n-gram speculation natively (`--speculative-config`). Structured
   JSON emission is highly predictable (field names, delimiters, the codebook's
   own integer motifs); `<think>` is less so. Expected: real gains on the
   visible-output portion, unknown on reasoning. Cheap to measure, nothing to
   lose — and it is the single largest untapped standard technique.
7. **Prefix-cache tuning** — enabled by default, and *only ever reliability-
   tested, never tuned*. Live logs during the parity run showed **57,9 % hit
   rate**, i.e. real headroom. Levers: order every prompt invariant-first
   (system prompt + codebook tables byte-identical, variable citizen data last),
   and order chunks so consecutive calls share the longest possible prefix.
   Pure win, no behavioural risk, no determinism cost.
8. **Reasoning-budget control** — `<think>` tokens dominate cost. The project
   checked for a `budget_tokens` equivalent, found none exposed, and stopped.
   Worth revisiting: budgets are currently sized against *worst case*
   (`_dynamic_max_tokens` now requests the maximum the window allows), never
   against the measured distribution. The 30-year run will produce that
   distribution for free.
9. **Model routing / cascade** — `candidacy_considered` is a threshold
   comparison; it does not need an 8B model. Route simple types to a small
   model, escalate on disagreement. Research: FrugalGPT, model cascades. Note
   §12's "un seul modèle fine-tuné généraliste" — a routing architecture is a
   deliberate departure from that and needs an explicit decision, not a silent
   one.

### 3.C — Long terme (v8, §12)

10. **Fine-tuning is already correctly scoped and correctly blocked.** §12 is
    resolved in favour of auto-distillation on the model's own successful
    trajectories; `plan-decision-quality-validation.md` establishes that
    "successful" has only ever meant *structurally valid* for 8 of 9 types, and
    that curating training data on that basis would engrave a demonstrated
    silent corruption. **That ordering is right and this program keeps it**:
    §3.A must land before any distillation data is curated.

---

## 4. Programme scientifique

### 4.A — Audit contre la littérature

The polity model has **no single academic reference** — `traceability.md` records
it as *"modèle propre au projet"*. Citations exist but are scattered and
one-directional (Granovetter for thresholds, Downs for spatial competition,
Superti for blank-vote protest, Shugart & Carey for calendars, Laakso &
Taagepera for fragmentation). The audit worth doing:

- **Ground the ungrounded.** `L(t)`'s decay-accumulator form, `écart(t)`'s
  weighting, the awakening-threshold shape (`beta(3,5)`, open point #13, flagged
  as the *most structurally important uncalibrated parameter* in the project),
  and the two-tier menu/choice separation are all project-invented. Each needs
  either a literature anchor or an explicit "this is ours" label.
- **Test the theses that are already contradicted by the project's own data.**
  The clearest: §7bis.6's purely-actional legitimacy model predicts a
  representative facing a passive population loses nothing — yet a president
  **conceded 13 times to a population with `inaction_rate=1.0`**. The design
  doc's own open question. §2's collapse mechanism is a candidate explanation
  (a collapsed `representative_response` concedes regardless of input) that
  would resolve it as an *instrumentation artefact rather than a finding* —
  which is exactly why §3.A must precede any theoretical interpretation here.
- **Add the missing literature: LLMs as human proxies.** Zero citations today.
  The relevant body (Argyle et al. 2023 on silicon sampling and algorithmic
  fidelity; Park et al. 2023 generative agents; Santurkar et al. 2023 on whose
  opinions models reflect; Bisbee et al. 2024 on LLM survey responses having
  *systematically lower variance than humans*) reports one consistent failure
  mode: **LLM populations are mode-collapsed and caricatured relative to real
  ones.** This project has independently rediscovered that phenomenon four times
  and called it a bug each time. Naming it correctly turns four scattered bug
  reports into one documented, literature-backed limitation — and points
  directly at §3.A.1 as the standard mitigation.

### 4.B — Validité et méthodologie

- **Single-seed is the project's largest standing methodological risk, and it
  has already fired once.** `seed=42` was used by every acceptance run since v4
  Lot 8 and was never validated; the Blank vote turned out to win 68 % of seeds
  under the shipped distribution. Every results doc says "n=1, une graine".
  The ABM standard is multi-seed with confidence bands.
- **Deterministic probes are optimistic ~2× on citizen-arbitrated quantities**
  (measured: 63,6 % predicted vs 33,3 % actual office occupancy) — currently a
  "working hypothesis, must not be cited as acquired". It needs either
  promotion to a validated rule or retirement.
- **The determinism question deserves reopening, on the project's own terms.**
  Byte-reproducibility has cost a great deal: concurrency rejected (a measured
  **5,84×**), `VLLM_BATCH_INVARIANT` rejected (11,3× slower). Yet the shipped
  flagship config runs `max_batch_replays: 2`, **which the plan itself documents
  as non-byte-reproducible**. The gate that rejected concurrency was applied at
  `replays=0` — a configuration that is not the one being shipped. This is worth
  stating plainly because it is a real inconsistency, *not* because the
  conclusion is obviously wrong: concurrency also **raised the failure rate
  30 % → 39 %**, which is a quality objection, not merely a reproducibility one.
  The honest position: that quality objection is a consequence of §3.A's
  problem, so **fixing decision quality is what would unlock this**, and the
  dependency runs quality → concurrency → multi-seed → real statistics.

### 4.C — Extension

Only after the above; listed so they are not lost:
- **The missing "law" concept** — blocks the sortition chamber's veto (open
  point #11) and, per the project's own note, is a chantier the size of v7.
- **Persona library (§9) is designed but never built.** Citizens are currently
  a 20-dim vector plus scalars. The silicon-sampling literature ties behavioural
  fidelity directly to conditioning richness — so this is not decoration, it is
  §3.A.1's natural complement for restoring population variance.
- **Conviction voting** — flagged as a fourth competing recall mechanism that
  would need to route through `écart(t)`; explicitly undecided.
- **Static-only social graph** — `evolving: true` is parsed then rejected at
  config load; homophily has never been tested.

---

## 5. Le format d'échange — la réponse honnête est contre-intuitive

### 5.A — Ce que dit la littérature, et ce qui s'applique vraiment ici

Two real findings, and only one of them applies to this project.

**Finding 1 — format restriction can degrade reasoning.** *"Let Me Speak
Freely?"* (Tam et al., 2024) measured constrained decoding hurting reasoning on
several tasks. Real, contested in magnitude, and **already partly mitigated
here**: `--reasoning-parser qwen3` exists precisely so the grammar does not
swallow the `<think>` block, and the project already caught the failure mode it
protects against (a silent `enable_thinking` no-op under grammar constraint).

**Finding 2 — JSON is token-expensive.** Also true in general: every key is
repeated for every array element, plus quotes, braces, commas. TSV/CSV states
keys once in a header; a minimal DSL (`1|0|4,2,1|101`) costs almost nothing.

**But finding 2 barely applies here, and it is worth saying so plainly rather
than shipping a satisfying-looking change with no effect.** Measured in this
session: a `vote_cast` decision's raw output was **81 characters** (~25 tokens),
against `think=True` budgets of 8 000–12 000 and actual generation of
~300–1 400 tokens per call. **The JSON output is under 5 % of what gets
generated; the reasoning is essentially all of it.** Converting JSON→TSV would
save on the order of 20 tokens out of 1 000. That is not where the cost is.

### 5.B — Où le format compte réellement ici : l'entrée, pas la sortie

The prompts are the part that hurts, and they are large: measured **2 242
tokens** (chamber, chunk=5) and **3 000 tokens** (vote_cast, chunk=5). Prompt
size is exactly what constrains chunk size — the entire `_dynamic_max_tokens`
saga was a fight for context headroom. Two untouched levers:

1. **Float precision.** Every numeric field is `round(x, 4)` — verified across
   `llm_behavior_engine.py` (positions, priorities, distances, platforms,
   thresholds, scores). `build_chamber_user_prompt` sends 3 arrays × 20 dims × 5
   members = **300 floats per call**; vote_cast sends ~330. Rough estimate: the
   last two decimals are ~10-20 % of prompt tokens — spent on precision the
   model cannot plausibly use for a coarse categorical judgement. Dropping to 2
   decimals is free, and the exact figure is **one cheap probe away** using the
   `count_prompt_tokens` method just built for `_dynamic_max_tokens`.
2. **Redundant payload at the exact point of a known bug.**
   `build_chamber_user_prompt` sends both `sincere_position` and
   `chamber_position` — 40 floats — and at seating time **they are identical by
   construction**. That is precisely the state that triggers the documented
   2,6 % Mode-A reasoning loop, currently patched by a sentence in the system
   prompt telling the model this case is trivial. Sending
   `position_unchanged: true` instead would halve that payload *and* remove the
   ambiguity structurally rather than verbally.

Why this compounds: smaller prompts → more context headroom → larger chunks
legal → fewer calls. It multiplies with §3.B rather than adding to it.

**Point 1 partiellement implémenté, 2026-09-09, scope volontairement restreint
au moment de l'écriture** (`_PROMPT_VECTOR_PRECISION = 2`,
`llm_behavior_engine.py`, offline-tested only — mypy/flake8/1306 tests green,
**pas encore vérifié en direct contre le serveur**, bloqué par le run
scale-probe de Phase 7 toujours en vol sur le même serveur partagé). Deux
restrictions découvertes en implémentant, pas anticipées en écrivant ce
paragraphe :

- **`distances`/`blank_threshold` (vote_cast) restent à 4 décimales.** Ce ne
  sont pas des vecteurs lus holistiquement — c'est la comparaison seuil-à-seuil
  exacte qui a déjà produit un collapse à 100 % blanc une fois ; coarsir cette
  précision sans A/B en direct risquerait de déplacer des décisions
  limitrophes sans que rien ne le détecte avant un run complet.
- **Seuls `vote_cast` et `chamber_deliberation` sont touchés pour l'instant.**
  `campaign_positioning` porte son propre défaut actif non résolu (50-66 %
  d'échec, troncature + fuite motif→cid) ; `representative_response`,
  `coalition_decision` et `reaction_to_event` (branche SCANDAL) ont un collapse
  confirmé. Changer leur prompt maintenant contaminerait toute future
  investigation sur CES défauts précis — même discipline « une variable à la
  fois » que le projet applique déjà partout ailleurs. Ces trois/quatre types
  restent candidats pour ce même changement, mais après que leurs propres
  chantiers de fiabilité aient conclu, pas en même temps.

Point 2 (`position_unchanged`) reste non implémenté — restructuration du
format d'entrée plus profonde que la précision seule, à ne pas faire sans A/B
en direct disponible dès le départ.

### 5.C — Lire les logprobs au lieu d'échantillonner (le vrai levier de format)

For any binary decision, the model does not need to *emit* a token — vLLM
exposes `logprobs`, so you can read **P(act)** directly. This is a different
protocol, not a different serialization, and it solves four problems at once:

- a **graded, continuous** signal instead of a single categorical draw;
- **calibration for free** — a threshold you can tune, rather than a coin flip;
- **collapse becomes measurable instead of inferred**: if P(act) is near-identical
  across wildly different citizens, that *is* the collapse, quantified on every
  call, rather than deduced from 4–6 hand-built extreme cases;
- determinism preserved exactly.

It composes directly with §3.A.2: the two-stage split's first stage (act /
don't-act) becomes a logprob read rather than a generation — cheaper *and*
better instrumented than what it replaces.

**Primitive implémenté, 2026-09-09** (`VllmJsonClient.complete_with_logprobs`,
`llm_client.py`, offline-verified — mypy/flake8/1313 tests green, 7 new
mocked-transport tests). Live-confirmé le même jour, avant le début de cette
implémentation, contre le serveur réel : un probe forced-choice trivial
("réponds oui/non") renvoie P(yes)=0.962, P(no)=0.038, exactement la forme
attendue. Deux choses restent **non résolues, délibérément pas attaquées par
ce premier incrément** :

1. **Vérification en direct de la méthode elle-même** — bloquée par le run
   scale-probe de Phase 7, toujours sur le même serveur partagé.
2. **Le vrai problème dur : localiser le bon token dans une sortie JSON
   contrainte par xgrammar.** Le probe déjà vérifié pose la question en
   forced-choice nu (le PREMIER token généré EST la réponse) — une décision
   de production réelle (`"act":3` quelque part dans un objet JSON) n'a pas
   cette propriété : le token qui compte est enterré après le boilerplate
   du schéma, à une position qui varie par prompt. `complete_with_logprobs`
   expose la matière première (un `TokenLogprob` par position générée) mais
   ne résout PAS cet alignement — c'est un problème séparé, pas encore
   attaqué, et la prochaine étape réelle avant d'instrumenter un type de
   décision de production.

### 5.E — TOON : bon outil, mais pas sur les prompts qu'on croit

TOON (Token-Oriented Object Notation, fin 2025) declares keys once as a header
and then emits rows, CSV-style, for uniform arrays of objects — plus explicit
length/field markers (`users[3]{id,name,role}:`) that double as a self-check for
the model. Its sweet spot is **many records × many scalar fields**, which is
exactly the shape of a batched decision prompt. So the fit is real here, unlike
generic "use YAML" advice.

**But the payoff splits sharply by decision type, and the split is measurable
from the code, not guessed:**

| Prompt | Shape per record | Ce qui domine | Levier qui paye |
|---|---|---|---|
| `vote_cast` | 5 clés, **47 nombres** (`positions` 20, `priorities` 20, `distances` 5, +2 scalaires) | Les **nombres** (~90 %) | **§5.B précision** (~25 %) ≫ TOON (~8 %) |
| `chamber_deliberation` | 4 clés, **60 nombres** (3 × 20 dims) | Les **nombres** | **§5.B précision + dédup** ≫ TOON |
| `pressure_action` | ~8-12 clés, **quasi que des scalaires** (docstring : « Deliberately NO 20-dim position vectors »), **jusqu'à 25 citoyens par chunk** | Les **clés répétées** | **TOON (~30-40 %)** ≫ précision |
| `candidacy_considered` | cid + 2-3 scalaires, chunks de 20+ | Les **clés répétées** | **TOON** ≫ précision |

So the two levers are **complementary, not competing**: float precision pays on
the vector-heavy types, TOON pays on the scalar-heavy high-volume ones. And
`pressure_action` — the single highest-volume decision type in the project — is
squarely in TOON's zone.

**Trois réserves, dont une bloquante pour l'ordonnancement :**

1. **Ne pas toucher à la sortie.** JSON-schema constrained decoding is
   load-bearing here: xgrammar, the `disable_any_whitespace` fix, `_inline_refs`,
   nine `decode_*_batch` functions and their Pydantic validators all hang off it.
   A TOON grammar is writable, but you would trade the entire structural-validity
   pipeline for the ~20 tokens §5.A already showed are negligible. **Input only.**
2. **Token count ≠ comprehension.** TOON is recent; these models have seen
   overwhelmingly more JSON in training. The published claims are largely about
   token count and retrieval benchmarks — not about numeric reasoning over
   positions and thresholds, which is what this project actually asks for. This
   demands an A/B on **decision quality**, not just a token count, exactly as
   this project demands for everything else.
3. **Bloquant : `pressure_action` est le cobaye idéal *et* le malade.** Changing
   its prompt format invalidates every prior collapse measurement on it — the
   61 % agreement figure, the ablations, the cross-model checks were all measured
   against the JSON prompt. So the TOON test there must be **paired with §5.C's
   logprob instrumentation** (measure P(act) before and after), or it produces a
   new prompt with no comparable baseline. One more reason instrumentation comes
   first.

### 5.D — Autres axes de la littérature

- **"Lost in the middle"** (Liu et al., 2023) — models attend unevenly across a
  context. **Already run** (2026-09-09,
  `check_positional_bias_within_chunk.py`/`_results.md`, read-only against the
  completed parity run, zero GPU): `chamber_deliberation` position 0 produced a
  deliberative shift **0/495** times across the whole run, while positions 1-4
  did so consistently at 1.6-2.4 % — not the known truncation mode (fallback
  flat and near-zero throughout), a real behavioural asymmetry isolated to
  primacy. `vote_cast` showed a similar-looking gradient but on a small,
  fallback-diluted sample — re-run once the scale-probe journal (5x the volume)
  completes before trusting it. This is now a concrete lead, not a hypothesis:
  worth folding into §3.A's decision-quality work rather than treated as a
  separate literature check.
- **Prompt compression** (LLMLingua) — moderate value; prompts are ~25 % of the
  token budget, so the ceiling is bounded.
- **XML tags for delimitation** rather than nested JSON — models are heavily
  trained on them; cheap to A/B if §5.A finding 1 ever looks binding here.
- **Field order in the schema** — partially explored already (`a_reasoning`
  first); worth completing rather than restarting.

---

## 6. Multi-agents — le projet en est déjà un, mais pas au sens LLM

### 6.A — La distinction qui compte

This simulation is already multi-agent in the **ABM** sense: 500 citizens, each
deciding. It is not multi-agent in the **LLM** sense: each citizen is a
*stateless prompt*, not a persistent agent. Every decision is computed fresh
from the current context, with no thread of identity across ticks.

### 6.B — Les trois couches manquantes (référence : Park et al., 2023, *Generative Agents*)

1. **Mémoire.** Citizens have no recollection. A citizen who petitioned three
   times and was ignored carries nothing forward. `event_salience` is a scalar
   decay — a crude proxy for memory. For a project whose core question is about
   *cumulative* political disaffection, this is a substantive theoretical gap,
   not just an engineering one.
2. **Réflexion.** No synthesis of experience into higher-level belief.
3. **Interaction.** **Citizens never communicate with each other.** Social
   influence is `neighbors_acting` — a *count* of how many neighbours mobilised.
   This is worth stating precisely, because it is the direct answer to the
   original question: *"les comportements des individus entre eux"* is currently
   modelled **entirely through numeric aggregates, never through exchange**.
   That is a defensible, cheap modelling choice — but it should be a stated one,
   because it bounds what the simulation can claim about inter-individual
   dynamics.

### 6.C — Le constat le plus net : la chambre délibérative ne délibère pas

§6bis.3's sortition chamber is the project's deliberative-democracy arm — the
whole control group for "does removing electoral pressure produce more sincere
decisions". But `decide_chamber_deliberation` asks **each member independently**
whether to adjust their own position. No member ever sees another member's
argument. That is parallel introspection, not deliberation.

The literature the chamber invokes (deliberative mini-publics; Fishkin is
already listed in `traceability.md` §7.5 as *prévu*) is *about the exchange* —
modelling it as independent introspection removes the very mechanism under
study. And it is tractable: 75 members is far too many for genuine deliberation,
but mini-publics in the literature run at 5–15. A real multi-agent exchange
inside a small subgroup is affordable.

There is a second reason to want this, from §2: a deliberating agent has
*another agent's argument* in its context — a far richer, more discriminating
input than a scalar. A decision that collapses when asked "should you adjust?"
in a vacuum may not collapse when asked to respond to a specific argument.

### 6.D — Le coût, honnêtement

Multi-agent debate multiplies calls by k. At 35 h per run, that is a non-starter
population-wide, and should not be proposed as one. Where it is genuinely
affordable:

- **the chamber subgroup above** — small n, high theoretical payoff;
- **as a diagnostic on the four collapsed types** — does the collapse break when
  two instances must argue? Small sample, cheap, and it directly probes §2's
  mechanism.

If the full architecture is ever wanted, **Concordia** (DeepMind) is the
reference library for generative agent-based social simulation and is worth
reading before building anything bespoke.

---

## 7. Graphe de dépendances et séquencement

The whole program has one spine, and §5.C changes where it starts: **you cannot
fix a collapse you can only detect with 4–6 hand-built extreme cases.**
Instrumentation comes first.

```
    §5.C  logprobs — la mesure continue de P(act)
      │      (transforme "collapse" d'une inférence en une quantité mesurée à chaque appel)
      │
      ▼
    §3.A  décision quality
      │      (per-citizen seeds · 2-stage split · grammar invariants · base-vs-instruct)
      │
      ├──► §4.A  interprétation théorique enfin défendable
      │           (le président qui concède à une population passive :
      │            vrai résultat, ou artefact d'un type collapsé ?)
      │
      └──► objection qualité de la concurrence levée (30 %→39 %)
             │
             └──► concurrence ré-autorisable (5,84× mesuré)
                    │
                    └──► §4.B  multi-graines, bandes de confiance
                           │
                           └──► §4.C extensions · §6.C chambre délibérante · §3.C fine-tuning (v8)
```

**Hors-spine, sans dépendance, exécutables immédiatement** — including *while*
the flagship runs, precisely because none can perturb it:

- **§3.B.6/7** speculative decoding + prefix-cache tuning (pure throughput);
- **§5.B** float precision + redundant-payload removal (pure prompt size, and it
  compounds: smaller prompts → more headroom → larger chunks → fewer calls);
- **§5.D** "lost in the middle" — per-position accuracy within a chunk, and the
  flagship is generating exactly that data right now, for free.

### Ordre proposé

| # | Travail | Coût | Pourquoi ici |
|---|---|---|---|
| 0 | §5.B précision des flottants + payload redondant · §3.B.6/7 prefix-cache + speculative decoding | heures | Zéro risque, zéro dépendance, gain immédiat sur tous les runs suivants ; se fait pendant que le flagship tourne |
| 1 | **§5.C logprobs — instrumenter la décision binaire** | 1 jour | **Passe avant tout le reste** : rend le collapse mesurable en continu au lieu d'inféré sur 4-6 cas construits à la main |
| 1bis | §5.E TOON en **entrée seulement**, sur `pressure_action`/`candidacy_considered` | 1 jour | Là où les clés répétées dominent (jusqu'à 25 enregistrements scalaires par chunk) ; **après §5.C**, sinon on change le prompt du seul type dont on mesure le collapse sans baseline comparable |
| 2 | §2 base-vs-instruct sur les 4 types collapsés | 1 après-midi GPU | Identifie ou élimine le mécanisme cherché depuis des semaines — et §5.C rend le verdict quantitatif |
| 3 | §3.A.1 per-citizen deterministic sampling | 1-2 jours | Le levier le plus prometteur, compatible avec la reproductibilité |
| 4 | §3.A.3 grammar-level invariants (`blank`/`ranking`) | 1 jour | Supprime une classe d'échec entière au lieu de la réessayer |
| 5 | §3.A.2 décomposition en deux étapes, `pressure_action` d'abord | pré-enregistrement + cycle de validation | Candidat déjà nommé par le projet ; §2 dit qu'il généralise ; §5.C fournit son étage 1 |
| 6 | §6.D multi-agents en diagnostic sur les types collapsés | petit échantillon | Sonde directe du mécanisme §2, coût borné |
| 7 | Re-mesurer les 4 types contre le protocole complet | selon §3 | Seulement une fois qu'il y a quelque chose à mesurer |
| 8 | Rouvrir la concurrence | proof existante à rejouer | L'objection qualité aura changé de valeur |
| 9 | §4.B multi-graines / bandes de confiance | GPU × N | Devient abordable une fois 0+8 acquis |
| 10 | §6.C faire délibérer réellement la chambre | chantier de conception | Extension théorique — après que la mesure et la qualité tiennent |

---

## Verification

- **§3.B.6/7** — measure against the existing harness shape
  (`check_vllm_chunk_size_throughput.py` is the template): tokens/s and
  wall-clock on identical prompts, before/after, plus vLLM's own logged prefix
  hit rate as the second signal. Determinism check: the byte-identical journal
  proof already built (`check_intra_run_concurrency_determinism.py`) re-run at
  `workers=1` must still pass — neither technique may perturb output.
- **§2 base-vs-instruct / §3.A.1 per-citizen seeds** — reuse the collapse-
  signature protocol already established (`plan-adversarial-framing-collapse.md`:
  extreme cases at both poles, 4-6 trials, content verified not just structure).
  Pre-register the criterion before any live call, as this project does.
- **§3.A.3 grammar invariants** — the existing polity suite (1304 tests) plus a
  targeted test that a `blank=1, ranking=[…]` response is now *ungenerable*
  rather than merely rejected.
- **§5.B prompt-size levers** — exact before/after token counts via the
  `count_prompt_tokens` probe already built for `_dynamic_max_tokens` (no
  estimation needed). Behaviour gate: decision output must be **unchanged** on a
  fixed sample when only precision drops — if 2-decimal positions change
  decisions, that is itself a finding worth stopping on, not a regression to
  paper over.
- **§5.C logprobs** — validate against the one decision type with real ground
  truth (`vote_cast`, `simple_rules.build_ranking`): does P(chosen) correlate
  with correctness? A calibration curve there licenses using the same signal on
  types that have no ground truth.
- **§5.E TOON** — two gates, not one. (a) token count before/after via
  `count_prompt_tokens`; (b) **a decision-quality A/B**, since token savings are
  worthless if comprehension drops — run it on `candidacy_considered` first,
  which has real ground truth (`simple_rules.decide_candidacy`) *and* no known
  collapse defect, so a quality regression is attributable to the format rather
  than confounded with an existing failure. Only then consider
  `pressure_action`, and only with §5.C's P(act) baseline captured first.
- **§5.D lost-in-the-middle** — read-only analysis of the flagship journal, no
  GPU: group decisions by position-within-chunk, compare accuracy/act-rate.
  Costs nothing and needs no new run.
- **§6.C/D multi-agent** — cost must be measured before scope: one deliberating
  subgroup of 5, wall-clock per exchange round, extrapolated before anything is
  wired into the tick loop.
- **Anything touching decision quality** — must clear
  `plan-decision-quality-validation.md`'s own bar (≥90 % agreement on unambiguous
  cases for Group A/B types), with the same pre-registration discipline, before
  it counts as resolved.

## Hors scope

- Changing anything about the flagship run currently executing.
- Curating fine-tuning data (blocked by §3.A, deliberately).
- Implementing §4.C / §6.C extensions before the spine lands.
- **Switching the output serialization away from JSON** — §5.A measured why:
  the output is under 5 % of generated tokens, so it is a satisfying-looking
  change with no effect. Revisit only if §5.A's finding-1 (grammar interfering
  with reasoning) ever measures as binding here.
