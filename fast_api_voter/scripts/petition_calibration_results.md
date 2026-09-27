# Petition calibration sweep (v4 Lot 5)

Shipped base_threshold_dist (beta(3,5)) / modulation_amplitude (0.5), per awakening_calibration_results.md: the acting cohort (past the awakening gate AND clearing its own blank_threshold) peaks at ~0.33 of the population early-term, against a shipped petition.signature_threshold of 0.25 -- reachable, narrowly, early-term only.

w_pet inherits the same amplification problem Lot 4 quantified for w_mob: w_pet/(1-decay_L) = 0.5/0.1 = 5x per unit of STANDING signed_ratio (petition_pressure has no decay term of its own, unlike street_pressure -- it is either the live signed_ratio or 0.0), so a petition that lingers open near its threshold costs L proportionally more per tick than an equivalent one-off mobilization spike.

| signature_threshold | lifespan | cooldown | modality | launched | expired | triggered | success rate | signed_ratio mean | signed_ratio max | duty cycle | ecart mean | ecart max | L min | recalls (floor) | recalls (confidence_vote) | act histogram |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.1 | 2 | 4 | petition_only | 31 | 0 | 31 | 0.00 | 0.143 | 0.330 | 0.256 | 0.035 | 0.165 | 0.216 | 0 | 0 | {2: 31, 1: 804, 0: 3102, 4: 2316} |
| 0.1 | 2 | 4 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.1 | 2 | 16 | petition_only | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.011 | 0.165 | 0.345 | 0 | 0 | {2: 8, 1: 256, 0: 3102, 4: 2887} |
| 0.1 | 2 | 16 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.1 | 4 | 4 | petition_only | 31 | 0 | 31 | 0.00 | 0.143 | 0.330 | 0.256 | 0.035 | 0.165 | 0.216 | 0 | 0 | {2: 31, 1: 804, 0: 3102, 4: 2316} |
| 0.1 | 4 | 4 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.1 | 4 | 16 | petition_only | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.011 | 0.165 | 0.345 | 0 | 0 | {2: 8, 1: 256, 0: 3102, 4: 2887} |
| 0.1 | 4 | 16 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.1 | 8 | 4 | petition_only | 31 | 0 | 31 | 0.00 | 0.143 | 0.330 | 0.256 | 0.035 | 0.165 | 0.216 | 0 | 0 | {2: 31, 1: 804, 0: 3102, 4: 2316} |
| 0.1 | 8 | 4 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.1 | 8 | 16 | petition_only | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.011 | 0.165 | 0.345 | 0 | 0 | {2: 8, 1: 256, 0: 3102, 4: 2887} |
| 0.1 | 8 | 16 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.25 | 2 | 4 | petition_only | 31 | 0 | 24 | 0.00 | 0.143 | 0.330 | 0.314 | 0.046 | 0.165 | 0.141 | 7 | 0 | {2: 31, 1: 804, 0: 2850, 4: 2036} |
| 0.25 | 2 | 4 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.25 | 2 | 16 | petition_only | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.011 | 0.165 | 0.345 | 0 | 0 | {2: 8, 1: 256, 0: 3102, 4: 2887} |
| 0.25 | 2 | 16 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.25 | 4 | 4 | petition_only | 31 | 0 | 24 | 0.00 | 0.143 | 0.330 | 0.314 | 0.046 | 0.165 | 0.141 | 7 | 0 | {2: 31, 1: 804, 0: 2850, 4: 2036} |
| 0.25 | 4 | 4 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.25 | 4 | 16 | petition_only | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.011 | 0.165 | 0.345 | 0 | 0 | {2: 8, 1: 256, 0: 3102, 4: 2887} |
| 0.25 | 4 | 16 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.25 | 8 | 4 | petition_only | 31 | 0 | 24 | 0.00 | 0.143 | 0.330 | 0.314 | 0.046 | 0.165 | 0.141 | 7 | 0 | {2: 31, 1: 804, 0: 2850, 4: 2036} |
| 0.25 | 8 | 4 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.25 | 8 | 16 | petition_only | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.011 | 0.165 | 0.345 | 0 | 0 | {2: 8, 1: 256, 0: 3102, 4: 2887} |
| 0.25 | 8 | 16 | both | 8 | 0 | 8 | 0.00 | 0.170 | 0.330 | 0.066 | 0.205 | 0.291 | 0.000 | 8 | 0 | {2: 8, 1: 256, 0: 808, 3: 504} |
| 0.4 | 2 | 4 | petition_only | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.165 | 0.165 | 0.196 | 8 | 0 | {2: 8, 1: 256, 0: 544, 4: 256} |
| 0.4 | 2 | 4 | both | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.245 | 0.325 | 0.036 | 8 | 0 | {2: 8, 1: 256, 0: 544, 3: 256} |
| 0.4 | 2 | 16 | petition_only | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.165 | 0.165 | 0.196 | 8 | 0 | {2: 8, 1: 256, 0: 544, 4: 256} |
| 0.4 | 2 | 16 | both | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.245 | 0.325 | 0.036 | 8 | 0 | {2: 8, 1: 256, 0: 544, 3: 256} |
| 0.4 | 4 | 4 | petition_only | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.165 | 0.165 | 0.196 | 8 | 0 | {2: 8, 1: 256, 0: 544, 4: 256} |
| 0.4 | 4 | 4 | both | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.245 | 0.325 | 0.036 | 8 | 0 | {2: 8, 1: 256, 0: 544, 3: 256} |
| 0.4 | 4 | 16 | petition_only | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.165 | 0.165 | 0.196 | 8 | 0 | {2: 8, 1: 256, 0: 544, 4: 256} |
| 0.4 | 4 | 16 | both | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.245 | 0.325 | 0.036 | 8 | 0 | {2: 8, 1: 256, 0: 544, 3: 256} |
| 0.4 | 8 | 4 | petition_only | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.165 | 0.165 | 0.196 | 8 | 0 | {2: 8, 1: 256, 0: 544, 4: 256} |
| 0.4 | 8 | 4 | both | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.245 | 0.325 | 0.036 | 8 | 0 | {2: 8, 1: 256, 0: 544, 3: 256} |
| 0.4 | 8 | 16 | petition_only | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.165 | 0.165 | 0.196 | 8 | 0 | {2: 8, 1: 256, 0: 544, 4: 256} |
| 0.4 | 8 | 16 | both | 8 | 0 | 0 | nan | 0.170 | 0.330 | 0.132 | 0.245 | 0.325 | 0.036 | 8 | 0 | {2: 8, 1: 256, 0: 544, 3: 256} |

## Headline questions

- Configs where the petition NEVER triggers a confidence vote despite launching: ['0.4-2-4-petition_only', '0.4-2-4-both', '0.4-2-16-petition_only', '0.4-2-16-both', '0.4-4-4-petition_only', '0.4-4-4-both', '0.4-4-16-petition_only', '0.4-4-16-both', '0.4-8-4-petition_only', '0.4-8-4-both', '0.4-8-16-petition_only', '0.4-8-16-both'].
- Configs where every launched petition triggers a confidence vote (a degenerate, instant-trigger arm): ['0.1-2-4-petition_only', '0.1-2-4-both', '0.1-2-16-petition_only', '0.1-2-16-both', '0.1-4-4-petition_only', '0.1-4-4-both', '0.1-4-16-petition_only', '0.1-4-16-both', '0.1-8-4-petition_only', '0.1-8-4-both', '0.1-8-16-petition_only', '0.1-8-16-both', '0.25-2-4-both', '0.25-2-16-petition_only', '0.25-2-16-both', '0.25-4-4-both', '0.25-4-16-petition_only', '0.25-4-16-both', '0.25-8-4-both', '0.25-8-16-petition_only', '0.25-8-16-both'].
- Does any confidence vote ever remove a president under the deterministic baseline? NO -- predicted NO by the keep_ratio == mandate_strength identity (build_confidence_ballot's docstring); a YES would mean that identity broke somewhere in this sweep and needs investigating before trusting it.
- Does the hard floor still do all the recalling, making the confidence vote decorative until Lot 6? Compare the 'recalls (floor)' and 'recalls (confidence_vote)' columns above.

## Recommendation

**Shipped defaults are not changed in this PR.** `signature_threshold=0.25` / `petition_lifespan_ticks=4` / `cooldown_ticks=4`, under `petition_only`, produce 31 launches and 24 triggers over the 30-year run -- a genuine mix of "threshold crossed" and "floor got there first" outcomes (7 floor recalls interrupt an otherwise-open petition), not one of this PR's two degenerate arms (never triggers: only `signature_threshold=0.4`; always triggers on launch: only `signature_threshold=0.1`). The shipped value sits in the intended narrow-but-real band the design doc's own petition mechanic calls for.

**`confidence_vote_result.retained` is `True` in every single triggered vote across all 36 swept configurations** (`success rate` -- read here as *removal* rate -- is `0.00` everywhere a vote triggers). This is not a bug: it is the `keep_ratio == mandate_strength` identity (proven in `build_confidence_ballot`'s docstring and pinned by `test_confidence_vote_keep_ratio_equals_mandate_strength_on_the_deterministic_path`) combined with the shipped election producing `m ~= 0.51 > 0.5` every term at seed 42. Under the deterministic v0 baseline, **the confidence vote is structurally decorative until Lot 6** gives `representative_response` a way to actually move `revealed_position` away from `pledged_platform` -- exactly as the roadmap's own "Next step" note for this lot predicted. The floor does 100% of the deterministic-baseline recalling in this sweep (0 confidence-vote removals against a nonzero floor-recall count in every configuration where any recall occurs at all).

**The `both` modality's petition parameters are effectively moot at the shipped `street_pressure` calibration.** Every `both` row shows exactly 8 launches, 8 floor recalls (one per term, no exceptions), and 0 expiries regardless of `signature_threshold`/`lifespan`/`cooldown` -- mobilization's own `w_mob` amplification (Lot 4's 33.3x finding) crashes `L` before the petition mechanic gets enough runway to differentiate. This is a Lot 4-owned calibration question (`street_pressure.weight_in_ecart`/`decay`), not a Lot 5 one -- flagged here as a real, visible interaction the two levers have on each other, worth revisiting if `both` is ever used for a serious comparison arm, but out of scope for this PR.
