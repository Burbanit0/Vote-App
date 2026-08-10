# Awakening/mobilization calibration sweep (v4 Lot 4)

Steady-state amplification factor L(t) drop per unit sustained mobilization rate: w_mob/(1-decay_street) / (1-decay_L) = 0.5/0.15 / 0.1 = 33.3x (shipped legitimacy.decay=0.9, street_pressure.decay=0.85, street_pressure.weight_in_ecart=0.5) -- this is why deterministic_pressure_action gates MOBILIZE on blank_threshold instead of mobilizing unconditionally.

mandate_deviation is provably 0.0 through Lot 5 (no representative_response yet), so f(context) = 1 + amp*proximity this lot -- consultation rate is maximal right after an election and falls as the next one approaches (the 'early_term' vs 'late_term' columns below isolate this).

| base_threshold_dist | amp | modality | consult mean | consult early-term | consult late-term | mobilize mean | mobilize max | street_pressure max | ecart max | L min | recalls | dt=10 calls/run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| beta(3,5) | 0.0 | electoral_only | 0.670 | 0.670 | 0.670 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 8107 |
| beta(3,5) | 0.0 | mobilization_only | 0.089 | 0.335 | 0.000 | 0.044 | 0.330 | 0.61 | 0.305 | 0.056 | 8 | 1072 |
| beta(3,5) | 0.5 | electoral_only | 0.517 | 0.645 | 0.390 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 6253 |
| beta(3,5) | 0.5 | mobilization_only | 0.088 | 0.333 | 0.000 | 0.043 | 0.330 | 0.60 | 0.300 | 0.061 | 8 | 1064 |
| beta(6,4) | 0.0 | electoral_only | 0.200 | 0.200 | 0.200 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 2420 |
| beta(6,4) | 0.0 | mobilization_only | 0.053 | 0.200 | 0.000 | 0.029 | 0.110 | 0.35 | 0.175 | 0.085 | 8 | 640 |
| beta(6,4) | 0.5 | electoral_only | 0.062 | 0.130 | 0.013 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 755 |
| beta(6,4) | 0.5 | mobilization_only | 0.045 | 0.130 | 0.000 | 0.017 | 0.110 | 0.15 | 0.077 | 0.177 | 8 | 544 |
| beta(7,3) | 0.0 | electoral_only | 0.040 | 0.040 | 0.040 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 484 |
| beta(7,3) | 0.0 | mobilization_only | 0.031 | 0.040 | 0.000 | 0.015 | 0.020 | 0.11 | 0.057 | 0.190 | 7 | 372 |
| beta(7,3) | 0.5 | electoral_only | 0.014 | 0.033 | 0.003 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 172 |
| beta(7,3) | 0.5 | mobilization_only | 0.014 | 0.033 | 0.003 | 0.009 | 0.020 | 0.06 | 0.030 | 0.314 | 0 | 172 |
| beta(8,3) | 0.0 | electoral_only | 0.030 | 0.030 | 0.030 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 363 |
| beta(8,3) | 0.0 | mobilization_only | 0.030 | 0.030 | 0.030 | 0.010 | 0.010 | 0.06 | 0.031 | 0.301 | 0 | 363 |
| beta(8,3) | 0.5 | electoral_only | 0.007 | 0.015 | 0.000 | 0.000 | 0.000 | 0.00 | 0.000 | 0.510 | 0 | 80 |
| beta(8,3) | 0.5 | mobilization_only | 0.007 | 0.015 | 0.000 | 0.005 | 0.010 | 0.05 | 0.024 | 0.389 | 0 | 80 |
