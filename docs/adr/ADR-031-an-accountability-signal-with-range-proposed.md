# ADR-031 (proposed): an accountability signal with range

**Status**: Proposed — for the owner's decision; nothing here changes the engine. Option B was chosen first (2026-10-21) and is **blocked on a model run**: see "Option B on the rule-only twin" below.
**Date**: 2026-10-21
**Context**: proposition #3 of the 2026-10-21 polity-engine investigation. ADR-025 removed the recalls of presidents
the population still approved (OBS-047). Since then no president has been recalled, and the question is whether the
loop from citizens to leaders still carries information.

## What the runs show

All of it from run files; the commands are in the last section.

- **No recall since ADR-025.** In the 39 runs from phase12 on (phase12-15, phase16, order-8y): 58 confidence votes,
  **0 lost**, **0 recalls**. Before it (phase10, phase11): 57 and 41 recalls in 10 seeds each.
- **A won vote is won by a wide margin.** The keep ratio of the 58 votes runs 0.67 to 0.94 (medians 0.78-0.88 by
  batch). The ballot is `build_confidence_ballot`: keep iff the president's revealed position is within the voter's
  `blank_threshold` (`simple_rules.py:772-800`). `legitimacy.approval` is the same tolerance test on the revealed position,
  judged with ADR-011's utility, so it also carries a policy-gain term (`vote.policy_retrospection` 2.0, zero unless
  bills are enacted); approval enters legitimacy at weight 0.5 (`legitimacy.approval_weight`) and is journaled on
  `legitimacy_updated` only while that weight is positive.
- **Approval is nearly constant within a term.** Over the 48 presidential terms of at least 8 ticks in phase12, phase16
  and order-8y, approval changes by +0.01 to +0.03 on average between a term's first and last tick (standard deviation
  0.05-0.06), moves within a term by a median 0.04-0.075, and a term's lowest approval is 0.59 at the least (median
  0.68-0.72). No president in these runs has approval under 0.5.
- **Presidents do act.** About half of the president's turns restate positions (168 of 330 in phase16, 134 of 297 in
  order-8y; a turn may restate up to three issues by at most 0.3 each), but only 12-14% draft a bill (39 of 330, 41
  of 297). The restatements read as the president's own convictions ("Prioritizing worker protections, open immigration,
  and progressive values"), and approval does not follow them: it already judges the revealed position and the term's
  policy, and it moves by about 0.06 (one standard deviation) over a term.

So approval hardly responds to what presidents do, because they move little from where they were elected and enact
little. The vote that could remove a president tests the same tolerance count, and the population is never against a
president it just elected. This is ADR-025's
rule working as written ("recalled when the population is against them"), not a defect in it. What it leaves is a
society where a leader's conduct cannot cost them office between elections: the interesting part of accountability,
a leader who misreads the population and loses it, never happens.

## Options

Each is a kernel change; each should be run against the control with the same seeds.

**A. Leave it.** Accountability is electoral only. Consequence: nothing a president does between elections matters to
their survival, so what they do (bills, restatements, amendments) is unconstrained by citizens. Cost: none.

**B. Give conduct more weight in what approval judges.** Approval already judges the revealed position and, through
`policy_retrospection`, the term's policy gain; both are nearly constant because presidents restate little and enact
little (12-14% of turns draft a bill). Candidates: open the agenda more often so more bills are drafted and enacted
(the policy term then moves), or let a restatement move `revealed_position` further per turn (today at most 0.3 on 3
issues). Effect: approval gets variance from conduct. Risk: it rewards presidents for moving to the median, an
equilibrium to measure, not assume.

**C. Make the floor's vote losable.** Keep the vote, change what retains: retain iff the keep ratio exceeds a
threshold above one half (0.6?), or count abstentions of disengaged citizens as against. Effect: a president at 0.55-0.62
approval can be removed. Risk: brings back OBS-047 ("recalled while approved") for presidents below the new bar,
which is the opposite of the owner's rule; this option needs the owner to restate the rule.

**D. Weigh pressure between 0.1 and 1.0** (`legitimacy.pressure_like_support` is today an on/off between 10x and 1x).
Effect: the floor is crossed more often, and each crossing calls a vote. Alone this changes nothing visible: the vote
is won with a keep ratio of 0.67-0.94, so more votes are won. It is only useful together with B or C.

**E. Different signal, not approval.** Recall on distance moved from the pledge (`mandate_deviation`, already
journaled), or on a sustained loss of the mandate ratio, instead of a snapshot of tolerance. Effect: punishes
broken promises specifically. Risk: needs a decision on what a president owes the electorate that a positional vote
does not capture.

My reading, labelled as an opinion: B first (it adds variance without changing the owner's rule), measured; C only if B
leaves votes unwon; D never alone; E if broken pledges, not loss of the center, are the thing to punish.

## Pre-registered test (for whichever option is chosen)

Written before any run, so the choice can be judged and not argued.

- **Design.** Control (today) and one candidate, same code otherwise, each seed's two runs started together on one
  server; 10 paired seeds at 8 years, exploration profile, 8B, thinking budget held at today's value (or the value
  proposition #2's experiment adopts, the same in both arms). Analysis by the sign-flip test of `schema_order_live_report.py`
  (#972), seeds as the unit, Holm across the outcomes.
- **Outcomes.** (1) Within-term standard deviation of approval (does conduct move it); (2) confidence votes held and lost
  per run, and votes called by the floor against by petitions (the "recall attempts"); (3) recalls per run; (4) turnover:
  distinct presidents; (5) for every recalled president, their approval at recall (the failure OBS-047 named is
  "recalled while approved": approval above 0.5); (6) for every lost vote, whether approval fell before it: the change
  in approval over the four ticks before the vote against its within-term standard deviation (does falling approval
  precede losing, or does the vote lose a president approval never warned about); (7) effective parties and office
  occupancy (collateral).
- **Success.** The candidate is adopted only if (1) rises significantly, (3) is above zero in at least 30% of seeds,
  and in at least half of the recalls the president's approval at recall is below 0.5. It fails if more than a quarter of the
  recalls are of presidents above 0.6 (OBS-047 again), whatever else it does.
- **Not part of this test.** The collateral effect on the party system (7) is reported, not gated; (6) is reported with its
  count, since lost votes may be few.

## Evidence commands

```bash
cd fast_api_voter
# confidence votes and recalls since ADR-025 (0 lost, 0 recalled)
python3 -c "import json,glob,sys
v=l=r=0
for ev in glob.glob(sys.argv[1]+'/**/run/*/events.jsonl',recursive=True):
    for line in open(ev):
        if '\"confidence_vote_result\"' in line: e=json.loads(line); v+=1; l+=not e['payload']['retained']
        elif '\"recalled\"' in line: r+=json.loads(line)['event_type']=='recalled'
print('votes',v,'lost',l,'recalls',r)" ~/Documents/Dev/polity-runs/phase16        # also phase12-15, order-8y
# approval within a term (legitimacy_updated.payload.approval over each term of the digest, terms of >= 8 ticks)
python3 -c "import json,glob,os,statistics,sys
ch=[];rg=[];mn=[]
for dg in glob.glob(sys.argv[1]+'/**/run/*/digest.json',recursive=True):
    run=os.path.dirname(dg); ap={}
    for l in open(run+'/events.jsonl'):
        if '\"legitimacy_updated\"' in l:
            e=json.loads(l)
            if e['event_type']=='legitimacy_updated' and 'approval' in e['payload']: ap[e['tick']]=e['payload']['approval']
    for t in json.load(open(dg))['terms']:
        s=[ap[x] for x in range(t['start_tick'],(t['end_tick'] if t['end_tick'] is not None else 32)+1) if x in ap]
        if len(s)>=8: ch.append(s[-1]-s[0]); rg.append(max(s)-min(s)); mn.append(min(s))
print(len(ch),'terms; end-start mean %+.3f sd %.3f; range median %.3f; minimum min %.2f median %.2f'%(statistics.mean(ch),statistics.pstdev(ch),statistics.median(rg),min(mn),statistics.median(mn)))" ~/Documents/Dev/polity-runs/phase16
python3 scripts/check_observations.py recalls ~/Documents/Dev/polity-runs/phase11                  # the shipped rule's recalls, OBS-047
```

(Counts per batch: phase12 3 votes, phase13 8, phase14 5, phase15 8, phase16 19, order-8y 15; 0 lost, 0 recalls in each.
The keep ratios are `confidence_vote_result.payload.keep_ratio` of the same events: minimum 0.72, 0.68, 0.77, 0.67, 0.76, 0.73,
medians 0.86, 0.82, 0.81, 0.78, 0.82, 0.88, maximum 0.89-0.94. The president-turn counts are `agent_turn` events with
`payload.role == "president"` and a non-empty `shifts` or `bill`.)

## Option B on the rule-only twin (2026-10-24, plan-scenarios-v1 step 4)

Step 4 of the scenarios plan wanted B, and C only if recalls stay at zero, gated on the divergence test. Before building it I measured the levers on ten 30-year rule-only runs (no model, the scenario profile, seeds 1-10, 100 citizens; the shipped profile's arm of `python scripts/probe_cohorts.py --output-dir <dir> --arm 0.03,0.35`, which keeps each run's `events.jsonl`; the command is at the end of this section; measured with the scenario profile's economic voting at 1.0, now 0.3 ([ADR-038](ADR-038-economic-voting-calibrated-on-volatility.md)), so the same command now gives other counts):

- The agenda is already open: the formula drafts a bill every `bill_interval_ticks` (2), 535 bills proposed and 62 enacted over ten runs, so `vote.policy_retrospection`'s policy-gain term in approval is live. The model arm's 12-14% of turns that draft a bill is the case B was meant to improve; on the twin there is nothing to open.
- The other lever, a president restating positions further per turn, is an agent behaviour: the twin has no agent turns (0 `agent_turn` events), so there is nothing to move.
- And the vote is still never lost: 34 confidence votes, 0 lost, 0 recalls.

So B as written cannot be measured on the twin, and building a rule-path stand-in for a president's conduct would measure the stand-in. B waits for the pre-registered model test (10 paired 8B seeds at 8 years, which needs vLLM; the GPU is shared). Option C (a retain threshold above one half) is the one that would act on the twin, and it brings back the "recalled while approved" failure OBS-047 named, so it needs the owner to restate the rule; it was not done. Option D of ADR-032 was built instead.

```bash
cd fast_api_voter
python3 -c "import json,glob,collections,sys
c=collections.Counter(); lost=0
for ev in glob.glob(sys.argv[1]+'/*/*/events.jsonl'):
    for line in open(ev):
        t=json.loads(line)['event_type']; c[t]+=1
        lost+= t=='confidence_vote_result' and not json.loads(line)['payload']['retained']
print({k:c[k] for k in ('bill_proposed','bill_enacted','confidence_vote_result','recalled','agent_turn')},'lost',lost)" <dir>/0.03-0.35
# {'bill_proposed': 535, 'bill_enacted': 62, 'confidence_vote_result': 34, 'recalled': 0, 'agent_turn': 0} lost 0
```
