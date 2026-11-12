"""
scripts/check_candidacy_forced_reasoning_comparison.py

Cheap comparative test, per direct instruction: pressure_action already showed that forcing
think=True in a single-citizen-batch configuration (never used in production for this decision
type) produces ZERO visible <think> content and collapses to a fixed default (act=4/motif=305),
regardless of each citizen's real self_gap (reasoning_budget_and_decision_quality_findings.md).
This asks whether that total reasoning suppression is itself tied to the relational/act-response
framing (pressure_action collapses under think=False too), or a general property of forcing
think=True onto a single-citizen batch for ANY decision type -- including one that does NOT
collapse under its own normal think=False path (candidacy_considered).

5 extreme-low-ambition citizens already confirmed correct under think=False
(check_candidacy_considered_isolation_disposition.py: 5/5 "decline", ambition_score 0.0069-0.0214,
14x-43x below the 0.30 threshold) PLUS 3 high-ambition citizens (0.43-0.48, well above the 0.30
threshold, who should "declare") -- both poles, per this project's own established discipline
against drawing a collapse verdict from a one-sided sample (a first draft of this script tested
only the 5 low-ambition citizens and its own printed verdict overclaimed "collapse" from a sample
where every citizen shared the same true answer -- caught and corrected before writing anything
down, not after). Forces think=True -- NOT candidacy_considered's own production configuration
(think=False) -- same exploratory register as the original pressure_action forced-reasoning
probe, with the same caveat: this does not reproduce production, it tests whether the mechanism
(single-citizen-batch think=True) suppresses reasoning independent of decision type.

Two readings, written before any call:
- If candidacy_considered ALSO shows zero visible reasoning + a collapsed/fixed decision -> total
  reasoning suppression under this configuration is a general property, not tied to the
  relational framing specifically -- weakens any theory that ties reasoning-suppression itself to
  act/response framing.
- If candidacy_considered shows REAL, visible reasoning (and/or stays correct) -> the suppression
  found for pressure_action is itself part of the relational-framing collapse, not a general
  single-citizen-batch think=True artifact -- strengthens the connection between the two findings.

Usage:
    python fast_api_voter/scripts/check_candidacy_forced_reasoning_comparison.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_candidacy_system_prompt,
    build_candidacy_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, _THINK_TAG_RE, decode_candidacy_batch  # noqa: E402
from api.domain.polity.llm_schemas import CANDIDACY_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import sympathizer_ratio  # noqa: E402

_POPULATION_SIZE = 190
_LOW_AMBITION_CIDS = [8, 178, 42, 41, 77]  # should decline, 0.0069-0.0214, 14x-43x below threshold
_HIGH_AMBITION_CIDS = [48, 92, 181]  # should declare, 0.4543-0.4797, well above the 0.30 threshold
_TARGET_CIDS = _LOW_AMBITION_CIDS + _HIGH_AMBITION_CIDS
_FORCED_THINK_TOKEN_ALLOWANCE = 8000  # same generous, uncalibrated allowance as the pressure_action probe


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    by_id = {c.citizen_id: c for c in population}
    support = {cid: sympathizer_ratio(by_id[cid], population) for cid in _TARGET_CIDS}

    results = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid in _TARGET_CIDS:
            citizen = by_id[cid]
            raw = client.complete_json(
                system_prompt=build_candidacy_system_prompt([citizen]),
                user_prompt=build_candidacy_user_prompt([citizen], support),
                json_schema=CANDIDACY_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1) + _FORCED_THINK_TOKEN_ALLOWANCE,
                think=True,
            )
            think_match = _THINK_TAG_RE.search(raw)
            think_content = think_match.group(0) if think_match else None
            think_len = len(think_content) if think_content else 0
            decision = decode_candidacy_batch(raw, [cid])[0]
            expected = "decline" if cid in _LOW_AMBITION_CIDS else "declare"
            print(f"\n=== cid={cid} ambition_score={citizen.ambition_score:.4f} (think=False expected: {expected}) ===")
            print(f"<think> content present? {'YES' if think_content else 'NO'} (length={think_len} chars)")
            if think_content:
                preview = think_content[:300] + ("..." if len(think_content) > 300 else "")
                print(f"preview: {preview!r}")
            actual = "declare" if decision.outcome == 1 else "decline"
            print(f"decoded: outcome={decision.outcome} ({actual}) motif={decision.motif} [{'AGREE' if actual == expected else 'DISAGREE'}]")
            results.append((cid, think_len, decision.outcome, decision.motif, cid in _HIGH_AMBITION_CIDS))

    print("\n--- verdict ---")
    any_reasoning = any(think_len > 0 for _cid, think_len, _o, _m, _h in results)
    distinct_decisions = {(o, m) for _cid, _t, o, m, _h in results}
    high_ambition_results = [r for r in results if r[4]]
    high_ambition_declared = sum(1 for _cid, _t, o, _m, _h in high_ambition_results if o == 1)
    if not any_reasoning and len(distinct_decisions) == 1:
        print(
            f"ZERO visible reasoning across all {len(results)} calls (5 low-ambition + 3 high-ambition), "
            "AND the decision collapsed to the SAME fixed outcome regardless of ambition_score -- "
            f"including {len(high_ambition_results) - high_ambition_declared}/{len(high_ambition_results)} "
            "high-ambition citizens who should have declared but didn't -- a genuine, mixed-pole-"
            "verified collapse, not an artifact of a one-sided sample. Total reasoning suppression "
            "under forced think=True at size=1 is a GENERAL property of this configuration, not "
            "tied to the relational/act-response framing specifically -- pressure_action's own "
            "think=True collapse looks like a separate, size=1/think=True artifact, not connected "
            "to why it collapses under think=False (its own real production path)."
        )
    elif not any_reasoning and high_ambition_declared == len(high_ambition_results):
        print(
            "ZERO visible reasoning across all calls, but high-ambition citizens still correctly "
            "declared -> reasoning suppression itself is general to this configuration, but does "
            "NOT by itself cause a decision collapse -- candidacy_considered stays correct even "
            "with the reasoning channel suppressed. Narrows what pressure_action's own think=True "
            "collapse actually demonstrates."
        )
    else:
        print(
            f"Mixed result: reasoning={'present' if any_reasoning else 'absent'}, "
            f"{high_ambition_declared}/{len(high_ambition_results)} high-ambition citizens declared "
            "correctly -> partial signal, does not cleanly fit either reading -- inspect the "
            "per-citizen output above before concluding."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
