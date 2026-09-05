"""
scripts/check_pressure_action_prompt_ablation.py

Seventh follow-up to the chunk-collapse finding (reasoning_budget_and_decision_quality_findings.md).
Pre-registration for this test is written in the findings doc BEFORE this script was run --
isolation guarantee, both-direction predictions, the 4/1 case selection, and why baselines are
reused rather than re-measured. Read that section before reading these results.

This is a CAUSAL test, not a passive observation like every prior probe in this workstream: it
builds an ABLATED copy of build_pressure_system_prompt (llm_behavior_engine.py) with exactly one
sentence removed -- "0 (ne rien faire) et 4 (attendre la prochaine election) sont des resultats
legitimes et journalises, jamais des echecs..." -- and nothing else, then re-runs the same size=1,
think=False (production path) calls already measured with the real prompt.

ISOLATION: this function is a local copy, built from the SAME imported constants
(PRESSURE_ACT_PROMPT_TABLE, PRESSURE_MOTIF_PROMPT_TABLE, menu_acts) the real
build_pressure_system_prompt uses, so it stays byte-identical to production except for the one
removed sentence. llm_behavior_engine.py itself is never edited by this script. This is a
parallel, in-memory prompt string passed directly to the client -- no file used by any production
or in-progress run is touched.

Usage:
    python fast_api_voter/scripts/check_pressure_action_prompt_ablation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.codebook import PRESSURE_ACT_PROMPT_TABLE, PRESSURE_MOTIF_PROMPT_TABLE  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_user_prompt,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_ACTING_CODES = {1, 2, 3}
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}

# 4 extreme "should act" cases + 1 extreme "should NOT act" control, all already measured at
# size=1/think=False with the REAL prompt in check_pressure_action_size_one.py -- baselines
# reused, not re-run (see the pre-registration's point on single-call determinism).
_CASES: list[dict[str, int | float | str]] = [
    {"cid": 6, "self_gap": 0.2802, "blank_threshold": 0.0663, "baseline_act": 0, "role": "extreme SHOULD-ACT"},
    {"cid": 152, "self_gap": 0.3458, "blank_threshold": 0.1064, "baseline_act": 4, "role": "extreme SHOULD-ACT"},
    {"cid": 270, "self_gap": 0.4825, "blank_threshold": 0.1871, "baseline_act": 4, "role": "extreme SHOULD-ACT"},
    {"cid": 146, "self_gap": 0.4161, "blank_threshold": 0.1736, "baseline_act": 4, "role": "extreme SHOULD-ACT"},
    {"cid": 158, "self_gap": 0.086, "blank_threshold": 0.487, "baseline_act": 0, "role": "extreme SHOULD-NOT-ACT (control)"},
]


def _build_ablated_system_prompt(consulted: list[Citizen], config: PolityConfig) -> str:
    """Byte-identical to build_pressure_system_prompt except the one sentence
    ("0 (ne rien faire) et 4 (attendre la prochaine election) sont des resultats legitimes...")
    is removed. Built from the same imported constants as the real function, not hand-copied
    text, so it cannot silently drift from production in any OTHER way."""
    cid_list = ",".join(str(c.citizen_id) for c in consulted)
    legal = menu_acts(config.pressure_menu)
    legal_table = "\n".join(
        line for line in PRESSURE_ACT_PROMPT_TABLE.splitlines() if int(line.split(" = ")[0]) in legal
    )
    if config.social_graph.enabled:
        neighbors_acting_line = (
            "ctx.neighbors_acting : proportion (0 a 1) de mon voisinage "
            "social qui a deja mobilise contre cette meme cible, au tick "
            "precedent. Le motif 306 (FOLLOWING_NEIGHBORS) est approprie "
            "pour un act 1, 2 ou 3 motive par ce signal -- jamais pour "
            "act 0 ou 4.\n"
        )
    else:
        neighbors_acting_line = (
            "ctx.neighbors_acting : toujours null dans cette simulation (aucun "
            "graphe social suivi), jamais zero.\n"
        )
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen mecontent recu "
        "(pressure_action), decide son action envers l'elu cible, en te "
        "basant sur son propre ecart de mecontentement (ctx) et le menu "
        "constitutionnel actif.\n"
        f"CONTRAINTE ABSOLUE : le champ act de CHAQUE decision doit valoir "
        f"UN DES CODES SUIVANTS, et aucun autre : {list(legal)}. Tout autre "
        "code invalide le batch entier.\n"
        f"act (les seuls codes autorises ce tick) :\n{legal_table}\n"
        # -- ABLATED: the "0/4 sont des resultats legitimes, jamais des echecs" sentence removed here --
        f"Motifs valides (code court obligatoire) :\n{PRESSURE_MOTIF_PROMPT_TABLE}\n"
        "ctx.self_gap : ecart pondere entre mes propres positions et la "
        "position actuelle de l'elu cible.\n"
        "ctx.mandate_dev : ecart pondere entre la promesse de l'elu et sa "
        "position actuelle -- une information sur l'elu, pas sur moi.\n"
        f"{neighbors_acting_line}"
        "ctx.ticks_to_election : nombre de ticks avant la prochaine "
        "election presidentielle, null si aucune election prevue.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(consulted)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois, et chaque "
        f"act doit appartenir a {list(legal)}.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def main() -> int:
    config = load_config()
    citizens_by_id = {c.citizen_id: c for c in generate_population(config.citizens, 280, config.run.seed)}

    results: dict[int, tuple[int, int]] = {}
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for case in _CASES:
            cid = int(case["cid"])
            citizen = citizens_by_id[cid]
            ctx = PressureContext(
                cid=cid, target=_TARGET, self_gap=float(case["self_gap"]), mandate_dev=_MANDATE_DEV,
                ticks_to_election=_TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            raw = client.complete_json(
                system_prompt=_build_ablated_system_prompt([citizen], config),
                user_prompt=build_pressure_user_prompt([citizen], {cid: ctx}),
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1),
                think=False,
            )
            decision = decode_pressure_batch(raw, [cid])[0]
            results[cid] = (decision.act, decision.motif)

    print("--- ablation results (line removed) vs. baseline (real prompt, size=1, think=False) ---")
    for case in _CASES:
        cid = int(case["cid"])
        role = str(case["role"])
        baseline_act = int(case["baseline_act"])
        ratio = float(case["self_gap"]) / float(case["blank_threshold"])
        ablated_act, ablated_motif = results[cid]
        baseline_acting = baseline_act in _ACTING_CODES
        ablated_acting = ablated_act in _ACTING_CODES
        flip = "FLIPPED to acting" if (ablated_acting and not baseline_acting) else (
            "FLIPPED to non-acting" if (not ablated_acting and baseline_acting) else "unchanged"
        )
        print(
            f"cid={cid:>4} [{role}] ratio={ratio:.3f} "
            f"baseline={_ACT_NAMES[baseline_act]} -> ablated={_ACT_NAMES[ablated_act]} "
            f"(motif={ablated_motif}) [{flip}]"
        )

    should_act_flips = sum(
        1 for case in _CASES
        if str(case["role"]).startswith("extreme SHOULD-ACT")
        and results[int(case["cid"])][0] in _ACTING_CODES
    )
    should_act_total = sum(1 for case in _CASES if str(case["role"]).startswith("extreme SHOULD-ACT"))
    control_case = next(case for case in _CASES if "control" in str(case["role"]))
    control_flipped_to_acting = results[int(control_case["cid"])][0] in _ACTING_CODES

    print("\n--- verdict ---")
    print(f"should-act cases that flipped to an acting code: {should_act_flips}/{should_act_total}")
    print(f"control (should-NOT-act) case flipped to acting: {control_flipped_to_acting}")
    if should_act_flips == should_act_total and not control_flipped_to_acting:
        print(
            "All should-act cases flipped, control stayed non-acting -> clean, strong support for "
            "the line as a causal factor, with no sign of over-correction on the control case."
        )
    elif should_act_flips > 0:
        print(
            f"Partial flip ({should_act_flips}/{should_act_total}) -> the line is plausibly ONE "
            "contributing factor, not sole cause -- consistent with the pre-registered 'no full "
            "effect does not exonerate' reading, not a clean confirmation either."
        )
    else:
        print(
            "Zero flips -> removing this one line alone did not change behavior on these cases. "
            "Per the pre-registration, this does NOT rule the line out as a contributing factor "
            "interacting with something else in the prompt -- it rules out the line as a SOLE, "
            "sufficient cause when removed in isolation."
        )
    if control_flipped_to_acting:
        print(
            "Control case (should stay non-acting) flipped anyway -> the line was serving a real "
            "suppressive function that any fix will need to replace, not just delete."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
