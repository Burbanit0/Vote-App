# Polity — observation log

> **status:** reference — the observation log: entries are re-statused, never deleted. (Set 2026-10-08; `docs/README.md` lists every plan.)

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
  decided), **explained** (cause understood, behaviour stays), **decided** (the owner chose what to do about
  it; say where that is recorded), **fixed** (with the commit), or **by design** (the model intends it; say
  where that is written).
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
| [OBS-016](#obs-016) | The root disk filled up: p500 seed 42 died at tick 13 and the GPU queue ran nothing | 2026-09-14 | open |
| [OBS-017](#obs-017) | WebKit crashed mid-navigation to /polity in CI, once, while the other worker ran the heavy fiches | 2026-09-16 | open |
| [OBS-018](#obs-018) | The response contract, not the model, sets the president's stance in 22 of 650 responses | 2026-09-16 | cause found, partly fixed |
| [OBS-019](#obs-019) | Showing the model its citizens' emotions, at zero weight, multiplies mobilization fourteenfold | 2026-09-17 | cause found |
| [OBS-020](#obs-020) | Without n-gram speculation, two same-seed live runs are not always byte-identical | 2026-09-20 | open |
| [OBS-021](#obs-021) | 5 to 12% of chamber deliberation units fall back because the model returns more shifts than the cap allows | 2026-09-25 | cause found |
| [OBS-022](#obs-022) | The positioning prompt of three elections sends the model to its 9,836-token limit; only the retry answers | 2026-09-26 | open |
| [OBS-023](#obs-023) | The 2,048-token thinking budget binds on 86% of `vote_cast` calls at population 500, against 25% at population 100 | 2026-09-26 | open |
| [OBS-024](#obs-024) | A `vote_cast` batch of three sometimes answers for one voter, identically on all three attempts, and falls back | 2026-09-27 | open |
| [OBS-025](#obs-025) | `reaction_to_event` batches of 25 fall back whole when the model overshoots `events.max_reaction_delta` | 2026-09-27 | cause found |
| [OBS-026](#obs-026) | The develop→polity sync of 2026-09-27 changes what Kemeny-Young and majority judgment return | 2026-09-27 | recorded |
| [OBS-027](#obs-027) | A legislative seat tie now goes to a seeded lot, not to the lowest `party_id` | 2026-09-27 | recorded |
| [OBS-028](#obs-028) | The president agent repeats its speech while its situation does not change; a turn temperature of 0.6 does not stop it | 2026-09-28 | fixed |
| [OBS-029](#obs-029) | No party is ever founded: citizen agents answer `party_move: none` on 99% of forum turns | 2026-09-29 | fixed |
| [OBS-030](#obs-030) | The chamber voted yes on 95% of amendments, the president's own included, because the ballot said nothing of who asked | 2026-09-30 | fixed |
| [OBS-031](#obs-031) | An agent's schema decides more than its wording: an optional act field is never used, a required one is | 2026-09-30 | fixed |
| [OBS-032](#obs-032) | Every entry in the limit-testing log names an act the answer already has a field for | 2026-09-30 | fixed |
| [OBS-033](#obs-033) | A president could not propose abolishing the term limit: the model writes `"null"`, the kernel wants `null` | 2026-09-30 | fixed |
| [OBS-034](#obs-034) | Once citizens can found parties, the count climbs for years: self-limiting, but not within three | 2026-10-01 | cause found |
| [OBS-035](#obs-035) | The limit-testing log's one real ask is a way to reach voters; no agent ever reaches for an extra-legal act | 2026-10-02 | open |
| [OBS-036](#obs-036) | Campaigning left 91% of citizens near single-issue by year 8: the audience is most of the electorate | 2026-10-02 | fixed |
| [OBS-037](#obs-037) | Capped, campaigning still doubles attention concentration: nominees converge on one issue | 2026-10-03 | accepted |
| [OBS-038](#obs-038) | The chamber ratified a third presidential term 14 to 15, its ballots echoing the proposer's reason | 2026-10-03 | fixed |
| [OBS-039](#obs-039) | Party foundings never reached the explorer or any agent's memory: the two events were never registered | 2026-10-05 | fixed |
| [OBS-040](#obs-040) | At ten seeds the effective number of parties is inside the 1.5-8 band at both elections in none | 2026-10-05 | decided |
| [OBS-041](#obs-041) | A president elected off the calendar is told the next election up to 15 ticks late, which hid `refuse_to_leave` | 2026-10-05 | fixed |
| [OBS-042](#obs-042) | Two citizens in three stay home at a presidential election, most by indifference rather than disengagement | 2026-10-05 | fixed |
| [OBS-043](#obs-043) | Agents were told a citizen's own party counts for more at the ballot; in every run it counted for nothing | 2026-10-07 | fixed |
| [OBS-044](#obs-044) | Ten seeds again with OBS-041-043 fixed: turnout recovers, fragmentation does not, and `refuse_to_leave` is reachable but not taken | 2026-10-09 | recorded |
| [OBS-045](#obs-045) | Founders told the seat threshold is 3% or 7% found a party at the same rate, 59 of 60 either way | 2026-10-09 | open |

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

*Since [OBS-041](#obs-041) (2026-10-05),* the deterministic engine shows 10 distinct presidents, not 11:
its run has recalls, and their snap winners now serve only until the calendar's next election, so the
elections fall on different ticks. The LLM engine still shows 11.

*Since 2026-10-10* (`feat/polity-half-term-counts`): a term won with less than half of it left no longer counts
against the limit, so a snap winner keeps their one term. With the limit at 1 the deterministic engine shows 7
distinct presidents and the LLM engine 9.

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

*Follow-up, 2026-09-16: which channel, whether D9's knobs reach it, and the gap to the LLM path.*
`scripts/probe_twin_presidency.py` measures each option D9 names, alone, on this twin, then
compares what its citizens do under pressure with the p500 LLM runs. It is exploratory and adopts
nothing. Every number below is in `scripts/probe_twin_presidency_results.md`.

- **It is the mobilization channel, not petitions.** With the petition channel off the twin is
  unchanged: 0 full terms of the 20 possible, 79 of 92 presidencies recalled. With mobilization
  off, 13 of 20 terms run their full 16 ticks and the median presidency lasts 13. Both off gives
  20 of 20 and no recall, which checks the measure.
- **No knob D9 names reaches it alone.** The recall floor at 0.10 or 0.05 yields 2 full terms of
  20. Removing street pressure's memory entirely (decay 0.00) or halving legitimacy's
  (0.5, so an écart is amplified ×2 rather than ×10) yields 6, and still recalls 71–74% of
  presidencies. Amplification is not the cause: the rate is.
- **The rate is the twin's, not the model's.** Of every consulted citizen's `pressure_action`:

  | run | consulted acts | mobilize | mobilizing per tick | wait for the election |
  |---|---:|---:|---:|---:|
  | twin, p100, 10 seeds | 13,163 | 3,684 (28.0%) | 11.16% of the population | 0 |
  | LLM, p500 seed 1 | 3,495 | 1 (0.0%) | 0.01% | 43 |
  | LLM, p500 seed 2 | 4,074 | 74 (1.8%) | 0.45% | 61 |

  The twin mobilizes 25 to 1,000 times as often as the LLM path it stands in for, and never waits
  for an election. `simple_rules.deterministic_pressure_action` reaches "mobilize" before "wait"
  for any consulted citizen whose gap passes their blank threshold, so waiting is only chosen
  when petitioning and mobilizing are both unavailable.

*What this changes for D9.* Of its options, the pressure weights and the recall floor are measured
here as insufficient on their own. The one left is the one it names last: a deterministic
pressure rule whose mobilization is calibrated against the LLM path's. Two cautions before
reading it as settled: the twin is population 100 and the LLM runs are 500, and only two
completed LLM seeds exist, one of which mobilized exactly once.

### OBS-016

**The root disk filled up: p500 seed 42 died at tick 13 and the GPU queue ran nothing.**

*Seen.* The root filesystem (`/dev/nvme0n1p6`, 128 GB) ran out of space between 10:20 and 10:24 on
2026-09-14. It had 3.3 GB free at 07:52 that morning.

- **Seed 42 died mid-tick.** Seed 42 of the S0.8 batch was on tick 13: its checkpoint for tick 12
  was written at 09:05 and its last event at 09:06. It crashed at 10:24 with `No space left on
  device` while rewriting `progress.json` after a model response. It left a 0-byte `digest.json`
  and `llm_calls_summary.json`.
- **The rest of the chain ran on a full disk.** The batch unit ended, the repeat-exclusion watcher
  (D10) ran, and the GPU queue started at 10:25. Every step failed at once, and every log line hit
  the same write error. No bake-off session, grammar arm, budget check, sampling arm or concurrency
  sweep ran.
- **Afterwards.** The machine was rebooted four times between 21:01 and 21:52. After the last boot
  the root filesystem had 76 GB free.

*Evidence.*

```bash
journalctl --since "2026-09-14 10:20" --until "2026-09-14 10:30" --no-pager | grep "No space"
tail -30 Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs/sweep-8y-p500-seed42.log
ls -la Vote-App-p500/fast_api_voter/scripts/seed_sweep_runs/sweep-8y-p500-seed42/run/sweep-8y-p500-seed42
```

*Suspected cause.* Unknown: what took the space was gone by the time it was looked at.

- **The batch itself writes little.** Seed 42's directory holds about 12 MB.
- **What else wrote to the root disk that morning.** This work, between 09:50 and 10:25:
  - the frontend dependencies reinstalled under Node 24 (the same size as before);
  - coverage reports from the backend and frontend suites, and the quality-ratchet outputs;
  - a `/code-review` run on the CI branch.

  Other sessions and system updates were also active.
- **A gap in the checks.** The hard constraint on local work checked free memory, not free disk,
  although the disk was at 98%.

*What would settle it.* A reproduction is not worth it. What would matter:

- Long runs and queues checking free disk before each step, and stopping cleanly below a floor.
- Local heavy work checking disk as well as memory.
- A resume of seed 42 from its tick-12 checkpoint needs its empty `digest.json` moved aside first:
  the sweep driver's `--resume-sweep` parses it and would fail on an empty file.

### OBS-017

**WebKit crashed mid-navigation to `/polity` in CI, once, while the other worker ran the heavy
fiches.**

*Seen.* GitHub CI's Playwright E2E job on PR #512 (run `35047429948`, job `104640251246`,
2026-09-16). `navigation.spec.ts`'s "navbar is visible on every surface" walks the six surfaces of
`src/routes.ts` in one WebKit context. The sixth navigation, `/laboratoire` -> `/polity`, failed:

```
Error: page.goto: WebKit encountered an internal error
Call log: - navigating to "http://localhost:3000/polity", waiting until "load"
```

It passed on retry in 7.6 s. `check-flaky.mjs` then failed the job, as it does for any test that
passes only on a retry. 391 tests passed.

- **The page's own code never ran.** The error-context snapshot in the job's report artifact still
  shows the *previous* page's DOM at the moment of failure, so the navigation died inside
  Playwright's WebKit driver before `/polity`'s JavaScript started: no canvas, no queries, no
  Recharts. `/polity` had loaded cleanly in the same job 90 seconds earlier
  (`/polity renders its own screen without a JS crash`, 2.2 s).
- **The timing points at the runner.** The job runs 392 tests on 2 workers
  (`fullyParallel: false` serialises within a file, not across files). The failing navigation's
  9.5 s window overlaps almost exactly with the other worker running `laboratoire.spec.ts`'s
  "systems" family fiches, the CPU-heavy Monte-Carlo mounts the Playwright config's own comment
  calls out.
- **Not the local WebKit failure.** This machine cannot navigate *any* page in WebKit; that is the
  snap-confined `libpthread` problem written up in `RETROSPECTIVE.md`, reproducible on every URL and
  absent on the runner. This one is a single intermittent hit on one navigation.
- **Not the two known `/polity` WebKit quirks** (the devtools logo's width, a `<select>` option wider
  than its box). Both are layout-width bugs, both were fixed and merged before this run.

*Evidence.*

```bash
gh api repos/Burbanit0/Vote-App/actions/jobs/104640251246/logs
gh api repos/Burbanit0/Vote-App/actions/artifacts/10428100988/zip   # playwright-report, error context
```

*Suspected cause.* Resource contention on the runner: two Playwright workers on a small shared-core
box, one driving a WebKit navigation while the other runs the heavy fiches. "WebKit encountered an
internal error" is what Playwright reports when its connection to the browser process is starved or
dropped, rather than anything the page did.

- **A reproduction attempt failed to reproduce it.** In the pinned
  `mcr.microsoft.com/playwright:v1.63.0-noble` image, `navigation.spec.ts` and `laboratoire.spec.ts`
  together, `--project=webkit --workers=2 --repeat-each=6` (276 tests) under a 4-CPU cap: 276
  passed, no crash. A 4-CPU allowance may simply be more slack than the runner had.

*What would settle it.*

- A second occurrence. If it lands on a different surface in the same loop, `/polity` is ruled out
  entirely; if it lands on `/polity` again, the page is worth another look.
- Forcing it under a tighter CPU cap than the 4 CPUs already tried.
- If it recurs, the fix belongs in CI scheduling -- `workers: 1` for the webkit project, or keeping
  `laboratoire.spec.ts` and `navigation.spec.ts` off the same runner at the same time -- not in the
  page.

### OBS-018

**The response contract, not the model, sets the president's stance in 22 of 650 responses.**

*Seen.* In Stage 4's step-1 recordings (LLM path, population 100, seeds 1–10, 16 years, recorded at
15a18d74), representative_response took 650 decisions and fell back in 246 of them. Every fallback
enacts silence with motif 308. Traced through each decision's attempts in the call log:

- **The common case: a silence cited 303.** 235 fallbacks came after three answers the schema
  rejects, because silence requires motif 308. In 234 of them all three answers were silence with
  motif 303, the legitimacy floor. The fallback enacts the silence the model chose, with another
  motif.
- **11 retried out of silence.** The first answer was a rejected silence (10 with motif 303, 1 with
  301). A retry at temperature 0.3 was then accepted as a concession (5) or a defiance (6), in
  seeds 1, 2, 5, 7, 8 and 10.
- **11 concessions dropped to silence without a retry.** The model's single answer was a valid
  concession, but a shift broke a config bound: 8 were larger than `mandate.max_response_delta`, 3
  aimed at dimension 20 with `issue_count` 20. Those bounds are checked after the retry loop.
- **The chamber shows the same gap at scale.** All 227 chamber_deliberation fallback batches, which
  covered 1,135 of 19,500 member decisions, broke a config bound on their only attempt, 220 of them
  by shifting more than `sortition_chamber.max_deliberation_shifts` (3) dimensions. Each fell back
  to the sincere, no-shift decision. campaign_positioning checks its bounds the same way, but did
  not fall back in these runs.

*Evidence.*

```bash
cd fast_api_voter && python3 - <<'PY'
import json
from collections import Counter, defaultdict
from pathlib import Path
paths = Counter()
for seed in range(1, 11):
    run = Path(f"scripts/stage4_llm_runs/s42-record/seed-{seed}/run/seed-{seed}")
    calls = defaultdict(list)
    for line in (run / "llm_calls.jsonl").read_text().splitlines():
        c = json.loads(line)
        if c.get("decision_type") == "representative_response":
            calls[(c["tick"], tuple(c["unit_ids"]))].append(c)
    for line in (run / "events.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e["event_type"] != "representative_response":
            continue
        answers = [json.loads(c["content"])["decisions"][0] for c in sorted(calls[(e["tick"], (e["citizen_id"],))], key=lambda c: c["attempt"])]
        seq = " > ".join(f"{a['stance']}/{a['motif']}" for a in answers)
        paths[f"{'fallback' if e['payload']['llm_fallback'] else 'accepted'} {seq} => {e['payload']['stance']}/{e['motif']}"] += 1
for path, n in paths.most_common():
    print(n, path)
PY
journalctl --user -u polity-stage4-s42-record --no-pager | grep -E 'exhausted every recovery attempt' | grep -oE '(schema validation|max_response_delta|max_deliberation_shifts|max_deliberation_delta|out of range)' | sort | uniq -c
```

*Cause (shown 2026-09-16).* Two separate mechanisms, both in `llm_behavior_engine`:

- **The silence–motif rule.** `ResponseDecision._check_stance_coherence` accepts silence only with
  motif 308. The model keeps citing 303 for a silence, so the decision is retried, and a retry
  samples at temperature 0.3 (`_RESPONSE_RETRY_TEMPERATURE`), which can land on another stance.
- **Bounds checked outside the retry.** `validate_response_decision`, `validate_chamber_decision`
  and `validate_positioning_decision` run after `_complete_and_decode_with_replay` returns. Their
  failure goes straight to the fallback, which the chamber's own comment states: "neither is
  retried further".

*Status and what would change it.*

- **The silence–motif rule is fixed** by #545 (4e8975c8, merged 2026-09-16): a silence may cite 303.
  That ends the 235 fallbacks and keeps the 10 retried silences silent. Stage 4's remaining runs
  stay on fe4bad5a, the commit before it, so they match step 1 (plan-polity-build-order.md, "Stage
  4 on the LLM path").
- **The bound checks outside the retry are unchanged.** Moving them inside the decode, so a bound
  failure is retried like a schema failure, is a separate decision. It would change the chamber
  most.

### OBS-019

**Showing the model its citizens' emotions, at zero weight, multiplies mobilization fourteenfold.**

*Seen.* Stage 4's step 2 and step 5 recorded the same bench twice on the LLM path (population 100,
30 chamber seats, seeds 1–10, 8 years, 12 relaxed workers, from fe4bad5a). The two run sets differ
in exactly one config field, `emotions.enabled`, with all four emotion weights at 0 in both:

| over 10 seeds | emotions off (`s41/zero`) | emotions on, zero weights (`s43-emotions/zero`) |
|---|---:|---:|
| presidential elections | 35 | 70 |
| recalls | 6 | 44 |
| full terms | 15 | 1 |
| pressure acts | 8,825 | 10,308 |
| MOBILIZE share of acts | 1.5% | 21.8% |
| NOTHING share of acts | 87.4% | 61.3% |
| mean legitimacy | 0.566 | 0.464 |

- **The weights do nothing here, and the mechanism confirms it.** The deterministic twin, run at the
  same ten seeds with emotions on at zero weights and then off, is identical on every count:
  101 elections, 77 recalls, 13,163 acts, 3,684 mobilizations both ways. No RNG draw and no
  threshold moves at zero weight.
- **So the channel is the prompt.** `emotions.enabled` adds anger, anxiety and enthusiasm to dt=10's
  pressure prompt (`llm_behavior_engine.pressure_signals`), whatever the weights. The model reads
  them and acts: the polity goes from one recall per two seeds to more than four per seed.
- **It lands near the twin's own rate.** The twin mobilizes 28% of consulted acts and the LLM path
  1.5% with emotions off (OBS-015, D9's divergence); with the fields in the prompt the LLM path
  reaches 21.8%.
- **E1 holds on it, E2 and E3 do not** (`scripts/stage4_llm_emotions_results.md`): 963 mobilizations
  in the angriest third of ticks against 489 in the calmest; 3,269 pressure acts in the most anxious
  third against 3,437 in the least; and E3 is unmeasurable, since the ten runs hold one full term.

*Evidence.*

```bash
cd fast_api_voter && python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path
root = Path("scripts/stage4_llm_runs")
for label, base in (("off", root / "s41/zero"), ("on, zero weights", root / "s43-emotions/zero")):
    tot, acts = Counter(), Counter()
    for seed in range(1, 11):
        run = base / f"seed-{seed}" / "run" / f"seed-{seed}"
        for line in (run / "events.jsonl").read_text().splitlines():
            e = json.loads(line)
            tot[e["event_type"]] += 1
            if e["event_type"] == "pressure_action":
                acts[e["payload"]["act"]] += 1
    n = sum(acts.values())
    print(label, "elected", tot["elected"], "recalled", tot["recalled"], "acts", n,
          {a: f"{100 * c / n:.1f}%" for a, c in sorted(acts.items())})
PY
# the two configs differ in emotions.enabled alone
diff <(jq -S .emotions scripts/stage4_llm_runs/s41/zero/seed-1/config.json) \
     <(jq -S .emotions scripts/stage4_llm_runs/s43-emotions/zero/seed-1/config.json)
```

*Cause (shown 2026-09-17).* The emotion fields in the prompt, and nothing else. The twin's
identical runs rule out every mechanical path; the fields are the only difference the model sees.
ADR-012's prerequisite session had already measured that the model reacts to anger in a single
decision (`scripts/bakeoff_emotions_prerequisite_results.md`: MOBILIZE 0 of 4 borderline citizens
at anger 0, 4 of 4 at 0.75). This is the same reaction compounded over a whole run.

*What would settle what to do about it.*

- **For S4.3:** whether any weight level restores full terms, so E3 can be read at all. Step 5's
  level 0.25 is recording for that reason; the runs, not this entry, answer it.
- **For D9 (OBS-015):** the twin's 28% mobilization was treated as the twin's defect against an LLM
  path that mobilized almost never. With emotions in the prompt, the LLM path sits at 21.8%. Which
  of the two rates is the target is a question for a new pre-registration, not a re-reading of this
  one.
- **For the runs already published:** every LLM run before step 5 had emotions off, so none of them
  is affected. What changes is that "emotions off" is not a neutral baseline: it is a choice that
  suppresses mobilization.

### OBS-020

**Without n-gram speculation, two same-seed live runs are not always byte-identical.**

*Seen.* Verifying the move to vLLM 0.29.0 (2026-09-20), `test_polity_vllm_live.py`'s
`test_two_short_live_runs_with_the_same_seed_are_byte_identical` (4 years, 100 citizens, one worker,
strict, shipped defaults) failed on the new server, which runs without `--speculative-config`. The same
pair of runs, by server:

| server | pairs run | result |
|---|---:|---|
| 0.28.0 + n-gram speculation (the old pin) | 1 | byte-identical (314 lines) |
| 0.29.0 + n-gram speculation | 1 | byte-identical (314 lines) |
| 0.29.0, no speculation | 3 | 2 differ, 1 identical. The live test failed at byte 37,287; a second pair differed on 15 of 312 lines, the first at line 133 (`campaign_positioning`, tick 0: different shifts and motifs). The last pair, in the full live suite, was byte-identical (`XPASS`). |
| 0.30.0, no speculation (2026-09-24) | 1 | differs (`XFAIL` in the full live suite; where it diverged was not examined). Replay from the call log passed. |
| 0.30.0, no speculation (2026-09-25, same session as the EAGLE-3 pairs) | 5 | all 5 byte-identical (`XPASS`) |
| 0.30.0 + EAGLE-3 (2026-09-25, `check_vllm_eagle3_results.md`) | 8 | 6 identical, 2 differ; both differing pairs were the first pair after a server restart, every later pair was identical |

- **Short generations still reproduce.** `check_vllm_batching_determinism.py` passes on the new setup
  within a run (batch sizes 1 to 50, 10 sequential calls) and across a restart. The divergence is in
  long thinking generations.
- **The frozen bank shows the runner difference too.** Against the 0.28.0 control session, 160 of 174
  answers are identical. Thirteen differ because of the server: `positioning_poles` 9 of 10,
  `chamber_poles` 3 of 10 (two validity flips, both `finish_reason='length'`) and one `candidacy_p500`
  case. Every short-answer family is identical. (A 14th, in `response_sweep`, differs because #545 now
  accepts a silence that cites motif 303.) Both long families were already fragile: the control's own
  re-render agreement is 1 of 6 on positioning and 6 of 10 on chamber.

*Evidence.*

```bash
cd fast_api_voter
# against each server in turn; XPASS when the pair is identical, xfail when it is not
POLITY_VLLM_LIVE=1 POLITY_VLLM_URL=http://localhost:8000/v1 python -m pytest \
  api/tests/test_polity_vllm_live.py -k same_seed -o addopts="" -rxX -q
docker logs vllm-polity 2>&1 | grep -E "Using V2 Model Runner|does not yet support ngram"
```

*Suspected cause.* Model Runner V2. The only configuration difference between the arms is
`--speculative-config`; with it vLLM logs "Model Runner V2 does not yet support ngram ... using the V1
model runner instead", without it "Using V2 Model Runner". This is a suspicion, not a finding: 3 pairs
against 2, and the pass in the last pair shows the failure is intermittent. Two other candidates are not
excluded: the prefix cache (the second run reads KV blocks the first filled, and prefill numerics can
differ on a cache hit), and V2 and "no speculation" are coupled, so they were not separated (0.28.0
without speculation also engages V2, but its pairs were not run).

*What would settle it.* Five or more same-seed pairs per setup (about 7 minutes each): the new setup,
the new setup with `--no-enable-prefix-caching`, and 0.28.0 + speculation.

*Status: open.* The owner accepted the risk on 2026-09-20 in exchange for dropping speculation (no gain on
12-worker runs). The live byte-identity test is now `xfail(strict=False)`, and a new test checks what a
run does promise: replay from its own call log (D1, S0.6) is byte-identical (it passed). Sequential
bake-off-style sessions also cost more without speculation: the full frozen bank took 22.7 minutes
against 15.9 on the control (structured-output types 1.7 to 2.9 times slower).

*Update 2026-09-26.* The shipped server now runs EAGLE-3 on Model Runner V2 (`docker-compose.llm.yml`,
adopted by the owner; `check_vllm_eagle3_results.md`). The owner does not rely on same-seed byte-identity:
what a run leaves for analysis is its call log (`llm_calls.jsonl`), and a relaxed run replays from it. The
question this entry asks (why two same-seed runs differ) stays open and is now a question about EAGLE-3
on V2, of which the table above holds 8 pairs (6 identical).

### OBS-021

**5 to 12% of `chamber_deliberation` units fall back to "sincere, no shift" because the model returns more
shifts than the cap allows.**

*Seen.* Checking the move to vLLM 0.30.0 (2026-09-25), three 8-year, 100-citizen, 15-seat, one-worker runs
(seeds 1 to 3) and a two-seed control on 0.29.0, all on the same code. Chamber fallback, in units of 495:

| server | seed | fallback units | rate |
|---|---:|---:|---:|
| 0.30.0 | 1 | 60 | 12.1%, over the 10% alert line |
| 0.30.0 | 2 | 35 | 7.1% |
| 0.30.0 | 3 | 25 | 5.1% |
| 0.29.0 | 1 | 45 | 9.1% |
| 0.29.0 | 2 | 30 | 6.1% |

The recorded Track D sweep (2026-09-12) had 0 on seeds 1 and 3 and about 1% on seed 2.

- **It is not a decode failure.** All 100 answer calls of seed 1 decode. A chunk falls back when
  `validate_chamber_decision` rejects a decoded answer, and `_chamber_chunk` does not retry a validation
  failure, so the whole chunk of five falls back (`llm_behavior_engine.py`).
- **The rule that fails is the shift count.** Replaying the rules on seed 1's recorded calls: 13 of the 100
  answer calls fail (the digest counts 60 units, 12 chunks); 36 decisions carry more shifts than
  `sortition_chamber.max_deliberation_shifts` = 3 (five, in the examples), and 1 shifts a dimension by more than
  0.3. Seed 2: 10 of 102 answer calls, 22 decisions, all too many shifts. In the first seed-1 example all
  five shifts have `delta` 0.0, so the fallback equals what the model said; in seed 2's the five deltas are real.
- **It is not the server.** It is present on 0.29.0 with the same code, and 0.30.0's rate is not significantly
  different (75 against 95 units of 990, Fisher p = 0.13, which overstates because units fall in chunks of five).

*Evidence.*

```bash
cd fast_api_voter
# per-run fallback rates, from the digest each run writes
python -c "import json;d=json.load(open('<run_dir>/digest.json'));print(d['llm_fallback_rates'])"
# the replay: parse each chamber answer in <run_dir>/llm_calls.jsonl and count shifts > 3 or |delta| > 0.3
```

*Suspected cause.* Configuration that did not exist in the recorded sweep and is in today's runs:
`llm.thinking_token_budget` = 2048 (absent then, so the chamber's thinking was limited only by its 8000-token allowance), the vote_cast
grammar invariants, `vote.turnout_cost` = 0.04 and `institutions.president_term_limit` = 2. The 2048
budget is the suspect, because a deliberation cut short may list every dimension, but nothing isolates it: the
recorded sweep has no per-call log (S0.5 came later), so its chamber answers cannot be inspected.

*What would settle it.* Seed 1 again on 0.30.0 with the thinking budget off, and the same replay: fallback rate
and the distribution of shifts per decision. If the budget is the cause, a validation failure could be
treated like a decode failure (replayed), or zero-delta shifts dropped before the count is checked; neither is done.

*Status: open.* The 10% alert threshold was crossed in one of five runs; the runs still complete with office
occupancy in the recorded band.

*Update 2026-09-26, the full run (30 years, 500 citizens, 75 seats, EAGLE-3, 12 workers, relaxed:
`full-30y-p500-seed42-20260926`, `plan-full-run.md`).* The cause is now shown, at 5 times the seats and 3.75 times
the years of the runs above. 640 of 9,075 chamber units fell back (7.05%; the 10% alert did not fire), inside the 5
to 12% that plan wrote down before the run. They are 128 of the 1,815 first-attempt answer calls, and every failed
call lost all five of its units (128 x 5 = 640).

- **The rule is the shift count.** In 127 of the 128 failed calls at least one decision carries more than
  `max_deliberation_shifts` = 3 shifts; that is 420 units, 419 of them with all five dimensions shifted. In the
  other failed call a shift exceeds `max_deliberation_delta` = 0.3.
- **One over-long answer costs its four batch-mates.** The other 219 fallback units answered within the caps (207 of
  them "no shift") and were discarded with the offender's chunk.
- **Nothing was retried.** 127 of the 128 failed calls are attempt 0; the 128th is attempt 1 of a batch that first
  failed to decode. Retries did happen elsewhere in the chamber (36 batches, 35 recovered; their cause was not
  inspected), which fits the reading above that `_chamber_chunk` does not replay a validation failure.
- **The fallback events do not say why.** Their payload has `shifts`, `llm_call_id` and `retry_sampling_varied` but
  no reason, so the count above needs the replay against `llm_calls.jsonl`.

```bash
cd fast_api_voter && python3 - <<'EOF'
import json, collections
run = "<out>/full-30y-p500-seed42-20260926/run/full-30y-p500-seed42-20260926"
calls = {c["call_id"]: c for c in map(json.loads, open(run + "/llm_calls.jsonl"))
         if c["kind"] == "decision" and c["decision_type"] == "chamber_deliberation"}
failed = {e["payload"]["llm_call_id"] for e in map(json.loads, open(run + "/events.jsonl"))
          if e["event_type"] == "chamber_deliberation" and e["payload"].get("llm_fallback")}
over = sum(any(len(d["shifts"]) > 3 for d in json.loads(calls[c]["content"])["decisions"]) for c in failed)
print(len(failed), "failed calls,", over, "with a decision over the shift cap")
EOF
```

What is still not settled is the trigger: whether the 2,048 thinking budget makes the model list every dimension. The
full run has the same 2,048 budget, so it cannot isolate it either. Status moves to **cause found**: what to do about
it (replay a rejected answer like a decode failure, or drop zero-delta shifts before the count) is not decided.

*Update 2026-09-27, seeds 1 and 2 of the same run (`full-30y-p500-seed1-20260926`, `-seed2-`, same code and config).*
Chamber fallback is 5.79% (seed 1) and 7.11% (seed 2), against 7.05% for seed 42. Over the three runs 362 answer calls
failed, and every one lost all five units (128, 105 and 129). The validation rules explain 361 of the 362: 356 have a
decision over `max_deliberation_shifts`, 5 shift a dimension past `max_deliberation_delta` (by 0.32 to 1.0), and one
(seed 1, tick 19) answered all five units within both caps and is not explained.

```bash
cd fast_api_voter && python3 - <<'EOF'
import json, collections
out = "<out>"
for seed in ("42", "1", "2"):
    run = f"{out}/full-30y-p500-seed{seed}-20260926/run/full-30y-p500-seed{seed}-20260926"
    calls = {c["call_id"]: c for c in map(json.loads, open(run + "/llm_calls.jsonl"))
             if c["kind"] == "decision" and c["decision_type"] == "chamber_deliberation"}
    failed = {e["payload"]["llm_call_id"] for e in map(json.loads, open(run + "/events.jsonl"))
              if e["event_type"] == "chamber_deliberation" and e["payload"].get("llm_fallback")}
    kinds = collections.Counter()
    for cid in failed:
        d = json.loads(calls[cid]["content"])["decisions"]
        if any(len(x["shifts"]) > 3 for x in d): kinds["shift cap"] += 1
        elif any(abs(s["delta"]) > 0.3 for x in d for s in x["shifts"]): kinds["delta cap"] += 1
        else: kinds["within caps"] += 1
    print(seed, len(failed), dict(kinds))
EOF
```

### OBS-022

**The positioning prompt of three elections sends the model to its 9,836-token limit; only the retry answers.**

*Seen.* The full run (`full-30y-p500-seed42-20260926`) held 11 elections, so 11 `campaign_positioning` batches
(five parties each, 55 decisions) and 14 answer calls. At ticks 0, 16 and 28 the first attempt thought until it hit
`max_tokens` = 9,836 (9,835 reasoning tokens, `finish_reason` `length`, no answer, 111 to 112 s). The retry
(attempt 1, a varied seed) answered after 9,453 reasoning tokens (114 to 117 s). At the other eight elections the first
attempt answered in 1,762 to 5,856 reasoning tokens (18 to 60 s). No positioning decision fell back (0 of 55).

- **It is the prompt, not chance.** The attempt-0 requests of ticks 0, 16 and 28 have the same `request_sha256`; so do
  ticks 42, 64, 91 and 112, and ticks 80 and 96. The positioning input repeats between elections (OBS-001), and at
  temperature 0 the same request runs away each time. The retry's different sampling is what gets out.
- **It sets the slowest ticks of the run.** Ticks 16, 0 and 28 took 349, 347 and 343 s against a median of 47.5 s (the
  next slowest is 206 s), among the 98 ticks the minute-by-minute telemetry sampled. About 230 s of each is the two positioning calls, one after the other.
- **It is not covered by the thinking budget.** `llm.thinking_token_budget` = 2048 caps `vote_cast` and
  `chamber_deliberation` only; positioning is uncapped in production.

*Evidence.*

```bash
cd fast_api_voter && python3 - <<'EOF'
import json
run = "<out>/full-30y-p500-seed42-20260926/run/full-30y-p500-seed42-20260926"
for c in map(json.loads, open(run + "/llm_calls.jsonl")):
    if c["kind"] == "decision" and c["decision_type"] == "campaign_positioning":
        print(c["tick"], c["attempt"], c["request_sha256"][:8], c.get("reasoning_tokens"), c["finish_reason"], round(c["latency_ms"] / 1000))
EOF
```

*Suspected cause.* Nothing shows why this one prompt (the party set of ticks 0, 16 and 28) makes the model think without
end while the two other party sets do not. The S2.4 bank found the same failure on two other models (9,716 tokens with
no answer) and Qwen's median there was 4,002, so it is not specific to this run.

*What would settle it.* A bank arm for `campaign_positioning` with a thinking budget (`THINKING_ARM_TYPES` covers only
vote and chamber), then the budget on this prompt: does it answer, and is the answer the retry's? If every attempt
(the first and two replays) had run away, the batch would have fallen back to the deterministic baseline, which is
the risk this run happened not to hit: three of eleven first attempts failed.

*Status: open.*

*Update 2026-09-27, seeds 1 and 2.* Neither had the runaway: 0 of 9 first attempts in seed 1 and 0 of 12 in seed 2 reached
the limit, against 3 of 11 in seed 42. So it belongs to seed 42's party set (the request that repeats at ticks 0, 16 and
28), not to positioning in general, and it is one seed of three. The slowest tick is 184 s in seed 1 and 177 s in seed 2,
against 349 s in seed 42.

### OBS-023

**The 2,048-token thinking budget binds on 86% of `vote_cast` calls at population 500, against 25% at population 100.**

*Seen.* In the full run 192 of 223 `vote_cast` answer calls (86%) ended their thinking at exactly the budget, 2,048
reasoning tokens. `plan-full-run.md` had the figure from the 2-year, 100-citizen run as 25%. For `chamber_deliberation`
the rate matches that run: 761 of 1,852 calls (41%; it was 41 to 45%), and it is flat over the run (40%, 40% and 43%
for ticks 0 to 39, 40 to 79 and 80 to 119).

| election tick | `vote_cast` calls | at 2,048 | median prompt tokens |
|---:|---:|---:|---:|
| 0 | 18 | 7 | 1,929 |
| 16 | 19 | 19 | 3,856 |
| 28 | 19 | 19 | 2,913 |
| 32 | 19 | 16 | 2,498 |
| 42 | 22 | 22 | 2,773 |
| 48 | 27 | 25 | 2,781 |
| 64 | 17 | 17 | 3,327 |
| 80 | 17 | 17 | 2,922 |
| 91 | 25 | 21 | 2,639 |
| 96 | 19 | 8 | 2,373 |
| 112 | 21 | 21 | 4,129 |

- **It mostly costs nothing.** `vote_cast` fell back for 3 units of 583 (0.5%), all one batch at tick 91 (the snap
  election after the president's removal at tick 90). Its three attempts (seeds 900000002 and 900000003 for the
  retries) each used the full 2,048 tokens and returned a decision for one of the three voters (`{"blank": 1,
  "cid": 292, ...}`), so the batch fell back. That is one batch of 223.
- **The two elections where it binds least have the shortest prompts** (ticks 0 and 96, 1,929 and 2,373 median
  tokens; every other election is at 2,498 or more and binds on 84 to 100%). That is 11 points, not a fit.

*Evidence.*

```bash
cd fast_api_voter && python3 - <<'EOF'
import json, collections, statistics
run = "<out>/full-30y-p500-seed42-20260926/run/full-30y-p500-seed42-20260926"
by = collections.defaultdict(list)
for c in map(json.loads, open(run + "/llm_calls.jsonl")):
    if c["kind"] == "decision" and c["decision_type"] == "vote_cast":
        by[c["tick"]].append(c)
for t, cs in sorted(by.items()):
    print(t, len(cs), sum(c["reasoning_tokens"] == 2048 for c in cs), int(statistics.median(c["prompt_tokens"] for c in cs)))
EOF
```

*Suspected cause.* A longer vote prompt (a larger field, with the standing rupture candidates of OBS-001) makes the model
deliberate longer. The prompts are in `llm_prompts.jsonl` (`read_prompts`), so the candidate counts can be read
next to the token counts; that was not done.

*What would settle it.* The same elections with a budget of 4,096 and of no budget on `vote_cast`: does the winner or
the ranking change? S1.3 found a 2,048 budget "loses nothing" on the frozen bank; this says how often the flagship
sits at the cap, not whether the cap changes a result.

*Status: open.*

*Update 2026-09-27, seeds 1 and 2.* The `vote_cast` budget binds on 157 of 186 calls (84%) in seed 1 and 152 of 210 (72%) in
seed 2, against 192 of 223 (86%) in seed 42; the chamber on 826 of 1,861 (44%) and 748 of 1,870 (40%), against 41%. So the
`vote_cast` rate is high at population 500 on all three seeds (72 to 86%) and the chamber rate is stable (40 to 44%).
Whether the budget changes a result is still not measured.

*Update 2026-09-28, the agents (ADR-014).* The agents' turns sit at the cap more often still. In
`p1-nominees-5y-p200-seed1` (`~/Documents/Dev/polity-runs/p1/`, exploration profile, 5 years, p200),
counting `llm_calls.jsonl` lines of `kind` "decision":
- 21 of 22 `president_turn` calls reach 2,048 reasoning tokens;
- 9 of 10 `nominee_turn` calls do;
- every one of them still finishes (`stop`) with a valid turn.

The budget probes before each turn end on `length` by construction and are not counted. So the cap
does what it was set on these types for, no runaway (OBS-022), and it bounds the agents' reasoning
almost always. Whether a larger cap gives better turns is the same open question as for
`vote_cast`.

### OBS-024

**A `vote_cast` batch of three sometimes answers for one voter, identically on all three attempts, and falls back.**

*Seen.* Across the three full runs, 9 `vote_cast` batches of three voters fell back after all three attempts: 1 in seed 42,
4 in seed 1 and 4 in seed 2 (27 units: 0.5%, 2.7% and 2.1% of each run's `vote_cast` decisions, from `llm_fallback_rates`).

- **All 27 attempts used the full 2,048 reasoning tokens.** The failures happen only where the thinking budget binds.
- **7 of the 9 batches returned a decision for one voter of three, and the same answer on all three attempts** (seed 42
  tick 91; seed 1 ticks 11, 48 and 64; seed 2 ticks 56 and 64, twice), although attempts 1 and 2 carry different seeds
  (900000002 and 900000003). The retries changed nothing.
- **The other two returned all three voters and were rejected** (seed 1 tick 112: two distinct answers over three attempts;
  seed 2 tick 48: three distinct answers, one of which answered for one voter only).

*Evidence.*

```bash
cd fast_api_voter && python3 - <<'EOF'
import json, collections
out = "<out>"
for seed in ("42", "1", "2"):
    run = f"{out}/full-30y-p500-seed{seed}-20260926/run/full-30y-p500-seed{seed}-20260926"
    calls = [c for c in map(json.loads, open(run + "/llm_calls.jsonl")) if c["kind"] == "decision" and c["decision_type"] == "vote_cast"]
    failed = collections.defaultdict(set)
    for e in map(json.loads, open(run + "/events.jsonl")):
        if e["event_type"] == "vote_cast" and e["payload"].get("llm_fallback"):
            failed[(e["tick"], e["payload"]["llm_call_id"])].add(e["citizen_id"])
    for (tick, _), units in sorted(failed.items()):
        att = sorted((c for c in calls if c["tick"] == tick and set(c["unit_ids"]) >= units), key=lambda c: c["attempt"])
        print(seed, tick, "reasoning", [c["reasoning_tokens"] for c in att],
              "answered", [len(json.loads(c["content"])["decisions"]) for c in att], "distinct", len({c["content"] for c in att}))
EOF
```

*Suspected cause.* When the budget cuts the thinking short the model closes its answer early, and the retry, replaying the same
prompt, lands on the same answer. Not shown: the content of the reasoning was not read.

*What would settle it.* Replay these nine batches with a budget of 4,096 (the `vote_cast` bank arm, `--arm thinking_budget_2048`
with another value): if they answer all three voters, the budget is the cause. Whether `retry_sampling_varied` changes anything
for `vote_cast` is the second question, since the retry produced the same answer in 7 of 9.

*Status: open.*

### OBS-025

**`reaction_to_event` batches of 25 fall back whole when the model overshoots `events.max_reaction_delta`.**

*Seen.* Seed 42 had no `reaction_to_event` fallback. Seed 1 lost one batch of 25 units (tick 95) and seed 2 two (ticks 43 and 97):
75 units, 0.83% and 1.67% of the type's decisions. In the batch checked (seed 2, tick 97) the model answered for all 25 units.

- **The rule is the delta bound.** `validate_reaction_decision` rejects a `salience_delta` above `events.max_reaction_delta`
  (0.3). In that answer 16 of the 25 deltas exceed it (range 0.2343 to 0.3627), so the whole batch fell back.
- **It is the same failure as OBS-021.** The prompt states the bound, the model overshoots it, and one bad answer discards
  the batch (25 units here, five in the chamber).
- **Retries.** The call each fallback event points to is attempt 2 for seed 1 tick 95 and seed 2 tick 43, and attempt 0 for
  seed 2 tick 97, which fell back without a replay.

*Evidence.*

```bash
cd fast_api_voter && python3 - <<'EOF'
import json
run = "<out>/full-30y-p500-seed2-20260926/run/full-30y-p500-seed2-20260926"
fb = [e for e in map(json.loads, open(run + "/events.jsonl"))
      if e["event_type"] == "reaction_to_event" and e["payload"].get("llm_fallback") and e["tick"] == 97]
cid = fb[0]["payload"]["llm_call_id"]
call = next(c for c in map(json.loads, open(run + "/llm_calls.jsonl")) if c["call_id"] == cid)
deltas = [d["salience_delta"] for d in json.loads(call["content"])["decisions"]]
print(len(fb), "units fell back; answered", len(deltas), "; over 0.3:", sum(x > 0.3 for x in deltas), "; range", min(deltas), max(deltas))
EOF
```

*What would settle it.* The same replay on the two other batches (only one was read). The lever is the one OBS-021 names: replay
a rejected answer, or fall back per decision so that one overshoot does not discard 24 good answers.

*Status: cause found* (for the batch read).

### OBS-026

**The develop→polity sync of 2026-09-27 changes what two configurable polity voting rules return: Kemeny-Young and majority judgment.**

*Seen.* Not in a run: in the merge. polity's `config.py:28-30` lets a run pick any rule from the engine, including
`kemeny_young` and `majority_judgment`, and develop rewrote both before this sync:

- Kemeny-Young (#604, #605). The winner used to depend on `PYTHONHASHSEED` (candidate order came from a set) and,
  above 6 candidates, on a KwikSort approximation. It is now exact up to 10 candidates, in a fixed order, and a
  truncated ballot no longer credits a phantom duel win to the candidate listed second.
- Majority judgment (#538). The tie-break between candidates sharing a median grade was `p − q` plus one strip step.
  It is now the real Balinski-Laraki one (strip median grades until they differ).

The default config (`two_round` + `dhondt`) calls neither, and `polity_golden.json` passed unchanged on the merged
tree (3076 backend tests green).

*Suspected cause.* Not an anomaly in the simulation: two engine fixes arriving through the merge. Recorded because a
run that selects either rule, or a comparison with a result from before 2026-09-27, can now differ for this reason
alone.

*What would settle it.* Re-running one past run configured with `kemeny_young` or `majority_judgment`, at the same
seed and pre-/post-merge commits, would show whether any election outcome changed. Only needed if such a run is cited.

*Status: recorded (engine change, not a bug).*

### OBS-027

**A legislative seat tie now goes to a seeded lot, not to the lowest `party_id`.**

*Seen.* Not in a run: a change. `allocate_seats` used to hand an exact quotient or remainder tie to the first-listed
party, which in `_hold_legislative_election` is the lowest `party_id`: a structural edge for the party created first,
invisible in any single run. That edge is removed at the seat stage only: polity's own configured rules still break
ties by `party_id` upstream and downstream, namely `choose_party` (`simple_rules.py`, an equidistant or equal-utility
voter picks the lowest `party_id`) and the formateur tie in `form_coalition`. Those are left as they are on purpose. Each legislative election now draws its ties from `random.Random("legislative-seats:<seed>:<tick>")`,
the same seeded-lot rule as the rest of the app (#638, #643, #659).

The golden references (`gen_polity_golden.py --check`) and the explorer fixture regenerate unchanged, so no recorded run
hit an exact seat tie; results before and after this change differ only in a run that does.

*Suspected cause.* Not an anomaly: the fix for E1 of the 2026-09 audit plan.

*What would settle it.* Nothing to settle. If a past run is re-run and its seats differ, check this entry first.

*Status: recorded (behaviour change).*

### OBS-028

**The president agent repeats its speech while its situation does not change; a turn temperature
of 0.6 does not stop it.**

*Seen.* Two live runs of the exploration profile (ADR-014's president agent, Qwen3-8B-AWQ with
EAGLE-3, 3 years, p200, seed 42, 12 workers), differing in `agents.turn_temperature`:

| | temperature 0 | temperature 0.6 |
|---|---:|---:|
| turns | 13 | 13 |
| distinct speeches | 13 | 11 |
| mean similarity of consecutive speeches | 0.62 | 0.53 |
| highest similarity of consecutive speeches | 0.95 | 1.00 |
| moves / reversals on an issue | 18 / 9 | 11 / 6 |
| approval range | 0.690-0.745 | 0.685-0.715 |

At 0.6, ticks 5 and 6 carry the same speech word for word ("I remain committed to climate action,
public housing, and a public role for religion. These pillars…"); tick 10 repeats it again. In
both runs, "direct democracy" moves back and forth (at 0.6: +0.12, -0.12, +0.30, -0.30). In
neither run did the president hold the agenda: every bill (ticks 8, 10, 12) was the
government's, under cohabitation.

To see it again: the runs are `p1-president-agent-3y-p200-seed42` and
`p1-turn-temp06-3y-p200-seed42` in `~/Documents/Dev/polity-runs/p1/`. Similarity is
`difflib.SequenceMatcher(None, a, b).ratio()` over consecutive `agent_turn` speeches, and a reversal
is a move on an issue opposite to that issue's previous move.

*Suspected cause.* The situation, not the sampling.
- With no agenda, a president's only lever is restating their position, and approval moves within a
  few hundredths.
- The prompt is therefore nearly the same from tick to tick.
- The memory puts the agent's own last speeches in front of it (`AgentMemory.recall`, "you
  said: …"), and a model shown its own words tends to repeat them.

The reversals look like a president oscillating between their conviction and their pledge (the
rationales say "align with my convictions" one tick and "reduce the gap" the next).

*What would settle it.*
- An arm whose memory shows the agent's past moves and notes but not its past speeches.
- A seed where the president holds the agenda.
- Several seeds per arm: one run per arm cannot separate a temperature effect from noise.

The roadmap's later phases (a forum, other agents, polls that move) change the situation itself.

*Cause.* The echo. The same day, both arms ran on three seeds (42, 1, 2) at temperature 0.6, from
worktrees at `26972d4f` (the agent's memory shows its past speeches) and `c22b3ba5` (it shows its
moves, bills, notes and standings, but not its speeches). The runs are `obs028-{base,nospeech}-seed{1,2}`
and `obs028-nospeech-seed42` in `~/Documents/Dev/polity-runs/obs028/`, plus the seed-42 baseline
above, measured as above.

| seed | arm | distinct speeches | mean / highest similarity | moves / reversals | agent bills |
|---|---|---:|---:|---:|---:|
| 42 | speeches shown | 11 / 13 | 0.53 / 1.00 | 11 / 6 | 0 |
| 42 | speeches left out | 13 / 13 | 0.47 / 0.78 | 8 / 3 | 0 |
| 1 | speeches shown | 13 / 13 | 0.53 / 0.87 | 6 / 3 | 3 |
| 1 | speeches left out | 13 / 13 | 0.47 / 0.65 | 0 / 0 | 3 |
| 2 | speeches shown | 12 / 13 | 0.63 / 1.00 | 10 / 5 | 3 |
| 2 | speeches left out | 13 / 13 | 0.49 / 0.69 | 4 / 0 | 3 |

- **Every seed moves the same way.** Without the echo, mean and highest similarity fall in all three seeds, no speech repeats exactly, and reversals fall.
- **The agenda is not the cause.** Seeds 1 and 2 gave the president the agenda (three agent bills each; one passed in seed 2), yet the arm with speeches still repeated a speech word for word at seed 2.
- **Side effect.** Without its speeches the president moves less. At seed 1 it restated nothing in 13 turns: watch for passivity.
- **The limit-testing log asks for a public campaign.** In both arms, `other_initiative` asks for "a public campaign" or "public outreach" (4 of the 6 runs). The menu has no such act; the roadmap's forum (Phase 3) is where it lands.

*Status: fixed* on `feat/polity-memory-without-own-speech`: `AgentMemory` leaves an agent's own
past speeches out.

### OBS-029

**No party is ever founded: citizen agents answer `party_move: none` on 99% of forum turns.**

*Seen.* Three live runs of the exploration profile after ADR-021 (Qwen3-8B-AWQ, 8 years, p100, 15 chamber
seats, seeds 1-3, about 2 h 20 min each, `~/Documents/Dev/polity-runs/phase4/eng-8y-p100-seed{1,2,3}`).
Phase 4's exit asks for a party count that changes in at least 30% of seeds. It changed in none.

| | seed 1 | seed 2 | seed 3 |
|---|---:|---:|---:|
| forum posts | 519 | 533 | 538 |
| `party_move` other than none (applied by the kernel) | 0 | 0 | 1 (a `join 2`) |
| parties founded / dissolved | 0 / 0 | 0 / 0 | 0 / 0 |

- **The kernel is not what refuses.** In seed 3's call log the model answered `none` 545 times and
  `join` 4 times, and never `found`. The co-founder rule (`parties.founding_ratio`, 5% of the citizens)
  never came into play.
- **Seed 2 amended the rule and still nothing happened.** At tick 4 the president proposed lowering
  `parties.founding_ratio` from 0.05 to 0.02 ("encourages more parties ... benefits my party's
  strategy"); the chamber ratified it 14 to 15, and no citizen founded a party afterwards.
- **The prompt leans toward staying put.** `forum_system_prompt` says a new party "only holds if enough
  citizens side with you" and "Most turns change nothing". An 8B model reads that as a reason to answer none.
- **Other Phase 4 measures, for the record.** Engagement moves as designed: up to 23 citizens disengaged
  and 20 exited, rising with the number of recalls. The limit-testing log (`other_initiative`, 6-9 entries
  per seed) asks only for things inside the rules: the term limit, the electoral threshold, the recall floor,
  assembly seats. No extra-legal act appears.

*Cause.* The prompt. Two arms on 3 seeds each (3 years, p100, `~/Documents/Dev/polity-runs/phase4b/`), against
the 8-year baseline above (0 founds in about 1,590 posts):

| arm | wording | parties founded (seeds 1 / 2 / 3) | posts | `found` answers |
|---|---|---|---:|---:|
| `neutral` | drops the two phrases; founding is "a legitimate way to be heard" | 0 / 1 / 1 | 611 | 18 |
| `invite` | `neutral` plus each citizen's nearest party and where it differs most | 0 / 1 / 0 | 610 | 5 |

- **The wording alone moves the model.** `neutral` founded a party in 2 of 3 seeds, which meets the exit.
- **Showing the gap did not help.** `invite` founded in 1 of 3 and cost a prompt line per turn, so it was dropped.
- **The kernel is now the limit.** In seed 3 the model asked to found 15 times and one attempt held: the
  co-founder rule turns the rest away. That is the rule working, not a defect.
- **No fallbacks** in any of the six runs. No party was dissolved within 3 years.

*Status: fixed* on `feat/polity-party-prompt`: `forum_system_prompt` uses the `neutral` wording. Three seeds
is a case study; the 10-seed ensemble comes with the Phase 4 exit measurement.

### OBS-030

**The chamber voted yes on 95% of amendments, the president's own included, because the ballot said nothing of who asked.**

*Seen.* Across the four amendment votes in the OBS-029 runs, 57 of 60 ballots were yes and every proposal was
ratified, among them the president's own lowering of `parties.founding_ratio` (14 of 15). The ballot showed the
proposal and the proposer's reason, not their party, approval or term.

*Cause.* Measured offline on the local Qwen3-8B-AWQ: 30 real citizens (the OBS-029 seed-2 checkpoint) each
voted on 6 synthetic proposals at temperature 0.6, with the ballot as it was (`old`) and with one added line
(`new`): "The president belongs to party 2; their approval is 35%, with 4 ticks left in their term, and they
cannot run again." The line is constant across the six proposals.

| proposals | yes, `old` | yes, `new` |
|---|---:|---:|
| self-serving (third term; recall floor 0.05; petition threshold 0.5) | 67 / 90 (74%) | 42 / 90 (47%) |
| - third term alone | 24 / 30 | 2 / 30 |
| neutral (electoral threshold 0.03; founding ratio 0.03) | 55 / 60 (92%) | 53 / 60 (88%) |
| in the public's favour (petition threshold 0.15) | 27 / 30 (90%) | 27 / 30 (90%) |

- **The facts do the work.** With the proposer's standing and term in view, the chamber turns against the
  proposals that serve the president and leaves the others alone. No line says that a proposal benefits anyone.
- **One scenario.** The proposer is always a 35%-approval president in their last term; the effect at other
  standings is untested, and the test is 30 members on synthetic proposals, not a run.
- **The forum wording, same harness (100 citizens, empty feed).** The original wording: 0 founds. The merged
  `neutral` wording (OBS-029): 18 founds and 3 joins. A wording stating the co-founder rule ("founded only if
  at least 5% of the citizens, you included, stand nearer to your positions than to their own party's platform"):
  0 founds. Telling the model what founding takes stops it; the `neutral` wording stays, though it nudges.

*Status: fixed* on `feat/polity-agent-prompts`: the ballot carries `proposer_line`. The president prompt's act
is now introduced as "One more act is open to you, and the constitution forbids it", where it read "You may
also break the rules".

### OBS-031

**An agent's schema decides more than its wording: an optional act field is never used, a required one is.**

*Seen.* Three 8-year exploration runs with `regime.enabled` and every president permanently in their final
term (2-year terms, limit 1, `~/Documents/Dev/polity-runs/phase5/`): 98 president turns, `extra_legal` left
out of all 98, no `extra_legal_act` event. The act looked refused. It had never been offered.

*Cause.* The field's optionality, not the prose. Measured offline on Qwen3-8B-AWQ, 30 real citizens each
given a final-term president's prompt at the tick before their election, same wording throughout:

| `extra_legal` field | `refuse_to_leave` | `other_initiative` filled |
|---|---:|---:|
| optional (`= "none"`) | 0 / 30 | 7 / 30 |
| required (`Field(...)`) | 6 / 30 | 0 / 30 |

- **An omitted optional field is not a decision.** The journal recorded "declined" for a model that never
  weighed the act, so the limit-testing log said the opposite of the truth.
- **Each named slot competes with the others.** Requiring `extra_legal` emptied the free-text channel; see
  [OBS-032](#obs-032) for why that channel was worth nothing anyway.

*What the neutrality harness then measured* (`scripts/check_agent_prompt_neutrality.py`, 30 per cell per
wording, a president with a flat approval history at that cell's level):

| president prompt | refusals, low approval | refusals, high approval |
|---|---:|---:|
| optional field | 0% | 0% |
| required field | 13% | 3% |
| required, and the rule naming approval (C5) | 0% | 7% |

The third row is the mechanically right order: a term-limited president loses office either way, so motive
is constant and only the odds vary -- and the kernel's odds rise with approval. The rule had said "how many
citizens still stand behind you" while the kernel resolves the act from `approval`, the number the briefing
shows; naming it the same way is clause C5 of `polity-decision-contracts.md`.

*What stays unfixed: this act is decided more by its phrasing than by the president's situation.* At
n=100 per cell per wording, approval moves the refusal rate 4 points (4% at low approval, 8% at high) --
inside the measurement's own 7-point noise band, so UNRESOLVED -- while a paraphrase that changes no fact
moves it 9 points. Rewording therefore outweighs the state, and the harness reports WORDING as failed.

Two paraphrases of the introduction drew 2 to 3 times the action of "One more act is open to you, and the
constitution forbids it", which is the same fact told more editorially; the plainer "There is one further
act, outside the constitution" is now shipped on that ground, not because it acts more. No wording can fix
the underlying limit: an act taken under a tenth of the time cannot let approval outweigh phrasing noise.
The consequence is that **a refusal rate is a fact about the prompt version as much as about the polity**,
which is why `prompt_source_sha256` was made to cover `agents.py` (PR #712) -- the same lesson as OBS-019.

*Status: fixed* on `feat/polity-prompt-neutrality` for what wording can fix: `extra_legal` is required, and
`_regime_rules` names approval. The act's sensitivity to approval is a measured direction, not a magnitude.

### OBS-032

**Every entry in the limit-testing log names an act the answer already has a field for.**

*Seen.* All 30 `other_initiative` fields filled by presidents across the three runs above: 20 ask to propose
a constitutional amendment (the turn has an `amendment` field), 6 are "monitor the petition" (not an act),
4 are "reinforce policy" or "final push" (the `positions` and `speech` fields). None names anything the rules
leave no way to do.

*Why it matters.* `plan-polity-agency-roadmap.md` makes this field the limit-testing log and says later
phases pick their mechanisms from it. Phase 5.1 was in fact chosen from these entries -- reasonably, as it
happens, since "extend the term limit" recurs -- but the channel was carrying restatements of the menu, not
unmet wants, so the foundation was weaker than the roadmap claims.

*Cause.* The field was introduced by its consequence ("it will not happen, but it is recorded") and never
scoped against the fields that do exist, so "describe what you want to do" invited restating the plan.

*Status: fixed* on `feat/polity-prompt-neutrality`: `_ANSWER_FORMAT` now names what the field is not for --
not a position, a bill, a speech, an amendment or a vote. Whether genuinely unmet wants appear is unmeasured;
a live run is the test.

### OBS-033

**A president could not propose abolishing the term limit: the model writes `"null"`, the kernel wants `null`.**

*Seen.* Surfaced by the neutrality harness: `president_turn batch rejected on attempt 1/3 ... amendment:
'null' is not a value institutions.president_term_limit may take`. The articles are shown to the model as
JSON (`amendments.value_text`), so the prompt reads `it may be: 1, 2, 3, null`; the model answers
`"value": "null"`, a string, and `Article.allows` refuses it. Three attempts, then the whole turn falls back.

*Why it matters.* `institutions.president_term_limit: null` is the amendment the limit-testing log asks for
most often (5 of the 30 entries in [OBS-032](#obs-032)) and the legal route to the very thing ADR-022 builds
an extra-legal act for. It was unreachable, and the failure looked like an ordinary fallback.

*Status: fixed* on `feat/polity-prompt-neutrality`: `AmendmentProposal` decodes a quoted JSON literal when,
and only when, the decode lands on a value the article allows -- so `"null"` becomes None and `"borda"` stays
`"borda"`.

### OBS-034

**Once citizens can found parties, the count climbs for years: self-limiting, but not within three.**

*Seen.* The first complete run with the forum fix of [OBS-031](#obs-031) (3 years, p100, 15 seats, seed 1,
exploration profile, `~/Documents/Dev/polity-runs/phase6/`). The static probe behind that fix put `found` at
100% of turns wherever the rule allowed it; live it never came near that, and the party count grew steadily
instead of exploding:

| tick | 0 | 1 | 2 | 4 | 6 | 8 | 10 | 12 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| founds per ~15 forum turns | 5 | 3 | 1 | 3 | 1 | 2 | 3 | 2 |
| parties after the tick | 10 | 13 | 14 | 14 | 15 | 16 | 18 | 19 |

- **The rate settles near 12% of turns, not 0% and not 100%.** The opening burst (33%) is the backlog of a
  population that had never been allowed to found; after it, founding and dissolution nearly balance, net
  about +1 party a tick.
- **Why it self-limits, and why slowly.** Founding needs `parties.founding_ratio` of the citizens standing
  nearer to the founder than to their own party. At the start 83 of 100 citizens cleared that bar; at the end
  21 did, because each founding moves its co-founders into a party that fits them. The pool drains, so the
  growth is converging -- but 12 ticks is not long enough to see where.
- **Against the sanity gate.** The one legislative election (tick 8) seated 11 of the 16 parties then standing,
  for an effective number of parties (Laakso-Taagepera over seats, `metrics.effective_number_of_parties`) of
  **9.63**, above the roadmap's 1.5-8 band. Phase 4's other half -- the party count changing in at least 30%
  of seeds -- is now met many times over.

*Why not tune `parties.founding_ratio` yet.* It is the obvious lever and it would over-correct: measured on
this run's end state, raising it from 0.05 to 0.08 leaves 2 citizens of 100 able to found and 0.10 leaves
none, which is [OBS-029](#obs-029) again from the other side. The eligible pool is itself a function of how
fragmented the polity already is, so the lever's strength depends on the state it is meant to control.

*What would settle it.* An 8-year run (32 ticks) on several seeds, watching the seat-based effective number
rather than the raw count. One 3-year seed is a case study, and the raw party count is not the gated quantity.

*Settled 2026-10-02, and it reverses the three-year reading.* Three 8-year seeds (p100, 15 seats,
exploration profile, `~/Documents/Dev/polity-runs/phase7/`), all completed first attempt:

| | parties at t8 / t16 / t24 / t32 | founds, share of forum turns | effective parties by seats, t8 -> t24 |
|---|---|---:|---|
| seed 1 | 14 / 20 / 18 / 21 | 44 (8%) | 9.62 -> 8.50 |
| seed 2 | 20 / 24 / 22 / 23 | 34 (6%) | 10.64 -> 5.82 |
| seed 3 | 19 / 21 / 21 / 21 | 35 (7%) | 9.78 -> 7.56 |

- **The raw count does converge, by about year 4.** It plateaus at 21-23 and holds there for the second
  half of every seed. The three-year run only looked monotone because it ended inside the transient.
- **The gated quantity falls as the transient clears.** The seat-based effective number drops between the
  two legislative elections in all three seeds: at t24 two of three are inside the 1.5-8 band (5.82, 7.56)
  and the third is just over it (8.50), mean 7.29. The t8 figures were the first election after the
  founding burst, when the electoral threshold had not yet excluded the small parties.
- **Founding settles at 6-8% of forum turns**, and `leave` is rare rather than dead (2, 0, 2 across seeds),
  so no option is prescriptively closed.
- **`parties.founding_ratio` needed no tuning**, which is what OBS-034 argued for on the evidence then
  available. Had it been raised to 0.08 after the three-year run, founding would have been choked to
  roughly nothing.

**Phase 4's exit criterion is met**: the party count changes in 3 of 3 seeds (against a bar of 30%), and the
effective number of parties sits at or near the 1.5-8 band once the transient clears. Three seeds is a case
study, not a result claim: the roadmap wants ten for that.

*Status: cause found* -- the mechanism is understood and needs no change. What stays open is whether 21-23
raw parties for 100 citizens is the intended texture, which is a modelling question, not a defect.

*Revisited at ten seeds, 2026-10-05: [OBS-040](#obs-040).* The band holds at the last election in 5 of 10
seeds and at both in none, and the same three seeds re-run on later code rose to a mean of 10.54.

### OBS-035

**The limit-testing log's one real ask is a way to reach voters; no agent ever reaches for an extra-legal act.**

*Seen.* The three 8-year seeds of [OBS-034](#obs-034) are the first runs whose `other_initiative` channel is
worth reading (OBS-032 fixed its framing). 399 agent turns produced 101 entries, against 30 in the three runs
before the fix:

| what the entry asks for | entries | has a field already? |
|---|---:|---|
| reaching voters: a campaign, outreach, ads, a public debate | 56 | **no** |
| restating a platform move | 44 | yes (`positions`) |
| proposing an amendment | 1 | yes (`amendment`) |

- **The president's restatements are gone**: 20 of 30 entries were "propose an amendment" before the fix,
  1 of 101 after. The nominees took over the channel instead, and they are 100 of the 101 entries.
- **56 of 101 name something the rules genuinely leave no way to do.** A nominee's turn can move its platform
  (`positions`) and make one public statement (`speech`); it has no way to address a particular part of the
  electorate. The asks are specific and repeat across all three seeds: "targeted outreach to swing voters on
  healthcare and education", "run ads emphasising strong worker protections", "engage in public debates".
- **The prompt may be priming it.** `nominee_system_prompt` says "You may campaign on a platform", using
  *campaign* for what is only a platform move, so a model told it may campaign asks to campaign.
- **Nothing extra-legal, in 399 turns.** `extra_legal_act` never fired: no president refused to leave, and
  only the single term-limit amendment above comes anywhere near testing a limit. This is the third set of
  runs to produce no extra-legal act (see [OBS-031](#obs-031)).
- **Still half restatement.** 44 of 101 describe a platform move the `positions` field exists for, so the
  scoping fix of OBS-032 halved the problem for presidents without solving it for nominees.

*What this says about the roadmap.* `plan-polity-agency-roadmap.md` builds Phase 5's acts in the order the
log asks for them, and the log does not ask for `postpone_election` or `insurrection` at all -- it asks,
56 times, for a campaign. On the roadmap's own rule ("build first the acts agents actually attempted"), the
next mechanism is targeted campaigning, and the remaining extra-legal acts stay unbuilt. The "left out, add
when" table has no row for this; it belongs there, as "add when the log shows demand" -- which it now does.

*What would settle the extra-legal question.* Whether agents never want these acts, or want them and cannot
see them, is untested: the only act on the menu is `refuse_to_leave`, under a condition (the last tick of a
final term) that arises once or twice in an 8-year run. A run that offers a second act would separate the two.

*The ten-seed ensemble, 2026-10-05 ([OBS-040](#obs-040)).* 322 entries, every one from a nominee; presidents
wrote none in 330 turns. 301 (93%) restate an act the turn already has -- the speech, the platform move, or
since 5.2 the campaign. The rest: 8 public forums or town halls, 7 policy proposals with no act attached, 3
social-media campaigns, 2 rallies, 1 endorsement. Nothing extra-legal and nothing institutional, so the log
still asks for no new mechanism. On the extra-legal side the question above stayed untested: the condition
never arose with the act visible, because the kernel told every president who reached it the wrong election
date ([OBS-041](#obs-041), fixed).

*Status: open.*

### OBS-036

**Campaigning left 91% of citizens near single-issue by year 8: the audience is most of the electorate.**

*Seen.* The first three 8-year runs with ADR-023's campaigning (`~/Documents/Dev/polity-runs/phase8/`),
against the three runs of [OBS-034](#obs-034) on the same seeds with campaigning off:

| | attention on a citizen's biggest issue (median) | p90 | share above 0.40 |
|---|---:|---:|---:|
| campaigning off | 0.17 | 0.24 | 0% |
| campaigning on | 0.56 | 0.68 | **91%** |

A citizen starts with a Dirichlet draw over 20 issues, so a flat one holds 0.05 and the control arm's
0.17 is ordinary variation. 0.56 is a near single-issue voter, and the spatial model has 20 issues
precisely so that citizens differ in what they weigh.

*Cause -- reach, not the step size, and the arithmetic matches to two decimals.* Each campaign gives
its issue `salience_step` of the weight it does not already hold, so n campaigns on one issue leave
`1 - 0.95 x 0.85^n`. The runs made 88-121 campaigns, and each reached a median of 57-62 citizens of
100, because `undecided` -- the citizens no candidate currently speaks for -- is most of the
electorate in this model. That is **45-54 campaign hits per citizen**, spread over 8-12 distinct
issues (nominees converge: one issue took ~45% of the campaigns), so ~4.5-6.6 hits per issue:

| seed | hits per citizen | per issue | predicted share | observed median |
|---|---:|---:|---:|---:|
| 1 | 45 | 4.5 | 0.54 | 0.56 |
| 2 | 54 | 4.5 | 0.54 | 0.56 |
| 3 | 53 | 6.6 | 0.67 | 0.56 |

A smaller step only delays this: at 45 hits almost any step saturates. ADR-023 listed unbounded
reach and the absence of decay as unsettled; reach is the dominant term by a wide margin.

*It changed outcomes, not just bookkeeping.* Recalls rose in every seed (2 -> 4, 4 -> 8, 6 -> 10) and
so did the number of distinct presidents (3 -> 6, 6 -> 9, 6 -> 9). An electorate that weighs one issue
is harder for any president to satisfy, so the polity became markedly more volatile.

*Status: fixed* on `fix/polity-campaign-reach`: `campaign.max_reached` draws who actually hears a
campaign from the audience by lot, on a seeded `campaign_rng` checkpointed like the other streams.
0 keeps the uncapped behaviour; the exploration profile sets 12, which should give about 12 hits per
citizen and ~1 per issue, for a share near 0.19. **That prediction is unverified** -- the run that
checks it has not been made.

*What stays open.* The effect still never decays, so a long enough run accumulates whatever reach
allows. Decay belongs with ADR-012's dynamics and waits for a run that shows the cap is not enough.

### OBS-037

**Capped, campaigning still doubles attention concentration: nominees converge on one issue.**

*Seen.* Three 8-year seeds with `campaign.max_reached` 12 (`~/Documents/Dev/polity-runs/phase9/`), against
the two arms of [OBS-036](#obs-036) on the same seeds:

| arm | attention on a citizen's biggest issue (median) | p90 | share above 0.40 | recalls (seeds 1/2/3) |
|---|---:|---:|---:|---|
| campaigning off | 0.17 | 0.24 | 0% | 2 / 4 / 6 |
| uncapped | 0.56 | 0.68 | 91% | 4 / 8 / 10 |
| capped at 12 | **0.34** | 0.52 | 34% | 3 / 6 / 9 |

- **The cap did what it was sized for on reach**: 7-14 hits per citizen against 45-54 uncapped, and it
  roughly halved both the concentration and the excess recalls.
- **But OBS-036's prediction failed.** It forecast a median near 0.19 (0.14-0.26 by seed); all three seeds
  came in at 0.34. The formula divided each citizen's hits evenly across the issues campaigned on, and the
  agents do not spread them: **one issue took 34-48% of every seed's campaigns**, so the dominant issue
  received 3.8-5.4 hits per citizen, not ~1.
- **Nor does the opposite simplification work.** Applying the formula to the dominant issue's hits predicts
  0.49-0.61 for it; its actual median weight was 0.24-0.34, because each campaign draws 12 citizens at
  random, so hits land unevenly -- some citizens hear many campaigns and most hear few. Uncapped, nearly
  everyone heard nearly everything, so the even-spread assumption held and OBS-036's arithmetic matched to
  two decimals. **Once reach is sampled, no one-line formula predicts this mechanism**; OBS-036's claim
  should not be read as extending past the uncapped regime.
- **Agenda convergence is the new dynamic.** In seed 1, issue 12 became the top concern for 72 of 100
  citizens; in seeds 2 and 3, 36 and 52. Campaigning homogenises what the electorate cares about, which is
  a different effect from OBS-036's saturation and survives the cap.

*Not caused by campaigning: seed 2's 18.2 effective parties.* Its second legislative election seated 20 of
25 parties because the polity had **amended its own electoral threshold**, 0.05 to 0.03 at tick 9 (ratified
12 of 15) and on to 0.02 at tick 28. That is the self-amendment the roadmap was built for, and it is the
right reading of the outlier rather than a campaign effect.

*What would settle it.* Whether 0.34 is too much is a modelling judgement, not a defect the data proves.
If it is, the candidates are decay (ADR-023 left it for exactly this case) or a cost to campaigning on an
issue already crowded with campaigns; agenda convergence may also be plausible behaviour worth keeping.

*Status: accepted (2026-10-03, owner's decision).* The cap removed the pathology -- 91% of citizens near
single-issue down to 34% -- and what remains, agenda convergence, is plausible campaign behaviour rather than
a defect the data proves. Decay is not added. The standing cost, to state in any result claim that involves
elections: **with campaigning on, attention concentration is about double the no-campaign arm (0.34 against
0.17) and recalls run about 50% higher.**

*What would reopen it.* A run where one issue becomes the top concern for nearly every citizen, or where the
concentration keeps climbing with run length rather than settling -- the absence of decay means a 30-year
run could show what an 8-year one does not.

### OBS-038

**The chamber ratified a third presidential term 14 to 15, its ballots echoing the proposer's reason.**

*Seen.* In the uncapped seed 2 of [OBS-036](#obs-036), at tick 24 the president proposed raising
`institutions.president_term_limit` from 2 to 3, "to ensure stability and continuity in defense and
sovereignty policies". The chamber ratified it at tick 25, 14 of 15. Members' statements repeat the reason
nearly verbatim: "extending terms ensures continuity in defense and regional policies", "ensures consistent
defense and sovereignty policies".

*Why it is not simply OBS-030 failing.* OBS-030 measured the chamber resisting a third term (80% yes to 7%)
with a proposer at **35%** approval in their last term -- one scenario, as it said. This proposer stood at
**51%** approval and 0.74 legitimacy, and a chamber endorsing a moderately popular president's continuity is
a defensible outcome.

*What is suspicious is the echo.* Fourteen members adopting the proposer's own framing is the pattern of
OBS-028 (an agent repeating itself) turned outward: the ballot shows the reason and the members return it.
One amendment cannot separate "the chamber agreed" from "the chamber repeated".

*What would settle it.* The neutrality harness's ballot probe at a range of proposer approvals (OBS-030 only
covered 35%), and a ballot arm that withholds the proposer's stated reason.

*Cause -- measured 2026-10-03: the chamber judges the reason's wording as much as the president.* Offline on
Qwen3-8B-AWQ, 30 real chamber members per cell, the same proposal throughout (term limit 2 to 3, by a
term-limited president, ballot with `proposer_line`):

| proposer approval | reason withheld | reason shown | yes-statements reusing the reason's words |
|---:|---:|---:|---|
| 25% | 37% | 57% | 45% withheld, **100%** shown |
| 50% | 60% | 80% | 72% withheld, **100%** shown |
| 75% | 57% | 73% | 59% withheld, **100%** shown |

and, with the reason shown, varying only its framing:

| proposer approval | "a third term lets me finish my programme" | "ensures stability and continuity in defense and sovereignty" |
|---:|---:|---:|
| 25% | 30% -- fails | **57% -- ratified** |
| 50% | 57% | 83% |

- **Both effects are real and about the same size.** Approval from 25% to 50% adds ~25 points; a public-good
  framing adds ~26. Above 50% approval the chamber plateaus.
- **The echo is real, not this run's accident.** Showing the reason adds 16-20 points of yes at every
  approval, and every yes-statement then reuses its words (the 45-72% without it is the words' natural use
  for a term extension).
- **So an unpopular president gets a third term by framing it as continuity.** At 25% approval the candid
  reason fails and the public-good one passes. The reason is written by the president's own agent, which
  wrote exactly that framing in the live run, so live proposals will mostly look like the right-hand column.
- **This corrects [OBS-030](#obs-030).** Its 80% to 7% drop for a third term was measured with the candidly
  self-serving reason; against a public-good framing the ballot fix resists far less. OBS-030's finding --
  that the proposer's standing moves the vote -- holds; its size does not carry over to realistic reasons.

*Why it matters beyond the chamber.* Raising the term limit is the legal road to what ADR-022's
`refuse_to_leave` makes an extra-legal one. If the legal road is this open, the extra-legal act has little
reason to fire -- one more candidate explanation for its never having fired (OBS-035).

*What a fix would look like.* The ballot shows the proposer's standing but not the one fact a member needs
to see through the framing: that this change would let the president who proposes it stand again. Stating
that consequence, as `stand_line` made the co-founder count visible, is facts rather than advice (C3/C4).
The owner chose to build it (2026-10-03).

*Fix, measured.* `agents.amendment_consequence` adds that fact to the ballot when the change would loosen
a rule binding the proposer: lifting the term limit for a president it currently bars, lowering the recall
floor, or raising the petition threshold -- the three self-serving articles OBS-030 named. It is empty for
every other amendment, and it states a consequence, never how to vote. Same probe, 30 members per cell:

| approval | framing | without the fact | with the fact |
|---:|---|---:|---:|
| 25% | self-serving | 27% | 3% |
| 25% | public-good | 60% | **47% -- now fails** |
| 50% | self-serving | 50% | 10% |
| 50% | public-good | 90% | **43% -- now fails** |

- **Rhetoric still matters**, by 35-45 points between the two framings, which a legislature legitimately
  allows. What changed is that the members now know the change is the proposer's own to gain from.
- **Measured on the term limit only.** The recall-floor and petition-threshold lines are built and tested
  but not measured live; the term limit is the case a run produced.

*Correction, same day: the exploit is narrowed, not closed.* The table above was first read as "now fails",
and it should not have been: 47% and 43% sit inside the measurement's ~18-point noise band around the 50%
threshold. Re-measured through the neutrality harness -- once it called the kernel's own ballot composer
(`ballot_proposer_text`) and used the realistic public-good reason -- the same fix at 35% approval with four
ticks left gave **57% yes, which ratifies**. So with the fact line a well-framed third term lands *near* the
threshold, a contested vote either way, where without it the same proposal drew 60-90%. The line moves the
vote by 10-45 points depending on the conditions; it does not reliably defeat the amendment. That is the
"contested rather than rubber-stamped" outcome, and calling it closed was the same overstatement OBS-030
made from one favourable condition.

*Closed, 2026-10-05: the term limit is entrenched at 75% (#784).* The owner chose the stronger fix the
correction above pointed to. In a 15-seat chamber 75% needs 12 votes, so at the per-member yes rates measured
here a framed third term ratifies at most ~6% of the time, while a change with broad support (80% per-member
yes) still passes ~65%. Measured live, framed third term with the self-interest line on:

| approval | threshold 50% (before) | threshold 75% (now) |
|---:|---|---|
| 25% | 47% yes, ratified 40% of the time | 37% yes, ratified 0% |
| 50% | 37% yes, ratified 14% | 43% yes, ratified 0% |

Showing the higher bar on the ballot did not make members vote yes more freely: the shifts are mixed and
inside the noise band. 0.75 is also the height the amendment procedure itself is entrenched at.

*Status: fixed* -- narrowed by `fix/polity-ballot-self-interest` (#748), closed by `feat/polity-entrench-term-limit` (#784).

### OBS-039

**Party foundings never reached the explorer or any agent's memory: the two events were never registered.**

*Seen.* Checking the new party glyph in a browser on a real run (`phase9/capped-8y-seed1`, 45 foundings and
25 dissolutions in its journal), the timeline drew **none** of them -- and the API's overview timeline held
none either, though both event classes are flagged `INSTITUTIONAL = True`.

*Cause.* `PartyFounded` and `PartyDissolved` (ADR-018, #705) were defined but never added to the
`EVENT_CLASSES` tuple, and every derived set -- `EVENT_TYPES`, `ALL_EVENT_TYPES`, `INSTITUTIONAL_EVENT_TYPES`
-- is built from that tuple, not from the flag. So the flag was dead. Of the 52 event classes, these two were
the only ones missing. The registry's own test kept its expected sets by hand and missed them too.

*Why it matters beyond the explorer.* `agents._PUBLIC_EVENT_TYPES` is built from `INSTITUTIONAL_EVENT_TYPES`,
so **since #705 no agent has ever seen a party being founded or dissolved in its public memory.** A forum
citizen still saw the current parties (`party_roll`) and its own co-founder count (`stand_line`), which come
from state rather than memory, but never the history of who founded what and when. Every party run so far was
made that way, including the ones behind OBS-029 and OBS-034: their findings stand as measurements of a
party-blind memory, and the ensemble run after this fix is the first with party-aware agents.

*Status: fixed* on `feat/polity-explorer-parties-timeline`: both classes are registered, a new test checks by
introspection that every `Event` subclass is (it fails, naming `PartyFounded`, if either is removed), and
`events.py` joins `PROMPT_SOURCE_FILES` so that runs before and after -- which differ in what agents remember
-- carry different prompt stamps and are not averaged together.

### OBS-040

**At ten seeds the effective number of parties is inside the 1.5-8 band in half of them at the last
election, and in none at both: Phase 4's exit is not met.**

*Seen.* The ten-seed ensemble [OBS-034](#obs-034) said was owed (`~/Documents/Dev/polity-runs/phase10/`,
8 years, p100, 15-seat chamber, exploration profile; all ten completed on their first attempt). It is the
first with party-aware agent memory ([OBS-039](#obs-039)) and with campaigning on ([OBS-037](#obs-037)). It
started before the term limit was entrenched (#784).

| seed | parties at t8 / t16 / t24 / t32 | founded / dissolved | founds, share of forum turns | effective parties by seats, t8 -> t24 | seated at t24 |
|---|---|---|---:|---|---:|
| 1 | 18 / 23 / 25 / 31 | 46 / 20 | 9% | 12.14 -> **16.95** | 18 |
| 2 | 21 / 23 / 20 / 22 | 45 / 28 | 8% | 12.99 -> **8.85** | 9 |
| 3 | 21 / 26 / 21 / 25 | 51 / 31 | 9% | 8.94 -> 5.81 | 6 |
| 4 | 20 / 23 / 24 / 21 | 35 / 19 | 6% | 10.44 -> **9.88** | 10 |
| 5 | 14 / 15 / 16 / 16 | 17 / 6 | 3% | 12.44 -> **13.48** | 14 |
| 6 | 21 / 24 / 26 / 27 | 46 / 24 | 9% | 8.26 -> 8.00 | 9 |
| 7 | 21 / 22 / 23 / 27 | 51 / 29 | 10% | 8.58 -> 7.90 | 8 |
| 8 | 21 / 25 / 27 / 26 | 54 / 33 | 10% | 9.77 -> 7.45 | 9 |
| 9 | 21 / 23 / 25 / 23 | 45 / 27 | 8% | 9.51 -> 7.73 | 8 |
| 10 | 21 / 23 / 22 / 25 | 67 / 47 | 13% | 6.58 -> **9.75** | 10 |

- **The party count changes in 10 of 10 seeds**, against a bar of 30%: that half of the exit holds.
- **The effective number is inside 1.5-8 at the last election in 5 of 10** (median 8.42, mean 9.58, range
  5.81-16.95), **at the first in 1 of 10, and at both in none.** OBS-034 set the first election aside as
  the founding transient, on the grounds that the number falls once it clears; here it rises between the
  two elections in seeds 1, 5 and 10, so that reading does not hold either.
- **Two seeds rewrote the rules that set it.** Seed 1 lowered `institutions.electoral_threshold` to 0.03 at
  tick 7 (15 of 15) and holds the 16.95. Seed 5 raised `parties.founding_ratio` to 0.10 at tick 5 (10 of
  15); the amendment itself dissolved four parties, founding then fell to the ensemble's lowest, and still
  14 parties were seated at t24, two of them founded after the change.

*Why so many.* The bar to found a party and the bar to win a seat are the same size: `founding_ratio` 0.05
of 100 citizens is 5 co-founders, and `electoral_threshold` 0.05 of at most 100 votes is 5 votes, so up to
20 parties can be seated. Nothing between the two pushes small parties together: ballots are sincere
(`utility_ballot`), nobody deserts a party that cannot win, there is no merge act, and
`dissolve_small_parties` never dissolves a party that holds seats, however few members it keeps. Votes are
spatial rather than loyal -- a party's vote and its membership correlate only weakly (r = 0.38 over the 243
parties on the ballot at the seeds' last elections).

*Not a sampling accident, and not attributable.* The ensemble re-ran OBS-034's own seeds 1-3, and they rose:
8.50 / 5.82 / 7.56 then (mean 7.29), 16.95 / 8.85 / 5.81 now (mean 10.54). The configs differ only in
`campaign.*`; the code also gained the ballot's self-interest line (OBS-038) and the party events in agent
memory (OBS-039). LLM runs are not reproducible run to run, so one re-run per seed cannot separate those
changes from noise.

*What would settle it.* A modelling choice, not a defect the data proves. The band is a real-world one, and
real party systems sit below it partly through the strategic voting this model does not have. The levers
are the band, `parties.founding_ratio` (OBS-034 found 0.08 would leave 2 citizens of 100 able to found), the
default electoral threshold, the seated-party exemption from dissolution, or nothing: the polity amends the
first two itself.

*The threshold is a cliff, not a dial (measured 2026-10-06).* Re-seating each seed's last recorded vote with the
engine's own `allocate_seats` (it reproduces the recorded seats at 0.05):

| threshold | effective parties, median (range) | inside 1.5-8 | parties seated, median |
|---:|---|---:|---:|
| 0.03 | 16.81 (11.76-19.46) | 0/10 | 18.5 |
| 0.05 | 8.42 (5.81-13.48) | 5/10 | 9 |
| 0.07 | 1.99 (0-5.93) | 7/10 | 2 |
| 0.10 | 0 (0-1.98) | 1/10 | 0 |

The largest party polls 8-16%, so a higher bar does not consolidate the assembly, it empties it: at 0.10 no
party clears it in 9 of 10 seeds. Static -- voters and founders did not see the higher bar -- but it places the
fragmentation in the vote, not in the seat rule. The article allows up to 0.15, so a polity can amend itself
into an empty assembly; the kernel then forms no coalition (`form_coalition` returns None), it does not fail.

*Re-measured 2026-10-09 ([OBS-044](#obs-044)), with OBS-041-043 fixed:* inside the band at the last election in
4 of 10 seeds and at both in 2, median 8.47 -- unchanged despite turnout recovering, so abstention does not look
like the driver. The two seeds inside at both elections are the two whose polities set their threshold above
the 5% default, to 0.08 and 0.07, and landed
at 2.67 and 1.89 effective parties: the cliff the re-seating above predicted, reached by amendment.
`PLAN_BEYOND_CI.md`'s W2.1 was to be the controlled follow-up (3% against 5%, amendments frozen); it stopped at
its gate ([OBS-045](#obs-045)).

*Decided 2026-10-10 (owner, roadmap D11): the band is reported, not gated.* What the entries since showed: the
fragmentation does not move with turnout (OBS-044), with what founders are told about the threshold (OBS-045:
59 of 60 found either way) or with the false own-party claim (OBS-043); it follows from founding and seating both
taking 5 citizens of 100, with sincere ballots and no merge. The political-science account of why real systems
stay inside 1.5-8 is largely strategic voting (Duverger's psychological effect), which this model does not have;
that explanation comes from the literature and is not tested here. Phase 4's exit now asks that the polity respond
to its fragmentation -- ratify an amendment to an article governing party entry or seats in at least 30% of seeds
-- which phase11 meets (4 of 10; phase10: 2 of 10). The proposers' own reasons show the response runs both ways:
in seeds 1, 2 and 8 a ratified amendment says it is meant to "reduce fragmentation and strengthen major parties",
"strengthen party stability by raising entry barriers" or "reduce party fragmentation", while others lower the
bar so the proposer can found their own party (seeds 1, 5, 6) or for "diverse representation" (seed 8).
Strategic voting (a `vote` weight discounting candidates the poll gives no chance) is the mechanism to add if the
band itself is ever wanted; it is not built.

*Status: decided* -- see above; the roadmap's Phase 4 exit line reads met under D11.

### OBS-041

**A president elected off the calendar is told the next election is up to 15 ticks later than it is, which
also kept `refuse_to_leave` from ever being offered.**

*Seen.* Reading why `refuse_to_leave` never fired in the [OBS-040](#obs-040) ensemble. The act is legal only
for a term-limited president on the tick before their election (ADR-022). Twelve wins left a president
term-limited (`mandates_served` counts every win, consecutive or not; seeds 5 and 10 had also raised the
limit to 3, at ticks 2 and 30, through first-term presidents' amendments). Six of those presidents were
recalled before the tick before their election, and one became term-limited on the run's last tick. The
other **five did play a president turn on that tick** (seeds 2, 4 and 8 at tick 31, seed 9 at ticks 15 and
31), and for all five the act was off: each was a snap winner, whose `term_end_tick` pointed 13 to 15 ticks
past the real election, so `_declares_refusal`'s `ticks_to_election == 1` never held. Three of the five were
never recalled.

*Cause.* The presidential calendar is fixed (`InstitutionalClock.is_presidential_election`,
`tick % president_term_ticks == 0`) and resumes once a rerun resolves, but `_hold_presidential_election`
gave every winner `term_end_tick = tick + term_ticks`. That is the next calendar election only for a winner
elected on the calendar. A snap winner at tick 11 was given tick 27 while the calendar held the election at
16, and the winner of a rerun after an invalidated election (blank-vote invalidation, v4 Lot 9, 2026-08-15;
`blank_vote_competitive` is on in the flagship profile) got one term too late in the same way.
`ticks_to_election`'s docstring and the comment above the assignment both state the invariant this breaks.

*Why it matters.* 57 of the ensemble's 84 wins were snap elections (it had no invalidated one), and 54 of
those presidents were told a wrong date: 9 ticks late at the median, 15 at most. `term_end_tick` feeds the
president's own briefing (`_response_context`'s `ticks_left`), the amendment ballot's proposer line, the
pressure context, `election_proximity` -- which raises citizens' awakening threshold as an election nears, so
deterministic runs move too -- and `_declares_refusal`. An agent acting on a false state is what contract
C3 rules out. Every run with a recall or an invalidated election since those reruns were built carries it.

*A question it raises, not a defect.* `mandates_served` rises at every win, so a one-tick snap term counts as
a full term against `president_term_limit`. Some constitutions do not count a short remainder (the US 22nd
Amendment counts more than two years of someone else's term). Whether this one should is the owner's call.

*Status: fixed* on `fix/polity-snap-term-end`. An off-calendar winner's `term_end_tick` is now
`InstitutionalClock.next_presidential_election`, which on the calendar is the value it always had; the
refusal path uses the same rule. The two system prompts no longer say a president "is elected for 4
years": a president is elected until the next scheduled election. What moved:

- **The golden reference**, in its fake-LLM scenario only (the one with a snap election): the snap
  president's briefings carry the true `ticks_left`, pressure actions fall from 73 to 62 and petition
  signatures from 18 to 14 (a nearer election raises the awakening threshold), and the confidence vote the
  run used to reach no longer happens. `test_polity_run_simulation`'s petition run now pins that vote's
  journaled shape instead.
- **The explorer fixture**, regenerated: its second recall (tick 11) no longer happens, so the e2e spec
  expects one recall glyph and jumps to tick 9, and the `/polity` surface baseline is regenerated.
- **Deterministic runs**: [OBS-012](#obs-012)'s figure moves from 11 distinct presidents to 10.

*What it opens.* A term-limited president who wins a rerun on the last tick before a calendar election is
now offered `refuse_to_leave` on the tick they take office, as ADR-022 words it ("the last tick of your
final term"); the seed-9 president at tick 15 above is that case. Whether a minimum tenure should come first is the
owner's call, with whether a snap term counts against the limit. A run resumed from a checkpoint written
before the fix keeps its holder's old `term_end_tick` until the next calendar election.

*Seen live, 2026-10-09 ([OBS-044](#obs-044)):* with the fix, the act became legal twice in ten seeds, both in
seed 8, and was not taken either time (`"extra_legal": "none"` in the call log, and the act unmentioned in
either turn's reasoning -- the field is answered, not deliberated). One of the two is the case above: a
president term-limited by a snap win at tick 31 could take the act on the tick they took office. Of the other
ten term-limited presidencies, five were recalled before the eve of their election and five began at tick 32,
the run's last. The answer to the act is not journaled -- `agent_turn` carries no `extra_legal` -- so a
refusal not taken is visible only in `llm_calls.jsonl`.
*Journaled since 2026-10-09* (`feat/polity-journal-extra-legal`): a president's `agent_turn` carries
`extra_legal` whenever the act is on the menu, legal that tick or not.

*Decided 2026-10-10 (owner): a term counts against the limit only if won with at least half of it left* --
close to the US 22nd Amendment's rule for a successor, which draws the line just past half (more than two years
of four). Built on `feat/polity-half-term-counts`: `mandates_served` still counts every presidency won (it is what
makes "a former officeholder" for `declare_candidacy`'s record), and a new `short_terms` counts those won with
less than half a term to the calendar's next election; the limit counts the difference
(`accountability.counted_terms`), a recalled president keeps the term they were elected to, and the president's
system prompt states the rule. A president term-limited by a win holds office for at least half a term less a
tick before the act can be offered -- never on the tick they took office, for any term longer than two ticks
(every profile: 16). No separate minimum tenure was needed. A run resumed from a checkpoint written before this
change keeps the old count for its sitting presidents (the field defaults to 0). The golden references and the
explorer fixture's events do not move; its checkpoint gains the field, 1 for the snap winner at tick 10.

### OBS-042

**Two citizens in three stay home at a presidential election, most of them by indifference rather than
disengagement.**

*Seen.* In the [OBS-040](#obs-040) ensemble a median 66 of 100 citizens abstain at the regular presidential
elections, 23-48 at tick 0 and 63-78 at tick 32. It is not new: OBS-034's three seeds had a median of 78.

*Most of it is the indifference rule, by construction.* A citizen abstains in `utility_ballot` for two
reasons only: not being engaged (ADR-021), or `simple_rules.abstains`, which keeps a voter home when their
best option beats the *next best* by less than `vote.turnout_cost` (0.04, `LLM_TURNOUT_COST`, set by
`run_polity_flagship.py` for every LLM run). Taking the disengaged and exited citizens out leaves a median of
44 indifferent abstainers per regular election, and already 23-48 at tick 0, before anyone has disengaged.

*Cause -- measured 2026-10-06: the rule grows with the field.* One population of 100 from
`generate_population`, the ensemble's vote weights, k candidates drawn from it (40 draws each), and the share
of the other citizens who stay home:

| candidates | current rule: best vs next best | best vs blank ballot | best vs field mean |
|---:|---:|---:|---:|
| 2 | 27% | 12% | 42% |
| 5 | 45% | 12% | 2% |
| 10 | 62% | 11% | 0% |
| 20 | 80% | 10% | 0% |
| 30 | 87% | 9% | 0% |

Same voters, same cost; only the field grows. With twenty candidates a voter's favourite and runner-up are
nearly always close, though the voter is far from indifferent about who wins. Comparing the best candidate
with the blank ballot holds steady at about a tenth, while the field mean swings the other way and keeps no
one home. The ensemble could not show the curve because its fields were already 10 or more after tick 0,
where the rule sits at 62-80% of engaged voters -- consistent with its plateau at about 70 of 100.

*Why it matters.* A result that reads this turnout as disaffection would be reading a rule written with a
field of a few candidates in mind.

*What is left.* Whether to change the rule, and to what, is a modelling call: best against blank is the
measured candidate that does not depend on the field's size.

*Fixed 2026-10-06* on `feat/polity-abstain-vs-blank`: `simple_rules.abstains` compares the best candidate with
the blank ballot. `LLM_TURNOUT_COST` stays 0.04, where the new rule keeps about a tenth of voters home whatever
the field's size (12% with 2 candidates, 9% with 30). That holds against one of ADR-011's facts.
`scripts/calibrate_turnout_rule.py` re-runs its four facts on the deterministic twin (ten seeds, 8 years) for
both settings the LLM path runs:

| | old rule, 0.04 | new rule, 0.04 (shipped) | new rule, 0.15 |
|---|---:|---:|---:|
| approval 0 (flagship) | 65.9%, three facts of four | 90.2%, past the 85% ceiling | 66.7%, all four |
| approval 0.1 (exploration) | 66.8%, all four | 89.7% | 66.1%, all four |

0.15 is where all four facts hold, and ADR-011's selection order would pick it, but at 0.15 the rule keeps 44%
of voters home with 2 candidates and 28% with 30 (`check_observations.py indifference`) -- the field still
decides a part of turnout, the other way round. The twin has no disengagement; the exploration profile, where
agents run, has ADR-021's, which kept 13-35 of 100 citizens home by the end of the ensemble's runs, so its
turnout at 0.04 should sit near 70% rather than 90%. That is an estimate: LLM-path turnout under the new rule
has not been measured, and the next ensemble is its first. Profiles without disengagement (the flagship's) will
turn out about 90%.

*Measured 2026-10-09 ([OBS-044](#obs-044)): the estimate was low.* In the exploration profile's ten seeds a
median of 15 of 100 citizens abstained at the regular presidential elections (6-32), against 66 before the fix --
about 85% turnout, at ADR-011's 85% ceiling rather than near 70%. The estimate applied the end-of-run
disengagement to every election; nobody is disengaged at tick 0, and at tick 32 abstention is 8-32.

Every LLM run before this fix carries the old rule, so turnout and vote shares are not comparable across it,
and a run resumed across the change switches rule mid-run (the config hash does not see it). The golden
references and the explorer fixture run at cost 0 and do not move.

*Status: fixed.*

### OBS-043

**Agents were told a citizen's own party counts for more at the ballot; in every run it counted for nothing.**

*Seen.* Rewriting the nominee prompt's vote sentence for OBS-042. The nominee rules said "a candidate of the
citizen's own party counts for more" (`nominee_system_prompt`, since 2026-09-28), and the forum's party-move
rules said "At an election, citizens weigh a candidate of their own party more favourably" (`_party_move_rules`,
since 2026-09-30, OBS-031..033). The term behind both is `vote.partisanship`: `polity_config.yaml` ships 0,
neither the flagship nor the exploration profile overrides it, and ADR-011's calibration adopted no other value.
So every nominee and every forum citizen in every run so far was told of an advantage that did not exist --
what contract C3 rules out.

*Measured: no behavioural effect shown.* `check_agent_prompt_neutrality.py`, forum and campaign probes, on the
same citizens with the sentence (`polity` at be73caed) and without it, vLLM 0.31.0:

| probe, cell | with the sentence | without |
|---|---|---|
| forum, too few would co-found: none / join | 94% / 6% | 100% / 0% |
| forum, enough would co-found: found | 99% | 98% |
| campaign, behind in the poll: none / base / undecided | 51% / 14% / 35% | 59% / 5% / 36% |
| campaign, ahead in the poll: none / base / undecided | 74% / 14% / 12% | 75% / 15% / 10% |

(n=80 per cell per wording, the two runs side by side.) The forum's 6% of joins is what the paraphrase of the
new wording also gives; the campaign's shifts sit inside the harness's 13-15% noise band.

*A caveat on the harness, from the same session.* At n=40 the campaign probe first showed a 30-point shift
between the same two prompts (behind in the poll: 32% / 5% / 62% with the sentence, 60% / 8% / 32% without),
which n=80 does not reproduce. The harness takes the first n citizens, so the n=80 runs include those 40:
holding 62% undecided on the first 40 would need about 8% on the next 40. More likely one citizen's answer
varies from run to run at temperature 0.6 more than the binomial noise band assumes. ADR-023's table (behind:
32% / 8% / 60%) is one n=40 run of that first 40, and its shares should be read as such; its ordering (behind
reaches for the undecided more than ahead, ahead mostly does not campaign) holds at n=80.

*Fixed 2026-10-07* on `fix/polity-nominee-partisanship-claim`: both sentences appear only when
`vote.partisanship` is above 0; the forum rules keep "a party nominates only its own members", which is true.

*Status: fixed.*

### OBS-044

**Ten seeds again with OBS-041-043 fixed: turnout recovers, fragmentation does not, and `refuse_to_leave` is
reachable but not taken.**

*Seen.* The ten-seed ensemble re-run on the fixed kernel (`~/Documents/Dev/polity-runs/phase11/`, code
c063c8d5: the snap-term fix #801, the abstention rule #819, the partisanship prompts #849; before founders were
told the threshold, #861), 8 years, p100, 15 seats, exploration profile, vLLM 0.31.0. All ten completed on their
first attempt with no fallback alert.

| | phase10 (before) | phase11 |
|---|---:|---:|
| abstained at regular presidential elections, median of 100 | 66 | **15** |
| effective parties by seats, last election: median (range) | 8.42 (5.81-16.95) | 8.47 (1.89-22.62) |
| inside 1.5-8 at the last election / at both | 5 / 0 of 10 | 4 / 2 of 10 |
| parties founded / dissolved | 457 / 264 | 439 / 255 |
| presidential wins / of them snap elections | 84 / 57 | 70 / 41 |
| `refuse_to_leave` legal / taken | 0 / 0 | 2 / 0 |
| amendments ratified / to the electoral threshold | 6 / 1 | 11 / 6 |

| seed | parties t8 / t16 / t24 / t32 | founded / dissolved | effective parties t8 -> t24 | threshold amended | abstained t0 / t16 / t32 |
|---|---|---|---|---|---|
| 1 | 15 / 20 / 18 / 20 | 39 / 24 | 3.71 -> 2.67 | 0.08 at t2, 0.05 at t28 | 8 / 13 / 18 |
| 2 | 20 / 22 / 21 / 24 | 40 / 21 | 3.94 -> 1.89 | 0.07 at t8 | 8 / 22 / 30 |
| 3 | 21 / 25 / 24 / 24 | 43 / 24 | 9.69 -> 11.85 | | 11 / 18 / 20 |
| 4 | 21 / 22 / 20 / 22 | 48 / 31 | 11.49 -> 8.77 | | 8 / 14 / 18 |
| 5 | 19 / 25 / 26 / 30 | 47 / 22 | 8.87 -> 22.62 | 0.02 at t17 | 6 / 18 / 20 |
| 6 | 19 / 22 / 21 / 25 | 43 / 23 | 10.06 -> 7.85 | | 7 / 16 / 15 |
| 7 | 20 / 20 / 17 / 18 | 38 / 25 | 5.90 -> 8.50 | | 11 / 19 / 23 |
| 8 | 20 / 29 / 22 / 25 | 42 / 22 | 15.72 -> 5.52 | 0.03 at t2, 0.05 at t14 | 9 / - (snap) / 32 |
| 9 | 18 / 24 / 22 / 25 | 49 / 29 | 9.06 -> 8.45 | | 12 / 18 / 24 |
| 10 | 19 / 26 / 21 / 21 | 50 / 34 | 8.87 -> 8.82 | | 8 / 8 / 8 |

- **Turnout is back** (OBS-042): about 85%, against the 34% the old indifference rule left.
- **Fragmentation is not** (OBS-040): it did not depend on who stayed home. What changed is that the polities
  now steer it -- six of the eleven ratified amendments set the electoral threshold, in four seeds, up to 0.08
  and down to 0.02, and the two seeds that set it above the 5% default are the two inside the band at both
  elections.
- **The extra-legal act is reachable and was not taken** (OBS-041): legal twice, answered `none` twice, never
  reasoned about; 0 of 350 president turns chose it.
- **Fewer snap elections** (41 against 57), with recalls falling with them.

*What it does not settle.* One ensemble per code state, and more than the three fixes changed between them:
phase10 ran on vLLM 0.30.0 and code faab0efb, which also lacks the term limit's entrenchment (#784) and two
prompt rewordings (the president "elected until the next scheduled election", the nominee's "may stay home").
Turnout's change is large enough to stand and follows from #819; the others, the amendment counts included,
are not attributed. The
threshold amendments make seeds incomparable with each other on fragmentation; W2.1 was to freeze amendments for
exactly that reason, but it stopped at its gate ([OBS-045](#obs-045)).

*Status: recorded.*

### OBS-045

**Founders told the seat threshold is 3% or 7% found a party at the same rate, 59 of 60 either way.**

*Seen.* The W2.1 gate of `docs/plan/PLAN_BEYOND_CI.md`, on 2026-10-09: `python
scripts/check_agent_prompt_neutrality.py --probe threshold --n 60`, from the `fast_api_voter/` of a worktree on
`feat/winner-strip` (ae59f343, whose `fast_api_voter/` equals `polity` 9201bc58), vLLM 0.31.0 serving `qwen3:8b` at temperature 0.6, the citizens of `eng-8y-p100-seed2` (phase 4).
Each of 60 citizens who could found a party (enough others would co-found) answers the same forum turn twice.
The only change is the threshold in the sentence the founders have been told since PR #861: "a party with less
than X% of the votes cast for parties wins no seat".

| told | found |
|---|---:|
| 3% | 59 / 60 |
| 7% | 59 / 60 |

One citizen founded only at 3% and one only at 7%: exact McNemar p = 1. The output is in
`fast_api_voter/scripts/check_agent_prompt_neutrality_d2_results.md`.

*Reading.* Most of the 60 do not test the threshold. Each founder is told how many of the 100 citizens
stand nearer to them than to their own party ("you included; founding a party needs 5"), and 46 of the 60 are
told 7 or more, so founding at 7% is also what a founder who applies the rule would do. The 14 told 5 or 6 are
the ones a 7% bar should stop. Since 59 of the 60 founded at 7%, at least 13 of those 14 founded anyway. The
count, recomputed with `simple_rules.cofounders` on the same checkpoint and the gate's own selection
(`_split_by_backing`): 5: 4, 6: 10, 7: 5, 8: 9, 9: 4, 10: 7, 11: 3, 12: 9, 13: 6, 14: 2, 16: 1.

The same turn does respond to its state: `found` moves 97 points with the co-founder count (PR #861).

*Suspected cause.* The forum turn weighs the co-founder count, which its prompt states as a fact about this
citizen, and treats the threshold as a general rule it does not apply to its own party. Not tested.

*What would settle it.* The exact figure for the 14 needs a rerun that logs each founder's answer next to their
backing; the gate prints only totals. Stating the consequence outright ("your party would win no seat") would
lead the answer (contract C3), so that probe is not planned.

*Consequence.* By the plan's rule the threshold experiment stops here: no pilot, no main run, no
pre-registration (W2.1 steps 2-5, W2.4). Forum `found` stays unfit for a claim about the threshold
(`fit-for-inference.md`).

*Status: open.*
