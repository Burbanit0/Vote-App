"""
scripts/check_pressure_action_primary_language_redesign.py

Tests §3.2 (langage primaire + traduction algorithmique) of plan-pressure-action-remediation.md,
priority raised after §3.1 (binary-then-lever) failed decisively (17/70, 24.3%) and reproduced the
SAME content-blind collapse phenomenon in a new guise (uniform will_act=True instead of uniform
NOTHING/WAIT) -- ruling out "the choice structure/number of stages" as the mechanism. Diagnostic
priority argument for testing this path next (not a preference): if pressure_action collapses
content-blind regardless of how many decision stages it's asked for, the more economical
hypothesis is that DIRECTLY FILLING A STRUCTURED JSON FIELD is itself the common factor -- the
model "completes a slot" rather than articulating a judgment, however many fields/stages that slot
count is split into. §3.2 is the only one of the three redesigns that changes HOW the response is
PRODUCED (a plain-text articulation step, THEN a purely algorithmic translation to a decision --
no second LLM call), not just what is asked.

ISOLATION: local prompt/parser only, nothing in llm_client.py/llm_behavior_engine.py touched. The
model is called via Ollama's native /api/chat endpoint WITHOUT a JSON schema constraint (no
`format` field) -- free-text generation, think=False (still the production decision path), then a
purely algorithmic (regex) parser extracts the decision. No second LLM call anywhere in this
pipeline -- that would violate the project's own standing rule against having an LLM judge an
LLM's own output.

Same scope discipline as §3.1: only the act/no-act judgment is tested (not a lever choice), same
70-citizen dataset construction (self_gap/blank_threshold computed deterministically against a
fresh, unshifted cid=5 officeholder via declare_candidacy -- see check_pressure_action_binary_
lever_redesign.py's own docstring for why this differs from, and does not need to match, the
earlier live pilot's campaign-shifted holder), same size=1/think=False/temperature=0.0 (unchanged
from production -- the temperature diagnostic already ruled that variable out).

Pre-registered criterion (plan §3.2 + user-selected §4.2 threshand old): >=80% agreement with the
deterministic proxy's act-vs-no-act prediction on unambiguous cases (same threshold used for
§3.1, for direct comparability).

Usage:
    python fast_api_voter/scripts/check_pressure_action_primary_language_redesign.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.accountability import self_gap  # noqa: E402
from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_client import (  # noqa: E402
    OllamaJsonClient,
    LlmResponseError,
    _extract_native_content,
    _post_with_transport_retry,
    _THINK_TAG_RE,
)
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

_POPULATION_SIZE = 190
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_SUCCESS_THRESHOLD = 0.80
_MAX_TOKENS = 400  # generous for a one-sentence SITUATION line + two short fields, think=False

_LINE_RE = re.compile(
    r"SITUATION\s*:\s*(?P<situation>.+?)\s*\n\s*"
    r"DECISION\s*:\s*(?P<decision>AGIT|N_AGIT_PAS)\s*\n\s*"
    r"MOTIF\s*:\s*(?P<motif>\S+)",
    re.IGNORECASE | re.DOTALL,
)


def build_primary_language_system_prompt() -> str:
    return (
        "Tu es un moteur de simulation. Pour le citoyen mecontent recu "
        "(pressure_action), decide s'il va agir contre l'elu cible ou non, "
        "en te basant sur son propre ecart de mecontentement (ctx).\n"
        "Articule d'abord la situation en une phrase courte, PUIS donne ta "
        "decision. Reponds EXACTEMENT dans ce format, trois lignes, rien "
        "d'autre avant ou apres :\n"
        "SITUATION: <une phrase libre decrivant la situation du citoyen>\n"
        "DECISION: AGIT ou N_AGIT_PAS\n"
        "MOTIF: <un code court parmi 301, 304, 305, 306>\n"
        "Agir (AGIT) signifie : signer une petition, en lancer une, ou se "
        "mobiliser -- n'importe lequel de ces trois choix compte comme "
        "agir. Ne pas agir (N_AGIT_PAS) signifie : rester passif, ou "
        "attendre sciemment la prochaine election.\n"
        "Agir et ne pas agir sont tous deux des resultats legitimes et "
        "journalises, jamais des echecs -- la part des mecontents qui "
        "n'agissent pas est une mesure du modele, pas une erreur a "
        "eviter.\n"
        "ctx.self_gap : ecart pondere entre mes propres positions et la "
        "position actuelle de l'elu cible.\n"
        "ctx.mandate_dev : ecart pondere entre la promesse de l'elu et sa "
        "position actuelle -- une information sur l'elu, pas sur moi.\n"
        "ctx.neighbors_acting : toujours null dans cette simulation "
        "(aucun graphe social suivi), jamais zero.\n"
        "ctx.ticks_to_election : nombre de ticks avant la prochaine "
        "election presidentielle, null si aucune election prevue.\n"
        "Ne reponds RIEN d'autre que les trois lignes SITUATION/DECISION/"
        "MOTIF."
    )


def build_primary_language_user_prompt(cid: int, target: int, gap: float, mandate_dev: float, ticks_to_election: int) -> str:
    payload = {
        "cid": cid,
        "target": target,
        "ctx": {
            "self_gap": round(gap, 4),
            "mandate_dev": round(mandate_dev, 4),
            "neighbors_acting": None,
            "ticks_to_election": ticks_to_election,
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def complete_plain_text(client: OllamaJsonClient, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    """Native /api/chat, think=False, deliberately WITHOUT a `format` field -- free-text
    generation, not JSON-constrained. Mirrors OllamaJsonClient._complete_json_native_no_think's
    own request shape exactly except this one field, reusing the same transport-retry/content-
    extraction helpers so this test's transport behavior matches production's own."""
    native_base = client._base_url.removesuffix("/v1")  # noqa: SLF001 -- exploratory script, documented reuse
    body = {
        "model": client._model,  # noqa: SLF001
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": client._temperature, "seed": client._seed, "num_predict": max_tokens},  # noqa: SLF001
    }
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    response = _post_with_transport_retry(client._client, f"{native_base}/api/chat", payload)  # noqa: SLF001
    return _extract_native_content(response)


def parse_primary_language_response(raw: str) -> tuple[bool, str, str]:
    """Purely algorithmic (regex) -- no LLM judges this output. Returns (will_act, situation,
    motif). Raises LlmResponseError on any format deviation, same discipline as every
    decode_*_batch function in this project: a malformed response is a full failure, not a
    silently-patched partial one."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    match = _LINE_RE.search(stripped)
    if not match:
        raise LlmResponseError(f"response did not match the required SITUATION/DECISION/MOTIF format: {raw!r}")
    decision = match.group("decision").upper()
    will_act = decision == "AGIT"
    return will_act, match.group("situation").strip(), match.group("motif").strip()


def _harvest_unambiguous_citizens(config: PolityConfig) -> tuple[Citizen, list[tuple[Citizen, float, bool]]]:
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    holder = next(c for c in population if c.citizen_id == 5)
    declare_candidacy(holder)
    cases = []
    for citizen in population:
        if citizen.citizen_id == holder.citizen_id or citizen.blank_threshold <= 0:
            continue
        gap = self_gap(citizen, holder)
        ratio = gap / citizen.blank_threshold
        if ratio < 0.5:
            cases.append((citizen, gap, False))
        elif ratio > 1.5:
            cases.append((citizen, gap, True))
    return holder, cases


def main() -> int:
    config = load_config()
    holder, cases = _harvest_unambiguous_citizens(config)
    print(f"harvested {len(cases)} unambiguous citizens (population_size={_POPULATION_SIZE}, holder=cid{holder.citizen_id})")
    if len(cases) < 60:
        print(f"WARNING: below the plan's own >=60 floor (§4.1) -- got {len(cases)}")

    system_prompt = build_primary_language_system_prompt()
    correct = 0
    failures = 0
    per_citizen: dict[int, dict] = {}
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for citizen, gap, expected_act in cases:
            user_prompt = build_primary_language_user_prompt(
                citizen.citizen_id, holder.citizen_id, gap, _MANDATE_DEV, _TICKS_TO_ELECTION
            )
            try:
                raw = complete_plain_text(client, system_prompt, user_prompt, _MAX_TOKENS)
                will_act, situation, motif = parse_primary_language_response(raw)
                agree = will_act == expected_act
                correct += agree
                per_citizen[citizen.citizen_id] = {
                    "self_gap": gap, "blank_threshold": citizen.blank_threshold,
                    "expected_act": expected_act, "will_act": will_act, "agree": agree,
                    "situation": situation, "motif": motif,
                }
                print(f"  cid={citizen.citizen_id} expected={expected_act} will_act={will_act} {'AGREE' if agree else 'DISAGREE'}")
            except Exception as exc:  # noqa: BLE001 -- count failures, keep testing the rest
                failures += 1
                per_citizen[citizen.citizen_id] = {
                    "self_gap": gap, "blank_threshold": citizen.blank_threshold,
                    "expected_act": expected_act, "will_act": None, "agree": None,
                }
                print(f"  cid={citizen.citizen_id} FAILED: {exc}")
                continue

    out_path = Path(__file__).with_name("check_pressure_action_primary_language_redesign_results.json")
    out_path.write_text(json.dumps(per_citizen, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nper-citizen results written to {out_path}")

    checked = len(cases) - failures
    rate = correct / checked if checked else float("nan")
    print("\n--- result ---")
    print(f"checked: {checked}/{len(cases)} ({failures} parse failures)")
    print(f"agreement with deterministic proxy (act-vs-no-act): {correct}/{checked} ({rate:.1%})")
    print(f"pre-registered success threshold: >= {_SUCCESS_THRESHOLD:.0%}")

    print("\n--- verdict ---")
    if checked == 0:
        print("No usable results -- cannot conclude.")
    elif rate >= _SUCCESS_THRESHOLD:
        print(
            f"PASSES the pre-registered {_SUCCESS_THRESHOLD:.0%} bar -> the primary-language + "
            "algorithmic-translation mechanism shows a real effect. Direct-JSON-slot-filling is "
            "supported as (at least) a contributing factor -- worth a confirmatory second sample "
            "before treating as settled, per the plan's own anti-fishing discipline (§4.4)."
        )
    else:
        print(
            f"FAILS the pre-registered {_SUCCESS_THRESHOLD:.0%} bar ({rate:.1%}) -> changing the "
            "output mechanism (free text + algorithmic parse) did not fix the collapse either. "
            "Combined with §3.1's failure, this weakens both 'choice structure' and 'direct JSON "
            "slot-filling' as sole causes, leaving §3.3 (few-shot anchoring) as the remaining "
            "untested candidate that touches neither the structure nor the output format."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
