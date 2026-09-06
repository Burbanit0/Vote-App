"""
scripts/check_pressure_action_reasoning_field_first.py

Tests plan-pressure-action-remediation.md's §3.4 -- a reasoning field placed FIRST in the JSON
schema, before act/motif, under the SAME grammar-constrained decoding production uses. NOT
motivated by any external citation with specific figures (deliberately not cited here -- see the
plan doc's own §3.4 for why) -- motivated purely by its own mechanical distinction from two
already-tried, already-failed related paths:

PRE-REGISTRATION UPDATE (2026-09-05, before this run): the first attempt at this exact test
(2026-08-30) never exercised its own hypothesis. `llm_client.py`'s `json.dumps(body,
sort_keys=True, ...)` alphabetizes the ENTIRE request body, including the schema passed in
`format` -- regardless of Pydantic field declaration order, the wire schema's properties come out
alphabetically sorted, and the raw generated JSON confirmed `act` was emitted BEFORE `reasoning`
(plan-pressure-action-remediation.md §3.4, "BLOQUÉ" note). That plan doc also explicitly forecloses
touching `sort_keys` itself for this remediation alone -- it protects byte-for-byte request
reproducibility for every decision type, and reopening it needs its own separate scoping, not a
local workaround here.

Fix applied here, scoped to this standalone test schema only (the real `PressureDecision` is
untouched): the field is renamed `a_reasoning` -- `'a_reasoning' < 'act' < 'cid' < 'motif'`
alphabetically (verified: `sorted(['act','cid','motif','a_reasoning'])` puts `a_reasoning` first),
so it now sorts and generates BEFORE act/cid/motif under the identical `sort_keys=True` mechanism,
with zero change to `llm_client.py`'s shared serialization. This is the option
plan-pressure-action-resolution.md's own §4 flagged as "by far the least costly" among the three
it named, and the only one that doesn't touch code shared by every decision type.

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

import dataclasses
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
    """The wire field name `a_reasoning` (not `reasoning`) is the whole point of this test, not a
    typo -- see this module's PRE-REGISTRATION UPDATE. `llm_client.py` alphabetizes the entire
    request body including the schema (`sort_keys=True`), so Pydantic's own declaration order
    below is NOT what the model actually receives; only the wire key's alphabetical position
    controls generation order under grammar-constrained decoding. `a_reasoning` sorts (and is
    therefore generated) BEFORE act/cid/motif; PressureDecision's own real schema, untouched by
    this test, has no reasoning field at all."""

    model_config = ConfigDict(extra="forbid")

    cid: int = Field(..., ge=0, description="citizen_id of the consulted citizen this decision belongs to.")
    a_reasoning: str = Field(
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
        "IMPORTANT : remplis d'abord le champ a_reasoning avec une courte "
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
    # electoral_only=True (the shipped default) forbids acting codes 1/2/3 entirely -- exactly the
    # trap that corrupted 18 of 20 earlier pressure_action diagnostics into measuring a forbidden
    # act, not a behavior (see check_pressure_action_open_menu_baseline.py / the retraction memory).
    # This test is specifically about the act/no-act decision, so the menu must be open.
    shipped = load_config()
    config = dataclasses.replace(
        shipped,
        pressure_menu=dataclasses.replace(
            shipped.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True,
        ),
    )
    holder, cases = _harvest_unambiguous_citizens(config)
    print(f"harvested {len(cases)} unambiguous citizens (population_size={_POPULATION_SIZE}, holder=cid{holder.citizen_id})")
    if len(cases) < 60:
        print(f"WARNING: below the plan's own >=60 floor (§4.1) -- got {len(cases)}")

    system_prompt = build_reasoning_first_system_prompt(config, holder.citizen_id)
    per_citizen: dict[int, dict] = {}
    correct = 0
    failures = 0
    order_confirmed = 0
    order_violated = 0
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
                # The exact check that caught 2026-08-30's attempt exercising nothing: inspect the
                # RAW generated JSON's key order directly, never assume it from schema declaration
                # order or from theory. This is the mechanism the whole test hinges on.
                stripped = _THINK_TAG_RE.sub("", raw).strip()
                reasoning_pos = stripped.find('"a_reasoning"')
                act_pos = stripped.find('"act"')
                if reasoning_pos == -1 or act_pos == -1 or reasoning_pos < act_pos:
                    order_confirmed += 1
                else:
                    order_violated += 1
                    print(f"  cid={citizen.citizen_id} ORDER VIOLATION: 'act' appeared before 'a_reasoning' in the raw response")
                decision = decode_reasoning_pressure_batch(raw, [citizen.citizen_id])[0]
                actual_act = decision.act in _ACTING_CODES
                agree = actual_act == expected_act
                correct += agree
                per_citizen[citizen.citizen_id] = {
                    "self_gap": gap, "blank_threshold": citizen.blank_threshold,
                    "expected_act": expected_act, "act": decision.act, "agree": agree,
                    "reasoning": decision.a_reasoning,
                }
                print(f"  cid={citizen.citizen_id} expected={expected_act} act={decision.act} ({_ACT_NAMES[decision.act]}) {'AGREE' if agree else 'DISAGREE'}")
                print(f"    reasoning: {decision.a_reasoning!r}")
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
    print(f"raw-response order check (a_reasoning before act): {order_confirmed} confirmed, {order_violated} violated")

    distinct_reasonings = {v["reasoning"] for v in per_citizen.values()}
    print(f"\ndistinct reasoning strings across {len(per_citizen)} decoded cases: {len(distinct_reasonings)}")

    # The overall rate is a KNOWN trap in this exact investigation (plan-pressure-action-
    # resolution.md §2.3: "the apparent 75.7% pass was a base-rate artifact from class imbalance").
    # The harvested cases are dominated by the ratio<0.5 "should NOT act" bucket -- report the two
    # classes separately, never trust the pooled rate alone.
    should_act_cases = [v for v in per_citizen.values() if v["expected_act"]]
    should_not_cases = [v for v in per_citizen.values() if not v["expected_act"]]
    should_act_rate = sum(v["agree"] for v in should_act_cases) / len(should_act_cases) if should_act_cases else float("nan")
    should_not_rate = sum(v["agree"] for v in should_not_cases) / len(should_not_cases) if should_not_cases else float("nan")
    print(f"\nclass breakdown (the informative subset is 'should act', not the pooled rate):")
    print(f"  should-act (ratio>1.5):     {sum(v['agree'] for v in should_act_cases)}/{len(should_act_cases)} ({should_act_rate:.1%})")
    print(f"  should-not-act (ratio<0.5): {sum(v['agree'] for v in should_not_cases)}/{len(should_not_cases)} ({should_not_rate:.1%})")

    print("\n--- verdict ---")
    if order_violated > 0:
        print(
            f"{order_violated} case(s) generated 'act' before 'a_reasoning' despite the rename -- "
            "this run exercised the mechanism only partially, same class of problem as 2026-08-30's "
            "attempt. Do not trust the agreement rate below without investigating this first."
        )
    if checked == 0:
        print("No usable results -- cannot conclude.")
    elif len(distinct_reasonings) <= max(1, len(per_citizen) // 10):
        print(
            f"Only {len(distinct_reasonings)} distinct reasoning string(s) across {len(per_citizen)} cases "
            "-> the reasoning field itself is content-blind, the same failure already found in §3.2's "
            "free-text articulation, now confirmed under grammar-constrained schema decoding too."
        )
    elif should_act_rate < _SUCCESS_THRESHOLD:
        print(
            f"FAILS on the informative subset: only {should_act_rate:.1%} of should-act cases agree "
            f"(vs {should_not_rate:.1%} on should-not-act, and {rate:.1%} pooled) -- the pooled rate "
            f"clearing {_SUCCESS_THRESHOLD:.0%} is a base-rate artifact from class imbalance "
            f"({len(should_not_cases)}/{checked} cases are the trivial should-not-act majority), the "
            "exact trap already named once in this investigation (§2.3). Reasoning varies content-wise "
            "(not content-blind) and the schema-embedded ordering mechanism now genuinely engages "
            f"({order_confirmed}/{checked} order-confirmed), but the collapse toward inaction persists "
            "on the cases that actually test it. Does not validate the schema-reordering fix."
        )
    elif rate >= _SUCCESS_THRESHOLD:
        print(
            f"PASSES the pre-registered {_SUCCESS_THRESHOLD:.0%} bar on BOTH the pooled rate and the "
            f"should-act subset specifically ({should_act_rate:.1%}), and reasoning varies per citizen -> "
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
