# Polity — observation log

Strange behaviour seen in simulation runs, kept so it can be studied instead of forgotten in a
commit message or a `TIMELINE.md`. An entry records **what was seen and how to see it again**. It
is not a bug report and not a conclusion: most entries are open questions.

**Rules for an entry**

- Every number is reproduced from a run's files, with the command or event ids that show it.
  Nothing from memory, nothing from a narrative's prose alone.
- *Suspected cause* is labelled as a suspicion until something settles it.
- *What would settle it* names the check, the run, or the plan step that answers the question.
- Status is one of **open**, **explained** (cause understood, behaviour stays), **fixed**
  (with the commit), or **by design** (the model intends it; say where that is written).
- New entries go at the end with the next number; an entry is never deleted, only re-statused.

Runs cited below live in `fast_api_voter/scripts/*_runs/` (gitignored); `python
scripts/run_registry.py` lists them and `marimo run scripts/run_explorer.py` browses them.

## Index

| ID | Observation | First seen | Status |
|---|---|---|---|
| [OBS-001](#obs-001) | The same citizen wins nearly every presidential election of a run | 2026-09-13 | open |
| [OBS-002](#obs-002) | Parties nominate the same five people at every election, snap elections included | 2026-09-13 | open |
| [OBS-003](#obs-003) | A recalled president usually wins the election that follows the recall | 2026-09-13 | open |
| [OBS-004](#obs-004) | The sortition chamber almost never moves: 99.9% of its decisions are "no change" | 2026-09-13 | open |
| [OBS-005](#obs-005) | A president kept by a confidence vote is recalled the same tick | 2026-09-13 | open |
| [OBS-006](#obs-006) | One party's nomination answer is out of range, the same wrong value six times | 2026-09-11 | open |
| [OBS-007](#obs-007) | `representative_response` and `coalition_decision` answer the same whatever the input | 2026-08 (Ollama), re-checked 2026-09 (vLLM) | open, partly fixed |
| [OBS-008](#obs-008) | Two truncated generations cost more time than all retries and rejected answers together | 2026-09-13 | open |
| [OBS-009](#obs-009) | Journals are not bit-identical across CPUs | 2026-09-13 | explained |
| [OBS-010](#obs-010) | Half the p100 seeds tell the same story | 2026-09-13 | open |
| [OBS-011](#obs-011) | About 40% of citizens declare candidacy at every election | 2026-09-11 | open |

---

### OBS-001

**The same citizen wins nearly every presidential election of a run.**

*Seen.* In the 8-year population-100 seed sweep (`seed_sweep_runs/sweep-8y-p100-seed*`), four of
ten runs have a single president for all eight years, elected at ticks 0, 16 and 32 (citizen 13 in
seed 1, 29 in seed 2, 95 in seed 7, 88 in seed 9). In seed 6, citizen 66 is elected six times (ticks
0, 16, 20, 24, 28, 32). Across seeds the winner differs, so this is within a run, not across runs.

*Evidence.* `elected` events per run:

```bash
cd fast_api_voter && python3 -c "import json,glob
for j in sorted(glob.glob('scripts/seed_sweep_runs/sweep-8y-p100-seed*/run/*/events.jsonl')):
    print(j.split('/')[2], [(e['tick'], e['citizen_id']) for e in map(json.loads, open(j)) if e['event_type']=='elected'])"
```

*Suspected cause.* The candidate field never changes (OBS-002), ordinary citizens' positions are
static after population generation (only officeholders' and candidates' positions move), and
`institutions.president_term_limit` ships `null` (unlimited). With the same field and the same
electorate, the same ranking wins.

*What would settle it.* The same sweep with `president_term_limit: 2`; S4.3 (dynamic citizens) as
the structural answer.

### OBS-002

**Parties nominate the same five people at every election, snap elections included.**

*Seen.* In seed 1 the dominant-path nominees are citizens 13, 37, 79, 82 and 99 at ticks 0, 16 and
32. In seed 6 the field is 46, 53, 63, 66 and 99 at all seven elections (0, 16, 20, 24, 28, 31,
32), four of them snap elections after a recall.

*Evidence.* `candidacy_declared` events with `payload.path == "dominant"`, grouped by tick.

*Suspected cause.* Nomination picks among declared members by ambition (the model is shown
`ambition_score`; the fallback is the highest-ambition tiebreak), and neither ambition nor the
electorate changes between elections. `institutions.barred_from_immediate_rerun` bars candidates
only after an *invalidated* election, not after a recall (see the comment at `_phase_snap_election`
in `run_polity_simulation.py`).

*What would settle it.* Check whether `ambition_score` is ever updated during a run; compare with a
run where the recalled president is barred from the snap election.

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

*Suspected cause.* OBS-001 and OBS-002: same field, same electorate, and a recalled president is
eligible again.

*What would settle it.* A design decision more than a check: should a recalled president be able
to stand in the snap election? If not, it is a rule; if so, OBS-001's term limit is the lever.

### OBS-004

**The sortition chamber almost never moves: 99.9% of its decisions are "no change".**

*Seen.* Across the ten p100 runs: 4,950 `chamber_deliberation` decisions, 4,944 with motif 701 and
no shift, 6 with motif 702 and three shifts each (18 shifts in total, deltas between -0.1 and
+0.05). 5 decisions fell back. Membership does differ by seed (the first seated chamber differs in
every run).

*Evidence.*

```bash
cd fast_api_voter && python3 -c "import json,glob,collections
c=collections.Counter(e['motif'] for j in glob.glob('scripts/seed_sweep_runs/sweep-8y-p100-seed*/run/*/events.jsonl') for e in map(json.loads, open(j)) if e['event_type']=='chamber_deliberation')
print(c)"
```

*Suspected cause.* Unknown. Candidates: members start at their sincere position (`chamber_position`
is `issue_positions` at seating), so there is no gap to close; the member's `ctx` carries only
`ticks_left`; the prompt may frame "no change" as the safe default; or a content-blind collapse like
OBS-007.

*What would settle it.* A collapse-signature probe for `chamber_deliberation` (does changing the
input change the output?), and reading the model's reasoning for chamber calls in
`llm_calls.jsonl` of any S0.5-or-later LLM run.

### OBS-005

**A president kept by a confidence vote is recalled the same tick.**

*Seen.* p500 scale probe (`flagship_runs/scaleprobe-8y-p500-v2-postfix`), tick 17, citizen 3: a
confidence vote is triggered (event 5680, 26.4% signed) and the president is **retained**, 346 of
500 voting to keep (event 5681, keep ratio 0.692). The same tick, the president is **recalled** by
the legitimacy floor, legitimacy 0.089 below the 0.2 floor (event 5682).

*Evidence.* `python scripts/check_timeline_claims.py` against the run with anchors
`[e5681: confidence_vote_result t17 c3 retained=true keep_ratio=0.692]` and
`[e5682: recalled t17 c3 legitimacy=0.089 trigger=legitimacy_floor]`.

*Suspected cause.* The two removal mechanisms are evaluated independently in the accountability
phase; the vote's outcome does not feed legitimacy or suspend the floor check that tick.

*What would settle it.* Read the order of the confidence vote and the floor check in
`_run_accountability_phase`, then decide (an ADR) whether a retained vote should protect the
president that tick or restore legitimacy.

### OBS-006

**One party's nomination answer is out of range, the same wrong value six times.**

*Seen.* p500 scale probe, ticks 16 and 32: party 3 answers `winner_position=26` for 18, then 19,
declared candidates, in all six attempts (`replays.log`). Because the batch was rejected whole,
`party_nomination_choice` fell back on 10 of its 15 decisions (67%): all five parties at tick 16 and
all five at tick 32.

*Evidence.* `grep winner_position scripts/flagship_runs/scaleprobe-8y-p500-v2-postfix/replays.log`.

*Suspected cause.* Unknown: a position the model derives from something other than the listed
candidates. The current `decide_party_nominations` retries each contested party alone before
falling back, so one party no longer drags the others' nominations with it; the wrong answer itself
is not explained.

*What would settle it.* Whether it recurs in the p500 batch (S0.8, pre-registered red flag 2), and
the model's reasoning for that call in `llm_calls.jsonl`.

### OBS-007

**`representative_response` and `coalition_decision` answer the same whatever the input.**

*Seen.* Six deliberately different inputs each: `representative_response` answered CONCESSION 6/6
and `coalition_decision` JOIN 6/6, on Ollama and again on vLLM with AWQ weights
(`fast_api_voter/scripts/check_vllm_collapse_signatures_results.md`). `representative_response`
was partly fixed on 2026-09-11 (Track B1: its stance is no longer flat once the prompt states the
scales), but both types stay listed as unverified (`viz_export._UNVERIFIED_DECISION_TYPES`).
Related: `representative_response` crossed the 10% fallback alert on p100 seeds 2 (30.3%) and 3
(36.4%), 26 of 330 pooled (7.9%).

*Suspected cause.* Survives a full change of serving stack and quantization, so the model's
behaviour on these two prompt shapes, not infrastructure.

*What would settle it.* S2.4's pre-registered question: does `coalition_decision`'s collapse persist
on at least two non-Qwen model families?

### OBS-008

**Two truncated generations cost more time than all retries and rejected answers together.**

*Seen.* S0.5's live run (2 years, population 100, vLLM): two calls, one `vote_cast` chunk and one
`chamber_deliberation` chunk, each spent about 14,000 reasoning tokens and hit the budget -- 133 s
together, against 121 s for six recovering retries and five rejected answers.

*Evidence.* `fast_api_voter/scripts/llm_call_log_s05_results.md`; `python
scripts/attribute_llm_time.py <run_dir>`.

*Suspected cause.* Non-converging reasoning loops (the "Mode A" pattern documented at
`decide_campaign_positioning`).

*What would settle it.* S1.1 on the p500 call logs (is it two events or a pattern?), then S1.3's
thinking-budget A/B.

### OBS-009

**Journals are not bit-identical across CPUs.**

*Seen.* The golden test failed on some GitHub runners only: `mandate_pledge_declared` content
changed with the same event count. Locally, forcing OpenBLAS's Sandybridge or Prescott kernel
changes `chamber_deliberation` instead.

*Cause (explained).* Population positions are BLAS matrix products; OpenBLAS picks its kernel per
CPU, and a different kernel changes the last bits of those floats. Events that journal raw positions
then differ in their digits. Fixed for the golden references by hashing floats rounded to 9
significant digits (commit `58b07f38`). A run's own journal is still CPU-dependent in its last bits.

*Still open.* Whether those last bits can ever flip a decision (a distance comparison at a tie);
none observed.

### OBS-010

**Half the p100 seeds tell the same story.**

*Seen.* At the `terms` grain (elections and recalls only), 5 of 10 p100 seeds are the same story:
three uninterrupted terms. The other five each have their own recall pattern, up to five
legitimacy-floor recalls in seed 6.

*Evidence.* `python scripts/story_skeletons.py scripts/seed_sweep_runs --grain terms`.

*Suspected cause.* Probably OBS-001 and OBS-002: with a fixed field, the only variation left is
whether legitimacy falls below the floor.

*What would settle it.* Re-run the grouping after OBS-001's term-limit experiment or S4.3.

### OBS-011

**About 40% of citizens declare candidacy at every election.**

*Seen.* p500 scale probe: 202 of 500 citizens declare at tick 0, 206 at tick 16, 206 at tick 32. p100
sweep: 25% to 45% per seed. Only one nominee per party (five in all) ever runs, so the declarations
mostly end in `nomination_lost`.

*Evidence.* `candidacy_considered` events with `payload.outcome == 1`, per tick.

*Suspected cause.* Unknown whether this is the model's reading of `ambition_score` and support or a
prompt effect; the deterministic path uses `candidacy.ambition_threshold` (0.30), the LLM path does
not consult it.

*What would settle it.* Compare with the deterministic threshold's declaration rate on the same
population; S2.2's candidacy case bank.
