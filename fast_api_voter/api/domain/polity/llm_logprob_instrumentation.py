"""
api/domain/polity/llm_logprob_instrumentation.py

plan-llm-protocol-and-theory-program.md §5.C's "real hard problem": given a
real production, xgrammar-constrained completion (VllmJsonClient.
complete_json_with_logprobs), locate the specific token whose probability
answers "how confident was the model in citizen cid's own decision on field
X" -- e.g. `"blank":1` or `"act":3`, somewhere inside a JSON array of
several decisions, not the first generated token the way a bare
forced-choice probe's is.

Two problems, solved separately:

1. **Reasoning-parser offset.** `complete_with_logprobs`/`complete_json_
   with_logprobs` return `content` already stripped of any `<think>...
   </think>` block (vLLM's `--reasoning-parser qwen3` splits it into a
   separate `message.reasoning_content` this codebase never reads) --
   but `tokens` (`logprobs.content`) covers the FULL raw generation,
   think block included. Concatenating every `token.token` in order
   therefore does NOT equal `content` under `think=True`; it equals
   `content` PLUS everything the reasoning parser stripped out, with
   `content` sitting at the END. Fixed by finding `content` as a
   substring of that raw concatenation (`_locate_content_in_raw_text`)
   and doing every subsequent character-offset calculation in that raw,
   token-aligned space -- never against `content`'s own offsets directly.
2. **Field-to-token alignment.** Field order inside one decision object is
   fixed by the JSON schema's own `properties` order (xgrammar generates
   keys in schema-declaration order, not alphabetically) but WHICH
   citizen's decision that is, and where exactly the value's characters
   fall in the token stream, still has to be read off the real text.
   `locate_decision_field_logprobs` finds every occurrence of
   `"<field>":<scalar>` in `content`, in document order, and zips it
   against `json.loads(content)`'s own parsed decision list (same
   document order, same count -- checked, not assumed) to attach each
   span to its own `cid`. Deliberately scalar-only (digit/true/false/
   null) -- every current single-token decision-relevant field in this
   project's schemas (`blank`, `act`, `stance`, ...) is one of those; a
   quoted-string field would need a different (quote-aware) span rule
   this module does not currently provide, because nothing here needs it
   yet.

Deliberately NOT wired into any decide_* entry point -- same framing as
complete_with_logprobs's own docstring: this reads a decision's own
confidence, it does not decide anything.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .llm_client import TokenLogprob

_SCALAR_VALUE_RE = re.compile(r"-?\d+(?:\.\d+)?|true|false|null")


class LogprobAlignmentError(ValueError):
    """Raised when the raw token stream / parsed content / field
    occurrences do not line up the way this module's own docstring
    assumes -- e.g. `content` is not a substring of the token
    concatenation, or the number of `"<field>":` occurrences does not
    match the number of parsed decisions. Always a signal that an
    assumption this module depends on broke for this particular
    completion, never silently ignored or best-efforted."""


@dataclass(frozen=True)
class DecisionTokenProbe:
    """One decision's own field-relevant token, located inside a real
    completion. `cid` comes from the parsed decision object itself (the
    field named by `locate_decision_field_logprobs`'s own `cid_field`
    argument), not from re-deriving it -- the caller's batch envelope is
    the authority on which decision belongs to which citizen, same as
    every decode_*_batch function elsewhere in this codebase."""

    cid: int
    token: TokenLogprob


def _locate_content_in_raw_text(raw_text: str, content: str) -> int:
    """The character offset in `raw_text` (the full raw generation,
    reconstructed by concatenating every TokenLogprob.token in order)
    where `content` (the reasoning-parser-stripped final answer) begins.
    `rfind`, not `find`: `content` is the LAST thing generated (after any
    `<think>` block), and a pathological completion could in principle
    echo a substring matching `content` earlier (inside its own
    reasoning) -- the real answer is always the rightmost match."""
    offset = raw_text.rfind(content)
    if offset == -1:
        raise LogprobAlignmentError(
            "content is not a substring of the raw token stream -- the "
            "reasoning-parser-split assumption this module depends on "
            "does not hold for this completion"
        )
    return offset


def _find_field_value_spans(content: str, field: str) -> list[tuple[int, int]]:
    """(start, end) character spans, in document order, of the SCALAR
    value immediately following each `"<field>":` occurrence in
    `content`. See this module's own docstring for why scalar-only."""
    spans = []
    key_pattern = re.compile(rf'"{re.escape(field)}"\s*:\s*')
    for key_match in key_pattern.finditer(content):
        value_match = _SCALAR_VALUE_RE.match(content, key_match.end())
        if value_match is None:
            raise LogprobAlignmentError(
                f"field {field!r} at content offset {key_match.end()} is not "
                f"followed by a scalar value (got {content[key_match.end():key_match.end() + 20]!r})"
            )
        spans.append(value_match.span())
    return spans


def _token_covering_offset(tokens: Sequence[TokenLogprob], raw_offset: int) -> TokenLogprob:
    """The single TokenLogprob whose own span in the raw text
    (reconstructed by walking cumulative token-string lengths, in
    generation order) covers `raw_offset`. Deliberately the token
    covering the VALUE'S FIRST character only -- sufficient for every
    field this module targets today (single-digit Literal fields:
    `blank` in {0,1}, `act` in {0..4}, `stance` in {1..4}, ...), where
    the discriminating character is the first (and usually only) one and
    is overwhelmingly likely to be its own single token immediately
    after a JSON `:` -- a multi-character value needing more than its
    first token's own probability is out of scope here, not silently
    mishandled."""
    cursor = 0
    for token in tokens:
        token_len = len(token.token)
        if cursor <= raw_offset < cursor + token_len:
            return token
        cursor += token_len
    raise LogprobAlignmentError(
        f"offset {raw_offset} is not covered by any token (raw text reconstructs to {cursor} characters)"
    )


def locate_decision_field_logprobs(
    content: str,
    tokens: Sequence[TokenLogprob],
    *,
    field: str,
    decisions_key: str = "decisions",
    cid_field: str = "cid",
) -> list[DecisionTokenProbe]:
    """The main entry point: given a real complete_json_with_logprobs
    result (`content`, `tokens`) for a `{"decisions": [...]}` batch
    envelope (every decide_* schema in this project's shape, per
    §3.6.0), return one DecisionTokenProbe per decision, each carrying
    that decision's own `cid` and the TokenLogprob covering `field`'s
    value for that decision.

    Raises LogprobAlignmentError (never returns a partial/best-effort
    result) if: `content` cannot be located inside the raw token stream,
    the count of `"<field>":` occurrences does not match the count of
    parsed decisions, or a decision object is missing `cid_field`. Each
    of those is a real, actionable signal that an assumption broke for
    this specific completion -- not something a caller should have to
    detect itself by noticing a suspiciously short result list."""
    raw_text = "".join(token.token for token in tokens)
    base_offset = _locate_content_in_raw_text(raw_text, content)

    parsed: Any = json.loads(content)
    if not isinstance(parsed, dict) or not isinstance(parsed.get(decisions_key), list):
        raise LogprobAlignmentError(f"expected a {{{decisions_key!r}: [...]}} object, got {parsed!r}")
    decisions = parsed[decisions_key]

    spans = _find_field_value_spans(content, field)
    if len(spans) != len(decisions):
        raise LogprobAlignmentError(
            f"found {len(spans)} occurrence(s) of field {field!r} in content but "
            f"{len(decisions)} decision(s) in {decisions_key!r} -- cannot align"
        )

    probes = []
    for decision, (start, _end) in zip(decisions, spans):
        if not isinstance(decision, dict) or cid_field not in decision:
            raise LogprobAlignmentError(f"decision {decision!r} is missing {cid_field!r}")
        token = _token_covering_offset(tokens, base_offset + start)
        probes.append(DecisionTokenProbe(cid=int(decision[cid_field]), token=token))
    return probes


def binary_probability(token: TokenLogprob, *, true_value: str, false_value: str) -> float:
    """Normalized P(true_value) for a token known to be one of exactly
    two candidate values (e.g. `blank` in {"0","1"}, read as
    true_value="1"), computed from `token.alternatives` -- vLLM's own
    top-K logprobs for that position, always including the chosen token
    (TokenLogprob's own docstring). Normalizes over ONLY the two named
    candidates, not the full top-K mass: correct exactly when the field
    is genuinely binary/exhaustive over those two literal values, which
    is the only case this function is for. Returns 0.5 (maximally
    uninformative, not an arbitrary 0.0/1.0) if NEITHER candidate
    appears in `alternatives` -- a real possibility if `top_logprobs`
    was set too low to capture a very unlikely branch, and a caller
    should treat that as "unmeasured", not "false"."""
    p_true = math.exp(token.alternatives[true_value]) if true_value in token.alternatives else 0.0
    p_false = math.exp(token.alternatives[false_value]) if false_value in token.alternatives else 0.0
    total = p_true + p_false
    if total == 0.0:
        return 0.5
    return p_true / total


def candidate_probability(token: TokenLogprob, candidate: str) -> float:
    """Raw (NOT renormalized against any other candidate) P(candidate),
    read directly off `token.alternatives` -- `exp(logprob)` if `candidate`
    is among the server's own top-K for this position, else 0.0 ("not
    captured by this top_logprobs budget", not "impossible": widen
    top_logprobs if a near-zero reading here needs to be trusted).

    Unlike `binary_probability`, does not assume `candidate` is one of
    exactly two exhaustive outcomes -- the right tool for reading one
    outcome's own probability out of a field with MORE than two possible
    values (e.g. `stance` in {1,2,3,4}: candidate_probability(token, "1")
    answers "how confident was the model in concession specifically",
    without forcing a choice of which of the other three values to
    normalize against)."""
    return math.exp(token.alternatives[candidate]) if candidate in token.alternatives else 0.0
