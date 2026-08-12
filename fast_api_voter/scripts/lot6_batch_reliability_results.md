# Lot 6/7 small-batch reliability spike -- model=qwen3:8b, base_url=http://localhost:11434/v1

sizes=[1, 3, 5, 10], repeats=2

| schema | batch_size | rep | ok | finish_reason | elapsed(s) | detail |
|---|---|---|---|---|---|---|
| representative_response | 1 | 1 | True | stop | 11.5 | got=[100] |
| representative_response | 1 | 2 | True | stop | 11.6 | got=[100] |
| representative_response | 3 | 1 | True | stop | 33.6 | got=[100, 101, 102] |
| representative_response | 3 | 2 | True | stop | 30.9 | got=[100, 101, 102] |
| representative_response | 5 | 1 | True | stop | 56.2 | got=[100, 101, 102, 103, 104] |
| representative_response | 5 | 2 | True | stop | 52.6 | got=[100, 101, 102, 103, 104] |
| representative_response | 10 | 1 | True | stop | 107.4 | got=[100, 101, 102, 103, 104, 105, 106, 107, 108, 109] |
| representative_response | 10 | 2 | True | stop | 92.9 | got=[100, 101, 102, 103, 104, 105, 106, 107, 108, 109] |
| pressure_action | 1 | 1 | True | stop | 5.5 | got=[100] |
| pressure_action | 1 | 2 | True | stop | 5.4 | got=[100] |
| pressure_action | 3 | 1 | True | stop | 15.9 | got=[100, 101, 102] |
| pressure_action | 3 | 2 | True | stop | 13.7 | got=[100, 101, 102] |
| pressure_action | 5 | 1 | True | stop | 25.1 | got=[100, 101, 102, 103, 104] |
| pressure_action | 5 | 2 | True | stop | 18.3 | got=[100, 101, 102, 103, 104] |
| pressure_action | 10 | 1 | True | stop | 41.6 | got=[100, 101, 102, 103, 104, 105, 106, 107, 108, 109] |
| pressure_action | 10 | 2 | True | stop | 36.2 | got=[100, 101, 102, 103, 104, 105, 106, 107, 108, 109] |

## Summary

failures: 0/16

**Overall: PASS**

## Caveat -- this is not a reliability guarantee

Immediately before this spike, `POLITY_LLM_LIVE=1 pytest api/tests/test_polity_llm_live.py` (run
against this same freshly-pulled `qwen3:8b`, same Docker container) hit a REAL batch misalignment
in already-shipped production code: `decide_campaign_positioning` (v2 increment 4, also
`think=False` + `compute_max_tokens`, the same call shape this spike mirrors) silently dropped one
citizen from a 5-nominee batch (`expected cids [1, 24, 51, 53, 88], got [1, 24, 51, 88]` --
`LlmResponseError`, correctly caught by the existing batch-alignment check, not a silent
corruption). 2 of 16 tests failed in that run (`test_sequential_calls_each_produce_a_valid_response`,
`test_a_short_live_run_produces_a_valid_journal`), 14 passed.

This spike's own 16/16 clean pass, at the exact same batch sizes and same `think=False` shape, is
therefore evidence that representative_response/pressure_action's SCHEMAS are not obviously harder
for the model than an already-shipped, already-relied-upon schema (positioning) that just failed
under the same conditions -- not evidence that misalignment cannot happen to these new decision
types too. The existing "reject the whole batch, never partially correct" contract
(`LlmResponseError` on any cid mismatch, §3.6's "rejeu intégral, jamais de correction partielle
silencieuse") is what makes this survivable in production either way; Lot 6/7 should assume the
same non-zero misalignment rate this project has already measured for a structurally identical
call shape, not treat this spike's clean run as proof it will always hold.

## Lot 7 confirmatory pass -- real pressure_action schema

Real llm_schemas.PressureBatch / llm_behavior_engine.build_pressure_*_prompt, not the toy schema above (which had the wrong motif set -- 303 is a ResponseMotif -- and never carried a per-citizen `available` acts list). Sweeps the batch sizes chunk_voters actually produces (20-25), not just the pre-flight 1-10 range.

| size | modality | rep | ok | elapsed(s) | out_of_available_rate | act x motif pairs | detail |
|---|---|---|---|---|---|---|---|
| 1 | electoral_only | 1 | True | 5.5 | 0.0 | [(4, 305)] |  |
| 1 | electoral_only | 2 | True | 5.4 | 0.0 | [(4, 305)] |  |
| 5 | electoral_only | 1 | True | 26.8 | 0.0 | [(4, 305)] |  |
| 5 | electoral_only | 2 | True | 22.7 | 0.0 | [(4, 305)] |  |
| 20 | electoral_only | 1 | True | 90.9 | 0.0 | [(4, 305)] |  |
| 20 | electoral_only | 2 | True | 74.8 | 0.0 | [(4, 305)] |  |
| 25 | electoral_only | 1 | True | 116.2 | 0.0 | [(4, 305)] |  |
| 25 | electoral_only | 2 | True | 95.8 | 0.0 | [(4, 305)] |  |
| 1 | full_menu | 1 | True | 6.0 | 0.0 | [(1, 301)] |  |
| 1 | full_menu | 2 | True | 5.6 | 0.0 | [(1, 301)] |  |
| 5 | full_menu | 1 | True | 27.7 | 0.0 | [(0, 304), (1, 301), (3, 301), (4, 305)] |  |
| 5 | full_menu | 2 | True | 22.7 | 0.0 | [(0, 304), (1, 301), (3, 301), (4, 305)] |  |
| 20 | full_menu | 1 | True | 93.1 | 0.0 | [(0, 304), (1, 301), (3, 301)] |  |
| 20 | full_menu | 2 | True | 75.2 | 0.0 | [(0, 304), (1, 301), (3, 301)] |  |
| 25 | full_menu | 1 | True | 117.0 | 0.0 | [(0, 304), (1, 301), (3, 301)] |  |
| 25 | full_menu | 2 | True | 96.0 | 0.0 | [(0, 304), (1, 301), (3, 301)] |  |

### Summary

failures: 0/16

**Overall: PASS**
