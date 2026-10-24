# Scenarios v1: from a world to an instrument

> **status:** live — steps 1 (trajectory metrics, archetypes, the divergence test; #979), 1b (the crowd, live, in the engine atlas; #981) and 2 (the scenario profile; the rule-only twin fails the divergence test, the baseline for steps 3–4), 3a (the radicalisation channel, ADR-033), 3b (economic voting and scripted events, ADR-034) and 3c part 1 (cohort replacement, ADR-035) built; the model arm of step 2 still to time; 3c part 2 (rewiring) and steps 4–7 to do. (Set 2026-10-21; `docs/README.md` lists every plan.)

**What this is.** The assessment of 2026-10-21 of why the polity engine, after phases 0–5 of
`plan-polity-agency-roadmap.md`, still does not hand the researcher *different scenarios of an
electoral lifecycle*, and the direction chosen with the owner that day. It is written for the person
who runs the engine, not for a reader of the code: `docs/overview/polity.md` says what the engine
does; this says what it does not yet do, why, and what to build in which order.

**Decisions taken with the owner (2026-10-21).** The scenarios are a research instrument for the
owner, so tooling and sweeps come first and rigour as needed. The objective is **diversity and
typology**, not treatment effects: runs are compared to each other, never to a baseline arm, and
self-amendment stays on (refuse-to-average stays). The plausibility anchor is **generic European
party-system facts**, as a band a run should not leave, not a target. The first PR is step 1; ADR-031
adopts option B first; ADR-032 adopts option D; the scenario profile caps the forum at about 10
speakers per tick.

---

## 1. Where the engine stands

| Area | State | Where |
|---|---|---|
| Research question | How do electoral system, electorate, candidate strategy, pressure levers and constitutional rules interact to produce stability or instability over decades? | `polity-simulation-design-v2.md` §0 |
| "Scenario" | Never defined. | this plan, §4 |
| Institutional variety run | None: all 151 run configs on record use two-round, D'Hondt, a 5% threshold and a 0.2 floor. 13 ranked methods and 3 seat rules are usable; score methods are refused; term length is not an article; no districts. | investigation of 2026-10-21, Q8 |
| Exogenous shocks | On in the flagship and exploration profiles (scandal 0.05 per tick, AR(1) economy), but they move attention (`event_salience`) and anxiety only: never a position, never a welfare outcome. | `run_polity_flagship.py` (`_flagship_config`), `shock.py` |
| What the world produces | Nothing a citizen feels: bills move a policy vector; `policy_retrospection` has nothing to be retrospective about. | ADR-009, ADR-011 |
| Electorate | Immortal (`birth_enabled`/`death_enabled` parsed, not built), 20 issues fixed at t=0, a static graph (`evolving` refused), personas templated from numbers. | roadmap §1.2, `social_graph.py` |
| Accountability | Since ADR-025: 0 recalls in 48 runs, 0 lost confidence votes, approval never below 0.57 and moving about 0.06 per term. | ADR-031 (proposed) |
| Opinion | Friedkin–Johnsen relaxes to a fixed anchor; a forum shift keeps 3% after 8 years; chamber shifts never reach `issue_positions`. | ADR-032 (proposed) |
| What the LLM decides | Who stands, what leaders say, pressure, forum posts, amendment votes, chamber shifts; never a counted vote. On an 8-year p100 exploration run: about 37 calls a tick, the forum 495 of 1,171. | ADR-011, `plan-rented-gpu-runs.md` §4.3 |
| LLM crowd quality | Mode collapse found four times (OBS-007, 013, 045, 053); `representative_response` and `coalition_decision` collapsed since August; the 8B audit vote wrong a third of the time at the 2,048 budget. | `fit-for-inference.md`, OBS-054 |
| Calibration | ADR-009/011/012 pre-registered facts: 0 of 9, 0 of 36, 0 of 81 settings met; no comparison to a real dataset; the ENP band dropped as a gate (D11). | the ADRs, design §11 |
| Cost | 8 years, 100 citizens, exploration: 4–7 h a seed locally, about 1 h rented; the rule-based twin runs in seconds and was never validated as a proxy. | `docs/runs/`, phase logs |
| Measurement | Until this step: no polarization, no vote shares or margins, no volatility, no archetype, no distance between runs, no diversity index. | `run_digest.py` |

The short version: **the engine is a world, not an instrument.** Each mechanism shipped under a
sanity gate (does it run, does it collapse), never under a variety gate (does it produce a different
trajectory). The variety that is missing comes from a world that does not act on the polity, leaders
who face no consequence, and too few runs to see a catalogue. Only the third is a cost problem.

## 2. What is missing, ranked by how much it blocks variety

1. **A scenario is not an object and diversity is not measured.** Fixed by step 1 (§4).
2. **The world does not push back.** Shocks touch feeling, not position or welfare; nobody is born
   or dies; the issue space and the graph are fixed. Two channels close most of it: shock → position
   (§3) and policy → welfare.
3. **Leaders cannot lose** (ADR-031), so leader strategy cannot matter, so the agent tier, the
   expensive part, cannot change a trajectory.
4. **Opinion settles** (ADR-032): an electorate that relaxes to a fixed point cannot realign.
5. **The LLM is spent where it adds least.** Crowd decisions are classification of numeric vectors,
   with known collapse, at hours a seed. Its comparative advantage (text, persuasion, novelty, the
   limit-testing log) sits in the ten or so leader agents.
6. **No cheap run path, so no catalogue.** A catalogue of scenarios is a population of runs.
7. **Measurement cannot see trajectories.** Step 1.
8. **Plausibility is unchecked.** A band, not a baseline (§4).
9. **The gate is sanity, not variety** (D4). The gate from now on: *does this mechanism increase the
   diversity of trajectories across seeds without leaving the plausibility band?*

What is probably *not* missing: more prompt engineering, a bigger model, extra-legal acts, more party
mechanisms. ADR-030 and the budget experiment were well run; their effect on trajectories is nil while
the LLM vote is uncounted and leaders cannot lose.

## 3. The crowd: rule-based, dynamic, and sociologically grounded

The crowd lives by rule. A citizen who takes a role (president, nominee, party leader, chamber
member, petition launcher) is promoted to an LLM agent in the first person with a persona and a
journal memory, as ADR-014 and ADR-016 already do, and demoted when the role ends. What stops going to
the model: `candidacy_considered`, `pressure_action`, `chamber_deliberation`, `reaction_to_event`,
the uncounted `vote_cast` audit, and the collapsed `coalition_decision` and `representative_response`.
What stays: the president's, nominees', leaders' and chamber members' turns and the forum.

"Rule-based" is not "static". What the kernel already draws for a citizen is a textbook of political
sociology: correlated issue positions from two latent factors (Converse's constraint), priorities
(issue publics), a tolerance beyond which a candidate is unacceptable (the blank ballot), an action
threshold drawn per citizen (Granovetter 1978), three emotions toward the president and the economy
(Marcus, Neuman and MacKuen's affective intelligence), an engagement state moved by anger with
hysteresis (Hirschman's exit, voice and loyalty, with pressure as voice and partisanship as loyalty)
and neighbours on a small-world graph. One quarter of a tick runs: the world moves (a scandal, the
economy); people feel; some give up or return; the awakening gate wakes those whose context pushed
them over their own threshold, with neighbours who acted last tick lowering it (the cascade); the
awake sign, launch, mobilise or wait; minds move one bounded-confidence step toward their neighbours
and a noise step (Friedkin–Johnsen with Hegselmann–Krause bounds, the anchor being Zaller's long-term
predisposition); at an election the utility ballot weighs distance, partisanship and the incumbent's
record under a turnout cost, and campaigns change what counts, not what people think.

Unpredictability comes from three nonlinearities (the threshold cascade, the engagement hysteresis,
the seat cliffs), four noise sources (opinion drift, scandal draws, the economy, seeded ties) and the
feedback from pressure to legitimacy to what the president does and back to anger. A scandal two
ticks earlier in one seed starts a cascade that reaches the petition bar before the election; the
vote is lost; another president is seated and proposes another amendment: path dependence.

What stops the crowd being true today, in order of cost: every one of those knobs ships at zero
(`dynamics`, `emotions`, `awakening.neighbors_acting`, `social_graph` off or neutral) and the one
calibration against panel stability met no setting; the society has no structure (one cloud, no
cleavage groups, a static graph); no cohort replacement; no elite cues beyond the forum; a scalar
economy with no welfare effect. Citizens will move, change their minds and radicalise through four
channels, each with its check: slow persistent drift (ADR-032 D plus `drift_std > 0`, checked against
a panel-stability band of about 0.7–0.8 year-to-year correlation of left–right self-placement);
**radicalisation after events** (a shock moves the position of the citizens it reaches, by
`radical_step × anger × salience` away from the president, and anger narrows the confidence bound
while enthusiasm widens it: Deffuant's extremist pull, so a crisis hardens a bloc that stays hardened);
realignment by structure (homophilous rewiring and cohort replacement turn a hardened bloc into a
period); and elites and campaigns (a nominee who campaigns on the issue the shock made salient wins
the bloc).

The guarantee that the crowd is dynamic is a test, not a promise: the divergence test of §4.

## 4. Step 1, built: scenarios, trajectories, archetypes, the divergence test

**A scenario** is {constitution, electorate, shock schedule, agent model}. The constitution is
ADR-015's articles; the electorate `plan-distribution-positions-seeds.md`'s shape; the agent model a
profile. The shock schedule as data (`events.scripted`, on the pattern of `constitution.scripted`) is
not built yet (step 3): today a shock schedule is the seed's draw.

**A trajectory** (`api/domain/polity/trajectory.py`, in every `digest.json` under `trajectory`):

- `legislative`: per legislative election, ENP by seats, whether a party held a majority, whether any
  party was seated, and the **Pedersen volatility** against the previous election (half the sum of
  absolute vote-share changes over the parties that stood in either).
- `elections`: per presidential vote held, the winner and the turnout.
- `margins`: per `vote_intention_poll` (the exploration profile), the leader's first-choice share and
  the margin over the runner-up. Absent where no poll was journaled: ballots are rule-based and only
  an audit sample is journaled, so there is no tally to count.
- `polarization`: per census year (`snapshots.jsonl`), the standard deviation of the population's
  scores on its own first principal axis (`dispersion`), Sarle's **bimodality** coefficient on them
  (5/9 for a uniform; higher for two camps) and the distance the population's mean has moved since the
  first census (`mean_shift`).
- `office`: terms, distinct holders, alternations, re-elections, recalls, the longest run of terms one
  holder kept through elections, the mean term length.
- `yearly`: eight series indexed by year, the trajectory vector: mean legitimacy of the sitting
  president, ENP by seats, turnout and volatility carried from the last election, dispersion,
  bimodality, mean shift, and pressure acts per citizen per tick.
- `archetype`, `archetype_blocks` and `plausibility_failed`, below. A run is labelled block by block (blocks of 8 to 16 years; the rules read each as if it were a run; the run takes the most common block label, a collapse of the whole run winning): the rules were cut on eight-year runs and "at some point this reached X" is met by every thirty-year run ([ADR-035](../../adr/ADR-035-generational-replacement.md)). Runs of up to 15 years are one block, labelled as before.

**Archetypes, first cut** (`ARCHETYPE_RULES`, first match wins; the thresholds are module constants
and will be re-cut once the catalogue shows what runs do):

| Archetype | Rule |
|---|---|
| collapse | office occupancy below 0.5, or a legislative election that seated no party |
| entrenchment | one holder kept office through 3 or more elections, or a refusal to leave succeeded |
| recall_cycle | 2 or more recalls |
| fragmentation | ENP by seats at least 8 at the last legislative election, and above the first's |
| dominant_party | one party held a majority of the seats at every legislative election (at least two) |
| realignment | the population's mean moved 0.1 or more from the first census |
| churn | a legislative volatility of 0.4 or more: parties come and go, opinion need not move |
| alternation | 2 or more alternations in office |
| stasis | none of the above |

**The plausibility band** (`PLAUSIBILITY_BAND`): ENP by seats at the last legislative election in
1.5–8, mean turnout in 0.5–0.85, mean legislative volatility in 0.05–0.30, and the four-year
correlation of each latent factor across citizens in 0.70–0.90 (`panel_stability`, ADR-012's D1: a static
population scores 1.0). Generic European facts (Laakso and Taagepera; Pedersen; turnout in national
elections; Ansolabehere, Rodden and Snyder's panel stability), used as a filter against absurd
runs, never as a target. A check with nothing to read is skipped, not failed.

**Across runs** (`divergence_by_year`, `pairwise_distances`, `diversity`, `divergence_verdict`): the
yearly series of every run are standardised feature by feature over the whole ensemble (an absent
value sits at the mean and adds nothing), the distance between two runs is the mean over years of
the per-year Euclidean distance, and the ensemble's diversity is the archetype counts, their entropy
in bits, the largest archetype's share and the mean pairwise distance.

**The divergence test**, the gate for every mechanism from now on, on N ≥ 10 seeds of one
configuration: (i) the runs drift apart, the mean pairwise distance of the last third of the years
exceeds the first third's; (ii) archetype entropy at least 1 bit; (iii) no archetype covers more than
half the runs; (iv) at least two thirds of the runs stay inside the plausibility band. A mechanism is
adopted only if it raises (i)–(iii) without breaking (iv). The seed sweep's summary reports all of it
(`run_polity_seed_sweep.py`, "Diversity").

**First reading, phase15** (5 seeds, 8 years, p100, exploration, run through this code on
2026-10-21, not pre-registered; a reading of five runs, not a result): archetypes churn ×3,
fragmentation ×1, stasis ×1; the mean pairwise distance grows from 2.3 in year 0 to 4.2 in year 8
(grows: yes; varied: 1.37 bits, yes; no dominant story: no, churn holds 3 of 5; plausible: no, every
run fails at least one band check). What fails the band: turnout in 4 of 5 (below 0.5), legislative
volatility in 4 of 5 (0.42–0.62, against a 0.30 ceiling), ENP by seats in 1 (17.2). The volatility is
party churn (phase15 founded and dissolved dozens of parties a run), while the population's mean moved
0.006–0.025 over 8 years: the crowd did not change its mind, the party system did. That is the
baseline the divergence test will be read against.

Not built in this step, on purpose: the shock schedule as data (a kernel change, step 3), the
`metrics.polarization` knob of `metrics.json` (still refused; the digest carries the figure instead),
and a two-run view in `/polity` (the atlas has one; step 1b promotes it).

## 5. Direction, in push order

Each step is one PR under the usual gates. Steps 1–3 need no GPU.

| Step | What | Gate |
|---|---|---|
| 1 | **Built.** Trajectory metrics, archetypes, plausibility, the divergence test in the sweep summary. | tests |
| 1b | **Built.** The crowd, live, in the engine atlas (`scripts/engine_atlas/crowd.html`, `build_engine_atlas.crowd_payload`): every citizen on the first census's two principal axes, frames from the yearly census and from every tick's `checkpoint.json` while the server watches (the only per-tick record of anger, engagement and who mobilised), the regenerated graph's ties, lenses (engagement, anger, salience, party, mobilised), a trail over the last frames, the president ringed, run B beside run A at the same tick. | a live run shows the cloud move |
| 2 | **Built, with two things left out and one reading.** `--profile scenario` (`run_polity_flagship.py`, `run_polity_seed_sweep.py`): the exploration profile with `llm.crowd: false` (new: the rules decide the nine batch decisions and the model plays only the agents; `vote.mode: utility` required; a flag outranks the profile and a contradiction is refused), the forum capped at 10 speakers a tick, `dynamics.drift_std` 0.02. **Left out:** chamber shifts on the rule path (the chamber's deliberation only ever ran on the model, and ADR-032 found its shifts never reach a citizen's views, so no rule was invented for a shadow position; the chamber still votes amendments as agents); the model arm's timing (no server was up and the GPU is shared), so the 'optimistic 2×' claim stays open. **Measured:** the rule-only twin runs 8 years at population 100 in 1.3 s a seed, ten seeds in 18 s; the catalogue of step 6 is minutes. **Reading** (ten seeds, rule-only twin, 2026-10-21, not pre-registered): the divergence test **fails**: grows yes (mean pairwise distance 2.26 at year 0 to 3.68 at year 8), varied no (0.88 bits: stasis 7, alternation 3), no dominant story no (70%), plausible no (turnout below 0.5 in all ten seeds, volatility outside the band in six). With `drift_std` 0.02 alone the population's mean moved 0.017 over 8 years against 0.015 without: the anchor pulls views back. That is the baseline steps 3 and 4 must move: the twin's world does not push back. | divergence test; minutes a seed |
| 3 | Open the world, in three PRs. (Archetype counts in this row are version 2, the fixed 0.1 realignment rule, which ADR-037 replaced; and the scenario profile's economic voting is now 0.3, not 3b's 1.0, ADR-038.) **3a (built): the radicalisation channel** ([ADR-033](../../adr/ADR-033-radicalisation.md)): `dynamics.radical_step` (once events have shaken the polity, an angry citizen steps away from the president in the latent space; salience is event-driven and the same for everyone on the rule path) and `dynamics.anger_narrows_bound`, both 0 by default and set in the scenario profile with `drift_std` 0.18; panel stability (the four-year factor correlation) is now a trajectory metric and a plausibility check. At those values the ten-seed twin sweep moves from varied no (0.88 bits) to varied yes (1.30 bits), panel stability from 0.996 to 0.877 (inside ADR-012's band), four of ten seeds inside the whole band (none before); still failing: no dominant story (realignment 6 of 10) and turnout below 0.5 in five seeds. **3b (built): economic voting and scripted events** ([ADR-034](../../adr/ADR-034-economic-voting-and-scripted-events.md)): `vote.economic_voting` (voters weigh the economy at the election, the same for everyone; set to 1.0 in the scenario profile, now 0.3 (ADR-038); a recession plus weight 2 takes re-elections from 0.8 to 0.0 a run) and `events.scripted` (a recession or a scandal at a named tick; the random stream is untouched). At the then-shipped 1.0 the divergence test was varied (1.49 bits) with no dominant story, three of four criteria; a crisis at the same tick in every seed makes the runs alike, so variety must come from varying the schedule across runs. Not built: a per-citizen shock reach (salience is still the same for everyone on the rule path) and an economic memory. **3c part 1 (built): cohort replacement** ([ADR-035](../../adr/ADR-035-generational-replacement.md)): `citizens.replacement_per_year` and `citizens.newcomer_spread` (3% a year and 0.35 in the scenario profile): an ordinary citizen is replaced in place (ids stay `range(n)`) by a newcomer whose views are the mean of their circle plus noise, with their own anchor; panel stability ignores replaced slots. Over 30 years the spread of positions grows by 83% instead of 133%. The archetype is now read block by block (blocks of 8 to 16 years, the run taking its most common block label): with the whole-run label every 30-year seed was realignment whatever the arm, which hid everything. With it, replacement at 3% reads 1.16 to 1.36 bits against 0.47 without (varied met at the middle spreads), still with one story at 7 of 10 and 0 to 2 seeds of ten in the plausibility band. **3c part 2 (to do):** homophilous rewiring once a year. | divergence test, panel band |
| 4 | ADR-031 option B (approval on conduct and policy gain; C only if recalls stay at zero); ADR-032 option D. | divergence test |
| 5 | Optional: LLM-distilled stochastic policies for the crowd decisions (a grid of situations × logprobs, stored and sampled; zero inference at run time). | dispersion retention vs the live model |
| 6 | **The catalogue (built, gate met at the third sweep).** The scenario profile as a model run by `scripts/run_polity_catalogue.py`; a Latin hypercube over {method, threshold, seat rule, recall floor, petition threshold, scandal rate, economy sigma, polarization pressure (no knob sets the electorate's initial spread), ambition distribution, amendment threshold}; 1,000 runs; PRIM boxes per archetype; the band as a filter. Then the GPU on the most original cells, 3-5 LLM-crowd runs each (not run: no vLLM, the GPU is shared). **Built:** `api/domain/polity/catalogue.py` (the dimensions, the hypercube, PRIM by peeling, relabelling) and the runner (run, resume, report); no EMA Workbench dependency, which would add pandas and scikit-learn for about 80 lines. **Three sweeps of 1,000 runs** (15 years, 100 citizens, 8 minutes each, [results](../../../fast_api_voter/scripts/run_polity_catalogue_results.md)): under archetype version 2 (a fixed 0.1) 89% read as realignment, exactly the share crossing 0.1, so the rule was changed to half the population's own spread ([ADR-037](../../adr/ADR-037-realignment-against-the-populations-spread.md), version 3); then churn took 60%, because economic voting at 1.0, the same for every voter, swung whole blocs between legislative elections (volatility 0.35, 0.10 without it), so the scenario profile's weight is now 0.3, the largest that keeps two thirds of the runs inside the volatility band ([ADR-038](../../adr/ADR-038-economic-voting-calibrated-on-volatility.md)). Third sweep: alternation 60%, churn 16%, stasis 13%, realignment 11%, each with a PRIM box with lift; 228 runs inside the whole band (97 before). The negative control shows up as an edge trim in one box: one run per point is noisy. Turnout is now the most frequent band failure. The GPU stage has not run. | at least 4 archetypes with non-trivial frequency, a PRIM box for each: **met (4)** |
| 7 | Typed leader rules (Sticker, Aggregator, Hunter, Explorer; Laver and Sergenti 2012) as the cheap leader arm, and the LLM president classified against them. | a research question, later |

**Stop doing for now:** field-order and thinking-budget experiments beyond the serial replay; new
Phase 5 acts, new party mechanisms or new ADRs that add a mechanism without a diversity measurement;
treating a single 8-year run as a result.

## 6. What the field does, and what of it applies here

- **Silicon sampling with real-data validation.** Park et al. 2024 (1,052 interview-grounded agents,
  85% of human test-retest on the GSS), ElectionSim 2024 (a tweet-built pool sampled to match
  demographics, scored against polls). The constant failure is variance collapse: Ziaei 2026 shows
  instruction tuning halves the spread of answers and later training never restores it, and proposes
  dispersion retention and the Wasserstein distance to the human distribution as the metrics; Gordon
  et al. 2026 find forced single answers triple distributional error against eliciting a distribution.
  Bisbee 2024, Santurkar 2023 and Argyle 2023 are the earlier line. OBS-007, 013, 045 and 053 are this
  phenomenon. The remedies: data-grounded conditioning, distribution elicitation, measuring dispersion,
  and not using the model as the crowd.
- **LLM deliberation and coalition.** *From Simulated Citizens to Simulated Deliberation* (2026, six
  models, a real deliberative poll): agents shift opinion even when they cannot see each other; use
  deliberation "for surfacing arguments and perspectives, rather than simulating a real public".
  *Digital Pantheon* (2026): coalition formation works after partisan fine-tuning plus manifesto
  retrieval and a formateur. ADR-032's evaporating shift and the collapsed `coalition_decision` are what
  the field finds: opinion change belongs in the kernel, coalition to a typed rule with leader text on
  top.
- **Classic electoral ABMs.** Laver and Sergenti 2012 (typed party rules, Monte-Carlo parameters run to
  steady state, calibrated on European party systems 1989–2002); Bendor et al. 2011 (aspiration-based
  adaptive agents reproduce turnout, retrospection and Duverger). The rule-based twin, done properly.
- **Exploratory modelling.** PRIM and the EMA Workbench: sample the input space, run thousands of cheap
  runs, label outcomes, find the input box per regime. No baseline needed: a typology over a sampled
  space, which is this plan's framing. Grimm's pattern-oriented modelling: several patterns at once.
  AgentSociety and OASIS use exogenous shocks as the lever.

## Not verified

- No simulation was re-run for this plan; the figures in §1 are quoted from the documents named.
- The step-2 cost ("minutes a seed") is a claim from the twin's docstring plus about ten leader agents
  a tick, not a measurement.
- The archetype thresholds and the plausibility band are a first cut from the literature's ranges, not
  a calibration.
- The field survey rests on abstracts and summaries of 2024–2026 preprints, not full texts.
