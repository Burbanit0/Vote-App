"""
api/domain/polity/llm_toon_encoding.py

plan-llm-protocol-and-theory-program.md §5.E: TOON (Token-Oriented Object
Notation, late 2025) declares an array's keys ONCE as a header, then emits
one CSV-style row per record -- unlike JSON, which repeats every key for
every element. §5.E's own analysis (measured from this project's own
prompt shapes, not guessed): the payoff is real specifically for
scalar-heavy, many-record prompts (`pressure_action`, `candidacy_
considered`), and NOT for the vector-heavy ones (`vote_cast`, `chamber_
deliberation`), where float precision dominates instead -- see
_PROMPT_VECTOR_PRECISION's own docstring in llm_behavior_engine.py.

**Input only, by design.** §5.E's own "hors scope" line: switching OUTPUT
serialization away from JSON is explicitly out of scope -- xgrammar
structured decoding, `disable_any_whitespace`, `_inline_refs`, and every
`decode_*_batch` function's Pydantic validation all hang off JSON output,
and §5.A already measured the output itself is under 5% of generated
tokens for a think=True call, so there is nothing to win there. This
module only ever encodes a *prompt*, never a response.

Deliberately minimal: `encode_toon_array` handles exactly the shape this
project's scalar-heavy prompts need (an array of same-shaped int/float
records, one key set for the whole array) -- no nested objects, no
strings, no TOON's own quoting/escaping rules, none of which any current
caller needs. A future caller needing those is a real extension, not
something to speculatively build here.
"""
from __future__ import annotations

from collections.abc import Sequence


def encode_toon_array(array_key: str, field_names: Sequence[str], rows: Sequence[Sequence[int | float]]) -> str:
    """TOON's own header+rows shape: `<array_key>[<row count>]{<field1>,
    <field2>,...}:` followed by one comma-separated row per record, in the
    SAME field order the header declares -- the `[N]`/`{...}` pair doubles
    as a self-check for the model (declared length/fields vs. what it
    reads), per §5.E's own description of the format.

    `rows[i]` must have exactly `len(field_names)` values, each already
    the exact int/float to render (rounding is the CALLER's job -- same
    "prompt builder owns precision" discipline every JSON prompt builder
    in this module already follows, e.g. _PROMPT_VECTOR_PRECISION). Raises
    ValueError on a row of the wrong width rather than silently
    mis-aligning a later row against the header's own field list."""
    for i, row in enumerate(rows):
        if len(row) != len(field_names):
            raise ValueError(
                f"row {i} has {len(row)} value(s), expected {len(field_names)} to match field_names {field_names!r}"
            )
    header = f"{array_key}[{len(rows)}]{{{','.join(field_names)}}}:"
    lines = [header] + [",".join(_encode_scalar(value) for value in row) for row in rows]
    return "\n".join(lines)


def _encode_scalar(value: int | float) -> str:
    """`repr` for floats (not `str`): identical for every value this
    project's rounded prompt floats ever produce, but `repr` is the one
    that never silently switches to scientific notation for a very small
    rounded value -- `str(1e-05)` and `repr(1e-05)` already agree today,
    kept explicit so that stays true if a future caller's own values ever
    get small enough to matter. `bool` is deliberately rejected: Python's
    bool is an int subtype, so an accidental bool would otherwise render
    as bare `True`/`False` (not valid inside a numeric TOON row) instead
    of `1`/`0` -- a caller wanting a 0/1 flag must pass an actual int."""
    if isinstance(value, bool):
        raise TypeError(f"encode_toon_array does not accept bool values (got {value!r}); pass an int instead")
    if isinstance(value, float):
        return repr(value)
    return str(value)
