# ADR-032 (proposed): opinion that persists

**Status**: Proposed — for the owner's decision; nothing here changes the engine.
**Date**: 2026-10-21
**Context**: proposition #4 of the 2026-10-21 polity-engine investigation. ADR-012 gave citizens drifting views,
ADR-016/017 gave them a forum where a citizen can change their mind. The question is whether, in the runs, anyone's
view ends up anywhere new.

## What the runs show

- **Citizens move, then settle.** Over 8 years a citizen's 20-issue position moves a mean of 0.16 (Euclidean), and
  the yearly mean displacement is 0.081, 0.045, 0.026, 0.018, 0.014, 0.011, 0.009, 0.010 (phase16, 10 runs): it
  roughly halves every year and is flat after year 5. Identical per seed across code versions and across models
  (27B 0.150, 8B 0.152 on seed 42).
- **The mover is the dynamics step, not the forum.** The only writers of `issue_positions` after generation are
  `opinion_dynamics.apply_dynamics` (every tick) and `shift_stance` (a forum shift). The step is Friedkin-Johnsen:
  `f' = (1-s)·anchor + s·(f + step·(m - f))`, with the exploration profile's `susceptibility` 0.9, `influence_step` 0.1,
  `drift_std` 0: a relaxation toward a fixed point, which is why displacement decays geometrically. About 78 citizens
  of 100 have a neighbour within `confidence_bound` each tick; the other ~22 never move unless they shift in the forum.
- **A forum shift leaves no trace.** The forum's 0.25-logit nudge (4-14% of turns per seed on the 8B, 0 of 495 on the
  27B) is pulled back by the same step at 0.9 per tick: 66% of it remains after a year, 3% after eight. A shifter's
  displacement over eight years exceeds a non-shifter's by a margin that accounts for 2-9% of the total.
- **The chamber's deliberation does not reach opinion.** Its shifts are written to `chamber_position` only
  (`llm_behavior_engine.py:4878`), never to `issue_positions`; only the bill votes read `chamber_position`. Since
  the dynamics moved the sincere position, the chamber answers "no change" on 92-96% of seating-tick decisions and
  42-50% afterwards (the update to OBS-004 in the ambition-gate PR, #975, with its command).
- **The shifts that do happen look like a prior.** 76-97% go to the "high" pole, 31-61% of them on one issue
  (technology), and toward the neighbours' mean in only 28-43% (from the investigation's scripts, not in the repo; see
  the last note). The 27B makes none (OBS-053, in the founding-lock PR, #974).

So the population's views settle within about four years, and nothing in the loop produces a lasting change: argument
does not accumulate, deliberation does not reach citizens, and a society that has settled has nothing for institutions
to react to.

## Why ADR-012's calibration does not settle it

ADR-012 searched 81 dynamics settings (susceptibility 0.90-0.98, step 0.1-0.4, bound 0.5-2.0, drift 0.02-0.10) on the
deterministic twin before ADR-025 and found none that met its facts D1-D4 (0 of 81), mostly because D4 ("the static arm already
elects 5.7 distinct presidents per run") was decided by the twin's recall churn (OBS-015), not by the mechanism: it
said "a calibration against a twin with a working presidency is a new pre-registration". With ADR-025 the twin has one.
The exploration profile's setting (0.9, 0.1, 1.0, drift 0) is not one of the 81 searched (`drift_std` 0 is outside the
grid) and was not put through D1-D4.

## Options

**A. Leave it.** Opinion is a start-up transient of about four years; later years are a stable society. Cost: none.

**B. A random walk** (`dynamics.drift_std` 0.02-0.05). Views keep moving; the population disperses over time (ADR-012
D2: too much drift shrinks the spread of views as it moves them together). Effect: displacement does not decay to zero.
Risk: movement without cause; a spread that grows with the square root of time.

**C. Less pull to the start** (`susceptibility` → 0.98-1.0). The anchor stops holding people; neighbours decide (bounded
confidence: clusters form). Effect: lasting movement and polarisation into groups. Risk: a long-run consensus or
split that depends on the graph, hard to tie to institutions.

**D. Anchors that follow.** After a forum shift, move the citizen's anchor part of the way (`anchor += k · shift`), so a
stance taken in the forum is partly kept. Effect: argument leaves a trace of size `k · 0.25` logit per shift. Needs a
new parameter and a checkpoint field; the 27B's zero shifts make it irrelevant for that model.

**E. Deliberation reaches opinion.** Write the chamber's shifts (≤ 0.3, three per decision) to `issue_positions`, or
drop them. Today they move a shadow position only the bill votes read. Effect: a citizen who sits in the chamber is
changed by it. Risk: the investigation's scripts found the 8B's non-zero shifts going away from the sincere position
in 74% of cases (the 27B's toward it in 85%), so this would move members off their views without a stated reason;
measure the direction first.

My reading, as an opinion: re-run the ADR-012 calibration on the post-ADR-025 twin first (CPU, minutes), then D with
a small `k` and E only after the chamber's direction is understood. B and C change the whole society to cure one symptom.

## Pre-registered test (for whichever option is chosen)

- **Re-calibration first.** ADR-012's D1-D4, run on the deterministic twin with the exploration profile's ADR-025
  switches, grid and selection as in that ADR, before any setting leaves the adopted values. Its facts are
  pre-registered there; D4 is re-read on a twin with a working presidency and stated in the results before the grid runs.
  The twin has no model, so the forum is not on in it; for options D and E the forum is emulated: shifts injected
  at the measured rate (4-14% of turns, 0.25 logit, issue and direction drawn from the observed distribution), so persistence
  can be tested mechanically before any GPU time.
- **Design for the live check.** Control and candidate, the same seeds started together, 10 paired seeds at 8 years,
  sign-flip test with Holm (`schema_order_live_report.py`), seeds as the unit.
- **Outcomes.** (1) Mean yearly displacement in years 5-8 (does it stay above 0.01); (2) the share of a forum shift
  still visible one year later; (3) spread of views per issue at year 8 over year 0 (no collapse: ratio at least 0.8, ADR-012's D2); (4) bill votes whose result changes when `chamber_position` is replaced by the sincere position, replayed on CPU from
  the journal (does deliberation reach a decision at all; option E turns it on); (5) approval's within-term variance
  and distinct presidents (collateral, ADR-031); (6) effective parties.
- **Success.** (1) significantly above control, (3) not below 0.8, and, for D, (2) above 0.3; for E, (4) above zero in
  at least a quarter of seeds. A candidate that raises (1) by collapsing (3) fails.

## Evidence commands

```bash
cd fast_api_voter
python3 -c "import json,glob,math,statistics,sys
tot=[];yr=[];infl=[]
for run in glob.glob(sys.argv[1]+'/**/run/*/',recursive=True):
    snap={}
    for l in open(run+'snapshots.jsonl'):
        s=json.loads(l); snap.setdefault(s['tick'],{})[s['citizen_id']]=s['issue_positions']
    t=sorted(snap); tot.append(statistics.mean(math.dist(snap[t[0]][c],snap[t[-1]][c]) for c in snap[t[0]]))
    yr.append([statistics.mean(math.dist(snap[a][c],snap[b][c]) for c in snap[a]) for a,b in zip(t,t[1:])])
    infl+= [json.loads(l)['payload']['influenced'] for l in open(run+'events.jsonl') if '\"opinion_dynamics_step\"' in l]
print('runs',len(tot),'mean 8y displacement %.3f'%statistics.mean(tot),'yearly:',' '.join('%.3f'%statistics.mean(r[i] for r in yr) for i in range(len(yr[0]))),'| with a neighbour in bound: mean %.0f of 100'%statistics.mean(infl))" ~/Documents/Dev/polity-runs/phase16
python3 scripts/check_observations.py chamber <run_dir>      # OBS-004: the chamber's motifs
```

The forum-shift persistence (66% after a year, 3% after eight) follows from the step's 0.9 retention per tick
(`0.9^4` and `0.9^32`); the forum shift's share of displacement, the direction and issue concentration of shifts, and the
chamber's direction come from the investigation's scripts (not in the repo) and are reproduced by the experiment above
when it is run.
