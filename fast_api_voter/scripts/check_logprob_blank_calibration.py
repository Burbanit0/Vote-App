"""
scripts/check_logprob_blank_calibration.py

plan-llm-protocol-and-theory-program.md §5.C's own Verification bar: before
trusting logprob-read P(x) on any decision type with NO ground truth
(pressure_action, the actual target), validate the technique on the one
decision type that HAS real ground truth -- vote_cast, via
simple_rules.build_ranking. Does P(blank=1), read directly off the model's
own real, xgrammar-constrained, think=True completion via
VllmJsonClient.complete_json_with_logprobs + llm_logprob_instrumentation's
field-locator, actually correlate with whether the deterministic rule says
this voter's sincere ballot is blank?

This is also the first live exercise of the "real hard problem" both
complete_with_logprobs's and llm_logprob_instrumentation's own docstrings
name and defer: locating the `"blank":` value's own token inside a real
production completion, not a bare forced-choice probe. Everything here
runs through the SAME prompt builders (build_system_prompt/build_user_prompt)
production cast_votes uses -- this is not a synthetic toy prompt.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_logprob_blank_calibration.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    _VOTE_THINK_TOKEN_ALLOWANCE,
    _dynamic_max_tokens,
    _vote_cast_chunk_size,
    build_system_prompt,
    build_user_prompt,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    binary_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import (  # noqa: E402
    BLANK_LABEL,
    assign_party_affiliation,
    build_ranking,
    declare_candidacy,
)


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _chunked(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


def main() -> int:
    config = _vllm_config()

    # A large-enough pool that both ground-truth outcomes occur naturally
    # (never hand-tuned toward one pole), then a BALANCED sample drawn from
    # it -- same "extreme cases at both poles" discipline plan-adversarial-
    # framing-collapse.md already established, applied by selection rather
    # than by hand-placing citizen vectors.
    citizens = generate_population(config.citizens, 200, config.run.seed)
    parties = initialize_parties(citizens, 5, config.run.seed)
    for c in citizens:
        c.party_affiliation = assign_party_affiliation(c, parties)
    nominees = []
    for p in parties:
        members = [c for c in citizens if c.party_affiliation == p.party_id]
        if members:
            nominees.append(max(members, key=lambda c: (c.ambition_score, -c.citizen_id)))
    for n in nominees:
        declare_candidacy(n)
    nominees = sorted(nominees, key=lambda c: c.citizen_id)
    nominee_ids = {n.citizen_id for n in nominees}

    pool = [c for c in citizens if c.citizen_id not in nominee_ids]
    truth: dict[int, bool] = {}
    for voter in pool:
        full = build_ranking(voter, nominees)
        truth[voter.citizen_id] = full[0] == BLANK_LABEL

    blank_voters = [v for v in pool if truth[v.citizen_id]][:8]
    nonblank_voters = [v for v in pool if not truth[v.citizen_id]][:8]
    voters = sorted(blank_voters + nonblank_voters, key=lambda c: c.citizen_id)
    print(f"calibration set: {len(voters)} voters ({len(blank_voters)} ground-truth blank, "
          f"{len(nonblank_voters)} ground-truth non-blank), {len(nominees)} candidates")

    chunk_size = _vote_cast_chunk_size(config)
    chunks = _chunked(voters, chunk_size)

    rows = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for chunk in chunks:
            system_prompt = build_system_prompt(chunk, nominees)
            user_prompt = build_user_prompt(chunk, nominees)
            max_tokens = _dynamic_max_tokens(
                client, config,
                system_prompt=system_prompt, user_prompt=user_prompt,
                chunk_size=len(chunk), flat_allowance=_VOTE_THINK_TOKEN_ALLOWANCE,
            )
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=system_prompt, user_prompt=user_prompt,
                json_schema=VOTE_CAST_JSON_SCHEMA, max_tokens=max_tokens, think=True, top_logprobs=10,
            )
            try:
                probes = locate_decision_field_logprobs(content, tokens, field="blank")
            except LogprobAlignmentError as exc:
                print(f"  ALIGNMENT FAILED for chunk {[v.citizen_id for v in chunk]}: {exc}")
                continue
            for probe in probes:
                p_blank = binary_probability(probe.token, true_value="1", false_value="0")
                rows.append((probe.cid, truth[probe.cid], p_blank, probe.token.token))

    print(f"\n{'cid':>5}  {'truth':>6}  {'P(blank=1)':>11}  {'chosen_token':>13}  {'threshold_call':>15}  {'match':>6}")
    correct = 0
    p_when_true = []
    p_when_false = []
    for cid, is_blank, p_blank, chosen in sorted(rows):
        call = p_blank > 0.5
        match = call == is_blank
        correct += match
        (p_when_true if is_blank else p_when_false).append(p_blank)
        print(f"{cid:>5}  {str(is_blank):>6}  {p_blank:>11.6f}  {chosen:>13}  {str(call):>15}  {str(match):>6}")

    print(f"\naligned decisions: {len(rows)}/{len(voters)}")
    print(f"threshold-call accuracy (P(blank=1)>0.5 vs ground truth): {correct}/{len(rows)}")
    if p_when_true and p_when_false:
        mean_true = sum(p_when_true) / len(p_when_true)
        mean_false = sum(p_when_false) / len(p_when_false)
        print(f"mean P(blank=1) | ground-truth blank:     {mean_true:.6f}  (n={len(p_when_true)})")
        print(f"mean P(blank=1) | ground-truth non-blank:  {mean_false:.6f}  (n={len(p_when_false)})")
        print(f"separation (higher is better discrimination): {mean_true - mean_false:+.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
