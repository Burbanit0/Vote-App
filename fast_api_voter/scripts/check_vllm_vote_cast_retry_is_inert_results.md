# vLLM: the `vote_cast` temperature-varied retry is inert — measured

`provider=vllm`, `model=qwen3:8b`, shipped `_VOTE_CAST_RETRY_TEMPERATURE=0.3`, seed=42, 5 nominees, chunk size 1.

## Base rate — first attempt, production settings (temperature=0, pinned seed)

- cid 6: **FAIL** — transport/response: generation did not finish cleanly: finish_reason='length'
- cid 8: **FAIL** — Value error, blank=1 requires an empty ranking (§3.6.1 hard rule) [type=value_error, input_value={'blank': 1, 'cid': 8, 'm...nking': [1, 2, 3, 5, 4]}, input_type=dict]
- cid 9: **FAIL** — Value error, blank=1 requires an empty ranking (§3.6.1 hard rule) [type=value_error, input_value={'blank': 1, 'cid': 9, 'm...nking': [1, 2, 3, 4, 5]}, input_type=dict]
- cid 12: **FAIL** — transport/response: generation did not finish cleanly: finish_reason='length'
- cid 13: **FAIL** — Value error, blank=1 requires an empty ranking (§3.6.1 hard rule) [type=value_error, input_value={'blank': 1, 'cid': 13, '...'ranking': [2, 3, 4, 1]}, input_type=dict]
- cid 16: **FAIL** — Value error, blank=1 requires an empty ranking (§3.6.1 hard rule) [type=value_error, input_value={'blank': 1, 'cid': 16, '...5, 'ranking': [3, 2, 4]}, input_type=dict]
- cid 17: **FAIL** — Value error, blank=1 requires an empty ranking (§3.6.1 hard rule) [type=value_error, input_value={'blank': 1, 'cid': 17, '...nking': [1, 5, 2, 3, 4]}, input_type=dict]
- cid 19: **FAIL** — Value error, blank=1 requires an empty ranking (§3.6.1 hard rule) [type=value_error, input_value={'blank': 1, 'cid': 19, '...nking': [4, 2, 3, 1, 5]}, input_type=dict]
- cid 23: **FAIL** — Value error, blank=1 requires an empty ranking (§3.6.1 hard rule) [type=value_error, input_value={'blank': 1, 'cid': 23, '...'ranking': [2, 3, 4, 1]}, input_type=dict]

**9 of 25 voters failed on the first attempt (36.0%)**

## The 2x2, on the voters that actually failed

Each cell: 3 attempts. `recovered` means at least one attempt decoded cleanly;
`identical` means every attempt returned the same failing answer.

| cid | temp 0.3, pinned seed (**shipped retry**) | temp 0.3, varied seed | temp 1.0, pinned seed | temp 1.0, varied seed |
|---|---|---|---|---|
| 6 | **recovered 1/3** | **recovered 2/3** | identical 3/3 | **recovered 2/3** |
| 8 | **recovered 3/3** | **recovered 3/3** | **recovered 3/3** | **recovered 1/3** |
| 9 | **recovered 1/3** | **recovered 1/3** | identical 3/3 | **recovered 1/3** |
| 12 | **recovered 3/3** | **recovered 3/3** | **recovered 3/3** | identical 3/3 |
| 13 | **recovered 3/3** | **recovered 2/3** | **recovered 3/3** | **recovered 3/3** |
| 16 | **recovered 3/3** | **recovered 1/3** | identical 3/3 | **recovered 2/3** |
| 17 | **recovered 3/3** | **recovered 2/3** | **recovered 3/3** | **recovered 3/3** |
| 19 | identical 3/3 | **recovered 2/3** | **recovered 3/3** | **recovered 2/3** |
| 23 | **recovered 3/3** | **recovered 3/3** | **recovered 3/3** | **recovered 2/3** |

