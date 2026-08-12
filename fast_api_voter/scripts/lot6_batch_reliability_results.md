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
