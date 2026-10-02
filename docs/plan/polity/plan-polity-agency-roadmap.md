# Polity agency roadmap: from classified citizens to a polity that rewrites itself

**What this is.** The plan for polity's next era, set on 2026-09-27. It has two parts: a state of the art of the code as it stands at `7c2adf37`, and a phased roadmap toward citizens and leaders who act, talk, organise and change the rules.

**Language.** English, like `plan-polity-build-order.md`.

**How it is run.** The same way as the build order. Each step gets a `feat/polity-<step>` branch cut from `polity` and a PR back into `polity`, under the usual gates. There is one exception: the *exploration gate* in §2 D4.

**Working rule.** Reuse what exists and derive what can be derived. Build a mechanism only when a run shows it is needed. §5 lists what was deliberately left out, and when to add each item.

---

## 1. State of the art

### 1.1 What polity is today

v0–v8 of `polity-simulation-design-v2.md` §13 are done. The full run (30 years, 500 citizens, 75 chamber seats) takes about 2 h on the local RTX 5070 Ti (16 GB). It uses vLLM 0.30.0 with Qwen3-8B-AWQ and EAGLE-3, 12 workers, and relaxed determinism (`plan-full-run.md`).

**The kernel.**
- `run_simulation` (`run_polity_simulation.py:477`) runs 11 phases per tick, 4 ticks a year.
- The phases are: snapshot, rupture candidacies, events, presidential election, legislative election and coalition, sortition chamber, legislation, emotions, accountability, snap election, opinion dynamics.
- State is `TickState` (`tick_state.py`). Configuration is a frozen `PolityConfig` (`config.py:591`).
- All the randomness comes from five seeded RNG streams.

**Where the LLM is used.** `llm_behavior_engine.py` handles nine decision types through `DecisionSpec` and `run_decision` (~L1051–1144):
- vote, candidacy, nomination, campaign positioning;
- representative response, reaction to events, coalition;
- pressure action, chamber deliberation.

Every system prompt opens with *"Tu es un moteur de simulation. Pour chaque citoyen reçu…"*. The model classifies chunks of citizens given as numeric JSON vectors. It answers with closed codes under an xgrammar JSON schema.

**Records.**
- `events.jsonl` (typed, coded events), `snapshots.jsonl` and `digest.json`.
- `llm_calls.jsonl` with its `llm_prompts.jsonl` sidecar. `ReplayClient` replays a run byte for byte (proven on the 30-year p500 run: 86 s on CPU).
- The `/polity` explorer, the marimo explorer, the run narrator (`TIMELINE.md`) and the OBS log.

**Institutions.**
- A president: 13 ranked methods are usable, two-round by default, term limit 2, blank invalidation, snap elections.
- A party-list assembly: D'Hondt with a 5% threshold, and coalitions.
- A sortition chamber.
- Legitimacy L(t) (`legitimacy.py`), recall petitions that lead to a confidence vote, and shocks.
- Legislation S4.2, built but off.
- ADR-012 opinion dynamics and emotions, built but off.

### 1.2 Gaps against the goals

| Goal | Today | Where |
|---|---|---|
| **(a)** Citizens and leaders change the rules, voting method included | Absent. Every config dataclass is frozen, and resume refuses a changed config hash. ADR-008 is design only. | `config.py`, `docs/adr/ADR-008-*.md` |
| **(b)** Leaders try to stay popular | The loop is open. There are no polls. The retrospective vote weights `vote.approval` and `vote.policy_retrospection` are 0. `declare_candidacy` resets an incumbent to their sincere views. The president does not draft bills: `_draft_bill` is a formula. | `simple_rules.py:129`, `:457`; `run_polity_simulation.py:917` |
| **(c)** Citizens change their minds from decisions and from each other | Friedkin–Johnsen dynamics are built but off (0 of 81 settings qualified). Citizens never exchange messages and have no memory (`memory_window_terms` is parsed but never read). | `opinion_dynamics.py`, `citizen.py:43` |
| **(d)** Citizens form parties | Five k-means parties are frozen at t=0, and affiliation never changes. `birth_enabled`/`death_enabled` are parsed but not implemented. | `parties.py` |
| **(e)** Citizens give up, take initiatives, test the limits | Only the turnout cost, the 5-act recall menu (petitions target only the president) and rare rupture candidacies. There is no exit and no initiative. | `accountability.py` |

Citizens have no persona text (`personas_count` is unused), and `rationale_mode` other than `codes` is refused. The LLM never proposes anything; it only picks codes from a menu.

### 1.3 Known defects that carry over

- **Batch-wide fallback** (backlog #1 in `plan-full-run.md`). `run_decision` validates *after* `_complete_and_decode_with_replay` returns (`llm_behavior_engine.py:1118`). One invalid unit therefore sends its whole chunk to the deterministic fallback, and is never retried. Chamber losses are 5.8–7.1% of units (OBS-021, OBS-024, OBS-025).
- **Collapsed decision types.** `coalition_decision` is flat on Qwen, Granite and Gemma. `representative_response` is only partially fixed (OBS-007). `pressure_action` works only at batch size 1.
- **Other open OBS entries.** Candidacy runs at about 40% (OBS-011). Positioning thinking is uncapped (OBS-022). The 2,048-token budget binds on `vote_cast` (OBS-023).

### 1.4 Infrastructure limits

- **Transport.** `VllmJsonClient` (`llm_client.py:580`) sends no auth header, and `provider: api` is refused by design (§12).
- **Local assumptions.** `run_polity_flagship.py:229` hardcodes `localhost:8000`. `run_provenance.py` asks `docker inspect` about a local container, but it degrades to "unknown" when docker cannot answer.
- **Memory.** The KV pool is about 22.9k tokens on 16 GB, which is about six concurrent 3.5k-token prompts.
- **Parallelism.** Phases run serially. `run_chunks` parallelises only inside one decision type.

---

## 2. Decisions (2026-09-27, with the owner)

| # | Topic | Decision |
|---|---|---|
| D1 | GPU | Undecided. Tier the models, and choose one by comparing short runs across candidates (§6). |
| D2 | Scope of rule change | A **typed constitution**: typed articles, including the amendment threshold, with per-article entrenchment. Agents propose structured amendments; the kernel validates and applies them. |
| D3 | Scale | A **tiered population**: at most about 100 persona agents inside a cheap numeric crowd of 500–1000. |
| D4 | Gate | An **exploration profile** (`run_polity_flagship.py --profile exploration`). New mechanisms ship ON there. They are gated by sanity checks (valid-action rate, non-collapse, cost) and by OBS entries, not by pre-registered stylized facts. Pre-registration is kept for claims stated as results. In `polity_config.yaml` everything new stays OFF. |
| D5 | Models | **Open weights only**, served by vLLM on rented GPUs. §12 stands: the inference is rented, not outsourced. |
| D6 | Limits | **Extra-legal acts can succeed**: a coup, a refusal to leave, an insurrection. Success depends on support, legitimacy and institutional loyalty, and it has an aftermath. |
| D7 | First phase | **Leaders and popularity.** |
| D8 | Leader goal | **Implicit.** A leader's persona holds convictions and wants to keep office, and it sees the polls. Whether leaders chase popularity or hold to conviction is something to observe, not an instruction. |
| D9 | Agent language | **English** for the new agent prompts and speech. The existing French batch prompts stay for the LLM-crowd arm. |
| D10 | Order | **Extra-legal acts come last**, after citizen agents, parties and initiatives. |

Non-determinism is wanted. A run is recorded, not regenerated: `llm_calls.jsonl` plus `ReplayClient` still give a byte-identical replay for debugging.

---

## 3. Target architecture: agents act, the kernel referees

- **The existing engine becomes the kernel.** "The model never mutates state" (`polity-llm-reference.md` §4.3) still holds. Agents emit *typed intents*, bounded per role by the xgrammar schema, plus free text: `speech`, `rationale`, `note_to_self` and `other_initiative`. The kernel validates the intents, applies them and journals them. This is the Concordia game-master pattern, without the dependency (§3.4 still applies: a plain Python loop).
- **An agent turn is a `DecisionSpec` with a chunk size of 1**, run by `run_decision` on the existing `run_chunks` thread pool. On rented GPUs the worker count goes up. There is no asyncio rewrite, and results are applied in id order.
- **The constitution is an overlay on the config.** Every phase reads institutional parameters from `TickContext.config` (`run_polity_simulation.py:731`); there are about 100 such reads. Each tick sets `context.config = effective_config(base, state.constitution)`, built with `dataclasses.replace` and checked by `validate_config` (`config.py:1180`). The checkpoint keeps hashing the *base* config, and the constitution state lives in `TickState`. This supersedes ADR-008's `ActiveLaws`, because no call site has to learn about laws.
- **Agent memory is a view over the journal.**
  - A tap on `Journal.write_event` (`journal.py:104`, the single write point) feeds a deque per agent: the events that concern them, plus their own `agent_turn` and `agent_reflection` events.
  - On resume, the deques are rebuilt in one pass over `events.jsonl`, which resume has already truncated.
  - So there are no sidecar files and no new checkpoint fields, and the explorer gets agent diaries for free.
- **Personas are a template** rendered from numeric traits: top named priorities, lean per issue, tolerance (`blank_threshold`), ambition, party, and a name drawn from a list. There is no LLM call and no cache. The numbers remain the kernel's source of truth.
- **The crowd is deterministic** in the exploration profile. It uses `utility_ballot`, `deterministic_pressure_action` (`simple_rules.py:541`) and `form_coalition` (`simple_rules.py:487`). The GPU goes to agents only. The LLM crowd stays available as a comparison arm.
- **The limit-testing log** is the `other_initiative` field of `agent_turn` events: things agents tried that the menu does not offer. It is read with a filter. It is data about the system's limits, and it decides which mechanisms later phases build.

---

## 4. Roadmap

Each row is one PR, small enough for the 100% diff-coverage gate.

### Phase 0: Foundations

| PR | Deliverable |
|---|---|
| 0.1 | **Root-cause fix for backlog #1, in one place.** `_complete_and_decode_with_replay` gains a `validate` parameter checked *inside* its retry loop. Its 7 callers (`llm_behavior_engine.py` L1100, 1715, 2289, 2838, 3263, 4810, 5449) pass the validators they currently run after the fact. Invalid answers then get the retries that already exist. |
| 0.2 | *Folded into Phase 1 (2026-09-27).* Nothing consumed it yet: the profile arrived with 1.1's first knob (as `--profile exploration`), the `llm.temperature == 0` relaxation (`config.py:1110`) with 1.2's agents, and the valid-action rate is already `1 − fallback_by_type / decisions_by_type` in `progress.json`. |

**Rented GPU runbook** (no code):
1. On the rented box, start vLLM with the same compose file, bound to `127.0.0.1`.
2. Locally, run `ssh -N -L 8000:127.0.0.1:8000 <box>`.
3. Run as usual. `run_provenance` records the docker fields as unknown.

Never expose vLLM publicly: it has no auth. Spot preemption is covered by `--resume`.

**Exit:** chamber unit fallback below 1% on a 2-year p200 run, and one tunnelled rented smoke run completes.

**0.1 result** (PR #679, 2026-09-27): on 2-year runs, the p500 / 75-seat / seed-42 run left 0 of 675 chamber units on fallback, against 45–50 of 600 (7.5–8.3%) in the same 8 ticks of the three full runs; its 13 shift-cap rejections were all rescued by a retry. The p200 run left 0 of 1,007 decisions on fallback. The rented smoke run waits for a rented GPU.

### Phase 1: Leaders and popularity

| PR | Deliverable |
|---|---|
| 1.1 | **Close the loop, no LLM** (PR: `feat/polity-approval-polls`). `legitimacy.approval` is the share of citizens whose utility ballot would rank the president above blank, judged on their *conduct* (`revealed_position`) and the term's policy, without the record term. `legitimacy.approval_weight` blends it into the support `update_legitimacy` takes (`legitimacy.py:89`; 0 reproduces today's behaviour), and it rides on `legitimacy_updated` as an optional `approval` field, not a new event. `candidacy.incumbent_keeps_record` runs a former president on their conduct. `run_polity_flagship.py --profile exploration` turns these on with `vote.approval` 0.1, `policy_retrospection` 2 and legislation. Vote-intention polls move to 1.4, which is the step that reads them; the approval curve in `MacroCurves` is 1.1b. |
| 1.1b | **Explorer.** `run_macro` reads `approval` from `legitimacy_updated`; `MacroCurves` draws it beside L(t). |
| 1.2 + 1.3 | **The president agent, one PR** (`feat/polity-president-agent`; the runtime alone would have had no user). `agents.py`: named issues, a template persona with each lean in words, `AgentMemory` as a view over the journal (`Journal.tap`, rebuilt on resume, never checkpointed), the English prompts, `validate_turn` and `decide_turn` on the replay helper. `_phase_leaders` runs before legislation: the turn names target `positions` (the kernel steps toward them) in place of `representative_response` (skipped for an agent president), and a target `bill` in place of `_draft_bill` when the agenda is the president's. New `agent_turn` event (with `other_initiative`, the limit-testing log), `bill_proposed.drafted_by`, config `agents.president`. ADR-014. Deferred: reflection calls (the agent's own `note_to_self` carries continuity) and a turn temperature above 0, since added as `agents.turn_temperature` (0.6 in the exploration profile, sent with a seed); it does not stop a president with nothing to do from repeating itself (OBS-028). |
| 1.4 | **Nominee campaign turns, with a vote-intention poll** (`feat/polity-nominee-agents`). With `agents.nominees`, every presidential nominee campaigns in one turn, in parallel, seeing the `vote_intention_poll` (first choices of every citizen's utility ballot over the field, journaled) and naming target positions the kernel steps toward within `campaign.max_positioning_*`. It replaces `campaign_positioning` for nominees, under the agents' thinking cap (OBS-022's runaway cannot happen on this path). The turn functions take the decision type and position limit, so president and nominee share them. No memory for nominees yet: a campaign comes every four years. |
| 1.5 | **Explorer.** A leader diary in `CitizenBiography`, from `agent_turn` events. |

Coalitions in the profile use `form_coalition`, and the collapsed LLM type stays off.

**Exit:**
- Valid-action rate at least 95% after retries.
- The agenda moves toward the median when approval is low or an election is near, in at least 2 of 3 seeds.
- Approval standard deviation across terms above 0.05.
- Low-approval incumbents lose more often.
- Wall clock at most 1.5 times the baseline.

### Phase 2: Constitution kernel

| PR | Deliverable |
|---|---|
| 2.1 | **The constitution kernel** (`feat/polity-constitution-kernel`, ADR-015). `config.ARTICLES` (7 articles, each a config path with a list or a range), `constitution.py` (`in_force`, `amend`), `TickState.constitution` (version and values, checkpointed only once amended), `_phase_constitution` first in the tick, a `constitution_amended` event (institutional: on the timeline), and scripted amendments in config, checked against their article and against every rule after each. A Hypothesis property runs any legal constitution. |
| 2.2 + 2.3 | **The amendment procedure and who proposes** (`feat/polity-amendment-procedure`, ADR-015). `constitution.amendment_threshold` is an article (8 now), with per-article entrenchment (`constitution.entrenched`). The procedure in force *when an amendment is proposed* governs it: the threshold is stored in the pending `Proposal`. The president proposes one amendment per turn (an optional `amendment` on their turn); the next tick each member of the sortition chamber votes yes or no in a turn of their own (`amendment_vote`, a new decision type, run in parallel and blind to each other), and it is ratified when strictly more than the threshold of all members voted yes (a failed turn counts against). Ratification is a `constitution_amended` event with source `vote`. `agents.amendments` is ON in the exploration profile. |
| 2.4 | **Reporting** (`feat/polity-constitution-reporting`). Each row of the digest's `population_impact_by_year` carries `constitution_version` (the constitution in force at the year's end) and `amendments` (proposed, ratified, rejected). The three amendment events sit on a new *Constitution* lane of the explorer's institutional timeline. |

**Initial articles:** only those read at election or rotation time, so the clock does not change: `presidential_method` (13 ranked methods), `president_term_limit`, seat allocation, electoral threshold, assembly seats, petition threshold, recall floor, and the amendment threshold.

**Exit:** an LLM-proposed amendment is ratified in at least 50% of seeds; at least 4 distinct articles are proposed across 10 seeds; zero invariant violations.

### Phase 3: Citizen agents and the public sphere

| PR | Deliverable |
|---|---|
| 3.1 + 3.2 | **The forum** (`feat/polity-citizen-agents`, ADR-016). The agent set is derived from the journal rather than promoted: the sortition chamber's members and the citizens who launched a petition in the last 8 ticks (`agents.forum_size` caps them). Each takes one turn a tick, in parallel and blind, and posts or stays silent (`forum_post` event). The feed is the last 8 posts of their graph neighbours, the president and nominees, and, for a chamber member, the other members. No promotion counter, `agents.max_full` or checkpoint field: the window runs out by itself. |
| 3.3 | **Opinion change** (`feat/polity-opinion-change`, ADR-017). No separate reflection turn: the forum turn returns a `shift_issue` and `shift_direction`, the kernel moves the speaker `agents.stance_step` along that issue's latent loading, and ADR-012 dynamics are ON in the exploration profile, so the move reaches the crowd through the graph with no new code. |
| 3.4 | **Explorer** (`feat/polity-forum-reader`). Forum posts join the citizen biography's turns section (`post`, and `shift` in words when the speaker changed their mind). The chamber members, who all speak, are already marked on the map, so a click reaches their posts. A run-level forum panel (all posts of a tick) is not built: add it when reading citizen by citizen proves too slow. |

**Exit:**
- Agents exposed to counter-arguments shift more than unexposed ones.
- The ratio of distinct posts stays high (no forum collapse).
- Token use stays within budget, with 1 post per agent per tick.

### Phase 4: Parties, initiatives, exit

| PR | Deliverable |
|---|---|
| 4.1 | **Mutable party membership** (ADR-018, built). A forum turn may `join`, `leave` or `found` a party (the co-founder share `parties.founding_ratio` is an article), and a party under half of it is dissolved. The party leader's `party_leader_turn` (moving a platform) is not built: nothing yet shows it is needed. |
| 4.2 | **Coalition negotiation between leaders** (ADR-019, built). `decide_coalition` takes a `negotiation` callable; `agents.negotiate_leaders` gives each party's leader (its most ambitious member, derived, no stored field) one turn a round, blind, and stops on the crowd's `_negotiation_converged` rule. ON in the exploration profile when the LLM is. |
| 4.3 | **Referendum** (ADR-020, built). `constitution.referendum` (`never`, `petition`, `always`) lets the citizens confirm a voting-method change the chamber ratified: the last election's ballots are re-counted under both methods and each citizen votes for the winner they ranked higher. In `petition` it is held when the citizens who would vote no reach the petition threshold. Agents do not vote in it; other articles are not referred. |
| 4.4 | **An `engagement` field** (ADR-021, built): `active`, `disengaged` or `exited`, moved by the citizen's anger with hysteresis (`emotions.disengage_anger`, `return_anger`, `exit_anger`). A disengaged or exited citizen abstains and signs nothing; `exited` is final and a state, not a deletion, because `apply_dynamics` requires ids equal to `range(n)` (`opinion_dynamics.py:92`). |

**Exit:** the party count changes in at least 30% of seeds, and the effective number of parties stays within 1.5–8. **Measured 2026-10-02 (OBS-034), met**: on three 8-year seeds the count changes in 3 of 3, plateaus at 21–23 parties by about year 4, and the seat-based effective number falls from 9.6–10.6 at the first legislative election to 5.8–8.5 at the second (mean 7.29) as the electoral threshold excludes the small parties. Ten seeds are still owed for a result claim.

### Phase 5: Extra-legal acts

**5.1 (ADR-022, built): `refuse_to_leave`.** Only the act the log points at (presidents proposing to lift the term limit); resolved with `regime_rng`, loyalty a constant, recalls suspended while irregular. `postpone_election`, `insurrection`, the drift of Λ and the way out of an irregular regime are still to do.

**Which acts.** Build first the acts that agents actually attempted in the limit-testing log. The likely ones are `refuse_to_leave`, `postpone_election` and `insurrection`. Each act has a severity σ.

**Resolution.** The kernel resolves each act with a new seeded `regime_rng`:

```
P(success) = logistic(a·(S − 0.5) + b·(Λ_for − Λ_against) − c·σ)
```

- S is support: approval for a leader's act; anger plus street pressure for an uprising.
- Λ is institutional loyalty, a single scalar starting at 0.8. It drifts with legitimacy and with constitutional churn.

**Aftermath.**
- On success, `regime` becomes `irregular` and recalls are suspended.
- An irregular regime ends either through a constituent process (Phase 2 plus the Phase 4 referendum) or through a counter-uprising.
- On failure, the author is removed from office and barred from holding it again.

ADR-022 (5.1) is the first of this phase; ADR-018 to ADR-021 cover 4.1 to 4.4 (mutable parties, leaders' coalition talks, referendum, engagement).

### Observatory

There is no separate phase: each phase ships its own explorer view. Ensembles reuse `run_polity_seed_sweep.py` and `sweep_statistics.py`. The run narrator gains an "emergent behaviours" section once the limit-testing log has content.

---

## 5. Deliberately left out, and when to add each

| Left out | Add when |
|---|---|
| Role router, multi-model runs | The comparison runs show leaders need a bigger model than citizens |
| API-key auth on the client | A run cannot go through an SSH tunnel |
| Per-unit fallback, repair prompt | Fallback stays above 1% after 0.1 |
| A `satisfaction` module | Never: `approval × record` and `policy_gain` already live in `utility_ballot` |
| LLM-written persona biographies | Agents' speech is visibly samey |
| Scored memory retrieval, embeddings | Diaries show agents forgetting what matters |
| Persona and memory sidecar files | Never: memory is a view over the journal |
| New bake-off families | Short-run comparisons are ambiguous |
| A term-length article and clock anchors | Agents try to amend the term length |
| Chamber members proposing amendments | The president-only proposals show that the chamber never initiates |
| Cardinal ballots (score and approval methods as articles) | Agents propose approval or score voting |
| Refuse-to-average across constitution versions | The first ensemble spans amendments |
| DMs, party caucus, evolving graph, party merge, primaries, online referee, novelty metric | The logs show demand |
| Fixed factor loadings for named issues | Templated personas read as incoherent |
| Separate ADRs for the exploration gate and rented inference | Never: they are D4, D5 and D9 above |

---

## 6. Models and cost

**Estimated volume.** A 30-year run with 100 agents needs about 27k calls, 95M prompt tokens (about 40M not served from the prefix cache) and 11M output tokens. The current full run needs 20.3k calls, 20.6M and 4.3M. These are estimates, to be measured in the Phase 0 smoke run.

| Tier | Hardware | Model class | 30-year run |
|---|---|---|---|
| Dev | local RTX 5070 Ti, 16 GB | 8B | too slow at full size; use 20 agents × 8 years |
| Standard | 1×H100 80 GB | 8B, or a 30B-A3B-class MoE in FP8 (~420k-token KV pool) | ~1.5–3 h |
| Flagship | 2×H100 | 70B class | ~4–5 h |

At about $2–3 per GPU-hour, a run costs roughly $5–25. **Choosing a model:** run the same 8-year exploration config on 2–3 candidates, taken from `tech-radar.md` at the time (TR-002 watches Qwen4), and compare the digests.

---

## 7. Science under non-determinism

**Kept:**
- typed events, the call log with prompts, and `ReplayClient`;
- the OBS log;
- pre-registration for any claim stated as a result.

**Added:** an `agent_prompt_version` stamp in run metadata. OBS-019 showed that a prompt change alone moved recalls from 6 to 44, so prompt versions are experimental variables.

**Claims:** a claim needs at least 10 seeds and 2 prompt variants, with ablation arms (agents off, approval loop off). A single run is a case study, never evidence.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Persona collapse: every agent drifts to a sensible centrist | The Phase 1 exit criteria measure directional responses; add LLM persona biographies if templates are too thin |
| Prompt sensitivity dominates the macro picture | Prompt-variant ensembles |
| Token blow-up from conversations | Hard per-tick caps; the digest's token totals |
| Named issues import real-world priors | Declared as a confound |
| Degenerate self-amendment (thresholds amended to nothing) | Article domains and entrenchment; anything beyond is an extra-legal act |
| Spot preemption on rented GPUs | `--resume` already exists |
