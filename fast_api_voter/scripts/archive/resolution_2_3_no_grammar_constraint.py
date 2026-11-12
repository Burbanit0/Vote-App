"""
scripts/resolution_2_3_no_grammar_constraint.py

plan-pressure-action-resolution.md §2.3 -- removes the grammar-constrained JSON decoding
(`format=json_schema`) entirely, replaced by a prose instruction asking for a JSON object with
keys cid/act/motif/target, parsed leniently. Tests Tam et al. 2024's own comparison (schema-
constrained decoding vs a bare JSON-in-prose instruction) -- structurally different from §3.2
(free TEXT with SITUATION:/DECISION:/MOTIF: lines, not JSON at all).

Reuses build_pressure_system_prompt/build_pressure_user_prompt verbatim (same convention as
resolution_2_1_temperature_0_7.py) rather than reconstructing the prompt by hand -- the ONE
change is the trailing instruction line, swapped from "Reponds UNIQUEMENT avec un objet JSON
conforme au schema fourni." (which names a schema that is no longer sent) to a prose instruction
naming the four keys directly. Everything else -- menu table, motif table, neighbors_acting
wording, self-check discipline -- is production's own text, not a duplicate.

Same 70-citizen dataset as §3.1/§3.2 (population_size=190, holder cid=5 via declare_candidacy),
size=1, think=False, temperature=0.0 -- the ONE variable changed is the absence of the `format`
field. Pre-registered criterion: >=60% agreement (lower bar than 80%, since tolerant parsing adds
its own error margin) -- see plan-pressure-action-resolution.md §2.3 for the full pre-
registration.

Usage:
    python fast_api_voter/scripts/resolution_2_3_no_grammar_constraint.py <experiment_id>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from typing import Any  # noqa: E402

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient  # noqa: E402
from llm_test_harness import trial  # noqa: E402
from pressure_action_harness import (  # noqa: E402
    ACT_NAMES,
    ACTING_CODES,
    MANDATE_DEV,
    TICKS_TO_ELECTION,
    harvest_unambiguous_citizens,
    raw_pressure_call,
    to_trial_result,
)

_SCHEMA_INSTRUCTION = "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
_PROSE_INSTRUCTION = (
    "Pas de schema impose au decodage. Reponds avec UNIQUEMENT un objet "
    "JSON, rien avant ni apres, de la forme exacte {\"cid\": <int>, "
    "\"act\": <int>, \"motif\": <int>, \"target\": <int>} -- ecris ce "
    "JSON toi-meme, avec ces quatre cles exactement."
)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def build_no_schema_system_prompt(citizen_stub: Any, config: PolityConfig) -> str:
    """Production's own build_pressure_system_prompt, with only the trailing
    schema-conformance line swapped for a prose JSON instruction -- see module
    docstring. Fails loudly (rather than silently no-op) if production's exact
    wording ever changes, so this test can't silently drift into testing
    something else."""
    base = build_pressure_system_prompt([citizen_stub], config)
    if _SCHEMA_INSTRUCTION not in base:
        raise RuntimeError(
            "build_pressure_system_prompt's trailing instruction line has changed -- "
            "update _SCHEMA_INSTRUCTION/_PROSE_INSTRUCTION in resolution_2_3 to match "
            "before rerunning, rather than silently testing the old wording."
        )
    return base.replace(_SCHEMA_INSTRUCTION, _PROSE_INSTRUCTION)


def lenient_extract_act(content: str) -> tuple[int | None, int | None, str | None]:
    """Tolerant parsing per §2.3's own pre-registration: a JSON object may be preceded/followed
    by prose despite the instruction, so extract the first {...} span rather than requiring the
    whole content to be valid JSON on its own. A parse failure is a real result to record
    (returns (None, None, error)), never silently skipped."""
    match = _JSON_OBJECT_RE.search(content)
    if not match:
        return None, None, "no JSON object found in response"
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        return None, None, f"JSON decode failed: {exc}"
    if not isinstance(parsed, dict) or "act" not in parsed:
        return None, None, f"parsed object missing 'act' key: {parsed!r}"
    act = parsed.get("act")
    motif = parsed.get("motif")
    if not isinstance(act, int):
        return None, None, f"'act' is not an int: {act!r}"
    return act, motif if isinstance(motif, int) else None, None


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: resolution_2_3_no_grammar_constraint.py <experiment_id>")
        return 1
    experiment_id = sys.argv[1]

    config = load_config()
    holder, cases = harvest_unambiguous_citizens(config)
    print(f"harvested {len(cases)} unambiguous citizens (holder=cid{holder.citizen_id})")

    outcomes: list[bool | None] = []
    parse_failures = 0
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for i, (citizen, gap, expected_act) in enumerate(cases, start=1):
            cid = citizen.citizen_id
            ctx = PressureContext(
                cid=cid, target=holder.citizen_id, self_gap=gap, mandate_dev=MANDATE_DEV,
                ticks_to_election=TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            citizen_stub = type("C", (), {"citizen_id": cid})()
            system_prompt = build_no_schema_system_prompt(citizen_stub, config)
            user_prompt = build_pressure_user_prompt([citizen_stub], {cid: ctx})
            case_outcome: dict[str, bool | None] = {"agree": None}

            def run_call(
                gap: float = gap, cid: int = cid, expected_act: bool = expected_act,
                system_prompt: str = system_prompt, user_prompt: str = user_prompt,
                case_outcome: dict[str, bool | None] = case_outcome,
            ) -> trial.TrialResult:
                nonlocal parse_failures
                raw = raw_pressure_call(client, system_prompt, user_prompt, None, compute_max_tokens(1))
                actual_act = None
                agree = None
                parse_error = None
                act = motif = None
                if raw.content:
                    act, motif, parse_error = lenient_extract_act(raw.content)
                    if act is not None:
                        actual_act = act in ACTING_CODES
                        agree = actual_act == expected_act
                if parse_error:
                    parse_failures += 1
                    print(f"  cid={cid} PARSE FAILED: {parse_error} (raw content: {raw.content!r})")
                else:
                    act_name = ACT_NAMES.get(act, "?") if act is not None else "?"
                    print(f"  cid={cid} expected={expected_act} act={act} ({act_name}) [{'AGREE' if agree else 'DISAGREE'}]")
                case_outcome["agree"] = agree
                return to_trial_result(raw, {
                    "cid": cid, "self_gap": gap, "expected_act": expected_act,
                    "actual_act": actual_act, "agree": agree, "parse_error": parse_error,
                    "variant": "2.3_no_grammar_constraint",
                })

            trial.record_trial(experiment_id, i, container_name="ollama-polity", run_call=run_call)
            outcomes.append(case_outcome["agree"])

    checked = [o for o in outcomes if o is not None]
    correct = sum(1 for o in checked if o)
    should_act_outcomes = [o for o, (_, _, expected) in zip(outcomes, cases) if expected]
    should_act_checked = [o for o in should_act_outcomes if o is not None]
    should_act_correct = sum(1 for o in should_act_checked if o)
    print("\n--- result ---")
    print(f"parse failures: {parse_failures}/{len(cases)}")
    print(f"checked (parsed successfully): {len(checked)}/{len(cases)}")
    if checked:
        rate = correct / len(checked)
        print(f"raw agreement (both poles): {correct}/{len(checked)} ({rate:.1%})")
        print("pre-registered threshold: >= 60%")
        print("PASSES" if rate >= 0.60 else "FAILS", "the naive pre-registered bar")
    if should_act_checked:
        sa_rate = should_act_correct / len(should_act_checked)
        print(
            f"\nshould-act subset only: {should_act_correct}/{len(should_act_checked)} ({sa_rate:.1%}) -- "
            "the informative number. The 'should not act' subset scores 100% under a trivial "
            "always-NOTHING policy, so it cannot by itself indicate discrimination; a raw agreement "
            "rate above threshold that is driven entirely by class imbalance is a base-rate "
            "artifact, not a positive signal. Check whether any acting code (1/2/3) was ever "
            "emitted before treating this run as informative."
        )
    print(f"All {len(cases)} trials recorded under experiment {experiment_id}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
