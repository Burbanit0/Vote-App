"""
scripts/check_campaign_positioning_truncation_reasoning.py

plan-adversarial-framing-collapse.md's campaign_positioning "PROCHAINE ETAPE IMMEDIATE" (flagged
2026-08-31, run same day at the user's explicit "do the test first" before any commit): the 6/8
truncations found by check_campaign_positioning_failure_rate.py all land at finish_reason='length'
-- the same surface signature already diagnosed for decide_chamber_deliberation as Mode A
(unbounded, non-convergent reasoning: a near-identical paragraph repeated dozens of times, landing
exactly on the token ceiling every time -- see llm_behavior_engine.py's own chamber_deliberation
docstring and scripts/lot3_chamber_reliability_results.md's "Lot 5 correction"). If campaign_
positioning shows the same signature, the same fix (prompt disambiguation, not a budget increase)
is a real candidate -- if not, this is a different failure mode and the chamber precedent doesn't
transfer.

Diagnostic gap this works around, same one the chamber probe hit: OllamaJsonClient.complete_json's
own _extract_content raises LlmResponseError the instant finish_reason != "stop", discarding
message.content AND message.reasoning before the caller ever sees them. campaign_positioning uses
think=True, which dispatches to _complete_json_openai_compat (POST {base_url}/chat/completions,
OpenAI-compat shape: choices[0].message.reasoning, choices[0].finish_reason) -- NOT the native
/api/chat endpoint pressure_action_harness.raw_pressure_call targets, so that helper doesn't apply
here; this script mirrors _complete_json_openai_compat's own request body directly instead.

Targets the exact 6 cids identified as truncations in check_campaign_positioning_failure_rate.py's
n=32 run (experiment 20260831T233502Z-586e3c0e): 184, 167, 126, 79, 209, 158. Same population
construction (population_size=300, same seed) reproduces the same nominees deterministically --
verified against each cid's previously-recorded dist_to_mean as a sanity check, not assumed.

No formal harness pre-registration: this is a diagnostic probe (does trace X show pattern Y?), not
a hypothesis test with a numeric accept/reject threshold -- same status as the chamber_deliberation
precedent's own probe_chamber_truncation.py. Committed here (unlike that one, which stayed
scratchpad) to keep this investigation's own convention of every script being reviewable.

Usage:
    python fast_api_voter/scripts/check_campaign_positioning_truncation_reasoning.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, _inline_refs, _post_with_transport_retry  # noqa: E402
from api.domain.polity.llm_schemas import POSITIONING_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation  # noqa: E402

_POPULATION_SIZE = 300
_THINK_TOKEN_ALLOWANCE = 8000
_TARGET_CIDS_WITH_EXPECTED_DIST = {
    184: 1.4675, 167: 1.5034, 126: 1.5262, 79: 0.3240, 209: 0.3601, 158: 0.3799,
}
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_DUMP_DIR = Path(r"C:\Users\burba\AppData\Local\Temp\claude\c--Users-burba-Vote-App-polity\22458a2f-ddf0-45bc-bb54-2e029e1a45ce\scratchpad\campaign_positioning_traces")


def _electorate_mean(population: list[Citizen]) -> tuple[float, ...]:
    issue_count = len(population[0].issue_positions)
    sums = [0.0] * issue_count
    for c in population:
        for i, v in enumerate(c.issue_positions):
            sums[i] += v
    return tuple(s / len(population) for s in sums)


def raw_positioning_call(
    client: OllamaJsonClient, system_prompt: str, user_prompt: str, max_tokens: int,
) -> dict[str, Any]:
    """Mirrors OllamaJsonClient._complete_json_openai_compat's exact request body (same
    endpoint, same shape) but parses the full response directly instead of calling
    _extract_content -- so a finish_reason != 'stop' response stays inspectable (reasoning
    included) instead of being thrown away in an LlmResponseError."""
    body = {
        "model": client._model,  # noqa: SLF001 -- exploratory probe, documented reuse
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": client._temperature,  # noqa: SLF001
        "seed": client._seed,  # noqa: SLF001
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "polity_decision_batch", "strict": True, "schema": _inline_refs(POSITIONING_JSON_SCHEMA)},
        },
    }
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    response: httpx.Response = _post_with_transport_retry(client._client, f"{client._base_url}/chat/completions", payload)  # noqa: SLF001
    return dict(response.json())


def _top_repeated_fragments(reasoning: str, min_len: int = 15, top_n: int = 5) -> list[tuple[str, int]]:
    """Splits on sentence boundaries and counts exact-duplicate sentences of at least
    min_len chars -- the same "count exact repeats" method the chamber diagnostic used
    informally (e.g. 'Wait, maybe' x71), just automated instead of eyeballed."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(reasoning) if len(s.strip()) >= min_len]
    counts = Counter(sentences)
    return counts.most_common(top_n)


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    parties = initialize_parties(population, config.parties.initial_count, config.run.seed)
    for c in population:
        c.party_affiliation = assign_party_affiliation(c, parties)
    parties_by_id = {p.party_id: p for p in parties}
    mean = _electorate_mean(population)
    by_cid = {c.citizen_id: c for c in population}

    verdicts = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid, expected_dist in _TARGET_CIDS_WITH_EXPECTED_DIST.items():
            nominee = by_cid[cid]
            dist = math.dist(nominee.issue_positions, mean)
            if abs(dist - expected_dist) > 1e-3:
                print(f"cid={cid}: dist_to_mean mismatch (got {dist:.4f}, expected {expected_dist:.4f}) -- population reconstruction diverged, aborting")
                return 1

            system_prompt = build_positioning_system_prompt([nominee], config)
            user_prompt = build_positioning_user_prompt([nominee], parties_by_id, mean)
            body = raw_positioning_call(client, system_prompt, user_prompt, compute_max_tokens(1) + _THINK_TOKEN_ALLOWANCE)

            choices = body.get("choices") or [{}]
            choice = choices[0] if isinstance(choices, list) and choices else {}
            finish_reason = choice.get("finish_reason")
            message = choice.get("message") or {}
            reasoning = message.get("reasoning") or ""
            content = message.get("content") or ""
            usage = body.get("usage") or {}
            completion_tokens = usage.get("completion_tokens")

            print(f"\n########## cid={cid} (dist_to_mean={dist:.4f}) ##########")
            print(f"finish_reason={finish_reason!r} completion_tokens={completion_tokens} reasoning_chars={len(reasoning)} content_chars={len(content)}")

            if finish_reason == "stop":
                print("  did NOT truncate this time (non-determinism under batching, already documented elsewhere in this project) -- skipping pattern analysis.")
                verdicts.append((cid, "no_repro"))
                continue

            _DUMP_DIR.mkdir(parents=True, exist_ok=True)
            (_DUMP_DIR / f"cid{cid}_reasoning.txt").write_text(reasoning, encoding="utf-8")
            (_DUMP_DIR / f"cid{cid}_user_prompt.txt").write_text(user_prompt, encoding="utf-8")
            (_DUMP_DIR / f"cid{cid}_system_prompt.txt").write_text(system_prompt, encoding="utf-8")

            top_fragments = _top_repeated_fragments(reasoning)
            print("  top repeated sentences:")
            for fragment, count in top_fragments:
                preview = fragment if len(fragment) <= 100 else fragment[:97] + "..."
                print(f"    x{count}: {preview!r}")

            if top_fragments:
                first_fragment = top_fragments[0][0]
                pivot_char = reasoning.find(first_fragment)
                pivot_word_estimate = reasoning[:pivot_char].count(" ") if pivot_char >= 0 else -1
                print(f"  pivot: most-repeated fragment first appears at char {pivot_char}/{len(reasoning)} (~{pivot_word_estimate} words in)")
            print(f"  full reasoning/prompts dumped to {_DUMP_DIR}")

            max_repeat = top_fragments[0][1] if top_fragments else 0
            if max_repeat >= 10:
                verdict = "MODE_A (repeated-paragraph signature)"
            elif max_repeat >= 3:
                verdict = "AMBIGUOUS (some repetition, below the x10+ chamber-precedent bar)"
            else:
                verdict = "MODE_B or other (no strong repetition -- long genuine content, or empty reasoning)"
            print(f"  verdict: {verdict}")
            verdicts.append((cid, verdict))

    print("\n--- summary ---")
    for cid, verdict in verdicts:
        print(f"  cid={cid}: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
