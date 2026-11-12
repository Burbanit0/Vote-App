# vote_cast's ballot rules in the grammar — checked in the server's own xgrammar (S1.2, 2026-09-13)

## Question

`VoteCastDecision` and `validate_decision` reject three kinds of ballot after the model has
written them:

- a blank ballot that also ranks candidates;
- a ranked ballot with no positions;
- a ranking longer than the field's limit.

The p500 scale probe spent retries on the first of these (`replays.log`: "blank=1 requires
an empty ranking"). S1.2 writes the three rules into the JSON schema, so that constrained
decoding cannot produce such a ballot in the first place (`llm_schemas.vote_cast_json_schema`).

That only works if the pinned server enforces the new schema. vLLM falls back to another
structured-output backend when xgrammar would refuse a schema, and a grammar can compile yet
fail to forbid what it should.

## Method

`python scripts/check_vote_grammar_xgrammar.py` runs the checks inside the pinned server image
(`vllm/vllm-openai:v0.28.0`, xgrammar 0.2.3) on the CPU, with no GPU and no model:

- **Schemas.** Today's schema and S1.2's (limit five), each with refs inlined, as
  `VllmJsonClient` sends them.
- **Backend check.** vLLM's own `has_xgrammar_unsupported_json_features`.
- **Grammar.** Compiled with the server's settings (`disable_any_whitespace`, strict mode).
- **Samples.** Six ballots, tested for acceptance.

## Result

| sample | today's schema | S1.2's schema |
|---|---|---|
| (vLLM would fall back to another backend) | no | no |
| ranked ballot | accepted | accepted |
| blank ballot | accepted | accepted |
| blank WITH a ranking | accepted | **refused** |
| not blank, EMPTY ranking | accepted | **refused** |
| six positions, limit five | accepted | **refused** |
| two voters, one of each | accepted | accepted |

xgrammar takes S1.2's `anyOf`/`const`/`maxItems` schema itself, with no fallback. The grammar
refuses all three rejected shapes and still accepts both valid ones, alone and mixed in one
batch. Today's schema accepts all six.

## What this does not settle

Whether the model decodes as well under the tighter grammar is still open. S1.2's acceptance
measures it on the GPU: a bake-off session with `--arm vote_grammar` against the control
session, on the same vote cases. Until then `llm.vote_cast_grammar_invariants` ships `false`.
