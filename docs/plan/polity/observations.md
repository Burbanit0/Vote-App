# Polity — observation log

Strange behaviour seen in simulation runs, kept so it can be studied instead of forgotten in a
commit message or a `TIMELINE.md`. An entry records **what was seen and how to see it again**. It
is not a bug report and not a conclusion: most entries are open questions.

**Rules for an entry**

- Every number is reproduced from a run's files, with the command or event ids that show it.
  Nothing from memory, nothing from a narrative's prose alone.
- *Suspected cause* is labelled as a suspicion until something settles it; it becomes *Cause* only
  with the evidence that shows it.
- *What would settle it* names the check, the run, or the plan step that answers the question.
- Status is one of **open**, **cause found** (the mechanism is shown; whether to change it is not
  decided), **explained** (cause understood, behaviour stays), **fixed** (with the commit), or **by
  design** (the model intends it; say where that is written).
- New entries go at the end with the next number; an entry is never deleted, only re-statused.

Runs cited below live in `fast_api_voter/scripts/*_runs/` (gitignored); `python
scripts/run_registry.py` lists them and `marimo run scripts/run_explorer.py` browses them. Most
numbers come from `python scripts/check_observations.py <subcommand>` (from `fast_api_voter/`),
named in each entry. "p500 seed 1" is the S0.8 batch's first run
(`Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs/sweep-8y-p500-seed1`), read while it was
still running: events up to tick 16, call log as of 2026-09-13 17:35.

## Index

| ID | Observation | First seen | Status |
|---|---|---|---|
| [OBS-001](#obs-001) | The same citizen wins nearly every presidential election of a run | 2026-09-13 | cause found |
| [OBS-002](#obs-002) | Parties nominate the same five people at every election, snap elections included | 2026-09-13 | cause found |
| [OBS-003](#obs-003) | A recalled president usually wins the election that follows the recall | 2026-09-13 | cause found |
| [OBS-004](#obs-004) | The sortition chamber almost never moves: 99.9% of its decisions are "no change" | 2026-09-13 | cause found |
| [OBS-005](#obs-005) | A president kept by a confidence vote is recalled the same tick | 2026-09-13 | by design |
| [OBS-006](#obs-006) | One party's nomination answer is out of range, the same wrong value six times | 2026-09-11 | open |
| [OBS-007](#obs-007) | `representative_response` and `coalition_decision` answer the same whatever the input | 2026-08 (Ollama), re-checked 2026-09 (vLLM) | open, partly fixed |
| [OBS-008](#obs-008) | Two truncated generations cost more time than all retries and rejected answers together | 2026-09-13 | cause found |
| [OBS-009](#obs-009) | Journals are not bit-identical across CPUs | 2026-09-13 | explained |
| [OBS-010](#obs-010) | Half the p100 seeds tell the same story | 2026-09-13 | cause found |
| [OBS-011](#obs-011) | About 40% of citizens declare candidacy at every election | 2026-09-11 | open |
| [OBS-012](#obs-012) | Term limits and the rerun bar do nothing on the LLM engine | 2026-09-13 | fixed |
| [OBS-013](#obs-013) | Party nominations often don't match the reason the model gives, and lean to the last listed candidate | 2026-09-13 | open |
| [OBS-014](#obs-014) | The p500 batch stopped: seed 1 received SIGTERM during the last vote of its last tick | 2026-09-13 | open |
| [OBS-015](#obs-015) | In the deterministic twin, presidents are recalled after a median of two ticks | 2026-09-13 | cause found |

---

### OBS-001

**The same citizen wins nearly every presidential election of a run.**

*Seen.* In the 8-year population-100 seed sweep (`seed_sweep_runs/sweep-8y-p100-seed*`), four of
ten runs have a single president for all eight years, elected at ticks 0, 16 and 32 (citizen 13 in
seed 1, 29 in seed 2, 95 in seed 7, 88 in seed 9). In seed 6, citizen 66 is elected six times (ticks
0, 16, 20, 24, 28, 32). Across seeds the winner differs, so this is within a run, not across runs.
Pooled over the ten runs, the winner of an election is the previous election's winner 18 times out
of 30.

*Evidence.* `python scripts/check_observations.py elections scripts/seed_sweep_runs`, or the
`elected` events per run:

```bash
cd fast_api_voter && python3 -c "import json,glob
for j in sorted(glob.glob('scripts/seed_sweep_runs/sweep-8y-p100-seed*/run/*/events.jsonl')):
    print(j.split('/')[2], [(e['tick'], e['citizen_id']) for e in map(json.loads, open(j)) if e['event_type']=='elected'])"
```

*Cause (shown 2026-09-13).* Nothing the candidacy, nomination and campaign decisions read changes
between two elections, and the model answers at temperature 0, so they return the same answers
every time. Only the vote sees anything new.

- `ambition_score` is drawn once in `generate_population` and never assigned again.
  `perceived_support` is `sympathizer_ratio`, computed from `issue_positions` and
  `blank_threshold`, both set once at generation. Party affiliation is assigned once, in
  `_fresh_tick_state`, and party platforms never change.
- p500 seed 1: all 20 candidacy requests, the party-nomination request and the campaign-positioning
  request at tick 16 are byte-identical to tick 0's (same `request_sha256`), and each got the same
  answer (`check_observations.py requests <run_dir> --ticks 0 16`).
- In the ten p100 runs, the set of citizens who declare and the five nominees are identical at 30
  of 30 consecutive elections (`elections`).
- The vote is the only step whose input changes: standing rupture candidates join the field (8 at
  tick 16 in p500 seed 1, so every vote prompt lists 13 candidates instead of 5; none of the 118
  vote requests at tick 16 matches one at tick 0). Voters' own positions never move.
- Where the winner did change, it was a rupture candidate twice (seed 10, ticks 16 and 32), and
  otherwise another member of the same field for one election, after which the previous winner
  returned (seeds 3, 4, 5, 6, 8).
- `institutions.president_term_limit` ships `null`. Until OBS-012's fix, setting it changed nothing
  on the LLM engine, so the term-limit sweep first proposed here would have repeated the same runs.

Not the cause: the model does not simply nominate the most ambitious member (OBS-013). It makes
the same pick every time.

*Decided 2026-09-13 (D6).* Four levers:

- **Shipped now:** `president_term_limit: 2` and a recalled president barred from the snap election
  that follows the recall (`recalled_barred_from_snap_election`, OBS-003).
- **Coming with later steps:** a retrospective vote (S4.1) and dynamic citizens (S4.3).

Re-measure OBS-001 and OBS-010 on the first sweep run with them.

*Update 2026-09-14, p500 seeds 1 and 2, complete.* Both runs come from the S0.7 worktree, before
D6's levers.

- **The party field never changed.** Seed 1's nominees are 31, 113, 398, 421 and 499 at all four
  elections. Seed 2's are 0, 70, 224, 248 and 271 at all four, with a rupture candidate added at
  ticks 16, 26 and 32 (`check_observations.py elections`: same field 3/3 in each run).
- **Winners.**
  - Seed 1: citizen 31 won ticks 0, 16 and 20.
  - Seed 2: 271 at tick 0, 224 at tick 16, 326 at tick 26, then 224 again at tick 32.
- **Rupture candidates take office.** Seed 1's last winner (287, tick 32) and seed 2's third (326,
  tick 26) are not among the declared nominees of those elections: both came in through the rupture
  path.

*What would settle it (before D6).* A design choice, not a check: what should differ between two elections?
Candidates are term limits (they work on both engines since OBS-012's fix), S4.3 (dynamic citizens: positions and ambition
that respond to what happened), or sampling above temperature 0 for candidacy and nomination.

### OBS-002

**Parties nominate the same five people at every election, snap elections included.**

*Seen.* In seed 1 the dominant-path nominees are citizens 13, 37, 79, 82 and 99 at ticks 0, 16 and
32. In seed 6 the field is 46, 53, 63, 66 and 99 at all seven elections (0, 16, 20, 24, 28, 31,
32), four of them snap elections after a recall. At p500 the same holds: seed 1 nominates 421, 499,
31, 113 and 398 at ticks 0 and 16.

*Evidence.* `candidacy_declared` events with `payload.path == "dominant"`, grouped by tick;
`check_observations.py elections` counts identical fields per run.

*Cause (shown 2026-09-13).* OBS-001: the candidacy and nomination requests are byte-identical at
every election, so the same citizens declare and the same one wins each party. `ambition_score` is
never updated during a run (the check first proposed here). `institutions.barred_from_immediate_rerun`
bars candidates only after an *invalidated* election, not after a recall (see the comment at
`_phase_snap_election` in `run_polity_simulation.py`), and until OBS-012's fix it barred nobody at all on
the LLM engine.

*What would settle it.* As OBS-001.

### OBS-003

**A recalled president usually wins the election that follows the recall.**

*Seen.* Seed 6 (p100): citizen 66 is recalled at the legitimacy floor at ticks 15, 19, 23, 27 and
30, and wins the election that follows the first four (ticks 16, 20, 24, 28). After the fifth recall,
citizen 53 wins the snap election at tick 31 -- and citizen 66 wins the regular election one tick
later, at 32. Seed 5: citizen 16 is recalled at ticks 11, 14 and 20, re-elected at the snap elections
of ticks 12 and 15, loses the one at 21 to citizen 89, and wins the regular elections at 16 and 32.
Recall mostly changes the calendar, not the president.

*Evidence.* `term_rows` in the run explorer, or `recalled` followed by `snap_election_triggered`
and `elected` with the same `citizen_id`.

*Cause (shown 2026-09-13).* No decision in the snap election can see the recall.

- The snap election bars nobody: `_phase_snap_election` schedules it with an empty barred set, on
  purpose (its comment).
- The candidacy prompt shows each citizen's `ambition_score` and `perceived_support`; the nomination
  prompt adds `platform_distance`. None of them moves when a president is recalled, so the recalled
  president declares and is nominated again (OBS-001, OBS-002).
- Each candidate in the vote prompt carries `position`, `cid`, `platform` and `party`, and each voter
  sees their own positions, priorities, blank threshold and distances. Nothing says who held office,
  their legitimacy, or that they were just recalled.

*Decided 2026-09-13 (D6).* A recalled president is barred from the snap election that follows the
recall, and may stand again at later elections (`institutions.recalled_barred_from_snap_election`,
shipped true). Voters' knowledge of the recall enters through S4.1's retrospective vote.

*Update 2026-09-14, p500 seeds 1 and 2 (before D6's bar).* The pattern is not universal.

- **Seed 1 repeats it.** Citizen 31, recalled at tick 19, wins the snap election at tick 20.
- **Seed 2 does not.** Neither recalled president wins their snap election, though both stand.
  - 271, recalled at tick 15, loses the tick-16 snap election to 224.
  - 224, recalled at tick 25, loses at tick 26 to 326, a rupture candidate. 224 then wins the
    scheduled election at tick 32.

Across the ten p100 runs and these two, recall still more often changes the calendar than the
president.

*What would settle it (before D6).* A design decision: should a recalled president stand in the snap election,
and should voters know who was recalled? A bar is a rule change; telling voters is a prompt change
that S2.2's case bank could test first.

### OBS-004

**The sortition chamber almost never moves: 99.9% of its decisions are "no change".**

*Seen.* Across the ten p100 runs: 4,950 `chamber_deliberation` decisions, 4,944 with motif 701 and
no shift, 6 with motif 702 and three shifts each (18 shifts in total, deltas between -0.1 and
+0.05). 5 decisions fell back. Membership does differ by seed (the first seated chamber differs in
every run). p500 seed 1 is the same: 1,200 decisions, 1,181 with motif 701, 14 with 702, 5 fallbacks.
*Update 2026-09-14, both p500 runs complete* (`check_observations.py chamber`):

- **Seed 1:** 2,475 decisions, 2,457 with motif 701 (10 of them fallbacks), 18 with 702. The reasoning
  of all 495 completed calls notes identical positions.
- **Seed 2:** 2,475 decisions, 2,463 with 701 (5 fallbacks), 12 with 702. All 497 completed calls note
  identical positions.

*Evidence.*

```bash
cd fast_api_voter && python3 -c "import json,glob,collections
c=collections.Counter(e['motif'] for j in glob.glob('scripts/seed_sweep_runs/sweep-8y-p100-seed*/run/*/events.jsonl') for e in map(json.loads, open(j)) if e['event_type']=='chamber_deliberation')
print(c)"
```

and `check_observations.py chamber <p500 seed 1 run_dir>` for the call-log half below.

*Cause (shown 2026-09-13).* The prompt tells the model not to move. `build_chamber_system_prompt`
says: "Si chamber_position est identique a sincere_position, c'est l'etat normal d'un membre qui
vient d'etre tire au sort ou qui n'a jamais devie -- tranche motif=701, shifts vide, sans
verification repetee ni hesitation." Every member is seated with `chamber_position` equal to their
sincere position, and a member who answers 701 stays in that state, so the instruction applies
again at every later deliberation. The sentence was added to stop reasoning loops on exactly this
state (the builder's docstring, v6b Lot 5). In p500 seed 1, the reasoning of all 240 completed chamber calls notes
that members' two positions are identical, and only 6 of those 240 answers contain a 702. The chamber also has nothing to deliberate on: by design it receives no pressure,
petition or election, and its context is `ticks_left` alone.

*What would settle it.* A design decision on what the chamber is for. With no agenda (S4.2's
legislation would give it one) and an instruction to hold still, "no change" is the expected
answer. Removing the sentence alone would likely bring back the loops it cured (OBS-008).

### OBS-005

**A president kept by a confidence vote is recalled the same tick.**

*Seen.* p500 scale probe (`flagship_runs/scaleprobe-8y-p500-v2-postfix`), tick 17, citizen 3: a
confidence vote is triggered (event 5680, 26.4% signed) and the president is **retained**, 346 of
500 voting to keep (event 5681, keep ratio 0.692). The same tick, the president is **recalled** by
the legitimacy floor, legitimacy 0.089 below the 0.2 floor (event 5682).

*Evidence.* `python scripts/check_timeline_claims.py` against the run with anchors
`[e5681: confidence_vote_result t17 c3 retained=true keep_ratio=0.692]` and
`[e5682: recalled t17 c3 legitimacy=0.089 trigger=legitimacy_floor]`.

*Cause (by design).* `polity-simulation-design-v2.md` §7bis.7, step 6: the hard floor on `L(t)` has
priority over the petition when both fire in the same tick ("la règle la plus dure l'emporte").
`_run_accountability_phase` implements it as written: the floor is evaluated right after
`legitimacy_updated`, the confidence vote still runs in full so its events are not dropped, and the
recall names the floor as its trigger.

*Still open.* The design does not say whether a retained vote should feed back into legitimacy. If
it should, that is a design change, not a fix.

### OBS-006

**One party's nomination answer is out of range, the same wrong value six times.**

*Seen.* p500 scale probe: party 3 answers `winner_position=26` for a field of 18 at tick 0 and 19
at ticks 16 and 32, six rejected answers in all (`replays.log` lines 1, 277, 560, 873, 1177, 1515).
All three elections fell back, not two: the tick-0 nominees are the highest-ambition contender in
each of the five parties, the fallback's choice. The digest counts 10 fallbacks of 15 only because
the tick-0 events were written without the `llm_fallback` field (their payload has only `contenders`
and `party_id`; `candidacy_considered` and `campaign_positioning` lack it at tick 0 too, and
`pressure_action` until tick 16, which suggests an earlier code version journaled the first ticks
before the run was resumed).

*Evidence.* `grep winner_position scripts/flagship_runs/scaleprobe-8y-p500-v2-postfix/replays.log`.

*Checked 2026-09-13.* 26 is not the cid of any party-3 contender, and not the 26th entry counted
across parties (at tick 16 that is party 0's cid 285). It has not recurred: p500 seed 1 got in-range answers
from its nomination call at ticks 0 and 16. The probe predates the call log, so the model's
reasoning for the probe's answer is not recorded.

*Suspected cause.* Unknown. OBS-013 shows the model's `winner_position` is loosely tied to the
listed candidates in general, and this may be an extreme case of it.

*What would settle it.* A recurrence in the p500 batch (S0.8, pre-registered red flag 2), which now
records the reasoning in `llm_calls.jsonl`.

### OBS-007

**`representative_response` and `coalition_decision` answer the same whatever the input.**

*Seen.* Six deliberately different inputs each: `representative_response` answered CONCESSION 6/6
and `coalition_decision` JOIN 6/6, on Ollama and again on vLLM with AWQ weights
(`fast_api_voter/scripts/check_vllm_collapse_signatures_results.md`). `representative_response`
was partly fixed on 2026-09-11 (Track B1: its stance is no longer flat once the prompt states the
scales), but both types stay listed as unverified (`viz_export._UNVERIFIED_DECISION_TYPES`).
Related: `representative_response` crossed the 10% fallback alert on p100 seeds 2 (30.3%) and 3
(36.4%), 26 of 330 pooled (7.9%).

*Update 2026-09-13, real runs.* Across the ten p100 runs, `coalition_decision` is JOIN in 152 of 160
decisions, and `representative_response` is CONCESSION in 299 of the 304 that did not fall back
(all 26 fallbacks are SILENCE, the fallback's value). p500 seed 1 so far: JOIN 8 of 8, CONCESSION
16 of 16. Whether real inputs ever call for another answer is not established, so this is
consistent with the collapse but does not prove it.

*Update 2026-09-14, both p500 runs complete.*

- **`coalition_decision`:** JOIN 16 of 16 in each run.
- **`representative_response`:**
  - Seed 1 concedes 33 of 33, none falling back.
  - Seed 2 concedes 25 times and answers SILENCE 8 times. One SILENCE is the fallback, so 7 of its
    32 model answers are not CONCESSION. That is the largest departure seen on a real run so far.
  - Seed 2's presidents faced more pressure: 74 mobilizations against seed 1's 1, 689 petition
    signatures against 530, and 2 confidence votes against 1.

*Suspected cause.* Survives a full change of serving stack and quantization, so the model's
behaviour on these two prompt shapes, not infrastructure.

*What would settle it.* S2.4's pre-registered question: does `coalition_decision`'s collapse persist
on at least two non-Qwen model families?

### OBS-008

**Two truncated generations cost more time than all retries and rejected answers together.**

*Seen.* S0.5's live run (2 years, population 100, vLLM): two calls, one `vote_cast` chunk and one
`chamber_deliberation` chunk, each spent about 14,000 reasoning tokens and hit the budget -- 133 s
together, against 121 s for six recovering retries and five rejected answers.

*Update 2026-09-13: a pattern, not two events.* p500 seed 1, ticks 0 to 16: 27 generations hit the
budget (21 `chamber_deliberation`, 6 `vote_cast`), costing 1,839 s, or 16.7% of 11,028 s of model
time. That is as much as all retries (1,089 s) and rejected answers (778 s) together. For the chamber
it is 21 of 261 calls (8.0%) and 1,434 s of its 4,051 s (35%).

*Evidence.* `python scripts/attribute_llm_time.py <run_dir>` for the time;
`python scripts/check_observations.py truncations <run_dir>` for the loops;
`fast_api_voter/scripts/llm_call_log_s05_results.md` for the S0.5 run.

*Cause (shown 2026-09-13).* Every one of the 27 truncated generations is a reasoning loop. In the
second half of each trace there are at most 24 distinct sentences among 79 to 435, and the most
repeated sentence appears 33 to 237 times. This is the "Mode A" pattern documented at
`decide_campaign_positioning` and `build_chamber_system_prompt`. The chamber loops circle around
whether and how to turn position differences into shifts, despite the sentence that was meant to
stop them (OBS-004).

*What would settle it.* S1.3's thinking-budget A/B and S1.4's sampling A/B, measured on these call
logs: a smaller budget cuts each loop's cost, and non-greedy sampling may keep a loop from starting.

### OBS-009

**Journals are not bit-identical across CPUs.**

*Seen.* The golden test failed on some GitHub runners only: `mandate_pledge_declared` content
changed with the same event count. Locally, forcing OpenBLAS's Sandybridge or Prescott kernel
changes `chamber_deliberation` instead.

*Cause (explained).* Population positions are BLAS matrix products; OpenBLAS picks its kernel per
CPU, and a different kernel changes the last bits of those floats. Events that journal raw positions
then differ in their digits. Fixed for the golden references by hashing floats rounded to 9
significant digits (commit `58b07f38`). A run's own journal is still CPU-dependent in its last bits.

*Checked 2026-09-13: those bits never flipped a decision.* 26 run shapes (both engines, the LLM one
with the test suite's fake client; population 100 seeds 1-10 and population 500 seeds 1, 2, 42;
8 years; the golden references' full-mechanism config) under five kernels (default, Haswell,
Sandybridge, Nehalem, Prescott). The raw journal differs between kernels in 19 of the 26 shapes, and
the float-rounded journal in none. Every request sent to the model is byte-identical across kernels
in all 13 LLM shapes. About 192,000 events per kernel, with the same decisions and the same prompts.

*Evidence.* `python scripts/check_observations.py kernels` (about 25 minutes, CPU only).

*Still open.* A distance tie at the last bit remains possible in principle, but none appeared in
these runs. The real model server's own nondeterminism is a separate question (S2.1).

### OBS-010

**Half the p100 seeds tell the same story.**

*Seen.* At the `terms` grain (elections and recalls only), 5 of 10 p100 seeds are the same story:
three uninterrupted terms. The other five each have their own recall pattern, up to five
legitimacy-floor recalls in seed 6.

*Evidence.* `python scripts/story_skeletons.py scripts/seed_sweep_runs --grain terms`.

*Cause (shown 2026-09-13).* OBS-001: the field is fixed within a run, so a run's story varies only
where something outside the candidacy and nomination decisions varies. That means a legitimacy-floor
recall, or a rupture candidate joining the vote. The five shared stories are the runs with no recall.

*What would settle it.* Re-run the grouping after whatever OBS-001's design choice introduces.

### OBS-011

**About 40% of citizens declare candidacy at every election.**

*Seen.* p500 scale probe: 202 of 500 citizens declare at tick 0, 206 at tick 16, 206 at tick 32. p100
sweep: 25% to 45% per seed. Only one nominee per party (five in all) ever runs, so the declarations
mostly end in `nomination_lost`.

*Evidence.* `candidacy_considered` events with `payload.outcome == 1`, per tick;
`check_observations.py elections` for the comparison below.

*Checked 2026-09-13.*

- **Against the deterministic threshold.** At the first election of the ten p100 runs, 384 of 1,000
  citizens declare (38.4%), while `candidacy.ambition_threshold` (0.30) would admit 204 (20.4%). Of
  the 384, 245 (63.8%) are below that threshold. The model agrees with the threshold on 69% of
  citizens.
- **Not three measurements.** The declaration decision is made once per run: its requests are
  byte-identical at every election (OBS-001), so "at every election" is the same answer repeated.
- **Already tried.** Track B3 (`scripts/check_candidacy_calibration_results.md`, 2026-09-11) stated
  the population's mean ambition in the prompt. Declarations rose to 47.6% and agreement with the
  threshold fell, against a pre-registered bar of under 5%. Not shipped.

*Suspected cause.* Unknown. The prompt gives `ambition_score` as a bare number with no threshold,
and the one reference tried argued in the wrong direction.

*What would settle it.* S2.2's candidacy case bank, and S2.4 (is it this model family?).

### OBS-012

**Term limits and the rerun bar do nothing on the LLM engine.**

*Seen.* Found while planning OBS-001's term-limit check (population 100, seed 1, 8 years, the golden
references' full-mechanism config). With `president_term_limit: 1`, the deterministic engine elects
11 different presidents. The LLM engine, using the test suite's fake client, re-elects citizen 13 at
all 12 elections, exactly as it does with no limit.

*Evidence.* `python scripts/check_observations.py term-limit`.

*Cause (shown 2026-09-13).* `_declare_nominees` filters term-limited and barred citizens only on its
deterministic branch. The LLM branch passes every citizen to `_declare_nominees_llm`, as its comment
says ("Term limits ... and ... the §6bis.2 barred set are enforced only on this deterministic
branch"), calling the gap "a legitimate, separately-scoped follow-up". Yet `is_term_limited` is
documented as "§6bis.1: a hard, always-on candidacy block, independent of the LLM", and
`validate_config` accepts the setting on either engine. No recorded run is affected: every run on
disk has `president_term_limit: null`, and none has an invalidated election, the only thing that
fills the barred set.

*Fixed 2026-09-13* (`fix/polity-llm-candidate-eligibility`). `_eligible_declared_cids` applies
both gates to the LLM path's declared set just before nomination. The staggered calendar passes
through the same function. The model is still asked about every citizen's candidacy, so candidacy
prompts don't depend on either rule, and `citizens` stays whole for perceived support and the
positioning electorate mean. `check_observations.py term-limit` now shows 11 distinct presidents on
both engines. The golden references are unchanged (no term limit, no invalidated election). No
recorded run changes, for the reason above.

### OBS-013

**Party nominations often don't match the reason the model gives, and lean to the last listed
candidate.**

*Seen.* p500 seed 1, tick 0, one nomination call for five parties, reconstructed from the checkpoint
(the rebuilt request has the logged `request_sha256`, so these are the values the model saw):

| party | contenders | answer | motif (reason given) | the pick's rank on that reason |
|---|---:|---:|---|---|
| 0 | 31 | 31 | 206 highest ambition | 9th of 31 |
| 1 | 41 | 41 | 207 broadest perceived support | 22nd of 41 (39th on ambition) |
| 2 | 24 | 2 | 208 closest to the party platform | 8th of 24 |
| 3 | 38 | 16 | 209 strategic electability | (holistic, not checkable) |
| 4 | 36 | 28 | 206 highest ambition | 2nd of 36 |

Two answers are exactly the last position (31 of 31, 41 of 41). Over the 48 model-made nominations
at the first election of the ten p100 runs, the pick is the best contender on the stated criterion
in 8 of 12 "highest ambition" answers (uniform choice would give 2.0), 4 of 12 "broadest support"
(2.1) and 3 of 15 "closest platform" (2.8). It is the last listed contender 15 times against 8.3
expected under uniform choice (a uniform chooser does this or better about 1% of the time), and the
first only 5 times.

*Evidence.* `python scripts/check_observations.py elections scripts/seed_sweep_runs` (the
nomination block). The same command on p500 seed 1's run directory prints the table's totals (none of
the four checkable picks is the best on its criterion; two are the last position); the per-party rows
come from the same ranking.

*Suspected cause.* Unknown. The prompt lists each party's candidates with `position` 1..N and states
`candidate_count` = N just before them; copying that count into `winner_position` would produce
exactly the last-position answers. OBS-006's out-of-range 26 may be a relative of this.

*What would settle it.* The model's reasoning for nomination calls in a call log: it is recorded
from S0.5 on, but nomination runs with `think=False`, so there is none to read. A nomination case
bank in S2.2 (shuffle candidate order and cids, and check whether the pick follows the position or
the candidate) would answer it.

### OBS-014

**The p500 batch stopped: seed 1 received SIGTERM during the last vote of its last tick.**

*Seen.* The S0.8 batch (`Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs`) ran seed 1 from
14:32. Its run ended `interrupted` after 25,044 s, with `_Terminated: received signal 15`, on tick
32 of 32, the final presidential election.

- **What tick 32 had done.** It had journaled candidacy, nomination and positioning (500
  `candidacy_considered`, 5 `candidacy_declared`, 5 `campaign_positioning`). It had made 286
  `vote_cast` calls, against 355 for the whole vote at tick 16.
- **When it stopped.** The last call started at 21:28:23 EDT. The traceback shows the process
  waiting in `httpcore` for a vLLM response when the signal arrived, and `digest.json` was written
  at 21:29.
- **What remains.** The last checkpoint is tick 31.
- **The batch driver died with it.** `p500_driver.log` ends at `[1/4] seed=1 repeat=1 ...`, and no
  batch process remains, so seeds 2 and 42 and the seed-1 repeat never started.
- **What else was running.** The `vllm-polity` container stayed up and healthy. A container named
  `flaky-backend-postfix` was created at 21:27:49, about a minute before the signal. Whether the
  two are related is not known.

*Evidence.*

```bash
cd Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs
python3 -c "import json; d=json.load(open('sweep-8y-p500-seed1/run/sweep-8y-p500-seed1/digest.json')); print(d['outcome'], d['error'], d['ticks'])"
tail -3 sweep-8y-p500-seed1.log; cat p500_driver.log
docker ps -a --format '{{.Names}} {{.CreatedAt}} {{.Status}}'
```

*Suspected cause: the machine ran out of memory, and the batch died with a process the kernel
killed.* The system journal shows the chain; the last link is inferred from timing.

1. At 21:28:10 a second container (`hungry_noyce`, auto-removed since) started, beside
   `flaky-backend-postfix` (image `fast_api_voter-api`, `uvicorn` on port 4434: the e2e suite's
   backend). The kernel's process table at the kill lists `playwright` and the Vite dev server
   among the largest processes.
2. At 21:29:25 the kernel ran out of memory machine-wide. The allocation that triggered it came
   from that container's scope, which systemd reports at a 16.7 GB memory peak over 77 s.
3. The OOM killer killed process 9443, `code`, in VS Code's snap scope.
4. The batch's `digest.json` was written at 21:29:26.35, one second later, after SIGTERM.

The batch process being a child of that VS Code instance, for instance started from its integrated
terminal, would explain the SIGTERM. That relationship is not recorded anywhere, so it stays a
suspicion. The e2e run was not part of this polity session.

```bash
journalctl --since "2026-09-13 21:27:00" --until "2026-09-13 21:30:00" --no-pager | grep -E "oom|Killed process|Consumed|Started docker"
```

*What would settle it.*

- **Confirming the link.** Rerun a long batch from a detached process (`nohup` or `systemd-run
  --user`) while the e2e suite runs. If it survives an OOM kill of the editor, the link is shown.
  Either way, a multi-hour batch should not share a process tree with an editor.
- **Finishing the batch** needs the GPU. The seed-1 run resumes from its tick-31 checkpoint
  (`run_polity_seed_sweep.py ... --resume-sweep`, which passes `--resume` to a started run). It
  redoes tick 32, then continues with seeds 2 and 42 and the repeat.

### OBS-015

**In the deterministic twin, presidents are recalled after a median of two ticks.**

*Seen.* The twin is `run_polity_flagship.py`'s full-mechanism config on the deterministic engine,
population 100 with 30 chamber seats, seeds 1–10, 8 years, on `polity` at the Stage 4 calibrations
(every Stage 4 mechanism off).

- **How often.** It holds 101 presidential elections with a winner and 77 recalls: 73 at the
  legitimacy floor and 4 by confidence vote.
- **How long.** 84 of the 101 terms end in a recall, after 0 to 10 ticks in office (median 2; 34 of
  them after exactly 2).
- **The spread.** Per seed there are 5 to 15 elections and 3 to 13 recalls. The only terms not ended
  by a recall start in the run's last half-year.
- **For comparison.** The p500 LLM run of seed 1 (S0.8) had 1 recall and 3 elections through tick
  31, and `office_occupancy` 0.94.

*Evidence.* The Stage 4 calibration results, which found no full term (ADR-012, E3), and:

```bash
cd fast_api_voter && python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from twin_runs import twin_config, run_twin, SEEDS
for seed in SEEDS:
    ev = run_twin(twin_config(seed, 8))
    print(seed, [e["tick"] for e in ev if e["event_type"] == "elected"],
          [(e["tick"], e["payload"]["trigger"]) for e in ev if e["event_type"] == "recalled"])
PY
```

*Cause (shown 2026-09-13).* The citizen pressure channels, petition and mobilization, drive
legitimacy down faster than support can hold it. Legitimacy updates as L(t) = 0.9·L(t−1) +
0.1·m − écart(t) (`legitimacy.update_legitimacy`), so under a steady écart it settles at
m − 10·écart. For the first president's m = 0.75, any écart above 0.055 held for a few ticks ends
at the recall floor of 0.2.

- **Seed 1's first term, tick by tick.**
  - A petition opens at tick 0.
  - From tick 1 the same 7 of about 30 consulted citizens mobilize every tick
    (`pressure_action` act 3).
  - écart climbs 0.045, 0.080, 0.110, 0.135, 0.157, 0.130, 0.145.
  - Legitimacy falls 0.705, 0.629, 0.532, 0.419, 0.295, 0.211, 0.119, and the president is recalled
    at tick 6.
  - The next president starts at m = 0.63 and faces 13 mobilizers from tick 8.
- **With the channels off** (`pressure_menu.electoral_only`, petition and street pressure off), all
  ten seeds hold exactly 3 elections and no recall.
- **The snap election (Track A3)** refills the office at once after each recall, and the recalled
  president is barred from it (D6). So the office turns over every few ticks instead of sitting
  vacant.

*What remains open.* Whether 7% of citizens mobilizing should be able to unseat a president in
six ticks is a model question, not a bug: the pressure weights or the legitimacy floor, or a
twin whose pressure rule is calibrated against the LLM path's. That is D9 in
`plan-polity-build-order.md`.

