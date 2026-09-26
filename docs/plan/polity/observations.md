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
| [OBS-016](#obs-016) | The root disk filled up: p500 seed 42 died at tick 13 and the GPU queue ran nothing | 2026-09-14 | open |
| [OBS-017](#obs-017) | WebKit crashed mid-navigation to /polity in CI, once, while the other worker ran the heavy fiches | 2026-09-16 | open |
| [OBS-018](#obs-018) | The response contract, not the model, sets the president's stance in 22 of 650 responses | 2026-09-16 | cause found, partly fixed |
| [OBS-019](#obs-019) | Showing the model its citizens' emotions, at zero weight, multiplies mobilization fourteenfold | 2026-09-17 | cause found |
| [OBS-020](#obs-020) | Without n-gram speculation, two same-seed live runs are not always byte-identical | 2026-09-20 | open |
| [OBS-021](#obs-021) | 5 to 12% of chamber deliberation units fall back because the model returns more shifts than the cap allows | 2026-09-25 | open |

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
