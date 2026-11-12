# Positional bias within a chunk — "lost in the middle", read from existing journals

§5.D of `plan-llm-protocol-and-theory-program.md`: does a citizen's decision depend on WHERE they
sat in a batched chunk (Liu et al. 2023, "lost in the middle")? Chunk composition was never
journaled directly, but `chunk_voters` is a pure, deterministic function of (ordered citizen list,
chunk size) — reconstructable after the fact from `scripts/check_positional_bias_within_chunk.py`,
zero GPU cost, run against `scripts/flagship_runs/parity-8y-p100-chunked-v1` (8y/pop100, the
completed Phase 7 parity run).

This is distinct from the project's own earlier chunk-*reorder* test
(`check_pressure_action_chunk_reorder.py`), which asked "is the collapse a positional artifact" and
found no — reordering reproduced the same collapse. This asks a finer question reordering cannot
answer: across a real run, does the *distribution* of decisions vary by position, independent of
whether any single decision collapses.

## chamber_deliberation (chunk_size=5, n=495/position, 0.2% fallback throughout)

| pos | motif=702 (deliberative shift) | mean shifts |
|---|---|---|
| 0 | **0.0%** | 0.00 |
| 1 | 2.2% | 0.06 |
| 2 | 2.0% | 0.06 |
| 3 | 2.4% | 0.07 |
| 4 | 1.6% | 0.04 |

**Position 0 never once produced a deliberative shift across 495 decisions, while positions 1-4
did so at a consistent 1.6-2.4%.** This is not the already-documented Mode-A truncation (fallback
rate is flat and near-zero at every position) — it is a real behavioural difference in which motif
the model chooses, isolated to the first member enumerated in the chunk. Sample size is large
(495/position) and the effect is consistent across positions 1-4, so this reads as a genuine,
if small, primacy effect rather than sampling noise — but n=1 run, one seed, so it should be
treated as a real lead, not an established result, until replicated.

## vote_cast (chunk_size=3, n=96-102/position, ~58-60% fallback)

| pos | blank% (of non-fallback) | mean ranking length |
|---|---|---|
| 0 | 7.0% | 3.30 |
| 1 | 4.7% | 3.51 |
| 2 | 0.0% | 4.00 |

A monotone gradient in both columns — but the "of non-fallback" base is only ~38-43 decisions per
position (57-60% of this slice fell back to `_deterministic_vote_fallback`, well above the ~15% of
all decisions the parity run averaged overall), so this is a small, possibly noisy sample riding on
top of a locally elevated failure rate, not yet a trustworthy signal on its own.

## Next step

The Phase 7 scale-probe run (8y/pop500, in progress) will produce ~5x the vote_cast volume once
complete — re-run this script against it before treating the vote_cast gradient as anything more
than suggestive. The chamber finding is large-sample already and worth carrying into
`plan-llm-protocol-and-theory-program.md` §5.D as a concrete lead, not just a placeholder section.
