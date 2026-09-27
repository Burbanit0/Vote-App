# Prefix-cache continuity fix — plan-llm-protocol-and-theory-program.md §3.B.7

## The problem, measured before touching anything

`build_system_prompt`/`build_user_prompt` for two DIFFERENT voter chunks of the SAME election (same
candidates), measured directly: the two chunks' own system prompt strings are byte-identical for the
first **84.4%** of their length, then diverge at the embedded, chunk-specific `cid_list`. Because the
system prompt precedes the user prompt in the token sequence vLLM actually sees, that late divergence
broke prefix-cache continuity for everything downstream too — including `build_user_prompt`'s own
`candidates` section, which is byte-identical across every chunk of the same election and would
otherwise be a clean cache hit.

## The fix

Moved the literal `cid_list` out of `build_system_prompt` (now a fixed reference to `expected_cids`
by name, identical across every chunk of the same election) into `build_user_prompt`'s own
`expected_cids` field (chunk-specific data belongs in the data message, not the instruction message).
`json.dumps(..., sort_keys=True)` still places `candidates` first alphabetically, unaffected by the
new key. No semantic change to the instruction itself — the model is still told exactly the same
thing, just via a stable reference instead of a literal, per-chunk list.

## Verified live — correctness unaffected

`check_vote_cast_prefix_cache_fix.py`, 6 consecutive vote_cast chunks (chunk_size=3) of one real
election (5 candidates, 18 voters): 3/18 fell back to the deterministic path — the same pre-existing,
already-documented blank+non-empty-ranking §3.6.1 quirk (unrelated to this change, chunk-size-
independent, first characterized earlier this session). Of the 15 non-fallback decisions, 14/15
matched `simple_rules.build_ranking` ground truth exactly — consistent with this session's own
established 93-100% correctness range for vote_cast, not a regression.

## Verified live — the actual cache-hit signal

vLLM's own periodic log line, read directly during the burst (not estimated):

| call in burst | Prefix cache hit rate |
|---|---|
| 1 | 65.2% |
| 2 | 68.0% |
| 3 | 68.0% |
| 4 | 69.9% |
| 5 | 71.2% |
| 6 | 71.2% |
| 7 | 72.2% |
| 8 | 73.0% |

Rising monotonically through the burst as more chunks of the same election land — exactly the
signature a warming, increasingly-effective prefix cache should produce. Higher than the ~57-58%
observed earlier this session under the old (pre-fix) prompt structure, though that earlier number
was a session-wide average mixed across decision types and elections rather than an isolated,
same-election burst, so this is a real, positive signal rather than a perfectly controlled A/B.

## Disposition

**Shipped.** `chamber_deliberation`'s own system prompt likely carries the same `cid_list`-in-
system-prompt pattern (not yet fixed in this pass — chamber's user prompt has no `candidates`-style
shared section the way vote_cast's does, so the win there would be narrower: only the system prompt
itself becoming a stable prefix across chunks, not also unlocking a shared user-prompt section).
Worth a follow-up pass with the same measurement discipline before claiming it, not assumed by
analogy.
