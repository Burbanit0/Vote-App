# Stage 4 on the LLM path: the pilot

`scripts/stage4_llm_pilot.py`, run on 2026-09-16 against the pinned vLLM 0.28.0 serving
`Qwen/Qwen3-8B-AWQ`, with the shipped defaults (the `vote_cast` grammar and the 2048-token thinking
budget adopted in #528). It measures what a Stage 4 calibration run costs on the LLM path, and
checks the one shortcut the design rests on, before anything is pre-registered.

The run is in the calibrations' own shape: population 100, 30 chamber seats, seed 1, 8 years, the
flagship's full-mechanism config, 12 workers (`llm.reproducibility: relaxed`). Legislation is on at
bill interval 4 and step 0.05, with `policy_retrospection` 0.

## Cost

| measure | value |
|---|---|
| wall clock | **18.0 min** (1,077.8 s) for 33 ticks |
| model calls | 1,158: 945 decisions, 211 budget probes, 2 warm-ups |
| CPU and memory | 5.2 s CPU, 102 MB peak: the model server is the whole cost |

One run is one data point. It had no recall, so no snap election: a seed with recalls holds more
elections and takes longer. A 16-year run, as S4.2 needs, is not measured here.

## What the run looked like

- **Presidency.** Citizen 82 elected at tick 0 and re-elected at 16; citizen 37 elected at 32, when
  82 had reached the term limit. **No recall.** This is the regime the deterministic twin never
  produced (OBS-015): a full term, and an incumbent standing again.
- **Pressure.** Of 639 consulted citizens' acts: 624 nothing, 14 petition signatures, 1
  mobilization. That matches the p500 LLM runs, not the twin.
- **Legislation.** 7 bills proposed at interval 4, none enacted. One run at the slowest interval:
  no reading of L2 should be taken from it.

## Fallbacks: decisions the model did not make

A decision whose every attempt fails validation falls back to the deterministic rule.

| decision | fell back | of |
|---|---:|---:|
| **representative_response** | **16 (48.5%)** | 33 |
| chamber_deliberation | 40 (4.0%) | 990 |
| candidacy, nomination, positioning, vote, pressure, coalition, reaction | 0 | 1,120 |

**Nearly half of the president's responses to pressure are the fallback's, not the model's.** The
journal shows the cause: the model answers `stance` 3 (silence) with motif 303, the validator
requires 308 for silence, every retry repeats it, and the engine substitutes silence. On the LLM
path, facts about incumbents and their terms rest partly on that substitute.

## The record-and-replay shortcut holds on real model output

`stage4_llm_pilot.py replay` replays the call log with legislation at interval 1 and step 0.20,
where the run recorded interval 4 and step 0.05:

- **1,156 recorded calls served, none left unasked** (the 2 warm-ups are never replayed), in 3 s of
  CPU. The replay client raises on any request it never recorded, so none was issued.
- **The legislative history genuinely differed:** 25 bills proposed in the replay against 7.

At `policy_retrospection` 0, a legislation setting changes nothing the model is asked. One
recorded LLM run per seed can therefore serve all nine of S4.2's (interval, step) settings for
L1–L3, at the cost of the recording alone.
