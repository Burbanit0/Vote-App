# Glossary

> **status:** reference. Part of the [project overview](README.md). Verified against `polity` at
> `ce0e674` (2026-10-12). Paths are relative to the repository root; `polity/` stands for
> `fast_api_voter/api/domain/polity/`.

Every term the project uses, with what it means here and where it lives. French words appear where
the interface or the design documents use them. Two other lexicons exist and stay authoritative for
their scope: the in-app glossary shown to visitors (`voter-app/src/lib/glossary.ts`, rendered by
`Term.tsx` and the Laboratoire's *lexique* fiche), and the French↔code bridge for Polity's design
documents ([`polity-llm-reference.md` §1](../plan/polity/polity-llm-reference.md#1-lexicon)).

**Sections:** [Methods](#methods) · [Social-choice concepts](#social-choice-concepts) ·
[Spatial and profile model](#spatial-and-profile-model) · [Metrics](#metrics) ·
[Vote Lab interface](#vote-lab-interface) · [Polity model](#polity-model) ·
[Polity institutions](#polity-institutions) · [Polity agents and the model](#polity-agents-and-the-model) ·
[LLM infrastructure](#llm-infrastructure) · [Research and process](#research-and-process) ·
[Decision labels D1…D11](#decision-labels-d1d11)

## Methods

The client's 29 rule ids (`Rule` in `voter-app/src/lib/playgroundVoting.ts`); the backend's names
are in `fast_api_voter/api/engine/utils/method_registry.py`. Definitions and sources are in
[`THEORY.md`](../../THEORY.md) §2 and [`research/traceability.md`](../research/traceability.md).

| Id | Method | In one line |
|---|---|---|
| `plurality` | Plurality (first past the post) | Most first-place votes wins |
| `two_round` | Two-round runoff | Top two go to a second round unless one has a majority |
| `irv` | Instant-runoff (alternative vote) | Eliminate the fewest first places, transfer, repeat |
| `borda` | Borda count | Points by rank: m−1 for first, …, 0 for last |
| `approval` | Approval | Approve any number; most approvals wins |
| `condorcet` | Copeland (backend `copeland`) | Most pairwise wins |
| `minimax` | Minimax | Smallest worst pairwise defeat |
| `schulze` | Schulze (beatpath) | Strongest paths in the pairwise graph |
| `bucklin` | Bucklin | Add lower ranks until someone has a majority |
| `coombs` | Coombs | Eliminate the most last places |
| `nanson` | Nanson | Eliminate everyone below the Borda average, repeat |
| `baldwin` | Baldwin | Eliminate the lowest Borda score, repeat |
| `ranked_pairs` | Ranked pairs (Tideman) | Lock pairwise wins by strength, skipping cycles |
| `kemeny` | Kemeny-Young (backend `kemeny_young`) | The ranking that disagrees least with the ballots |
| `black` | Black | Condorcet winner, else Borda |
| `anti_plurality` | Anti-plurality (veto) | Fewest last places wins |
| `dowdall` | Dowdall (Nauru) | Points 1, 1/2, 1/3… by rank |
| `raynaud` | Raynaud | Eliminate the candidate with the worst pairwise defeat |
| `benham` | Benham | IRV, stopping as soon as a Condorcet winner exists |
| `river` | River | Like ranked pairs, each candidate defeated at most once |
| `smith_irv` | Smith-IRV (Tideman's) | IRV restricted to the Smith set |
| `split_cycle` | Split Cycle (Holliday & Pacuit) | Discard the weakest defeat in each cycle |
| `random_ballot` | Random ballot (lottery) | One ballot drawn at random decides. Not parity-locked |
| `star` | STAR | Score, then an automatic runoff between the top two |
| `majority_judgment` | Majority judgment | Grades; highest median grade wins |
| `score` | Score (range) | Highest total score |
| `cumulative` | Cumulative | Spread a budget of points |
| `maximin` | Maximin (utility) | Best worst-off voter |
| `nash` | Nash | Highest product of utilities |

Backend-only score rules: `median_voting`, `mean_median_hybrid`, `variance_based`
(`simulation_score_utils.py`). **Multiwinner:** SPAV, Phragmén, STV (single transferable vote),
equal shares (`simulation_multiwinner_utils.py`). **Seat allocation:** D'Hondt, Sainte-Laguë,
largest remainder (Polity's `institutions.seat_allocation`). **Threshold:** the minimum vote share a
party needs to win seats.

## Social-choice concepts

| Term | Meaning | Where |
|---|---|---|
| Condorcet winner | Beats every other candidate head to head | `playgroundVoting.ts`, `simulation_metrics.py` |
| Condorcet loser | Loses to every other candidate head to head | Criteria registry |
| Condorcet cycle | A beats B, B beats C, C beats A; no Condorcet winner | `profile_engine.py::cycle_rate` |
| Smith set | Smallest set of candidates who each beat everyone outside it | `playgroundVoting.ts` |
| Spoiler | A losing candidate whose presence changes the winner | `glossary.ts` |
| Criterion (axiom) | A property a method may satisfy: majority, monotonicity, participation, IIA, reversal symmetry, strategy resistance, Condorcet winner, Condorcet loser | `voter-app/src/data/method_criteria.json` |
| Monotonicity | Ranking the winner higher never makes them lose | Criteria registry |
| Participation | Voting sincerely never gives a worse result than abstaining | Criteria registry |
| IIA | Independence of irrelevant alternatives: removing a loser never changes the winner | Criteria registry |
| Arrow's theorem | No ranked method satisfies a short list of fairness conditions at once | THEORY.md §3 |
| Gibbard–Satterthwaite | Every non-dictatorial method with 3+ candidates can be manipulated | THEORY.md §3, `gibbard_satterthwaite.py` |
| Sincere vote | Ballot that reports true preferences | `playgroundSincerity.ts` |
| Compromise ("vote utile") | Ranking a more viable candidate above your favourite | `playgroundSincerity.ts` |
| Burying | Ranking a strong rival below candidates you like less | `playgroundSincerity.ts` |
| Pivotality | Chance that one ballot changes the outcome | `glossary.ts` |
| Blank vote (*vote blanc*) | A ballot for none of the candidates; in Vote Lab and Polity it can count and even win | `lib/blankVote.ts`, `blank_vote_rules.py`, `polity/citizen.py` |
| Tie lot | Exact ties broken by a seeded hash (FNV-1a), never by listing order, identically on both engines | `tie_lot.py`, `tieLot.ts`, [`LISTING_ORDER_TIES.md`](../plan/vote-app/LISTING_ORDER_TIES.md) |

## Spatial and profile model

| Term | Meaning | Where |
|---|---|---|
| Spatial model | Voters and candidates are points in an ideological space; nearer is preferred | THEORY.md §1.2 |
| Dims | 1, 2 or 3 ideological dimensions | `playgroundVoting.ts` (`Dims`) |
| Utility | −distance + valence (Vote Lab); −priority-weighted distance (Polity) | `playgroundVoting.ts`, `polity/simple_rules.py` |
| Valence | A candidate's quality apart from ideas, added to every voter's utility | `glossary.ts`, `profile_engine.py` |
| Electorate, community | A mixture of communities, each with a centre, spread, size and turnout propensity | `lib/playgroundElectorate.ts` |
| Preference profile | Every voter's utility for every candidate; what every method reads | `profile_engine.py` (`UtilityMatrix`) |
| Profile generators | spatial, single-peaked, impartial culture (IC), IAC, Mallows, Pólya urn, Plackett-Luce and others | `profile_engine.py::build_profile` |
| Ballot projection | Turning utilities into a ranking, scores, grades or approvals | `profile_engine.py::project_ballot` |
| Turnout model | full, alienation (too far from everyone), indifference (no difference between candidates) | `playgroundVoting.ts::applyTurnout` |
| Win region | Map of which candidate would win at each position | `playgroundVoting.ts::winRegionGrid` |
| PCA embedding | 2D projection of a non-spatial profile for display | `engine/utils/pca.py` |

## Metrics

| Term | Meaning | Where |
|---|---|---|
| VSE | Voter satisfaction efficiency: (E[u(winner)] − E[u(random)]) / (E[u(best)] − E[u(random)]) | `lib/playgroundBehavior.ts` |
| Bayesian regret | Expected utility lost against the utilitarian best | `simulation_metrics.py::bayesian_regret` |
| Condorcet efficiency | Share of electorates with a Condorcet winner where the method elects them | `lib/scorecard.ts` |
| Scorecard | Leader-mode axes, each over Monte-Carlo re-rolls with a band: Condorcet efficiency, strategic resistance, welfare, majority satisfaction, simplicity, stability | `lib/scorecard.ts`, `Scorecard.tsx` |
| Parliament axes | Proportionality, pluralism, effective votes, minority representation, governability, gerrymander resistance | `lib/playgroundMeta.ts` |
| Gallagher index | Disproportionality between vote shares and seat shares | `glossary.ts` |
| Effective number of parties (NEP) | Laakso–Taagepera: 1 / Σ share²; in Polity, reported per election | `playgroundMeta.ts`, `polity/metrics.py` |
| Values lens, Pareto frontier | Remove the dominated methods, then let weights highlight one of the rest; never a ranking | `lib/scorecard.ts` |
| Robustness | How often the same winner returns over re-drawn seeds | `lib/playgroundRobustness.ts` |
| Equilibrium | Whether the sincere winner survives iterated better-response voting | `lib/playgroundEquilibrium.ts` |
| Manipulability | How often a coalition can change the result by voting insincerely | `gibbard_satterthwaite.py`, `/api/v2/simulations/manipulability` |

## Vote Lab interface

| Term | Meaning | Where |
|---|---|---|
| Surface | One of the six real pages | `voter-app/src/routes.ts` |
| Playground | The single live instrument | `components/playground/`, [ADR-006](../adr/ADR-006-playground-single-five-moment-instrument.md) |
| Moment | A step of the playground's rail: Électorat, Méthode, Stratégie, Campagne, Bilan | `components/playground/moments/` |
| Dirigeant / Assemblée | Electing one leader, or an assembly | `PlaygroundController.tsx` (`mode`) |
| Bilan | The last moment: how good each method was and why winners differ | `BilanMoment.tsx` |
| Winner strip | Every enabled method's winner, shown at every step | `WinnerStrip` |
| Map lens | What the playground map colours by | `useJourneyCtx` |
| Story | A scripted scenario that drives the playground (`?story=`), its claims checked against the engine | `lib/stories.ts`, `storyClaims.ts` |
| Laboratoire, fiche, établi | The lab; one experiment in it (63, in 6 families); the bench a fiche opens on | `components/lab/labCatalog.tsx` |
| Découvrir, À vous de jouer | The guided introduction; the hands-on challenges | `pages/` |
| Static build | The site with the engine in the browser (Pyodide), no server | `npm run build:static`, `api/browserEngine.ts` |
| Pyodide | Python compiled to WebAssembly; runs the backend's routers inside a Web Worker in the static build | `api/browser.py`, `workers/engine.worker.ts`, [EXP-023](../exploration/EXP-023-pyodide-web-worker-vs-fly-container.md) |
| Form lock | Performance invariant: typing in a form must not recompute the instrument | [EXP-005](../exploration/EXP-005-form-lock-profiler-invariant-and-bundle-budget.md), `voter-ui` skill |

## Polity model

| Term | Meaning | Where |
|---|---|---|
| Polity | The society simulator | [`polity.md`](polity.md) |
| Kernel | The deterministic engine that validates, applies and journals every decision | `run_polity_simulation.py` |
| Tick | One quarter; 4 per year | `polity_config.yaml` (`run`) |
| Tick phase | One of the 14 steps of a tick | `TICK_PHASES`, [`polity-llm-reference.md` §2.3](../plan/polity/polity-llm-reference.md#23-the-per-tick-sequence) |
| Run | One simulated history, with its seed and config, in one run directory | [`polity.md` §5](polity.md#5-what-a-run-leaves-behind) |
| Seed, RNG streams | One seed; a fresh generator per concern (rupture, events, sortition; dynamics, campaign, regime when on; population and graph at setup) | `polity/tick_state.py` |
| Profile (flagship, exploration) | Which mechanisms a run turns on; exploration adds the agency mechanisms | `scripts/run_polity_flagship.py` |
| Deterministic engine, twin | Rule-based version of every model decision; a twin run is the same society without the model | `polity/simple_rules.py`, `scripts/twin_runs.py` |
| Citizen (*citoyen*) | One member: 20 issue positions, priorities, blank threshold, ambition, awakening threshold, role, office, party | `polity/citizen.py` |
| Issue position, priority | A view on one of 20 issues, in (0,1); how much that issue matters | `polity/citizen.py` |
| Factor structure | Positions drawn from two latent factors plus noise, not uniformly | `polity-llm-reference.md` §2.1 |
| Role, office | voter, candidate, elected; none, president, deputy | `polity/citizen.py` |
| Ambition, ambition threshold | Drive for office, `beta(2,8)`; on the deterministic path a citizen above 0.30 may stand (the LLM candidacy path does not read the threshold: ADR-002, [OBS-011](../plan/polity/observations.md#obs-011)) | [ADR-002](../adr/ADR-002-ambition-threshold-blocks-candidacy.md) |
| Blank threshold | Distance beyond which a candidate ranks below Blank | `polity/citizen.py` |
| Static population | Nobody is born or dies during a run | `citizens.static_population` |
| Pledged platform, revealed position | What a candidate promised (fixed for the term); where they actually stand (drifts) | `polity/citizen.py` |
| Mandate deviation | Distance from promise to current position | `polity/indexer.py` |
| Mandate strength (m) | The officeholder's support at election, revised by a won confidence vote | `polity/legitimacy.py` |
| Legitimacy L(t) | Officeholder's standing in [0,1]: decay · L + support − écart | `polity/legitimacy.py` |
| Écart | The pressure term (petitions, street pressure) that erodes legitimacy | `polity-llm-reference.md` §1 |
| Awakening (*éveil*) | The gate that decides **who** is consulted about pressure, never what they decide | `awakening` config |
| Contagion (`neighbors_acting`) | An awakening mode where neighbours who act lower a citizen's bar | `awakening.context_modulation` |
| Pending rerun | The state between an invalidated (Blank-won) election and its rerun; the regular calendar is suspended meanwhile | `PendingRerun`, `run_polity_simulation.py` |
| Pressure action | A consulted citizen's act: wait, sign a petition, mobilise… (`dt=10`) | `llm_behavior_engine.py` |
| Petition, signature threshold | A drive that calls a confidence vote when enough sign | `petition` config, `accountability.py` |
| Street pressure | Accumulated mobilisation, decaying each tick | `street_pressure` config |
| Confidence vote, keep ratio | Citizens vote to keep the president; the share who do | `accountability.py` |
| Recall, legitimacy floor | Removal; the floor is the L(t) below which it is triggered | `accountability.py`, [ADR-025](../adr/ADR-025-majority-recall.md) |
| Snap election | Election held because the presidency fell vacant | `_phase_snap_election` |
| Exogenous events | Scandals (Poisson), an economic shock (AR(1)), event salience | `polity/shock.py`, `polity/salience.py` |
| Social graph | Watts–Strogatz small world linking citizens | `polity/social_graph.py` |
| Opinion dynamics | Friedkin–Johnsen update with bounded confidence | `polity/opinion_dynamics.py`, [ADR-012](../adr/ADR-012-dynamic-citizens.md) |
| Emotions | Anger, anxiety, enthusiasm, with decay | `polity/emotions.py` |
| Engagement | active, disengaged or exited, moved by anger | [ADR-021](../adr/ADR-021-engagement.md) |
| Abstention, turnout cost | Not voting when no candidate is worth it | `vote.turnout_cost`, [ADR-011](../adr/ADR-011-utility-vote-with-turnout.md) |
| Strategic (wasted-vote) voting | Deserting a party below the threshold | [ADR-024](../adr/ADR-024-strategic-voting.md) |

## Polity institutions

| Term | Meaning | Where |
|---|---|---|
| Institutional clock | Election, campaign and rotation calendar | `polity/institutional_clock.py`, [ADR-010](../adr/ADR-010-phase-clock-and-campaign-windows.md) |
| Mid-term elections | Legislative elections offset 2 years from presidential ones | `institutions.assembly_offset_years` |
| Staggered election | Presidential declaration and nomination spread over several ticks (Track E), not the mid-term offset | `institutions.staggered_election` |
| Term limit, lame duck | At most 2 presidential terms; an officeholder who cannot run again | `institutions`, `agents.py` |
| Candidacy, nomination, contested party | Declaring; the party choosing among declared members; a party with 2+ declared | `candidacy_considered`, `party_nomination_choice` |
| Rupture candidacy | Running against your own party | `_phase_rupture_candidacies` |
| Campaign window, campaigning | The ticks before an election; a nominee raising an issue's salience | [ADR-023](../adr/ADR-023-campaigning.md) |
| Vote intention poll | First choices shown to nominees during a campaign | `vote_intention_poll` event |
| Utility vote, audit sample | Deterministic ballots; the model votes for a 10% sample, journaled with `audit: 1` | [ADR-011](../adr/ADR-011-utility-vote-with-turnout.md) |
| Blank-vote invalidation, rerun | An election Blank wins is invalidated and run again | `pending_rerun`, `polity-llm-reference.md` §5.1 |
| Coalition, formateur | Parties forming a majority; leader negotiations in rounds | [ADR-019](../adr/ADR-019-leader-coalition.md) |
| Cohabitation | President and assembly majority from different sides; the president can block a bill | `legislation.py` |
| Bill, policy status quo | Ordinary legislation moving at most 2 issues | [ADR-009](../adr/ADR-009-ordinary-legislation.md) |
| Sortition chamber | Randomly drawn, yearly, never re-elected (the control group), with a suspensive veto | `polity/sortition_chamber.py` |
| Constitution, article, entrenchment | The rules in force: 10 amendable config paths; entrenched articles need more | `polity/constitution.py`, `config.ARTICLES`, [ADR-015](../adr/ADR-015-typed-constitution.md) |
| Amendment, amendment threshold | A rule change the president proposes and the chamber ratifies | `polity/amendments.py` |
| Amendment stakes | Briefing showing what a rule change would have done (past ballots recounted, seats reallocated) | [ADR-026](../adr/ADR-026-amendment-stakes.md) |
| Forward stakes | Methods weighed on the next election's ballots, not the last | [ADR-027](../adr/ADR-027-forward-method-stakes.md) |
| Referendum | Citizens confirm a voting-method change | [ADR-020](../adr/ADR-020-referendum.md) |
| Extra-legal act, refuse to leave, regime | An act outside the rules, rolled by the kernel; an irregular regime suspends recalls | `polity/regime.py`, [ADR-022](../adr/ADR-022-extra-legal-acts.md) |
| Law system | The designed but unbuilt seam for laws | [ADR-008](../adr/ADR-008-law-system-seam-bounds-and-comparability.md) |

## Polity agents and the model

| Term | Meaning | Where |
|---|---|---|
| Crowd | Citizens decided in batches by the model, in the third person | `llm_behavior_engine.py` |
| Agent tier, agent | Citizens the model plays in the first person: president, nominees, forum speakers, party leaders | `agents.py`, [ADR-014](../adr/ADR-014-agent-tier.md) |
| Turn | One agent decision: president turn, nominee turn, amendment vote, forum post, coalition turn | `agents.py` |
| Persona | Text rendered from an agent's numeric traits (no model call) | `agents.py::persona` |
| Agent memory | An agent's own past turns, rebuilt from the journal on resume | `agents.py` (`AgentMemory`) |
| President goal | Set by ambition band | `agents.py::president_goal`, [ADR-028](../adr/ADR-028-ambition-shapes-the-presidents-goal.md) |
| Party leader | A party's most ambitious member, derived, not stored | `agents.py::party_leader` |
| Forum, forum post | Where chamber members and recent petitioners post | [ADR-016](../adr/ADR-016-forum.md) |
| Stance shift | A forum turn moving its speaker's view | [ADR-017](../adr/ADR-017-opinion-change.md) |
| Join, leave, found, dissolution | Party moves; founding needs co-founders; a too-small party is dissolved | [ADR-018](../adr/ADR-018-mutable-parties.md) |
| `founding_ratio` | Share of citizens who must co-found a party (0.05); a party below half of it can be dissolved | `polity_config.yaml` (`parties`), [ADR-018](../adr/ADR-018-mutable-parties.md) |
| Decision type (`dt=N`) | The project's numbering of crowd decisions (1 vote … 11 chamber); not sequential | `codebook.py` (`DecisionType`) |
| Motif | Closed-enum reason code attached to every decision, banded by family (1xx vote, 2xx candidacy…) | `codebook.py` |
| Codebook | The motif and act enums and their version | `codebook.py` |
| DecisionSpec, chunk | One crowd decision type's prompt, schema and decoder; a batch of citizens per call | `llm_behavior_engine.py` |
| Fallback (`llm_fallback`) | The deterministic answer used when the model fails, flagged in the journal | `polity-llm-reference.md` §4.4 |
| Content-blind collapse | A decision whose answer does not depend on its input: the model returns the same code whatever it is shown | [`polity-llm-reference.md` §9](../plan/polity/polity-llm-reference.md#9-what-is-actually-trustworthy) |
| Comparison arm | The deterministic baseline every LLM decision is compared against (design §11.4) | `simple_rules.py` |
| Retry, batch replays | Resampling a failed batch at temperature 0.3 with an offset seed | `polity-llm-reference.md` §4.4 |
| Journal, event | The typed event log of a run; one event per institutional fact or decision | `polity/journal.py`, `polity/events.py` |
| Digest | Structured account of a run, written at every ending | `polity/run_digest.py` |
| Snapshot | Yearly census of the population | `snapshots.jsonl` |
| Checkpoint, resume | Saved state each tick; continuing a run from it | `polity/checkpoint.py` |
| Replay (call-log) | Re-running from the call log, byte for byte. Not the same as **batch replays** (`max_batch_replays`), which are retries | `polity/llm_replay.py`, [EXP-020](../exploration/EXP-020-replay-calls-vs-seed-determinism-full-run.md) |
| Provenance | Commit, image, GPU, prompt-file hashes recorded with a run | `polity/run_provenance.py` |
| `config_hash` | Hash of a run's configuration; resume and replay refuse a different one | `run_metadata.json` |
| Timeline claims | Checking a run story's anchored claims against its journal | `polity/timeline_claims.py`, `scripts/check_timeline_claims.py` |

## LLM infrastructure

| Term | Meaning | Where |
|---|---|---|
| vLLM | The inference server, OpenAI-compatible | `fast_api_voter/docker-compose.llm.yml` |
| Ollama | The previous server, still selectable | [ADR-001](../adr/ADR-001-serving-layer-ollama-vs-llama-server.md), `llm_client.py` |
| Qwen3-8B-AWQ | The model of every full run, 4-bit AWQ quantised | `polity/model_profiles.py` |
| Quantisation (AWQ, NVFP4, FP8) | Lower-precision weights to fit the GPU | `model_profiles.py`, compose variants |
| Model profile | Per served model: chunk sizes, context limit, thinking switch and budgets | `polity/model_profiles.py` |
| Structured outputs, xgrammar | Decoding constrained to a JSON schema | `llm_client.py`, compose `--structured-outputs-config` |
| Thinking, reasoning parser, thinking budget | Qwen3's reasoning before answering; the cap on reasoning tokens (2,048, on `vote_cast` and `chamber_deliberation`) | `llm.thinking_token_budget` |
| Think allowance | The per-call `max_tokens` room a profile gives a decision (e.g. 12000 for a vote), not the reasoning cap | `model_profiles.py` |
| Speculative decoding, EAGLE-3 | A small draft head proposes tokens the model verifies | [EXP-019](../exploration/EXP-019-eagle3-speculative-decoding.md) |
| n-gram speculation | Drafting from repeated text; rejected | [EXP-018](../exploration/EXP-018-vllm-ngram-speculation-real-traffic.md) |
| Prefix cache | Reuse of computation for prompts sharing a beginning | `polity-llm-reference.md` |
| Reproducibility (strict, relaxed) | One worker and identical regeneration, or parallel workers with replay | `llm.reproducibility`, plan-full-run D2 |
| Logprobs | The model's token probabilities, used as a measuring instrument | `polity/llm_logprob_instrumentation.py`, [`docs/preprint/`](../preprint/) |
| TOON | Compact tabular prompt encoding | `polity/llm_toon_encoding.py` |
| Bake-off | Harness comparing models and prompts on fixed cases | `polity/bakeoff_*.py`, `scripts/run_bakeoff.py` |

## Research and process

| Term | Meaning | Where |
|---|---|---|
| ADR | Architecture decision record: a binding decision and its rejected alternatives | [`adr/README.md`](../adr/README.md) |
| EXP | Experiment record: a tool or method tried, its verdict and cost | [`exploration/README.md`](../exploration/README.md) |
| OBS | Numbered observation of strange simulation behaviour, with status | [`observations.md`](../plan/polity/observations.md) |
| Run story (`TIMELINE.md`) | A run told from its digest, every claim anchored to an event | [`docs/runs/`](../runs/), `/log-run` |
| Ensemble, seed sweep | The same configuration run on several seeds | `scripts/run_polity_seed_sweep.py` |
| Phase (of the roadmap) | Stages of the agency roadmap: leaders, constitution, public sphere, parties, extra-legal acts | [`plan-polity-agency-roadmap.md`](../plan/polity/plan-polity-agency-roadmap.md) |
| Phase 4 exit | The roadmap's test for Phase 4 being done; restated by D11: the party count changes in enough seeds, and the effective number of parties is reported, not gated | Agency roadmap D11, [OBS-044](../plan/polity/observations.md#obs-044) |
| phaseN runs | The ensembles run as each roadmap step landed (phase4…phase14) | `~/Documents/Dev/polity-runs/` (not in the repo) |
| p100, p500 | Population 100 or 500 | Run names |
| p500 batch | The first batch of population-500 runs, under build-order stage S0.8 and its pre-registration | [`plan-polity-build-order.md`](../plan/polity/plan-polity-build-order.md) |
| Pre-registration | Writing the hypothesis, sample size and analysis before running | `scripts/llm_test_harness/` |
| Behaviour catalogue | Each Polity invariant with the test that locks it | [`spec/behaviors.md`](../spec/behaviors.md) |
| Parity lock, parity fixture | The test and generated file holding the two engines to the same winners | [ADR-004](../adr/ADR-004-dual-voting-engine-with-parity-lock.md), `engineParity.json` |
| `KNOWN_DIVERGENT` | The per-rule list of accepted client/backend mismatches in the parity test; empty, and meant to stay so | `playgroundVoting.parity.test.ts` |
| Criteria registry | The single list of method × criterion verdicts and their basis (E, L, L?, V) | `method_criteria.json`, [review packet](../research/expert-review-packet.md) |
| Generated doc block | Documentation rendered from the code by cog and checked in CI | `scripts/check_generated_docs.sh` |
| Gate | A check that blocks a merge | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |
| Ratchet | A quality number allowed to improve, never to worsen | `.github/quality-baseline.json` |
| Fast gate | The local subset of CI run before a push | `scripts/fast-gate.sh` |
| High-risk review gate | Owner approval (`/reviewed <sha>`) required for sensitive paths | `.mergify.yml`, `human-review.yml` |
| Lot | A section of the technical-solidity plan (Lot 0 docs … Lot 13 synthesis) | [`PLAN_SOLIDITE_TECHNIQUE.md`](../plan/vote-app/PLAN_SOLIDITE_TECHNIQUE.md) |
| W0…W6 | Workstreams of the current plan: status page, claims, Polity experiment, playground, docs, engine backlog, hosting | [`PLAN_BEYOND_CI.md`](../plan/PLAN_BEYOND_CI.md) |
| S0…S5 (stages) | Stages of the Polity build order | [`plan-polity-build-order.md`](../plan/polity/plan-polity-build-order.md) |
| v0…v8 | Versions of the Polity design | [design v2 §13](../plan/polity/polity-simulation-design-v2.md) |

## Decision labels D1…D11

Several plans number their decisions D1, D2…, and the labels collide. Always name the plan.

| Plan | Range | Examples |
|---|---|---|
| [Agency roadmap](../plan/polity/plan-polity-agency-roadmap.md) §2 | D1–D11 | D3 tiered population; D5 open weights on vLLM; D8 implicit leader goal (superseded by ADR-028); D9 agents in English; D11 Phase 4 exit restated (2026-10-10) |
| [Build order](../plan/polity/plan-polity-build-order.md) | D1–D10 | D1 replayable, not regenerable; D2 utility vote with an audit sample; D3 legislation before amendments; D6 what differs between elections |
| [Full-run plan](../plan/polity/plan-full-run.md) | D1–D6 | D1 EAGLE-3; D2 relaxed reproducibility, 12 workers; D4 seed 42; D5 emotions off |
| [PLAN_BEYOND_CI](../plan/PLAN_BEYOND_CI.md) | D1–D10 | D1 first Polity experiment; D3 documentation language; D7 the journal; D8 textbook verdict plus variant note; D9 registry location |
| [Audit precision plan](../plan/polity/audit-precision-plan.md) | D1–D9 | Design gaps; D9 is `polity_config.yaml` as single source |
| [ADR-012](../adr/ADR-012-dynamic-citizens.md) | D1–D4 | Acceptance criteria |
