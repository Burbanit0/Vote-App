# Polity LLM — reference

**What this is.** A precise account of what the polity simulator actually does today: the
vocabulary, the mechanisms, the nine LLM decisions, every knob, and — stated plainly — which parts
are trustworthy and which are not. Written to be read by someone deciding where to spend effort
next.

**Snapshot.** Verified against the code at commit `a691e29` (2026-09-11). Everything below was read
from the source, not recalled; where two sources disagreed the code won. This is a snapshot, not a
contract: it will drift, and `polity-simulation-design-v2.md` (the design intent, French) and
`polity-decision-contracts.md` (the prompt-quality contract, French) remain the authorities on
*intent*. This document is the authority on *what is built*.

**Language.** English, matching `plan-flagship-30y-run.md` and the `scripts/*_results.md` lineage
this belongs to. The design docs are French, so §1 bridges the two vocabularies.

---

## 0. The one thing to understand first

**The shipped config and the flagship config are different simulations.**

`api/domain/polity/polity_config.yaml` — what `load_config()` returns — has **the LLM off and the
entire accountability layer off**. It runs a 121-tick, 100-citizen, 5-party polity with elections
and coalitions, and *nothing else*: `_run_accountability_phase` early-returns on every single tick.

The flagship runner (`scripts/run_polity_flagship.py::_flagship_config`) turns everything on:
legitimacy, mandate drift, petitions, street pressure, awakening, exogenous events, the social
graph, the sortition chamber, and the LLM.

Almost every confusing result traces back to this. A run started from the bare shipped defaults
produces **zero** `pressure_action` events, and that is correct behaviour, not a bug — no awakening
gate means nobody is ever consulted.

| | shipped `polity_config.yaml` | flagship runner |
|---|---|---|
| LLM decisions | off | on |
| legitimacy / mandate / awakening | off | on |
| petitions / street pressure | off | on |
| exogenous events / social graph | off | on |
| sortition chamber | off | on |
| pressure menu | `electoral_only` — only acts 0 and 4 legal | **open**: petitions *and* mobilisation, all 5 acts legal |

That last row is easy to miss and changes which findings apply. Verified in a real flagship run's
own journal: its citizens chose `SIGN_PETITION`, an act that does not exist under the shipped
config. So the closed-menu `pressure_action` collapse (P(act=4) ≥ 0.976) describes the *control*
configuration; the flagship runs the open menu, where the measured figure is the weaker 60%
agreement rather than a flat constant.

---

## 1. Lexicon

Design docs are French; identifiers are English. This table is the bridge.

| French (design) | Code identifier | What it is |
|---|---|---|
| citoyen | `Citizen` | One agent. 20 issue positions, priorities, thresholds |
| écart | `ecart` | The pressure term that erodes legitimacy each tick |
| éveil / seuil d'éveil | `awakening` / `awakening_threshold` | The gate deciding **who is consulted**, never what they decide |
| consulté | `select_consulted` | The cohort asked for a `pressure_action` this tick |
| mandat / promesse | `pledged_platform` | What a candidate promised. Immutable for the term |
| position révélée | `revealed_position` | Where the officeholder actually stands now. Drifts |
| dérive de mandat | `mandate_deviation` | Distance promise → current position |
| pression citoyenne | `pressure_action` (dt=10) | A citizen's act toward the officeholder |
| pétition de défiance | petition / `confidence_vote` | Signature drive → confidence vote → possible removal |
| pression de rue | `street_pressure` | Accumulator of mobilisation, decays 0.85/tick |
| rappel | `recalled` | Removal, by legitimacy floor or lost confidence vote |
| légitimité | `legitimacy_capital` / L(t) | Officeholder's standing, [0,1] |
| chambre de tirage au sort | `sortition_chamber` | Randomly drawn chamber — the control group |
| rupture (candidature) | `attempt_rupture_candidacy` | Rare path: run against your own party |
| vote blanc | `Blank` / `blank_threshold` | Blank is a real ballot option and can win |
| motif | `motif` | Closed-enum reason code attached to every LLM decision |
| tick | `tick` | One quarter. 4/year |

**dt=N** is the project's own decision-type numbering (`codebook.DecisionType`). It is not
sequential in any meaningful way — dt=3 and dt=7 do not exist as LLM decisions.

---

## 2. What is simulated

### 2.1 The world

A fixed population of `Citizen` objects (`citizen.py:42-125`), drawn once from `run.seed` and never
replaced (`static_population: true`). Each carries:

- `issue_positions` — 20 floats in (0,1), their sincere views. **Never mutated after generation.**
- `issue_priorities` — Dirichlet weights summing to 1: how much each issue matters to them.
- `blank_threshold` — `beta(3,5)`. Their tolerance: a candidate farther than this ranks below Blank.
- `ambition_score` — `beta(2,8)`. Most citizens are unambitious.
- `base_threshold` — `beta(3,5)`. Their awakening bar.

Positions are drawn with `factor_structure` (two latent factors + noise, squashed through a
sigmoid), not uniformly — because uniform positions let **Blank win the runoff outright on 68% of
seeds**. The factor structure preserves issue correlation and dropped that to 0%.

Officeholder-only fields (`legitimacy_capital`, `mandate_strength`, `street_pressure`, petition
state) live on the same dataclass but mean nothing for an ordinary citizen. **There is no
citizen-level "satisfaction" or "legitimacy" anywhere in the model** — a fact worth knowing before
asking for population-mood metrics.

Five parties (`parties.py`), platforms set by deterministic k-means over citizen positions, then
**frozen for the whole run** (no birth, no death, no platform movement).

### 2.2 The clock

`ticks_per_year: 4`, `duration_years: 30` → **121 ticks** (the loop is inclusive of the last tick,
deliberately: a half-open range silently dropped the final legislative election).

- Presidential election: `tick % 16 == 0` → ticks 0, 16, 32… (every 4 years)
- Legislative election: `(tick - 8) % 16 == 0` → ticks 8, 24, 40…
- Sortition rotation: `tick % 4 == 0`
- Yearly snapshot: `tick % 4 == 0`, taken **before** the tick runs

This is why elections are the expensive ticks: a presidential tick adds a full-population
`candidacy_considered` pass **and** a full-population `vote_cast` pass on top of the normal
per-tick work. Measured on a real 500-citizen run: an election tick took ~50 minutes against
~4-6 minutes for an ordinary tick.

### 2.3 The per-tick sequence

```
snapshot (yearly)
  → rupture candidacies          [off by default]
  → exogenous events             [off by default]
  → presidential election        [on election ticks]
  → legislative election + coalition
  → sortition rotation           [off by default]
  → chamber deliberation         [off by default]
  → accountability phase         [off by default]
  → checkpoint + progress
```

Ordering is load-bearing: sortition runs after the elections so a same-tick new president is
excluded from the draw; accountability runs last so a new winner's pledge and initial legitimacy are
already on record.

---

## 3. The two engines

`llm.enabled` is a single switch between two complete implementations of the same decisions:

- **off** → `simple_rules.py`, the deterministic baseline. Elections still happen; candidates run on
  their sincere positions; nothing ever diverges `revealed_position` from `pledged_platform`, so
  mandate deviation is **zero by construction**.
- **on** → `llm_behavior_engine.py`, nine LLM decisions replacing (not supplementing) those rules.

The baseline is not a fallback stub — it is the permanent §11.4 comparison arm. Every LLM decision
has, or deliberately lacks, a deterministic counterpart, and that choice is documented per type.

---

## 4. The nine LLM decisions

### 4.1 Summary

| decision | dt | unit | think | chunking | fallback if the model fails |
|---|---|---|---|---|---|
| `vote_cast` | 1 | citizen | ✅ | 3 (vLLM) / 1 (Ollama) | ✅ deterministic ballot |
| `candidacy_considered` | 2 | citizen | ❌ | 25 | ❌ **none — run dies** |
| `party_nomination_choice` | 4 | contested party | ❌ | none | ✅ highest-ambition tiebreak |
| `campaign_positioning` | 5 | nominee | ✅ | none | ❌ **none — run dies** |
| `representative_response` | 6 | officeholder | ❌ | none | ✅ silence *(added 2026-09-11)* |
| `reaction_to_event` | 8 | citizen (pop-wide) | ❌ | 25 | ❌ **none — run dies** |
| `coalition_decision` | 9 | party × round | ❌ | none | ⚠️ round ≥2 only |
| `pressure_action` | 10 | consulted citizen | ❌ | **1** | ❌ **none — run dies** |
| `chamber_deliberation` | 11 | chamber member | ✅ | 5 (vLLM) / 1 (Ollama) | ✅ sincere, no shift |

### 4.2 What each one asks

**dt=1 `vote_cast`** — "Rank every candidate you find acceptable, best first, or vote blank." The
model is *given* precomputed weighted distances and the acceptability rule verbatim; it is not asked
to do the geometry. Above 6 candidates it must return only its top 5 (§3.6.1 truncation).

**dt=2 `candidacy_considered`** — "Do you run?" From `ambition_score` and `perceived_support`
(the fraction of citizens within tolerance of you). Sent as **TOON**, not JSON — the one place TOON
shipped, worth −6.9% tokens at identical accuracy.

**dt=4 `party_nomination_choice`** — "Which of your party's declared members becomes the nominee?"
Only for contested parties (≥2 declarants).

**dt=5 `campaign_positioning`** — "Adjust your displayed platform, or run sincere." Bounded: ≤3
dimensions, ≤0.3 each. This is the first decision where the model can change *who wins*.

**dt=6 `representative_response`** — "You are under pressure. Concede, defy, stay silent, or
counter-mobilise?" Plus the position shifts that go with it. Sees legitimacy, mandate deviation,
street pressure (lagged one tick, deliberately), lame-duck status and ticks left.

**dt=8 `reaction_to_event`** — "A scandal/economic shock just happened. How much does your awareness
rise?" Population-wide, one call per firing event.

**dt=9 `coalition_decision`** — "Join the formateur's coalition, or refuse?" Up to 3 negotiation
rounds; round ≥2 shows each party its own prior answer.

**dt=10 `pressure_action`** — "You are discontented. What do you do about it?" Within the
constitutional menu, which is an experimental variable: under the shipped `electoral_only` control
menu the only legal acts are **do nothing** or **wait for the election** (so a zero mobilisation
rate there is the configuration, not a failure); under the flagship's open menu all five acts —
including signing and launching petitions, and mobilising — are available.

**dt=11 `chamber_deliberation`** — "Hold your sincere position, or adjust it?" A drawn chamber
member, insulated from every pressure channel by design. Sees only how far they have already drifted
and how long they have left.

### 4.3 The shared pipeline

Every decision follows the same path:

```
build system prompt  (rules, motif table, expected-cid self-check)
build user prompt    (canonical JSON: sort_keys, compact separators, rounded floats)
  → client.complete_json(schema-constrained decoding)
  → decode_*_batch    (Pydantic: field constraints + cross-field validators)
  → validate_*        (context checks the static schema cannot express)
  → resolve           (positions/ballots/winners computed here, never by the model)
  → journal
```

Three things are worth knowing about this pipeline:

1. **The model never mutates state.** It returns a decision; the engine resolves it. A returned
   `winner_position` becomes a cid here, not there; shifts become a clamped position here.
2. **`validate_*` deliberately sits outside the retry loop.** A schema failure may be resampled; a
   judgment failure is not, because an identical retry at temperature 0 reproduces it.
3. **Motifs are closed enums, never free text**, banded by decision family (1xx vote, 2xx candidacy,
   3xx pressure/response, 4xx reaction, 5xx coalition, 6xx campaign, 7xx chamber). This is what lets
   "why did this happen" be queried rather than re-read.

### 4.4 Retry and fallback — the part that decides whether a run survives

Two independent mechanisms, and the coverage is uneven:

**Retry sampling variation.** A retry at temperature 0 with the same seed is not a retry — it is the
same request again. Only three types vary sampling on retry (`vote_cast`, `chamber_deliberation`,
and `representative_response` since 2026-09-11): temperature 0.3 and a per-attempt seed offset, on
retries only, never the first attempt.

**Deterministic fallback.** When replays are exhausted: four types fall back cleanly and the run
continues (`vote_cast`, `party_nomination_choice`, `representative_response`,
`chamber_deliberation`); `coalition_decision` falls back only from round 2 onward, so a round-1
failure still kills the run; and **four propagate outright**: `candidacy_considered`,
`campaign_positioning`, `pressure_action`, `reaction_to_event`.

This is not theoretical. Three separate multi-hour runs died this way in two days:

| date | type | cause |
|---|---|---|
| 2026-09-10 | `vote_cast` | prompt told the model to rank *every* acceptable candidate while the validator enforced top-5 |
| 2026-09-11 | `party_nomination_choice` | `winner_position` exceeded the party's candidate count → raw `IndexError` |
| 2026-09-11 | `representative_response` | two shifts on the same dimension; no fallback existed |

All three are fixed. The remaining four gaps are a standing risk to any long run, and closing them
is probably the highest-value reliability work available.

---

## 5. The mechanics

### 5.1 Elections

**Presidential.** Incumbent vacated → candidacies (party nominees by ambition; plus the rare rupture
path) → campaign positioning → every citizen ranks candidates with Blank spliced in at their
tolerance → `two_round` runoff.

**Blank is a real competitor.** It is an ordinary option in the field, so it can win the runoff, in
which case there is simply no president (`election_no_winner`). Optionally (`blank_vote_competitive`,
off by default) a blank share above 50% invalidates the election and forces a rerun.

**Legislative.** Party-list: each citizen picks the nearest platform within tolerance, else blank.
D'Hondt over parties clearing 5%. Then coalition formation — deterministic (greedy by proximity
until majority) or LLM (up to 3 negotiation rounds).

### 5.2 Legitimacy and removal

```
L(t) = 0.9·L(t−1) + 0.1·m − écart(t)                     clamped to [0,1]
écart(t) = 0.5·petition_pressure + 0.5·street_pressure + 0.0·mandate_deviation
m = share of ballots that ranked the winner above Blank
```

With `passive_erosion_weight: 0.0` (shipped), **drift alone never erodes legitimacy** — only citizen
action does. That is a deliberate modelling choice ("purely actionnel"), not an oversight.

Removal has two triggers: legitimacy crossing the 0.2 floor, or losing a confidence vote. When both
fire in the same tick **the floor wins the attribution**, but the office is vacated exactly once
either way.

### 5.3 The awakening gate

```
threshold = base_threshold × f(context),    f ∈ [0.5, 1.5]
  visible mandate drift      → lowers the bar
  election proximity         → raises it ("wait for the ballot")
  event salience, neighbours → lower it   [both off by default]
consulted ⟺ self_gap > threshold
```

No RNG, no cap, holder excluded. It decides **who is asked**, never what they answer — the
separation §7bis.9d insists on, and the reason `pressure_action`'s prompt must never contain the
threshold rule itself.

### 5.4 Petitions

Launch (the launcher is auto-signed) → others sign → either the signature threshold (25% of the
population) triggers a confidence vote, or it expires after 4 ticks. Either ending starts a 4-tick
cooldown. At most one open petition per target.

A subtlety that matters when reading journals: **`pressure_action.act` is the act the citizen
decided, before live state is applied.** A LAUNCH that is not launchable is silently downgraded to a
signature. Only the adjacent `petition_launched` / `petition_signed` event says what actually
happened.

### 5.5 The sortition chamber

30 members drawn at random, 1-year terms, non-renewable **by construction** (`renewable: true` is
rejected at load). They face no election, no petition, no street pressure, no recall — which is
exactly the point: they are the control group for "does electoral pressure change behaviour?" Their
drift ceiling is deliberately identical to the officeholder's, so the comparison isolates insulation
rather than a different bound.

### 5.6 Exogenous events and the graph

Scandals arrive as a per-tick Bernoulli draw; economic shocks follow an AR(1) crossing a threshold.
Both feed `event_salience`, which decays 0.85/tick. The social graph (Watts-Strogatz) feeds
`neighbors_acting` — contagion. All off by default.

---

## 6. Parameters

19 config sections. Rather than repeat every default (they are in `polity_config.yaml` with good
French comments), here is what actually matters when advising.

### 6.1 The knobs that change results most

| Parameter | Shipped | Why it matters |
|---|---|---|
| `citizens.position_dist` | `factor_structure` | `uniform` makes Blank win 27.5% of elections. Published results predating 2026-08-25 used `uniform` and were never re-baselined |
| `candidacy.ambition_threshold` | `0.30` | At the old 0.7, 39/40 seeds produced **zero candidates**. Acceptance scripts still force `0.0` |
| `pressure_menu.*` | `electoral_only` | The 4-modality experimental variable. Under the control setting only acts 0 and 4 are legal |
| `legitimacy.passive_erosion_weight` | `0.0` | Whether drift alone can erode legitimacy |
| `awakening.modulation_amplitude` | `0.5` | `0.0` is the sensitivity-control arm (context stops mattering) |
| `llm.max_batch_size` | `25` | Ignored by 5 of 9 decisions, which use their own measured chunk size |
| `llm.max_batch_replays` | `0` (runner: `2`) | Any value >0 makes the run non-byte-reproducible |

### 6.2 Cross-field rules (design constraints encoded as guards)

The loader refuses incoherent combinations rather than running a silently dead experiment:

- `pressure_menu.petition_enabled` **must equal** `petition.enabled`; same for mobilisation/street.
- `petition.weight_in_ecart + street_pressure.weight_in_ecart == 1.0`.
- Either lever ⇒ `legitimacy.enabled` **and** `awakening.enabled` (a lever with nobody consulted, or
  with nothing to erode, is "a silently dead experiment").
- `events.enabled` ⇒ `awakening.enabled` **and** `context_modulation.event_salience`.
- `context_modulation.neighbors_acting` ⇒ `social_graph.enabled`. **The reverse is deliberately not
  required** — the graph feeding ctx without modulating the gate is a real experimental arm.
- `sortition_chamber.enabled` ⇒ `population_size >= seats`.
- `llm.temperature` must be exactly 0.0; `llm.model` must be pinned (no `:latest`).

### 6.3 Knobs that do nothing

Worth knowing before tuning them: `assembly_term_limit`, `assembly_mode`, `coalition_initiator`,
`max_candidates_hard_cap`, `memory_window_terms`, `blank_vote_enabled` (blank is always available
regardless), `journal.snapshot_every_ticks` (the code keys off `ticks_per_year`),
`metrics.compute_every_ticks`, `sortition_chamber.veto_power` / `veto_delay_ticks`,
`llm.cache_backend` / `cache_url` / `personas_count`, `parties.birth_enabled` / `death_enabled`,
and the 4 score-based `presidential_method` values (accepted by config, refused at run start).

---

## 7. Determinism

The project treats byte-identical reproducibility as a hard requirement, and most odd-looking design
choices follow from it.

- **One seed** (`run.seed: 42`), consumed by several **independent** streams (population, rupture,
  events, sortition, graph) so enabling one mechanism never shifts another's draws.
- **Draw position is sacred.** Gated citizens are still drawn for, then discarded — skipping them
  would shift the stream.
- **temperature = 0**, enforced at config load. Two narrow exceptions exist for retries only, each
  with its own constant and rationale, never on a first attempt, and marked in the journal
  (`retry_sampling_varied`) so a varied-sampling answer is never mistaken for a deterministic one.
- **No intra-run concurrency.** Measured: 20/497 events diverged at 8 workers vs 1, *and* the
  failure rate itself rose 30%→39%. `run_chunks()` is built and tested but deliberately unreachable.
- **Temperature 0 is not sufficient on its own** — two byte-identical requests have produced
  different answers on real hardware. This is acknowledged in the code, not papered over.
- **Replays break reproducibility by design**, which is why the shipped default is 0 and the flagship
  accepts the trade explicitly.

---

## 8. What a run leaves behind

| File | What it is |
|---|---|
| `events.jsonl` | The journal. 9 fields per line, **no wall-clock timestamp** (it would break byte-identity). Ordering is `event_id`, flushed per write |
| `snapshots.jsonl` | Per-citizen census, once per simulated year. Positions/role/party — **not** legitimacy or pressure |
| `checkpoint.json` | Per-tick resumable state incl. 3 RNG stream positions and a `config_hash` that refuses a mismatched resume |
| `progress.json` | Live status: tick, ETA, decisions by type, retries, fallbacks. The only artifact with a wall-clock timestamp |
| `digest.json` / `digest.jsonl` | **Written on every ending** — completed, crashed or interrupted. Per-year counts of all 30 event types, population impact, terms, outcome. One appended line per attempt |
| `viz_export.json`, `metrics.json`, `events.duckdb` | Post-run only, i.e. **only if the run finished cleanly** |
| `replays.log` | Every rejected batch, with the reason. Appended across resumed attempts |
| `TIMELINE.md` | The human-readable story, written from the digest by the `run-narrator` agent |

**30 event types** can be journaled. The digest reports a count for every one of them, per year,
including zeros — so "this did not happen" is distinguishable from "nobody looked".

---

## 9. What is actually trustworthy

The honest part. Stated per decision, from measurements in the code's own docstrings.

**Confirmed content-blind collapse — the model returns the same answer regardless of input:**

- **`representative_response` (dt=6)** — the worst. P(stance=1) stayed within 0.000001 of 1.0 across
  the entire range from "near-perfect legitimacy, zero pressure" to "collapsing legitimacy, deep
  drift, mass mobilisation". No gradient at all. No remediation attempted.
- **`coalition_decision` (dt=9)** — P(action=JOIN) 0.965–0.999 everywhere, including the
  decline-obvious pole. Still collapses on vLLM.
- **`pressure_action` (dt=10)** — P(act=4) ≥ 0.976 for every citizen tested. **Root-caused and fixed
  2026-09-10**: `self_gap` was sent with no scale reference at all, making the question unanswerable.
  Adding the citizen's own threshold restores 100% agreement — but **only at batch size 1**; at batch
  5 or 25 every variant collapses back. Shipped calibrated, at batch 1.

**Reliability (completion) problems, content verified to vary:**

- `campaign_positioning` — 25% failure rate at batch size 1 (truncation, misalignment). Not a
  content collapse; the decisions genuinely vary when a call completes.
- `chamber_deliberation` — 2.6% Mode-A reasoning loops; silently drops decisions above its chunk
  ceiling (24 of 30 dropped in one call).

**Measured against real ground truth:**

- `vote_cast` — 23/24 and 29/30 correct at chunk 3/5 on vLLM. The most trustworthy decision.
- `candidacy_considered` — 16/25 (64%) against the deterministic proxy, identical across JSON and
  TOON. Below the project's own ≥80% bar; single run.

**Resolved but not explained:** `reaction_to_event` SCANDAL collapsed on Ollama and does not
reproduce on vLLM. Measured, not root-caused. The ECONOMIC_SHOCK branch is untested for intensity.

**Effectively unmeasured:** `party_nomination_choice`.

**Downstream consequence:** metrics derived from dt=6 and dt=9 — `mandate_deviation`,
`mandate_deviation_unified`, `lame_duck_deviation_delta`, `cohabitation_rate`, `coalition_lifespans`
— are carried through the export labelled `unverified`, and should be read as such.

---

## 10. Known gaps worth a decision

Ordered by how much they would change things.

1. **Four decision types can still kill a multi-hour run** (`candidacy_considered`,
   `campaign_positioning`, `pressure_action`, `reaction_to_event`). Three runs died this way in two
   days. The fix pattern is established and mechanical.
2. **`candidacy_considered` fails the C3 contract** — `ambition_score` is sent with no population
   reference, exactly the defect that caused `pressure_action`'s collapse. A real run shows **~40% of
   citizens declaring candidacy**, which is implausible against any real polity. The fix vehicle is
   already written down in `polity-decision-contracts.md` and unbuilt.
3. **`representative_response` and `coalition_decision` have written calibration vehicles and no
   implementation.** They are the two confirmed collapses left.
4. **A known metric design bug**: `mandate_deviation` weights only the top-5 priorities, so drift in
   any other dimension reads as exactly 0.0. Live-verified: a term drifted three dimensions to the
   clamp ceiling while the metric read 0.0 throughout. `unified_mandate_deviation` exists as the
   honest measurement but deliberately feeds nothing.
5. **A ctx/journal divergence introduced by the dt=10 calibration fix**: the prompt now sends
   `blank_threshold` inside ctx, but the journal writes the older four-key payload. The invariant
   "the ctx an analyst reads is the ctx the model saw" no longer holds exactly for dt=10.
6. **Only 3 of 9 types vary sampling on retry**, so for the other six a "retry" re-sends an identical
   request and reproduces the identical failure.
7. **Published results predate two calibration changes** (`position_dist`, `ambition_threshold`) and
   were never re-baselined.

---

## 11. Where things live

```
api/domain/polity/
  run_polity_simulation.py   the tick loop; the ONLY place that journals
  llm_behavior_engine.py     the 9 decisions: prompts, chunking, retries, fallbacks
  llm_schemas.py             wire schemas + cross-field validators
  llm_client.py              vLLM/Ollama transports, decode_*_batch
  codebook.py                motif enums, CODEBOOK_VERSION
  simple_rules.py            the deterministic baseline
  accountability.py          awakening gate, self_gap, petitions, street pressure
  legitimacy.py              L(t), the recall floor
  indexer.py                 RunMetrics, terms
  run_digest.py              the per-ending digest
  config.py / polity_config.yaml
scripts/run_polity_flagship.py   the runner (turns everything on)
```

Docs: `polity-simulation-design-v2.md` (intent, FR) · `polity-decision-contracts.md` (prompt
contract, FR) · `plan-flagship-30y-run.md` (the run tracker, EN) ·
`plan-llm-protocol-and-theory-program.md` (the research programme).
