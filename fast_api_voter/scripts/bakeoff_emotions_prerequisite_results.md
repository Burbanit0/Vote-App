# ADR-012's prerequisite: the emotion fields in the pressure prompt

Session `qwen3-8b-awq-emotions-prerequisite` on the emotions bank, read by `bakeoff_emotions.read_verdict` as pre-registered in `plan-polity-build-order.md` ("ADR-012's prerequisite, pre-registered before its session").

## Verdict

**Accepted.** An LLM run may turn emotions on; Stage 4's step 5 proceeds.

| criterion | `pressure_act` | `pressure_act_emotions` | holds |
|---|---:|---:|---|
| 1. valid answers | 24/24 | 24/24 | yes |
| 2. citizens answered correctly (at most 1 fewer) | 15/24 | 18/24 | yes |

Paired McNemar over 24 citizens: right only without the fields 1, right only with them 4, exact p = 0.375.

## Reported, not accepted on: anger and mobilization

| anger | answered | MOBILIZE | share |
|---:|---:|---:|---:|
| 0 | 4 | 0 | 0% |
| 0.25 | 4 | 0 | 0% |
| 0.5 | 4 | 1 | 25% |
| 0.75 | 4 | 4 | 100% |
| 1 | 4 | 4 | 100% |
