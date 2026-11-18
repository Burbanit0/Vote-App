# ADR-041: the JSON spacing of an answer is part of the prompt, sent as a grammar

**Status**: Proposed (2026-11-17), built. The owner approved the plan it comes from; merging the PR that carries it is the acceptance.
**Date**: 2026-11-17
**Context**: The vLLM server is started with `disable_any_whitespace` (the 2026-09-06 whitespace-loop fix). Up to vLLM 0.31 that flag left xgrammar's default spacing, `", "` and `": "`. Since vLLM PR #58067 (0.32) the same flag also passes `separators=(",", ":")`, so every answer is compact JSON, and Qwen3-8B-AWQ answers differently on it: `representative_response` goes from 48 valid answers of 50 to 0 of 50 on 0.32, 0.33 and 0.34 (EXP-025, EXP-026, the 0.34.0 probe of 2026-11-17). Upstream has no setting for the separators. The pin stayed on v0.31.0 for a month for this one reason. ADR-030 already says the order of a schema's fields is part of the prompt and sends it from the client; the spacing was the same kind of thing, left to a server default.

## Decision

- **The client sends the grammar, not the schema.** `VllmJsonClient.from_config` sets `structured_output = "grammar"`: each request carries `structured_outputs: {"grammar": <EBNF>}` in place of `response_format`. The EBNF is what xgrammar builds from the wire schema (refs inlined, fields in `WIRE_ORDER`) with `any_whitespace=False` and separators `", "` and `": "`: the grammar vLLM 0.31 built for itself from the same schema. vLLM compiles a grammar request as given, with the same xgrammar compiler, and the `separators` line does not touch it (`backend_xgrammar.py`, read in the v0.31.0 and v0.34.0 images).
- **The grammars are a generated, committed artifact.** `api/domain/polity/wire_grammars.json` maps the sha256 of a wire schema to its EBNF. `scripts/gen_wire_grammars.py` writes it by running xgrammar inside the pinned server image on the CPU; `--check` compares. xgrammar is not a backend dependency (its wheel pulls torch, transformers and triton). The file is never edited by hand.
- **A schema with no grammar is an error.** `llm_client.wire_grammar` raises `LookupError` naming the generator; it never falls back to the server's spacing. A test fails when the artifact's keys are not exactly the schemas the client can send (every schema of `llm_schemas`, the six `vote_cast` ranking limits, the run's warm-up, the bake-off's renamed-`motif` schemas, each under production's order and every bake-off arm's). That list is the generator's own: a schema built anywhere else would have no grammar and would stop its run at its first call. `from_config` reads the artifact, so a missing file stops a run at its start.
- **The schema mode stays**, as the class default of a client built directly and as `run_bakeoff.py --structured-output schema`: it is the control of any later measurement, and what the Ollama client sends.
- **No config key.** A key in `polity_config.yaml` would change `config_hash` and stop a checkpoint from before it resuming, for a value no run should vary.

## Measured

On the pinned v0.31.0, the grammar and the schema give the same bytes (EXP-032): the two-minute probe (64 calls of 64, answers and reasoning), the full bank (191 rows of 191, 225 calls of 225), a strict one-year flagship run (186 calls of 186, 421 events of 421), a strict one-year scenario run (121 calls of 121, 245 events of 245) and every production schema sent once (24 of 24). On stock v0.34.0 the grammar gives 48 valid answers of 50 on the probe where the schema gives 0, and matches the separators-restored 0.34.0 image on all 59 requests.

## Consequences

- Request hashes, replay logs and the golden are unchanged: the grammar replaces the schema on the wire, after the hash (the property `WIRE_ORDER` has). The prompt hash changes once, because `llm_client.py` changed and `wire_grammars.json` joins `PROMPT_SOURCE_FILES`.
- A vLLM bump no longer waits on the separators line. `scripts/vllm_bump_protocol.sh` and `check_vllm_batching_determinism.py` now send and expect the grammar (the protocol's separators-restored arm is removed: it cannot differ from stock under a grammar request). The bump still needs that protocol: 0.34.0 differs from 0.31.0 on 14 bank rows of 191 with the grammar (EXP-032), which is the server's own drift to judge, not the spacing.
- A schema, `WIRE_ORDER` or a bake-off arm that changes needs `python scripts/gen_wire_grammars.py` (Docker and the pinned image), like the parity fixture needs its generator. CI cannot regenerate the artifact (no image there); it checks the key set only.
- The grammar's text is pinned by this repository, not by the server image: an xgrammar that built another grammar from the same schema would no longer change behaviour silently. xgrammar 0.2.7 (the 0.31.0 image) and 0.2.8 (the 0.34.0 image) print the same 84 grammars byte for byte.
- `disable_any_whitespace` stays in the server flags: it does nothing to a grammar request and still protects a schema request. Two live tests (`test_polity_vllm_live.py`) still post raw `response_format` bodies on purpose (a raw `$ref` schema, thinking under a schema): on vLLM 0.32 and later they exercise the compact path, which production no longer uses.
- Not done here: the artifact is not in the hooks that guard generated files (`.claude/hooks/guardlib.py`), and CI checks its keys, not its values; `gen_wire_grammars.py --check` (Docker and the image) is the value check, run by the bump protocol's preflight.
- If upstream adds a separators setting (the request drafted in EXP-026 was not filed), the artifact could be dropped for a server flag. Nothing here depends on that.

## Not chosen

- **A patched server** (the one line restored in a derived image or at container start): same bytes on the probe, but a standing fork of one upstream line, to re-anchor when it moves, and a stock image tag in a run's provenance over patched code.
- **Another field order chosen on compact JSON** (ADR-030's sweep on each version): changes simulated behaviour and ties the table to the vLLM version; production's order gives 0 of 50.
- **`disable_any_whitespace: false`**: brings back the whitespace loop.
- **The `guidance` backend with `x-guidance` separators in the schema**: a public setting too, but another masking engine, so identity with 0.31.0 would have to be shown again on every schema.
