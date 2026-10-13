# full-30y-p500-seed2-20260926 — a 30-year, 500-citizen polity with twelve presidential terms held by nine citizens, four ended at the legitimacy floor while all nine confidence votes kept the president

**Provenance.** Run `full-30y-p500-seed2-20260926`, code at commit `cca7d12a96f647932162b0bf531793b419246bb9` (clean tree), started 2026-09-27 01:59 UTC (`run_metadata.json`).
**Model.** `qwen3:8b` = `Qwen/Qwen3-8B-AWQ` served by vLLM 0.30.0 (`run_metadata.json`); the run (started 2026-09-27) predates every fix logged in `docs/plan/polity/observations.md` from OBS-028 (first seen 2026-09-28) to OBS-047, so read it as a measurement of that code, not of today's.
**Setup.** 500 citizens, 30 years (4 ticks per year, 120 ticks), seed 2 (`config.json`); presidency on a 4-year term with a limit of 2 terms, 100-seat party-list assembly, 75-seat sortition chamber.

**How it ended.** Completed: tick 120 of 120 planned, single attempt (no resume), 7,498.1 s of wall-clock (`digest.json` `elapsed_seconds`; `progress.json` shows 7,408.1 s at its last write). The journal holds 45,549 events and 0 malformed lines were skipped. Office occupancy was 0.9587 (`office_occupancy`); each of the four recalls left a gap between two terms.

## The story

**Years 0 to 11: three full terms, no recall.** Citizen 131 took the presidency at tick 0 [e739: elected t0 c131] and served the full term to tick 16 (`terms`). Petitions to remove them were launched at ticks 0 and 8 [e907: petition_launched t0 c288] [e2577: petition_launched t8 c3] and both died short of the 25% signature threshold, at 22.2% and 17.6% [e1923: petition_expired t4 signed_ratio=0.222] [e3470: petition_expired t12 signed_ratio=0.176]. Legitimacy fell as low as 0.269 in that term (`legitimacy_trajectory`) but never reached the 0.2 recall floor.

**Citizen 325 won in year 4 and was nearly removed on day one.** 325 was elected at tick 16 [e4717: elected t16 c325], and a petition at 25.8% of the electorate forced a confidence vote the next tick [e5310: confidence_vote_triggered t17 c325 signed_ratio=0.258]. The citizens kept them: 352 of 500 voted to retain [e5311: confidence_vote_result t17 c325 keep=352 keep_ratio=0.704 retained=true]. 325 finished the term, with legitimacy touching 0.251 (`legitimacy_trajectory`), and a scandal hit them at tick 32 [e8513: scandal_occurred t32 c325]. Their term ended at the tick-32 election, which 131 won, returning for a second, non-consecutive term [e9254: elected t32 c131].

**The second 131 term ended in scandal.** Three scandals struck 131 in four ticks [e11571: scandal_occurred t40 c131] [e12531: scandal_occurred t42 c131] [e13232: scandal_occurred t43 c131], but the petition against them peaked at 15% [e14128: petition_expired t44 signed_ratio=0.15] and no recall followed. 131 served to the end of the term (their second, which exhausts the two-term limit), and the tick-48 election went to citizen 141 [e15420: elected t48 c141]. That closed the polity's stable stretch: three straight full terms (131, 325, 131).

**Years 12 to 19: three recalls in twenty-three ticks.** 141 faced a confidence vote one tick after taking office, with 30.8% signed [e16189: confidence_vote_triggered t49 c141 signed_ratio=0.308], and was kept, 353 of 500 [e16190: confidence_vote_result t49 c141 keep=353 keep_ratio=0.706 retained=true]. A second petition reached 42.4% [e17931: confidence_vote_triggered t54 c141 signed_ratio=0.424]; the vote again kept them (344 of 500, 68.8%) and averted the recall that tick [e17932: confidence_vote_result t54 c141 keep=344 keep_ratio=0.688 averted_recall=true retained=true]. One tick later the legitimacy rule removed them anyway, at 0.036 against a floor of 0.2 [e18250: recalled t55 c141 legitimacy=0.036 recall_floor=0.2 trigger=legitimacy_floor], and a snap election was scheduled for tick 56 [e18251: snap_election_triggered t55 recalled_citizen_id=141 next_attempt_tick=56]. In year 13 the pressure table shows why: 185 of 935 consulted citizens decided to mobilise, against 0 in years 0 and 4 and 2 in year 14 (see the year table).

The snap election of tick 56 went to citizen 425 [e19005: elected t56 c425 attempt=1], who survived two confidence votes, at ticks 57 and 62, with 72.2% and 69.8% to keep [e19756: confidence_vote_triggered t57 c425 signed_ratio=0.284] [e19757: confidence_vote_result t57 c425 keep_ratio=0.722 retained=true] [e21322: confidence_vote_triggered t62 c425 signed_ratio=0.35] [e21323: confidence_vote_result t62 c425 keep_ratio=0.698 retained=true] and served to the tick-64 election, which citizen 224 won [e22327: elected t64 c224].

The cycle then ran twice more, each time against a president the electorate had just voted to keep:

- 224 won a confidence vote at tick 65 with 362 of 500 [e23135: confidence_vote_triggered t65 c224 signed_ratio=0.388] [e23136: confidence_vote_result t65 c224 keep=362 retained=true], then was recalled at tick 70 at legitimacy 0.167 without a second vote [e24733: recalled t70 c224 legitimacy=0.167 trigger=legitimacy_floor] [e24734: snap_election_triggered t70 recalled_citizen_id=224 next_attempt_tick=71]. The snap election went to citizen 0 [e25468: elected t71 c0 attempt=1].
- Citizen 0 was kept twice, at 59.4% both times (297 of 500), after a petition that reached 45.8% [e26468: confidence_vote_triggered t72 c0 signed_ratio=0.458] [e26469: confidence_vote_result t72 c0 keep=297 keep_ratio=0.594 retained=true] [e28317: confidence_vote_triggered t77 c0 signed_ratio=0.33] [e28318: confidence_vote_result t77 c0 keep=297 averted_recall=true retained=true]. Legitimacy hit zero at tick 78 [e28625: recalled t78 c0 legitimacy=0 trigger=legitimacy_floor] [e28626: snap_election_triggered t78 recalled_citizen_id=0 next_attempt_tick=79]. The snap election returned citizen 141, the president recalled 24 ticks earlier (the bar `recalled_barred_from_snap_election`, true in `config.json`, keeps a recalled president out of the snap election that follows their own recall only; at tick 56, 141 was barred, and 425 won) [e29363: elected t79 c141 attempt=1].

**A one-tick presidency.** The snap election of tick 79 was held one tick before the scheduled election of tick 80. Citizen 483 won that [e30432: elected t80 c483], so 141's second term lasted from tick 79 to tick 80 (`terms`: `ended_by: election`). It was the shortest in the run.

**Years 20 to 25: the longest calm.** 483 served the full term to tick 96. Petitions found little support: the one opened at the election drew 7.8% and the next, opened at tick 88, 18.8% [e31882: petition_expired t84 signed_ratio=0.078] [e33886: petition_expired t92 signed_ratio=0.188]. In year 20 the share of consulted citizens who decided to do nothing was 88.5%; in year 21 it was 98.5% (digest `inaction_rate`).

**Last cycle: another recall and a comeback.** Citizen 142 won at tick 96 [e35269: elected t96 c142] and a scandal hit them the next tick [e35608: scandal_occurred t97 c142]. A petition at 30% forced a confidence vote at tick 105 [e39025: confidence_vote_triggered t105 c142 signed_ratio=0.3], which they won (345 of 500) [e39026: confidence_vote_result t105 c142 keep=345 keep_ratio=0.69 averted_recall=true retained=true]; the legitimacy floor removed them at tick 106 anyway, at 0 [e39290: recalled t106 c142 legitimacy=0 recall_floor=0.2 trigger=legitimacy_floor] [e39291: snap_election_triggered t106 recalled_citizen_id=142 next_attempt_tick=107]. Citizen 70 won the snap election [e40032: elected t107 c70 attempt=1]; a petition against them closed at 2.4% [e41753: petition_expired t111 signed_ratio=0.024]. Citizen 483 returned at the tick-112 election for a second term [e42495: elected t112 c483], a scandal touched them at tick 116 [e43709: scandal_occurred t116 c483], and their petition got 0.8% [e44494: petition_expired t116 signed_ratio=0.008]. The run closed at tick 120 with 483 in office and a lame-duck flag, legitimacy 0.732 (`terms`, `legitimacy_trajectory`; term ended `run_end`).

**The legislature never changed.** There were 8 legislative elections (ticks 8, 24, ..., 120). All eight journaled the same result: the same five-party seat split (20, 22, 18, 20, 20), the same vote totals, 16 blank ballots, and a governing coalition of parties 1, 0 and 3 formed in two rounds [e2488: legislative_result t8 blank_count=16] [e2497: coalition_formed t8] [e45295: legislative_result t120 blank_count=16] [e45304: coalition_formed t120]. No bill was ever proposed, reviewed, voted, enacted or blocked in 30 years: every `bill_*` count is 0, as is `policy_status`. This is what the configuration predicts: legislation, opinion dynamics and emotions are switched off in this run (`legislation.enabled`, `dynamics.enabled`, `emotions.enabled` false in `config.json`) and the population is static, so nothing that feeds the legislative vote changes between elections, and no bill can be proposed. The coalition findings carry the `coalition_decision` caveat (`unverified_decision_types`): that type is known to answer the same whatever the input (OBS-007), so a stable coalition is not independent evidence of anything.

**What did not happen.** Economic shocks were enabled in the configuration and none fired (`economic_shock_tick` is 0 in every year). Six scandals occurred (ticks 32, 40, 42, 43, 97, 116), each followed by one reaction round from all 500 citizens (3,000 reactions total). The first round, at tick 32, is content-blind: 499 of 500 citizens returned exactly the same salience shift of 0.1 [e9332: reaction_to_event t32 c0 salience_delta=0.1], so the digest's year-8 mean salience delta (0.0998) is not a finding about how a scandal moved opinion. The later rounds vary, but each is dominated by one value (0.15 or 0.2). Opinion dynamics and emotions were switched off in this run's configuration (`dynamics.enabled` and `emotions.enabled` false in `config.json`), so their zero counts are a setting, not a quiet society. No election was invalidated and none ended without a winner (both 0).

## Year by year

Notes on the table. "Candidacy" counts the whole population being asked (`candidacy_considered`); "wanted to run" is the citizens whose answer was yes (`outcome` 1), "declaration events" is the `candidacy_declared` events that year (far fewer: parties nominate five, others stand outside elections). "Pressure" counts decided acts, not applied ones; a decided petition launch the citizen could not make becomes a signature, so the Petitions column is what took effect. "Blank vote" is not the electorate's blank voting. The ballots that decide an election are the utility ballots (`vote.mode` is `utility`). The `vote_cast` events are a separate probe that asks the model how a sample of citizens would vote; they are journaled with `audit=1` and never counted. The sample is drawn from all 500 citizens, not from those who vote (`vote.audit_fraction` 0.1), so its size stays near 50 whatever the abstention: 43 `vote_cast` answers at tick 0, where the election itself journals 184 abstentions [e739: elected t0 c131 abstained=184]. Read the column as the model's blank answers on an uncounted ~10% probe of the whole population. "0 ballots" means no election that year.

| Year | Ticks | What happened | Candidacy | Pressure (decided) | Petitions | Blank answers (uncounted probe) |
|---|---|---|---|---|---|---|
| 0 | 0-3 | c131 elected t0 | 500 considered, 185 wanted to run (37%), 5 declaration events | 561 consulted: NOTHING 399, SIGN_PETITION 111, MOBILIZE 0, WAIT_FOR_ELECTION 51 | 1 launched, 110 signed, 0 expired, peak 0.222, 0 conf. votes | 17/43 (39.5%) |
| 1 | 4-7 | no election, recall or vote | 0 considered; 3 declaration events | 451 consulted: NOTHING 435, SIGN_PETITION 5, MOBILIZE 4, WAIT_FOR_ELECTION 7 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 2 | 8-11 | legislative election t8 | 0 considered; 2 declaration events | 400 consulted: NOTHING 307, SIGN_PETITION 88, MOBILIZE 1, WAIT_FOR_ELECTION 4 | 1 launched, 87 signed, 0 expired, peak 0.176, 0 conf. votes | 0 ballots |
| 3 | 12-15 | no election, recall or vote | 0 considered; 3 declaration events | 356 consulted: NOTHING 291, SIGN_PETITION 12, MOBILIZE 51, WAIT_FOR_ELECTION 2 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 4 | 16-19 | c325 elected t16; confidence vote t17: kept 352/500 | 500 considered, 186 wanted to run (37%), 8 declaration events | 598 consulted: NOTHING 465, SIGN_PETITION 131, MOBILIZE 0, WAIT_FOR_ELECTION 2 | 1 launched, 128 signed, 0 expired, peak 0.258, 1 conf. votes | 24/51 (47.1%) |
| 5 | 20-23 | no election, recall or vote | 0 considered; 2 declaration events | 569 consulted: NOTHING 443, SIGN_PETITION 120, MOBILIZE 0, WAIT_FOR_ELECTION 6 | 1 launched, 118 signed, 0 expired, peak 0.238, 0 conf. votes | 0 ballots |
| 6 | 24-27 | legislative election t24 | 0 considered; 3 declaration events | 524 consulted: NOTHING 511, SIGN_PETITION 5, MOBILIZE 0, WAIT_FOR_ELECTION 8 | 0 launched, 1 signed, 1 expired, peak 0.24, 0 conf. votes | 0 ballots |
| 7 | 28-31 | no election, recall or vote | 0 considered; 2 declaration events | 472 consulted: NOTHING 354, SIGN_PETITION 115, MOBILIZE 0, WAIT_FOR_ELECTION 3 | 1 launched, 113 signed, 0 expired, peak 0.228, 0 conf. votes | 0 ballots |
| 8 | 32-35 | scandal t32 (c325); c131 elected t32 | 500 considered, 185 wanted to run (37%), 8 declaration events | 597 consulted: NOTHING 469, SIGN_PETITION 123, MOBILIZE 0, WAIT_FOR_ELECTION 5 | 1 launched, 122 signed, 0 expired, peak 0.246, 0 conf. votes | 35/44 (79.5%) |
| 9 | 36-39 | no election, recall or vote | 0 considered; 2 declaration events | 468 consulted: NOTHING 465, SIGN_PETITION 3, MOBILIZE 0, WAIT_FOR_ELECTION 0 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 10 | 40-43 | scandal t40 (c131); legislative election t40; scandal t42 (c131); scandal t43 (c131) | 0 considered; 2 declaration events | 462 consulted: NOTHING 368, SIGN_PETITION 75, MOBILIZE 0, WAIT_FOR_ELECTION 19 | 1 launched, 74 signed, 0 expired, peak 0.15, 0 conf. votes | 0 ballots |
| 11 | 44-47 | no election, recall or vote | 0 considered; 3 declaration events | 431 consulted: NOTHING 425, SIGN_PETITION 3, MOBILIZE 2, WAIT_FOR_ELECTION 1 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 12 | 48-51 | c141 elected t48; confidence vote t49: kept 353/500 | 500 considered, 186 wanted to run (37%), 8 declaration events | 884 consulted: NOTHING 708, SIGN_PETITION 156, MOBILIZE 7, WAIT_FOR_ELECTION 13 | 1 launched, 153 signed, 0 expired, peak 0.308, 1 conf. votes | 36/49 (73.5%) |
| 13 | 52-55 | confidence vote t54: kept 344/500, recall averted; c141 recalled t55 (legitimacy 0.036) | 0 considered; 1 declaration events | 935 consulted: NOTHING 532, SIGN_PETITION 218, MOBILIZE 185, WAIT_FOR_ELECTION 0 | 1 launched, 211 signed, 0 expired, peak 0.424, 1 conf. votes | 0 ballots |
| 14 | 56-59 | c425 elected t56 (snap); legislative election t56; confidence vote t57: kept 361/500 | 500 considered, 185 wanted to run (37%), 10 declaration events | 851 consulted: NOTHING 704, SIGN_PETITION 145, MOBILIZE 2, WAIT_FOR_ELECTION 0 | 1 launched, 141 signed, 0 expired, peak 0.284, 1 conf. votes | 24/58 (41.4%) |
| 15 | 60-63 | confidence vote t62: kept 349/500 | 0 considered, 0 declaration events | 761 consulted: NOTHING 566, SIGN_PETITION 184, MOBILIZE 10, WAIT_FOR_ELECTION 1 | 1 launched, 174 signed, 0 expired, peak 0.35, 1 conf. votes | 0 ballots |
| 16 | 64-67 | c224 elected t64; confidence vote t65: kept 362/500 | 500 considered, 185 wanted to run (37%), 8 declaration events | 892 consulted: NOTHING 661, SIGN_PETITION 200, MOBILIZE 30, WAIT_FOR_ELECTION 1 | 1 launched, 193 signed, 0 expired, peak 0.388, 1 conf. votes | 18/47 (38.3%) |
| 17 | 68-71 | c224 recalled t70 (legitimacy 0.167); c0 elected t71 (snap) | 500 considered, 185 wanted to run (37%), 6 declaration events | 952 consulted: NOTHING 698, SIGN_PETITION 139, MOBILIZE 109, WAIT_FOR_ELECTION 6 | 2 launched, 134 signed, 0 expired, peak 0.246, 0 conf. votes | 18/40 (45.0%) |
| 18 | 72-75 | legislative election t72; confidence vote t72: kept 297/500 | 0 considered; 1 declaration events | 1089 consulted: NOTHING 787, SIGN_PETITION 220, MOBILIZE 65, WAIT_FOR_ELECTION 17 | 0 launched, 216 signed, 0 expired, peak 0.458, 1 conf. votes | 0 ballots |
| 19 | 76-79 | confidence vote t77: kept 297/500, recall averted; c0 recalled t78 (legitimacy 0.000); c141 elected t79 (snap) | 500 considered, 185 wanted to run (37%), 7 declaration events | 969 consulted: NOTHING 681, SIGN_PETITION 171, MOBILIZE 112, WAIT_FOR_ELECTION 5 | 2 launched, 167 signed, 0 expired, peak 0.33, 1 conf. votes | 9/43 (20.9%) |
| 20 | 80-83 | c483 elected t80 | 500 considered, 185 wanted to run (37%), 10 declaration events | 834 consulted: NOTHING 738, SIGN_PETITION 39, MOBILIZE 0, WAIT_FOR_ELECTION 57 | 1 launched, 38 signed, 0 expired, peak 0.078, 0 conf. votes | 6/49 (12.2%) |
| 21 | 84-87 | no election, recall or vote | 0 considered; 3 declaration events | 684 consulted: NOTHING 674, SIGN_PETITION 3, MOBILIZE 0, WAIT_FOR_ELECTION 7 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 22 | 88-91 | legislative election t88 | 0 considered; 3 declaration events | 622 consulted: NOTHING 527, SIGN_PETITION 94, MOBILIZE 0, WAIT_FOR_ELECTION 1 | 1 launched, 93 signed, 0 expired, peak 0.188, 0 conf. votes | 0 ballots |
| 23 | 92-95 | no election, recall or vote | 0 considered; 3 declaration events | 553 consulted: NOTHING 542, SIGN_PETITION 4, MOBILIZE 4, WAIT_FOR_ELECTION 3 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 24 | 96-99 | c142 elected t96; scandal t97 (c142) | 500 considered, 185 wanted to run (37%), 7 declaration events | 1015 consulted: NOTHING 958, SIGN_PETITION 39, MOBILIZE 6, WAIT_FOR_ELECTION 12 | 1 launched, 38 signed, 0 expired, peak 0.078, 0 conf. votes | 14/44 (31.8%) |
| 25 | 100-103 | no election, recall or vote | 0 considered; 1 declaration events | 865 consulted: NOTHING 791, SIGN_PETITION 8, MOBILIZE 64, WAIT_FOR_ELECTION 2 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 26 | 104-107 | legislative election t104; confidence vote t105: kept 345/500, recall averted; c142 recalled t106 (legitimacy 0.000); c70 elected t107 (snap) | 500 considered, 185 wanted to run (37%), 8 declaration events | 864 consulted: NOTHING 578, SIGN_PETITION 158, MOBILIZE 128, WAIT_FOR_ELECTION 0 | 2 launched, 154 signed, 0 expired, peak 0.3, 1 conf. votes | 15/46 (32.6%) |
| 27 | 108-111 | no election, recall or vote | 0 considered; 3 declaration events | 1032 consulted: NOTHING 644, SIGN_PETITION 6, MOBILIZE 50, WAIT_FOR_ELECTION 332 | 0 launched, 6 signed, 1 expired, peak 0.024, 0 conf. votes | 0 ballots |
| 28 | 112-115 | c483 elected t112 | 500 considered, 185 wanted to run (37%), 5 declaration events | 897 consulted: NOTHING 564, SIGN_PETITION 4, MOBILIZE 0, WAIT_FOR_ELECTION 329 | 1 launched, 3 signed, 0 expired, peak 0.008, 0 conf. votes | 12/47 (25.5%) |
| 29 | 116-119 | scandal t116 (c483) | 0 considered; 2 declaration events | 767 consulted: NOTHING 728, SIGN_PETITION 3, MOBILIZE 0, WAIT_FOR_ELECTION 36 | 0 launched, 0 signed, 1 expired, peak n/a, 0 conf. votes | 0 ballots |
| 30 | 120-120 | legislative election t120 | 0 considered; 1 declaration events | 163 consulted: NOTHING 160, SIGN_PETITION 3, MOBILIZE 0, WAIT_FOR_ELECTION 0 | 1 launched, 2 signed, 0 expired, peak 0.006, 0 conf. votes | 0 ballots |

## Full event accounting

Totals over the 31 year-buckets (year 30 is the final tick, 120). "0 in all 31 years" is a measured zero: the run tracks the event and it never fired. Where the configuration switches a subsystem off (emotions, opinion dynamics) the zero is a setting.

| Event type | Total | Years with a nonzero count (year:count) |
|---|---|---|
| bill_blocked | 0 | 0 in all 31 years |
| bill_enacted | 0 | 0 in all 31 years |
| bill_proposed | 0 | 0 in all 31 years |
| bill_reviewed | 0 | 0 in all 31 years |
| bill_voted | 0 | 0 in all 31 years |
| campaign_positioning | 60 | 0:5, 4:5, 8:5, 12:5, 14:5, 16:5, 17:5, 19:5, 20:5, 24:5, 26:5, 28:5 |
| candidacy_considered | 6000 | 0:500, 4:500, 8:500, 12:500, 14:500, 16:500, 17:500, 19:500, 20:500, 24:500, 26:500, 28:500 |
| candidacy_declared | 130 | 0:5, 1:3, 2:2, 3:3, 4:8, 5:2, 6:3, 7:2, 8:8, 9:2, 10:2, 11:3, 12:8, 13:1, 14:10, 16:8, 17:6, 18:1, 19:7, 20:10, 21:3, 22:3, 23:3, 24:7, 25:1, 26:8, 27:3, 28:5, 29:2, 30:1 |
| chamber_deliberation | 9075 | 0:300, 1:300, 2:300, 3:300, 4:300, 5:300, 6:300, 7:300, 8:300, 9:300, 10:300, 11:300, 12:300, 13:300, 14:300, 15:300, 16:300, 17:300, 18:300, 19:300, 20:300, 21:300, 22:300, 23:300, 24:300, 25:300, 26:300, 27:300, 28:300, 29:300, 30:75 |
| clamped_at_bound | 76 | 0:3, 2:1, 3:1, 5:2, 6:4, 7:4, 8:2, 9:2, 10:1, 12:5, 13:8, 14:11, 16:2, 17:7, 20:1, 21:2, 22:2, 23:4, 24:4, 27:2, 28:3, 29:5 |
| coalition_decision | 64 | 2:8, 6:8, 10:8, 14:8, 18:8, 22:8, 26:8, 30:8 |
| coalition_failed | 0 | 0 in all 31 years |
| coalition_formed | 8 | 2:1, 6:1, 10:1, 14:1, 18:1, 22:1, 26:1, 30:1 |
| confidence_vote_result | 9 | 4:1, 12:1, 13:1, 14:1, 15:1, 16:1, 18:1, 19:1, 26:1 |
| confidence_vote_triggered | 9 | 4:1, 12:1, 13:1, 14:1, 15:1, 16:1, 18:1, 19:1, 26:1 |
| economic_shock_tick | 0 | 0 in all 31 years |
| elected | 12 | 0:1, 4:1, 8:1, 12:1, 14:1, 16:1, 17:1, 19:1, 20:1, 24:1, 26:1, 28:1 |
| election_invalidated | 0 | 0 in all 31 years |
| election_no_winner | 0 | 0 in all 31 years |
| emotions_updated | 0 | 0 in all 31 years |
| legislative_result | 8 | 2:1, 6:1, 10:1, 14:1, 18:1, 22:1, 26:1, 30:1 |
| legitimacy_updated | 121 | 0:4, 1:4, 2:4, 3:4, 4:4, 5:4, 6:4, 7:4, 8:4, 9:4, 10:4, 11:4, 12:4, 13:4, 14:4, 15:4, 16:4, 17:4, 18:4, 19:4, 20:4, 21:4, 22:4, 23:4, 24:4, 25:4, 26:4, 27:4, 28:4, 29:4, 30:1 |
| mandate_deviation_recorded | 6 | 13:4, 15:2 |
| mandate_pledge_declared | 12 | 0:1, 4:1, 8:1, 12:1, 14:1, 16:1, 17:1, 19:1, 20:1, 24:1, 26:1, 28:1 |
| nomination_lost | 2145 | 0:180, 4:181, 8:180, 12:180, 14:178, 16:179, 17:178, 19:178, 20:178, 24:178, 26:177, 28:178 |
| opinion_dynamics_step | 0 | 0 in all 31 years |
| party_nomination_choice | 60 | 0:5, 4:5, 8:5, 12:5, 14:5, 16:5, 17:5, 19:5, 20:5, 24:5, 26:5, 28:5 |
| petition_expired | 10 | 1:1, 3:1, 6:1, 9:1, 11:1, 21:1, 23:1, 25:1, 27:1, 29:1 |
| petition_launched | 23 | 0:1, 2:1, 4:1, 5:1, 7:1, 8:1, 10:1, 12:1, 13:1, 14:1, 15:1, 16:1, 17:2, 19:2, 20:1, 22:1, 24:1, 26:2, 28:1, 30:1 |
| petition_signed | 2476 | 0:110, 2:87, 4:128, 5:118, 6:1, 7:113, 8:122, 10:74, 12:153, 13:211, 14:141, 15:174, 16:193, 17:134, 18:216, 19:167, 20:38, 22:93, 24:38, 26:154, 27:6, 28:3, 30:2 |
| policy_status | 0 | 0 in all 31 years |
| pressure_action | 21518 | 0:561, 1:451, 2:400, 3:356, 4:598, 5:569, 6:524, 7:472, 8:597, 9:468, 10:462, 11:431, 12:884, 13:935, 14:851, 15:761, 16:892, 17:952, 18:1089, 19:969, 20:834, 21:684, 22:622, 23:553, 24:1015, 25:865, 26:864, 27:1032, 28:897, 29:767, 30:163 |
| reaction_to_event | 3000 | 8:500, 10:1500, 24:500, 29:500 |
| recalled | 4 | 13:1, 17:1, 19:1, 26:1 |
| representative_response | 121 | 0:4, 1:4, 2:4, 3:4, 4:4, 5:4, 6:4, 7:4, 8:4, 9:4, 10:4, 11:4, 12:4, 13:4, 14:4, 15:4, 16:4, 17:4, 18:4, 19:4, 20:4, 21:4, 22:4, 23:4, 24:4, 25:4, 26:4, 27:4, 28:4, 29:4, 30:1 |
| scandal_occurred | 6 | 8:1, 10:3, 24:1, 29:1 |
| snap_election_triggered | 4 | 13:1, 17:1, 19:1, 26:1 |
| sortition_rotation | 31 | 0:1, 1:1, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1, 9:1, 10:1, 11:1, 12:1, 13:1, 14:1, 15:1, 16:1, 17:1, 18:1, 19:1, 20:1, 21:1, 22:1, 23:1, 24:1, 25:1, 26:1, 27:1, 28:1, 29:1, 30:1 |
| vote_cast | 561 | 0:43, 4:51, 8:44, 12:49, 14:58, 16:47, 17:40, 19:43, 20:49, 24:44, 26:46, 28:47 |

## Population impact

**Who wanted to run.** At each of the 12 presidential elections (years 0, 4, 8, 12, 14, 16, 17, 19, 20, 24, 26, 28) all 500 citizens were consulted and 185 or 186 wanted to run (37%). The count barely moved across 30 years, with presidents, scandals and recalls in between. This is the repetition OBS-011 and OBS-001 describe. Five parties nominated one candidate each (`party_nomination_choice` 5 at each election).

**Who stayed home.** Each `elected` event journals its abstentions: 184 at tick 0 [e739: elected t0 c131 abstained=184] and 375 at tick 96 [e35269: elected t96 c142 abstained=375] are the extremes, with the other ten elections between 218 and 370, out of 500 citizens. The journal gives no reason for the swing; OBS-042 records the same pattern on earlier code (two citizens in three staying home).

**Who was consulted and what they chose.** The pressure menu was asked 21,518 times (decided acts, not applied): NOTHING 17,173, SIGN_PETITION 2,585, WAIT_FOR_ELECTION 930, MOBILIZE 830. Most of the mobilisation sat in five years: 51 in year 3, 185 in year 13, 109 in year 17, 112 in year 19 and 128 in year 26. WAIT_FOR_ELECTION is small everywhere except 332 in year 27 and 329 in year 28. The spike starts in year 27, before the tick-112 presidential election (year 28 holds it), and the journal shows it in two bursts, ticks 108 to 110 and 113 to 115. Seed 42 of the same batch shows the same spike at ticks 113 to 115 (319 in its year 28, from its `digest.json`). It is a cross-run pattern; the cause is unknown.

**Who signed.** 23 petitions were launched, 2,476 signatures were journaled, 10 petitions expired. Nine reached the threshold and forced a confidence vote; every one of those 9 kept the president, with keep ratios between 0.594 and 0.724. The largest petition was 0.458 of the electorate (year 18). Each of the 4 recalls came from the legitimacy floor, not a vote.

**The officeholder's standing.** Term-by-term minimum legitimacy (`legitimacy_trajectory`): 0.269 (131), 0.251 (325), 0.260 (131), 0.036 (141), 0.439 (425), 0.167 (224), 0.0 (c0), 0.685 (141, 1 tick), 0.363 (483), 0.0 (142), 0.534 (70), 0.730 (483). Mandate strength at the start of each term ranged from 0.616 to 0.746 (`terms`). The first three presidencies never touched the floor: the lowest was 0.251. Three of the four recalls came in a block (ticks 55, 70, 78), the fourth at tick 106; a recalled president took office again (141, 24 ticks after their recall); and the final term is the best in the run for legitimacy.

**Unverified metrics.** `mandate_deviation_recorded` (6 events: 4 in year 13, 2 in year 15), mandate deviation, lame-duck deviation delta (all from `representative_response`) and the coalition fields (`coalition_decision`) are on the known-collapse list in `metadata.unverified_decision_types`. Do not read the six deviation events as a finding.

## Data quality

- 24,129 LLM calls completed by `progress.json`, `llm_calls_summary.json` logs 26,139 call records; 256 retries and 710 fallbacks across 40,459 decisions (`progress.json`, `digest.json`). `llm_fallback_alerts` is empty.
- Fallbacks by type: `chamber_deliberation` 645 (7.11% of its 9,075 decisions; OBS-021: the model returns more shifts than the cap allows), `reaction_to_event` 50 (1.67%; OBS-025: a whole batch of 25 discarded when the model overshoots the delta bound), `vote_cast` 12 (2.14%; OBS-024, thinking budget binding), `representative_response` 3 (2.48%). Zero for `candidacy_considered`, `pressure_action`, `coalition_decision`, `campaign_positioning` and `party_nomination_choice`.
- The tick-32 scandal reactions are content-blind (499 of 500 answers identical, see "What did not happen"); treat scandal-reaction means as unverified.
- `vote_cast` fell back for 12 of 561 ballots: the blank rates in the year table are the model's answers on the uncounted ~10% probe of the whole population (not the electorate's blank voting) and include those fallbacks.
- The journal has no malformed lines and the run was not resumed (`resumed_attempt` false, `resumes` empty).
- Unverified metrics: see the end of "Population impact".
- Provenance caution: the code at `cca7d12` predates every fix logged from OBS-028 to OBS-047 (first seen 2026-09-28 onward). It shows how the engine behaved then.
