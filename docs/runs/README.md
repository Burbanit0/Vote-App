# Run stories

The story of a Polity run (what the simulated society went through, election by election, and what
the population did), written from the run's `digest.json` by the `run-narrator` agent (`/log-run`).
Every factual claim carries an anchor such as `[e7921: elected t28 c463]`: the `event_id`, type,
tick and citizen of the journal event that backs it, checked with
`python scripts/check_timeline_claims.py <run_dir> --timeline <story>` (from `fast_api_voter/`).

Run directories are not in the repository: they are gigabytes, and `.gitignore` keeps them out. The
stories here are copies, so the runs can be read without them. The same three runs ship as a
compact export (`voter-app/polity-export/`) that the `/polity` explorer reads; the key below opens
a run there (`/polity?run=<key>`).

## The three full runs

30 simulated years, 500 citizens, the flagship profile (the LLM, accountability, events, the social
graph and a 75-seat chamber on; emotions, opinion dynamics and legislation off: plan-full-run D5),
model `qwen3:8b` (`Qwen/Qwen3-8B-AWQ`) on vLLM 0.30.0, on one 16 GB RTX 5070 Ti. All three
completed their 120 ticks in one attempt. Plan and decisions:
[`plan-full-run.md`](../plan/polity/plan-full-run.md). They predate the fixes recorded in OBS-028
and later, and the exploration-profile mechanisms (ADR-014 onward).

| Run | Seed | Code commit | Wall clock | Explorer key | Story |
|---|---|---|---|---|---|
| `full-30y-p500-seed1-20260926` | 1 | `cca7d12a` | 7,162 s | `81aa1c96f54109d1` | [story](full-30y-p500-seed1.md) |
| `full-30y-p500-seed2-20260926` | 2 | `cca7d12a` | 7,498 s | `40891af63e3d8811` | [story](full-30y-p500-seed2.md) |
| `full-30y-p500-seed42-20260926` | 42 | `e362f4d3` | 7,705 s | `f94644cd849efaa8` | [story](full-30y-p500-seed42.md) |

Commit, model and timings come from each run's `run_metadata.json` and `digest.json`.

Each story passes `check_timeline_claims.py` against its run's journal with 0 contradicted
anchors (seed 1: 75 anchors; seed 2: 61; seed 42: 37). Zeros that come from the configuration
(legislation, emotions and opinion dynamics off, a static population) are labelled as such.
The blank-vote figures in them are the model's answers on the uncounted 10% audit probe
(ADR-011), drawn from the whole population, not the electorate's blank voting.
