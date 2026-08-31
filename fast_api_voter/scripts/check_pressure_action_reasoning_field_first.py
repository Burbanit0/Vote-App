"""
scripts/check_pressure_action_reasoning_field_first.py

Tests plan-pressure-action-remediation.md's §3.4 -- a reasoning field placed FIRST in the JSON
schema, before act/motif, under the SAME grammar-constrained decoding production uses. NOT
motivated by any external citation with specific figures (deliberately not cited here -- see the
plan doc's own §3.4 for why) -- motivated purely by its own mechanical distinction from two
already-tried, already-failed related paths:

  1. think=True forced (reasoning_budget_and_decision_quality_findings.md): a FULL, UNCONSTRAINED
     reasoning block before the entire JSON, produced ZERO visible <think> content and collapsed
     to a fixed default (act=4/motif=305) -- a different code path (separate block, not grammar-
     constrained), but a real prior failure of "let it reason before deciding" in a stronger form.
  2. Section 3.2 (primary-language + algorithmic translation): free-text articulation BEFORE the
     decision, parsed externally. The articulation itself was content-blind (near-identical
     boilerplate regardless of the citizen's real ratio) and the decision collapsed identically
     (17/70, 24.3%) -- "reason before deciding" already failed in a form close to this one.

This tests whether the SPECIFIC mechanism matters: a reasoning field inside the JSON schema,
under the identical grammar constraint as act/motif -- neither a separate unconstrained block nor
free text parsed outside the schema. Real production 5-way menu (NOT the binary redesign of
§3.1), real production prompt plus one added sentence asking for a short justification before the
act. Same 70-citizen dataset as §3.1/§3.2 for direct comparability (population_size=190, holder
cid=5 via declare_candidacy, deterministic, no LLM needed to build the test cases).

Pre-registered criterion (same bar as §3.1/§3.2): >=80% agreement with the deterministic proxy on
unambiguous cases. Three distinct readings, not collapsed into a single pass/fail:
  - >=80%: the schema-embedded mechanism is real and actionable.
  - reasoning field itself content-blind (generic text regardless of citizen): same failure as
    §3.2, now confirmed under grammar-constrained decoding too.
  - reasoning varies plausibly but act/motif still collapse: a NEW, distinct signature -- points
    at a translation-from-reasoning-to-decision problem, not a content-blindness problem.

Usage:
    python fast_api_voter/scripts/check_pressure_action_reasoning_field_first.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, ConfigDict, Field, ValidationError  # noqa: E402

from api.domain.polity.accountability import self_gap  # noqa: E402
from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.codebook import PRESSURE_ACT_PROMPT_TABLE, PRESSURE_MOTIF_PROMPT_TABLE  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import compute_max_tokens, menu_acts  # noqa: E402
from api.domain.polity.llm_client import LlmResponseError, OllamaJsonClient, _THINK_TAG_RE  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

_POPULATION_SIZE = 190
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_SUCCESS_THRESHOLD = 0.80
_ACTING_CODES = {1, 2, 3}
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}


class ReasoningPressureDecision(BaseModel):
    """Field declaration order (cid, reasoning, act, motif) is the whole point of this test --
    reasoning is generated BEFORE act/motif under Ollama's grammar-constrained decoding, unlike
    PressureDecision's own real schema, which asks for act/motif with no reasoning field at all."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the consulted citizen this decision belongs to.")
    reasoning: str = Field(
        ..., min_length=1, max_length=400,
        description="Courte justification (1-2 phrases) AVANT de choisir l'acte, basee sur ctx.self_gap et ctx.mandate_dev.",
    )
    act: int = Field(..., ge=0, le=4, description="0=rien, 1=signer, 2=lancer, 3=mobiliser, 4=attendre.")
    motif: int = Field(..., description="Code court obligatoire -- voir PressureMotif.")


class ReasoningPressureBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[ReasoningPressureDecision] = Field(..., min_length=1)


REASONING_PRESSURE_JSON_SCHEMA = ReasoningPressureBatch.model_json_schema()


def decode_reasoning_pressure_batch(raw: str, expected_cids: list[int]) -> list[ReasoningPressureDecision]:
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc
    try:
        batch = ReasoningPressureBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc
    got_cids = [d.cid for d in batch.decisions]
    if got_cids != expected_cids:
        raise LlmResponseError(f"batch misaligned: expected cids {expected_cids}, got {got_cids}")
    return batch.decisions


def build_reasoning_first_system_prompt(config: PolityConfig, target: int) -> str:
    """Real production system prompt (build_pressure_system_prompt) plus exactly one added
    sentence: fill `reasoning` first, briefly, grounded in ctx. Nothing else changed -- same
    CONTRAINTE ABSOLUE line, same act table, same motif table, same '0/4 legitimate' sentence
    (already shown insufficient alone, held constant here rather than removed, same isolation
    discipline as every prior follow-up in this investigation)."""
    legal = menu_acts(config.pressure_menu)
    legal_table = "\n".join(
        line for line in PRESSURE_ACT_PROMPT_TABLE.splitlines() if int(line.split(" = ")[0]) in legal
    )
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen mecontent recu "
        "(pressure_action), decide son action envers l'elu cible, en te "
        "basant sur son propre ecart de mecontentement (ctx) et le menu "
        "constitutionnel actif.\n"
        "IMPORTANT : remplis d'abord le champ reasoning avec une courte "
        "justification (1-2 phrases) basee sur ctx.self_gap et "
        "ctx.mandate_dev, AVANT de choisir act et motif.\n"
        f"CONTRAINTE ABSOLUE : le champ act de CHAQUE decision doit valoir "
        f"UN DES CODES SUIVANTS, et aucun autre : {list(legal)}. Tout autre "
        "code invalide le batch entier.\n"
        f"act (les seuls codes autorises ce tick) :\n{legal_table}\n"
        "0 (ne rien faire) et 4 (attendre la prochaine election) sont des "
        "resultats legitimes et journalises, jamais des echecs -- la part "
        "des mecontents qui n'agissent pas est une mesure du modele, pas "
        "une erreur a eviter.\n"
        f"Motifs valides (code court obligatoire) :\n{PRESSURE_MOTIF_PROMPT_TABLE}\n"
        "ctx.self_gap : ecart pondere entre mes propres positions et la "
        "position actuelle de l'elu cible.\n"
        "ctx.mandate_dev : ecart pondere entre la promesse de l'elu et sa "
        "position actuelle -- une information sur l'elu, pas sur moi.\n"
        "ctx.neighbors_acting : toujours null dans cette simulation (aucun "
        "graphe social suivi), jamais zero.\n"
        "ctx.ticks_to_election : nombre de ticks avant la prochaine "
        "election presidentielle, null si aucune election prevue.\n"
        "IMPORTANT : la liste decisions doit contenir EXACTEMENT 1 cid, "
        "celui du citoyen fourni. Reponds UNIQUEMENT avec un objet JSON "
        "conforme au schema fourni."
    )


def build_reasoning_first_user_prompt(cid: int, target: int, gap: float, mandate_dev: float, ticks_to_election: int) -> str:
    payload = {
        "cid": cid,
        "target": target,
        "ctx": {
            "self_gap": round(gap, 4),
            "mandate_dev": round(mandate_dev, 4),
            "neighbors_acting": None,
            "ticks_to_election": ticks_to_election,
        },
        "available": [0, 1, 2, 3, 4],
        "petition": {"open": False, "expires_at_tick": None, "already_signed": False},
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


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

    system_prompt = build_reasoning_first_system_prompt(config, holder.citizen_id)
    per_citizen: dict[int, dict] = {}
    correct = 0
    failures = 0
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for citizen, gap, expected_act in cases:
            user_prompt = build_reasoning_first_user_prompt(
                citizen.citizen_id, holder.citizen_id, gap, _MANDATE_DEV, _TICKS_TO_ELECTION
            )
            try:
                raw = client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_schema=REASONING_PRESSURE_JSON_SCHEMA,
                    max_tokens=compute_max_tokens(1) + 300,  # headroom for the reasoning field itself
                    think=False,
                )
                decision = decode_reasoning_pressure_batch(raw, [citizen.citizen_id])[0]
                actual_act = decision.act in _ACTING_CODES
                agree = actual_act == expected_act
                correct += agree
                per_citizen[citizen.citizen_id] = {
                    "self_gap": gap, "blank_threshold": citizen.blank_threshold,
                    "expected_act": expected_act, "act": decision.act, "agree": agree,
                    "reasoning": decision.reasoning,
                }
                print(f"  cid={citizen.citizen_id} expected={expected_act} act={decision.act} ({_ACT_NAMES[decision.act]}) {'AGREE' if agree else 'DISAGREE'}")
                print(f"    reasoning: {decision.reasoning!r}")
            except Exception as exc:  # noqa: BLE001 -- count failures, keep testing the rest
                failures += 1
                print(f"  cid={citizen.citizen_id} FAILED: {exc}")
                continue

    out_path = Path(__file__).with_name("check_pressure_action_reasoning_field_first_results.json")
    out_path.write_text(json.dumps(per_citizen, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nper-citizen results written to {out_path}")

    checked = len(cases) - failures
    rate = correct / checked if checked else float("nan")
    print("\n--- result ---")
    print(f"checked: {checked}/{len(cases)} ({failures} decode failures)")
    print(f"agreement with deterministic proxy (act-vs-no-act): {correct}/{checked} ({rate:.1%})")
    print(f"pre-registered success threshold: >= {_SUCCESS_THRESHOLD:.0%}")

    distinct_reasonings = {v["reasoning"] for v in per_citizen.values()}
    print(f"\ndistinct reasoning strings across {len(per_citizen)} decoded cases: {len(distinct_reasonings)}")

    print("\n--- verdict ---")
    if checked == 0:
        print("No usable results -- cannot conclude.")
    elif len(distinct_reasonings) <= max(1, len(per_citizen) // 10):
        print(
            f"Only {len(distinct_reasonings)} distinct reasoning string(s) across {len(per_citizen)} cases "
            "-> the reasoning field itself is content-blind, the same failure already found in §3.2's "
            "free-text articulation, now confirmed under grammar-constrained schema decoding too."
        )
    elif rate >= _SUCCESS_THRESHOLD:
        print(
            f"PASSES the pre-registered {_SUCCESS_THRESHOLD:.0%} bar, and reasoning varies per citizen -> "
            "the schema-embedded mechanism is a real, actionable difference from the two already-failed "
            "reasoning-before-deciding attempts."
        )
    else:
        print(
            f"FAILS the pre-registered {_SUCCESS_THRESHOLD:.0%} bar ({rate:.1%}) despite reasoning varying "
            "plausibly per citizen -> a NEW, distinct signature: the reasoning itself is not content-blind, "
            "but translating it into act/motif still collapses. Points at a reasoning-to-decision problem, "
            "not a content-blindness problem."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
