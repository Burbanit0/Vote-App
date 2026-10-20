# Field order per decision: the latest verdict (ADR-030)

Written by `scripts/check_schema_order.py decide` on the order bank (`case_bank_order.jsonl`, sha `0b190ae7842f7c9c`). The rule, written before any run: a candidate replaces the current order only if it beats the first control on the type's primary measure (paired McNemar, Holm across that type's distinct candidate orders, p < 0.05), also beats the second control, does not lower validity significantly and does not collapse onto one answer; a measure whose two controls disagree on more than 10% of units keeps the current order.

| decision | primary measure | noise | current order | verdict | reason |
| --- | --- | ---: | --- | --- | --- |
| vote_cast | vote_first_choice_wide | 0.0% | blank, cid, motif, ranking | keep | no candidate beats the control |
| candidacy_considered | candidacy_p500 | 0.0% | cid, motif, outcome | keep | no candidate beats the control |
| party_nomination_choice | validity | 0.0% | motif, party_id, winner_position | keep | no candidate beats the control |
| campaign_positioning | - | – | cid, motif, shifts | keep | not in the bank |
| representative_response | validity | 0.0% | cid, motif, shifts, stance | keep | no candidate beats the control |
| pressure_action | pressure_act_wide | 0.0% | act, cid, motif, target | keep | no candidate beats the control |
| reaction_to_event | validity | 0.0% | cid, motif, salience_delta | keep | no candidate beats the control |
| chamber_deliberation | validity | 0.0% | cid, motif, shifts | keep | no candidate beats the control |
| coalition_decision | validity | 0.0% | action, motif, party_id | keep | no candidate beats the control |

## vote_cast

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx | cid, blank, motif, ranking | 152/160 | 149 | 149 | 3 / 0 | 1 | - |
| order_dxm | cid, blank, ranking, motif | 149/160 | 149 | 149 | 3 / 3 | 1 | - |
| order_mdx | cid, motif, blank, ranking | 152/160 | 149 | 149 | 3 / 0 | 1 | - |
| order_mxd | cid, motif, ranking, blank | 152/160 | 149 | 149 | 3 / 0 | 1 | - |
| order_xdm | cid, ranking, blank, motif | 152/160 | 149 | 149 | 3 / 0 | 1 | - |
| order_xmd | cid, ranking, motif, blank | 152/160 | 149 | 149 | 3 / 0 | 1 | - |

## candidacy_considered

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx = order_dxm = order_xdm | cid, outcome, motif | 332/500 | 318 | 318 | 31 / 17 | 0.0595 | - |

## party_nomination_choice

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx = order_dxm = order_xdm | party_id, winner_position, motif | 10/10 | 10 | 10 | 0 / 0 | 1 | - |
| order_mdx = order_mxd = order_xmd | party_id, motif, winner_position | 10/10 | 10 | 10 | 0 / 0 | 1 | - |

## representative_response

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx | cid, stance, motif, shifts | 18/18 | 17 | 17 | 1 / 0 | 1 | - |
| order_dxm | cid, stance, shifts, motif | 18/18 | 17 | 17 | 1 / 0 | 1 | - |
| order_mdx | cid, motif, stance, shifts | 18/18 | 17 | 17 | 1 / 0 | 1 | - |
| order_xdm | cid, shifts, stance, motif | 18/18 | 17 | 17 | 1 / 0 | 1 | - |
| order_xmd | cid, shifts, motif, stance | 18/18 | 17 | 17 | 1 / 0 | 1 | - |

## pressure_action

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx | cid, act, motif, target | 102/144 | 97 | 97 | 27 / 22 | 1 | - |
| order_dxm | cid, act, target, motif | 102/144 | 97 | 97 | 27 / 22 | 1 | - |
| order_mdx | cid, motif, act, target | 70/144 | 97 | 97 | 19 / 46 | 0.00545 | collapsed onto one answer |
| order_mxd | cid, motif, target, act | 70/144 | 97 | 97 | 15 / 42 | 0.00276 | - |
| order_xdm | cid, target, act, motif | 107/144 | 97 | 97 | 19 / 9 | 0.261 | - |
| order_xmd | cid, target, motif, act | 72/144 | 97 | 97 | 19 / 44 | 0.00891 | collapsed onto one answer |

## reaction_to_event

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx = order_dxm = order_xdm | cid, salience_delta, motif | 4/4 | 4 | 4 | 0 / 0 | 1 | - |

## chamber_deliberation

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx = order_dxm = order_xdm | cid, shifts, motif | 4/4 | 4 | 4 | 0 / 0 | 1 | - |

## coalition_decision

| candidate | order | score | control | 2nd control | better / worse | p (Holm) | failed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| order_dmx = order_dxm = order_xdm | party_id, action, motif | 10/10 | 10 | 10 | 0 / 0 | 1 | - |
| order_mdx = order_mxd = order_xmd | party_id, motif, action | 10/10 | 10 | 10 | 0 / 0 | 1 | - |
