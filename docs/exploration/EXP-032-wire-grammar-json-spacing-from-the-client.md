# EXP-032 — Sending the grammar instead of the schema: the JSON spacing decided by the client, not by vLLM

- **Date**: 2026-11-18 UTC (the evening of 2026-11-17 local; 00:16Z to 02:11Z) · **Status**: adopted on the pinned v0.31.0 (ADR-041, where it changes no byte); the bump to a newer vLLM is a separate step that this unblocks and does not decide · **Real cost**: about 1 h 40 of the local GPU in five chains, no rented compute, no image pull (v0.31.0 and v0.34.0 were local) · **Token cost**: not measured
- **Verdict in one sentence**: the vLLM client can send each schema as the EBNF grammar xgrammar builds from it, spacing included; on v0.31.0 that gives the same bytes as today on everything measured (the probe, the full bank, two strict one-year runs, every schema once), and on stock v0.34.0 it turns the probe's 0 valid answers of 50 back into 48, with no patched server.

## Starting hypothesis
vLLM 0.32, 0.33 and 0.34 all fail the two-minute probe for one line (EXP-025, EXP-026): since vLLM PR #58067, `disable_any_whitespace` also passes `separators=(",", ":")` to xgrammar, the answers are compact JSON, and Qwen3-8B-AWQ closes `"shifts":[]` every time. EXP-026 left five options; none avoided both a patched server and a behaviour change. Reading `vllm/v1/structured_output/backend_xgrammar.py` in the two local images gave a sixth: the `separators` line only applies to a JSON-schema request. A grammar request (`structured_outputs: {"grammar": ...}`, a public per-request field in both versions) is compiled as given by the same compiler, and xgrammar prints the grammar it builds from a schema (`str(Grammar.from_json_schema(schema, any_whitespace=False))`). What I expected: the same language through the same masking engine gives the same tokens, so the grammar would be byte-identical to the schema on 0.31.0, and to the separators-restored image on 0.34.0. Not known before running: whether a grammar request costs compile time, and whether it behaves with thinking and EAGLE-3.

## Protocol
Code: branch `feat/polity-wire-grammar` from origin/polity at `444d5821`. `VllmJsonClient.structured_output` chooses `schema` (today's `response_format`) or `grammar`; `scripts/gen_wire_grammars.py` runs xgrammar inside the pinned image on the CPU and writes `api/domain/polity/wire_grammars.json` (84 grammars: every schema the client can send, under production's field order and every bake-off arm's). The runs below were made on that code at `444d5821`; the branch was then moved to polity's tip, and the review's fixes (what a session records, the generator's list, the bump protocol's scripts) came after the runs and change no request. Servers: `docker-compose.llm.yml` as shipped (Qwen3-8B-AWQ, `disable_any_whitespace`, EAGLE-3), and the same file with the tag swapped to v0.34.0. One server at a time, temperature 0.

Gate written before the first run: on the `response_sweep` probe, the grammar on 0.31.0 must match the schema on 0.31.0 byte for byte (G1), and the grammar on stock 0.34.0 must give at least 45 valid answers of 50 and match the 0.31.0 control byte for byte (G2).

1. **Without a GPU.** The generator on the v0.31.0 image (xgrammar 0.2.7) and, with `--check --image`, on the v0.34.0 image (xgrammar 0.2.8).
2. **The probe**, four sessions: `run_bakeoff.py --families response_sweep --structured-output schema|grammar` on 0.31.0, then on 0.34.0.
3. **The full bank** (174 cases, 191 scored rows, 225 calls), three sessions: schema and grammar on 0.31.0, grammar on 0.34.0.
4. **Two strict one-year runs** (one worker, seed 1, population 100) in each mode on 0.31.0: the flagship profile (the crowd's batch decisions), then the scenario profile (the agents' turns, which no bank family covers).
5. **Every production schema once**, in each mode, on each server: 24 schemas (the two warm-ups among them are the same schema), one short invented prompt, to send the grammars the runs above did not reach (amendment ballot, leader coalition turn).

## What it found

**The grammar is the one 0.31.0 builds for itself.** For all 84 schemas, the EBNF printed with explicit `", "` and `": "` separators equals the one printed by the call 0.31.0's backend makes (`any_whitespace=False`, no separators). xgrammar 0.2.8 prints the same 84 texts byte for byte and parses them.

**On v0.31.0 the two modes give the same bytes, everywhere measured.**

| measurement on v0.31.0 | calls with the same answer text | same reasoning | rows or events equal | time, schema / grammar |
|---|---:|---:|---:|---:|
| probe (`response_sweep` + logprob gate) | 64/64 | 64/64 | 56/56 rows | 86 s / 87 s |
| full bank | 225/225 | 225/225 | 191/191 rows | 809 s / 819 s |
| strict 1-year run, flagship profile | 186/186 | 186/186 | 421/421 events (run id aside) | 388 s / 371 s |
| strict 1-year run, scenario profile | 121/121 | 121/121 | 245/245 events (run id aside) | 559 s / 549 s |
| every production schema once | 24/24 | (no thinking) | | |

Request hashes are equal call for call in both runs, so neither run left the other's path. No fallback in any run, no error line in the server log. The one-year runs made `candidacy_considered`, `party_nomination_choice`, `campaign_positioning`, `vote_cast`, `chamber_deliberation`, `representative_response`, `pressure_action`, `nominee_turn`, `president_turn` and `forum_post` calls, with thinking on for those that use it and the thinking budget's probes.

**On stock v0.34.0 the grammar gives back the answers.**

| probe arm | server | valid | same answer text as the 0.31.0 control |
|---|---|---:|---:|
| schema (control) | v0.31.0 | 48/50 | reference |
| grammar (G1) | v0.31.0 | 48/50 | 64/64 calls |
| grammar (G2) | stock v0.34.0 | **48/50** | 63/64 calls |
| schema | stock v0.34.0 | 0/50 | 6/64 calls |

- **G1 passes as written.**
- **G2 passes on validity and fails the byte-identity clause on one call**: a `motif` code, 301 where 0.31.0 writes 302, on a case invalid on both servers (cid 6000, `stance` 2 with empty `shifts`). Decoded answers and validity are equal on all 56 rows.
- **That difference is 0.34.0's, not the grammar's.** The separators-restored 0.34.0 image, run that morning on the same 59 requests, writes the same 301, and the grammar session matches it on 59 of 59 requests, answer text and reasoning both. (The patched 0.33.0 of EXP-026 wrote 302.) The byte-identity clause of G2 asked two things at once, whether the route is neutral and whether 0.34.0 drifts from 0.31.0; only the first is this experiment's question, and the comparison with the patched image answers it. The clause is reported as failed, not reinterpreted.
- On 0.34.0 the reasoning text differs from 0.31.0 on 5 of the 13 thinking calls, with the same final answers (EXP-026 saw the same on 0.33.0).
- Every production schema: the grammar is accepted for 24 of 24 on 0.34.0, and its answer text equals 0.31.0's on 24 of 24. In schema mode 0.34.0 answers compact on 24 of 24, and 3 of them run to the 300-token limit.
- No compile cost visible: 88 s for the probe on 0.34.0 with the grammar, 78 s with the schema (whose answers stop after about 31 tokens).

**0.34.0 itself is close to 0.31.0 on the bank, not identical.** With the grammar, 177 rows of 191 have 0.31.0's text:

| family | rows | same text | what moved |
|---|---:|---:|---|
| `positioning_poles` | 11 | 1 | shifts and motifs on 10 rows, all valid |
| `chamber_poles` | 10 | 9 | one thinking call ran to the token limit: invalid |
| `reaction_scandal` | 11 | 10 | one batch's `salience_delta` 0.15 to 0.10 |
| `coalition_diagonal` | 28 | 27 | text differs, decoded answers equal |
| `vote_first_choice` | 16 | 15 | text differs, decoded answers equal |
| `response_sweep`, `pressure_act`, `candidacy_p500`, `nomination_permutation`, `logprob_gate` | 125 | 125 | nothing |

`positioning_poles` is the family ADR-030 set aside (9 answers of 10 changed on identical bytes across a restart). The 0.34.0 bank took 919 s against 809 s; how much of that is the one runaway chamber call was not looked at. No patched-0.34.0 bank exists, so on the bank the grammar and the server version are not separated: only the probe separates them.

## What was not run
- The bump protocol on 0.34.0: determinism within a run and across a restart, the three restarts, the live suite, the two-year A/B runs, the scorecard, `check_schema_order.py`. Nothing here says 0.34.0 is adoptable; it says the spacing no longer forbids it.
- The amendment ballot and the leader's coalition turn in a real run: no such turn came up in one year. Their grammars were sent once each on an invented prompt (step 5), which shows the server takes them and answers as with the schema, not how they behave in situ.
- A relaxed (12-worker) run, the exploration profile, a population above 100, more than one seed, more than one year.
- The other compose profiles (4B, Gemma, Granite, NVFP4, H100) and a rented pod: the artifact is the same for every server, but none was started.
- Ollama: its client is untouched.

## What it cost
About 1 h 40 of the local GPU: the probe chain 11 minutes, the bank chain 48, the two run chains 15 and 21, the every-schema chain 6, eight server starts of about 2 min 30 among them. No pull, no derived image. In the repository: about 60 lines in `llm_client.py` and `run_bakeoff.py`, a 120-line generator, a 253 KB generated artifact, four tests. Standing cost: `python scripts/gen_wire_grammars.py` (Docker and the pinned image, under a minute) whenever a schema, `WIRE_ORDER` or a bake-off arm changes; a test fails until it is run, and CI cannot run it.

## Verdict and why
**Adopted on v0.31.0** (ADR-041): `VllmJsonClient.from_config` sends the grammar. It changes nothing measurable on the current pin and removes the reason the pin could not move. **The bump stays to be done**, with the protocol, as its own reviewed step: 14 bank rows of 191 move on 0.34.0 for reasons that are the server's, and one chamber call that no longer finishes is the kind of thing the protocol exists to weigh.

Left as they are: EXP-025, EXP-026 and ADR-030 are dated records. Their option lists did not have this route.

## What I take from it (transferable)
- **Read the code path of the default before choosing among workarounds.** Five options were on the table for a month; the sixth was two branches below the offending line, in a file already open in a patch script.
- **A server default is an input you do not control.** The field order had already moved from the server's sort to the client's table; the spacing took the same road. What a measured behaviour depends on belongs in the request.
- **A generated artifact can stand in for a dependency.** xgrammar's wheel pulls torch; the grammar text does not. The library that defines the reference behaviour was already on disk, inside the server image.
- **A gate clause should ask one question.** "Byte-identical to the 0.31.0 control" on a 0.34.0 server asked about the route and about the version together, and failed on the version. The comparison that isolates the route (against the patched image of the same version) should have been the clause.
- **A check covers what it sends.** The first one-year run was launched to cover the agents' turns and made none: the flagship profile has no agents. Reading which decision types a run actually produced caught it; the scenario run and the every-schema pass closed most of the gap, and the rest is listed above.

## Where the evidence is
Outside git, in `~/Documents/Dev/polity-runs/vllm-grammar/`: `gate.sh`, `bank.sh`, `sim.sh`, `sim_scenario.sh`, `all_schemas.sh` and their logs (`gate.log`, `bank.log`, `sim.log`, `sim-scenario.log`, `all-schemas.log`); `bank/` (`ctl-schema`, `ctl-grammar`, `new-grammar`, `new-schema`, `bank-ctl-schema`, `bank-ctl-grammar`, `bank-new-grammar`, each with `results.jsonl`, `llm_calls.jsonl`, `session.json`); `sim/` (`schema`, `grammar`, `schema-scenario`, `grammar-scenario`); `all-schemas-v0.31.0.json`, `all-schemas-v0.34.0.json`; `compare.py`, `sim_ab.py`, `all_schemas.py`. The separators-restored 0.34.0 session is `~/Documents/Dev/polity-runs/vllm-v0.34.0/bank/probe-arm-sep`. The vLLM source was read inside the two local images.
