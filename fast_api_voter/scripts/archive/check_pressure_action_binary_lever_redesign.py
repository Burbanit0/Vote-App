"""
scripts/check_pressure_action_binary_lever_redesign.py

Tests §3.1 (binaire-puis-levier) of plan-pressure-action-remediation.md -- the redesign path
prioritized in §2bis since both Etape 0 diagnostics (temperature, menu order) came back null and
this is the candidate most directly motivated by the full elimination chain (position, batch size
1-25, the "0/4 legitimate" sentence all ruled out as sole causes; the leading remaining hypothesis
is the menu's own flat, 5-way, 2-safe-slots STRUCTURE).

Only STAGE 1 (the binary act/don't-act judgment) is built and tested here -- deliberately. The
pre-registered accuracy criterion for this whole workstream (plan-decision-quality-validation.md)
only ever measured act-vs-no-act, never which specific lever (SIGN/LAUNCH/MOBILIZE) -- that stays
this palier's own free-choice research question. Building stage 2 (the lever choice, only reached
if stage 1 says "act") before knowing whether stage 1 itself clears its own bar would be premature
engineering for a question not yet answered.

ISOLATION: this script defines its own local BinaryPressureDecision/BinaryPressureBatch Pydantic
models and prompt builders. Nothing in llm_schemas.py or llm_behavior_engine.py is touched --
exploratory, not production code.

DATA: self_gap and blank_threshold are pure, deterministic functions of citizen data (accountability.
self_gap, Citizen.blank_threshold) -- no LLM needed to construct realistic test inputs. The
officeholder used is cid=5 via declare_candidacy() (design doc §7bis.5: revealed_position pinned
to issue_positions on the deterministic path, zero campaign shift by construction) -- NOT the same
cid=5 instance from the earlier live pilot, whose revealed_position WAS shifted by LLM-driven
campaign_positioning during that run (verified directly: self_gap(cid=87, pilot's real holder) =
0.1777 in the journal vs 0.1648 recomputed against this deterministic holder -- a real, expected
divergence, not an inconsistency, since an unshifted sincere position is more extreme relative to
the electorate than a campaign-moderated one). population_size=190 gives ~70 unambiguous citizens
against this holder, comfortably over the plan's own >=60 floor (§4.1) with margin for decode
failures.

Pre-registered criterion (plan §3.1 + user-selected §4.2 threshold): >=80% agreement with the
deterministic proxy's act-vs-no-act prediction on unambiguous cases (ratio<0.5 or >1.5, same
definition used throughout this workstream) -- below the 90% bar used for VALIDATING a method,
since a remediation candidate only needs to clearly exit the current degenerate state (0/63 acting
codes; 38.1% overall accuracy), not already match the reliability bar of an accepted method.

Usage:
    python fast_api_voter/scripts/check_pressure_action_binary_lever_redesign.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, ConfigDict, Field, ValidationError  # noqa: E402

from api.domain.polity.accountability import self_gap  # noqa: E402
from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import compute_max_tokens  # noqa: E402
from api.domain.polity.llm_client import _THINK_TAG_RE, LlmResponseError, OllamaJsonClient  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

_POPULATION_SIZE = 190
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_SUCCESS_THRESHOLD = 0.80


class BinaryPressureDecision(BaseModel):
    """Stage 1 only -- act vs don't-act, no lever. Mirrors PressureDecision's own field style
    (llm_schemas.py) but deliberately minimal: this tests ONE mechanism (decomposing the choice),
    not a full replacement schema."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the consulted citizen this decision belongs to.")
    will_act: bool = Field(
        ...,
        description=(
            "true = ce citoyen va agir contre l'elu cible (signer une petition, en lancer une, "
            "ou se mobiliser). false = ce citoyen ne va pas agir (rien faire, ou attendre la "
            "prochaine election)."
        ),
    )


class BinaryPressureBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[BinaryPressureDecision] = Field(..., min_length=1)


BINARY_PRESSURE_JSON_SCHEMA = BinaryPressureBatch.model_json_schema()


def decode_binary_pressure_batch(raw: str, expected_cids: list[int]) -> list[BinaryPressureDecision]:
    """Same contract as decode_pressure_batch (llm_client.py): strip <think>, parse, validate,
    enforce exact cid alignment -- a misalignment is a full failure, not a silent partial fix."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc
    try:
        batch = BinaryPressureBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc
    got_cids = [decision.cid for decision in batch.decisions]
    if got_cids != expected_cids:
        raise LlmResponseError(f"batch misaligned: expected cids {expected_cids}, got {got_cids}")
    return batch.decisions


def build_binary_system_prompt() -> str:
    """Deliberately does NOT present the 5-way act menu at all -- the mechanism under test.
    Keeps the same 'inaction is legitimate' reassurance the original prompt has (already shown
    insufficient ALONE in the flat 5-way schema, but held constant here rather than dropped, so
    a result difference can be attributed to the STRUCTURE change, not a second removed variable)."""
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen mecontent recu "
        "(pressure_action), decide UNIQUEMENT s'il va agir contre l'elu cible "
        "ou non -- pas quelle action precise, seulement si oui ou non il agit "
        "-- en te basant sur son propre ecart de mecontentement (ctx).\n"
        "CONTRAINTE ABSOLUE : le champ will_act de CHAQUE decision doit etre "
        "un booleen (true ou false), rien d'autre.\n"
        "Agir (true) signifie : signer une petition, en lancer une, ou se "
        "mobiliser -- n'importe lequel de ces trois choix compte comme agir. "
        "Ne pas agir (false) signifie : rester passif, ou attendre "
        "sciemment la prochaine election plutot que d'agir maintenant.\n"
        "Agir et ne pas agir sont tous deux des resultats legitimes et "
        "journalises, jamais des echecs -- la part des mecontents qui "
        "n'agissent pas est une mesure du modele, pas une erreur a eviter.\n"
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


def build_binary_user_prompt(cid: int, target: int, gap: float, mandate_dev: float, ticks_to_election: int) -> str:
    payload: dict[str, Any] = {
        "consulted": [
            {
                "cid": cid,
                "target": target,
                "ctx": {
                    "self_gap": round(gap, 4),
                    "mandate_dev": round(mandate_dev, 4),
                    "neighbors_acting": None,
                    "ticks_to_election": ticks_to_election,
                },
            }
        ]
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _harvest_unambiguous_citizens(config: Any) -> tuple[Citizen, list[tuple[Citizen, float, bool]]]:
    """Deterministic, no LLM: generate a population, pin a real (unshifted) officeholder via
    declare_candidacy, compute self_gap for everyone else, keep only unambiguous cases."""
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

    system_prompt = build_binary_system_prompt()
    correct = 0
    failures = 0
    per_citizen: dict[int, dict[str, Any]] = {}
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for citizen, gap, expected_act in cases:
            user_prompt = build_binary_user_prompt(
                citizen.citizen_id, holder.citizen_id, gap, _MANDATE_DEV, _TICKS_TO_ELECTION
            )
            try:
                raw = client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_schema=BINARY_PRESSURE_JSON_SCHEMA,
                    max_tokens=compute_max_tokens(1),
                    think=False,
                )
                decision = decode_binary_pressure_batch(raw, [citizen.citizen_id])[0]
                agree = decision.will_act == expected_act
                correct += agree
                per_citizen[citizen.citizen_id] = {
                    "self_gap": gap, "blank_threshold": citizen.blank_threshold,
                    "expected_act": expected_act, "will_act": decision.will_act, "agree": agree,
                }
                print(f"  cid={citizen.citizen_id} expected={expected_act} will_act={decision.will_act} {'AGREE' if agree else 'DISAGREE'}")
            except Exception as exc:  # noqa: BLE001 -- count failures, keep testing the rest
                failures += 1
                per_citizen[citizen.citizen_id] = {
                    "self_gap": gap, "blank_threshold": citizen.blank_threshold,
                    "expected_act": expected_act, "will_act": None, "agree": None,
                }
                print(f"  cid={citizen.citizen_id} FAILED: {exc}")
                continue

    out_path = Path(__file__).with_name("check_pressure_action_binary_lever_redesign_results.json")
    out_path.write_text(json.dumps(per_citizen, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nper-citizen results written to {out_path}")

    checked = len(cases) - failures
    rate = correct / checked if checked else float("nan")
    print("\n--- result ---")
    print(f"checked: {checked}/{len(cases)} ({failures} decode failures)")
    print(f"agreement with deterministic proxy (act-vs-no-act): {correct}/{checked} ({rate:.1%})")
    print(f"pre-registered success threshold: >= {_SUCCESS_THRESHOLD:.0%}")

    print("\n--- verdict ---")
    if checked == 0:
        print("No usable results -- cannot conclude.")
    elif rate >= _SUCCESS_THRESHOLD:
        print(
            f"PASSES the pre-registered {_SUCCESS_THRESHOLD:.0%} bar -> binary-then-lever clears "
            "its own criterion in isolation. Real signal, not a full validation (stage 2/lever "
            "choice still unbuilt, single holder, single config) -- next step per the plan's own "
            "protocol (§4.3) would be deciding whether to build stage 2 or seek a second "
            "confirmatory sample before treating this as settled."
        )
    else:
        print(
            f"FAILS the pre-registered {_SUCCESS_THRESHOLD:.0%} bar ({rate:.1%}) -> decomposing "
            "the choice into two stages did not, on its own, fix the collapse. Per the plan's own "
            "protocol (§4.3), this is real information: it weakens the 'menu structure' hypothesis "
            "and should redirect priority toward §3.2 (output format) or §3.3 (few-shot anchoring) "
            "with a stronger argument than an a priori guess, not toward combining §3.1 with "
            "another path blindly."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
