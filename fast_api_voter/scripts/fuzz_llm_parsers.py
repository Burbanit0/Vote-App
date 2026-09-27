#!/usr/bin/env python3
"""fuzz_llm_parsers.py — coverage-guided fuzzing harness for the polity
simulation's LLM response parsers (Lot 9, PLAN_SOLIDITE_TECHNIQUE.md —
"Fuzzing à couverture", the "parsers" half of this item).

Targets the 9 `decode_*_batch` functions in `api/domain/polity/llm_client.py`
(`decode_vote_batch`, `decode_candidacy_batch`, `decode_party_nomination_batch`,
`decode_positioning_batch`, `decode_response_batch`, `decode_pressure_batch`,
`decode_reaction_batch`, `decode_chamber_batch`, `decode_coalition_batch`).
They are the one genuinely hand-written PARSER of untrusted structured input
in this backend: an LLM's raw text completion, stripped of `<think>` tags,
`json.loads`-parsed, `pydantic`-validated, then checked for cid/party_id
alignment against what was actually requested. Every other "parse" hit in
`api/` (grepped before writing this) is either Pydantic doing its own
request-body validation (already exercised by test_schema_contract.py's
Schemathesis suite) or config/log-file loading of TRUSTED, repo-controlled
input -- an LLM completion is the one place this backend decodes text that
is neither.

Contract: a malformed/misaligned response must raise `LlmResponseError` and
ONLY `LlmResponseError` -- the caller (`llm_behavior_engine.py`) is written
to catch exactly that and retry/log, so any OTHER exception escaping here is
a crash the caller doesn't handle. `LlmResponseError` itself is therefore
never a finding; anything else is.

This is the harness that actually found something: an early, unfixed
version of `decode_vote_batch` (and, since the parse step is identical, all
8 siblings) let a bare `RecursionError` escape past `except
json.JSONDecodeError` on pathologically deep JSON nesting -- `json.loads`'
recursive-descent parser overflows the C stack before it can raise its own
exception. An LLM stuck in a degenerate repetition loop emitting `[[[[[...`
is exactly this shape. Fixed in llm_client.py (catches RecursionError
alongside JSONDecodeError now) with a dedicated regression test in
api/tests/test_polity_llm_client.py; see docs/exploration/EXP-009-atheris-
coverage-fuzzing.md for the full campaign writeup.

Why raw text mutation (not FuzzedDataProvider-constructed JSON like
fuzz_engine.py's votes): the interesting bugs here are in STRING/PARSE
handling (encoding edge cases, regex behaviour, recursion, alignment
logic) that a Python-side JSON-object builder would never generate --
those only show up by mutating actual bytes a real HTTP/LLM response could
carry. `fuzz_corpus/llm_parsers/seed_*` seeds real example payloads (a
valid batch, a `<think>`-wrapped one, a schema-invalid one, plain non-JSON
prose) so the mutator starts from realistic shapes instead of empty bytes.

Usage:
    cd fast_api_voter
    python scripts/fuzz_llm_parsers.py fuzz_corpus/llm_parsers -max_total_time=600
    python scripts/fuzz_llm_parsers.py fuzz_corpus/llm_parsers/crash-<sha1>  # replay
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Sequence

import atheris

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

with atheris.instrument_imports():
    from api.domain.polity.llm_client import (
        LlmResponseError,
        decode_candidacy_batch,
        decode_chamber_batch,
        decode_coalition_batch,
        decode_party_nomination_batch,
        decode_positioning_batch,
        decode_pressure_batch,
        decode_reaction_batch,
        decode_response_batch,
        decode_vote_batch,
    )

# Every decode_*_batch this repo ships. Signature-compatible: the 2nd
# positional param is `expected_cids` for 7 of them and `expected_party_ids`
# for 2 (decode_party_nomination_batch, decode_coalition_batch) -- same
# position either way, so one uniform call site below works for all 9.
_DECODERS: list[Callable[[str, Sequence[int]], object]] = [
    decode_vote_batch,
    decode_candidacy_batch,
    decode_party_nomination_batch,
    decode_positioning_batch,
    decode_response_batch,
    decode_pressure_batch,
    decode_reaction_batch,
    decode_chamber_batch,
    decode_coalition_batch,
]


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    # Small selector/cid-list values first: atheris's FuzzedDataProvider
    # consumes ConsumeIntInRange etc. from the END of the buffer (confirmed
    # empirically), leaving the FRONT intact for ConsumeUnicodeNoSurrogates
    # below -- so a seed file's actual JSON payload survives byte-for-byte
    # as long as it has a little trailing whitespace padding (`raw.strip()`
    # in every decoder discards that anyway).
    decoder = _DECODERS[fdp.ConsumeIntInRange(0, len(_DECODERS) - 1)]
    n_cids = fdp.ConsumeIntInRange(0, 6)
    expected_cids = [fdp.ConsumeIntInRange(0, 20) for _ in range(n_cids)]

    raw = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())

    try:
        decoder(raw, expected_cids)
    except LlmResponseError:
        pass  # the documented contract for malformed/misaligned input -- not a finding


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
