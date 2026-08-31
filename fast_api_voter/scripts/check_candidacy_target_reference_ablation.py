"""
scripts/check_candidacy_target_reference_ablation.py

Causal test for plan-adversarial-framing-collapse.md's open question: does the collapse pattern
require ADVERSARIAL framing specifically ("contre", "pression"), or does the mere PRESENCE of a
named target/other-party reference in the ctx suffice, regardless of tone?

Takes candidacy_considered -- the one decision type tested so far that does NOT collapse, purely
self-referential (ambition_score, perceived_support, both about the citizen alone) -- and adds
exactly one thing: a neutral, informational reference to the current officeholder in each
citizen's ctx. No adversarial verb, no "against", no pressure framing -- just a fact ("the current
officeholder is citizen X"), the same register ResponseContext/PressureContext use for their own
purely informational fields (mandate_dev is explicitly framed as "information about the
officeholder, not about me").

Same 5 extreme-low-ambition citizens already confirmed correct without any target reference
(check_candidacy_considered_isolation_disposition.py: 5/5 "decline", far below the 0.30
threshold). Same isolation discipline: size=1, think=False, everything else about the prompt
held constant except the one added field.

Pre-registered readings, written before any call:
- If these citizens now "declare" despite near-zero ambition -> the mere PRESENCE of a named
  target suffices, independent of tone. The relational STRUCTURE itself is the risk factor, not
  adversarial wording specifically.
- If they still correctly "decline" -> presence alone is not sufficient. Adversarial/pressure
  framing is the more specific factor, not just having a named other party in context.

ISOLATION: local prompt copy only, build_candidacy_system_prompt/build_candidacy_user_prompt in
llm_behavior_engine.py are never touched.

Usage:
    python fast_api_voter/scripts/check_candidacy_target_reference_ablation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.codebook import CANDIDACY_MOTIF_PROMPT_TABLE  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import compute_max_tokens  # noqa: E402
from api.domain.polity.llm_client import OllamaJsonClient, decode_candidacy_batch  # noqa: E402
from api.domain.polity.llm_schemas import CANDIDACY_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import sympathizer_ratio  # noqa: E402

_POPULATION_SIZE = 190
_TARGET_CIDS = [8, 178, 42, 41, 77]  # same 5 extreme-low-ambition citizens, already confirmed correct without a target reference
_CURRENT_OFFICEHOLDER = 5  # a neutral, real citizen id, unrelated to this citizen's own decision


def _build_system_prompt_with_target(citizens: list[Citizen]) -> str:
    """Same as build_candidacy_system_prompt except one added sentence explaining a new,
    purely informational ctx field -- no adversarial framing, no verb of opposition."""
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide "
        "s'il se presente comme candidat (outcome=1) ou renonce "
        "(outcome=0), a partir de son ambition et du soutien qu'il "
        "percoit.\n"
        "ctx.current_officeholder : l'identifiant du titulaire actuellement "
        "en poste -- une information de contexte factuelle, pas une cible "
        "d'action ni un rival a affronter.\n"
        "Motifs valides (code court obligatoire) :\n"
        f"{CANDIDACY_MOTIF_PROMPT_TABLE}\nIMPORTANT : la liste decisions "
        f"doit contenir EXACTEMENT ces {len(citizens)} cid, chacun une "
        f"seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse "
        "avant de la finaliser : chaque cid de cette liste doit apparaitre "
        "exactement une fois.\nReponds UNIQUEMENT avec un objet JSON "
        "conforme au schema fourni."
    )


def _build_user_prompt_with_target(citizens: list[Citizen], support: dict[int, float], officeholder: int) -> str:
    citizen_blocks = [
        {
            "cid": c.citizen_id,
            "ambition_score": round(c.ambition_score, 4),
            "perceived_support": round(support[c.citizen_id], 4),
            "current_officeholder": officeholder,
        }
        for c in citizens
    ]
    return json.dumps({"citizens": citizen_blocks}, sort_keys=True, separators=(",", ":"))


def main() -> int:
    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    by_id = {c.citizen_id: c for c in population}
    support = {cid: sympathizer_ratio(by_id[cid], population) for cid in _TARGET_CIDS}

    declared = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid in _TARGET_CIDS:
            citizen = by_id[cid]
            raw = client.complete_json(
                system_prompt=_build_system_prompt_with_target([citizen]),
                user_prompt=_build_user_prompt_with_target([citizen], support, _CURRENT_OFFICEHOLDER),
                json_schema=CANDIDACY_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1),
                think=False,
            )
            decision = decode_candidacy_batch(raw, [cid])[0]
            expected = 0
            agree = decision.outcome == expected
            if decision.outcome == 1:
                declared.append(cid)
            print(
                f"cid={cid} ambition_score={citizen.ambition_score:.4f} "
                f"current_officeholder={_CURRENT_OFFICEHOLDER} "
                f"-> outcome={decision.outcome} ({'declare' if decision.outcome == 1 else 'decline'}) "
                f"motif={decision.motif} [{'AGREE' if agree else 'DISAGREE'}]"
            )

    print("\n--- verdict, per the pre-registered readings ---")
    if declared:
        print(
            f"{len(declared)}/{len(_TARGET_CIDS)} extreme-low-ambition citizens 'declared' anyway "
            f"({declared}) despite a purely neutral, informational target reference -> the mere "
            "PRESENCE of a named target suffices, independent of tone. The relational structure "
            "itself is the risk factor, not adversarial wording specifically."
        )
    else:
        print(
            "0 declared -- candidacy_considered stays correct even with a neutral target reference "
            "added -> presence alone is not sufficient. Adversarial/pressure framing is the more "
            "specific factor, not just having a named other party in context."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
