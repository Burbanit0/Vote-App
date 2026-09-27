"""
scripts/check_pressure_action_order_diagnostic.py

Step 0.2 of plan-pressure-action-remediation.md -- the second cheap diagnostic before committing
to any of the three redesign paths (§3).

Hypothesis: the ORDER the 5 act codes are listed in the prompt's own table (not the citizen's
position in a batch -- already eliminated) could produce a classic primacy/recency effect. Worth
noting before running: the CURRENT production table order is NOTHING(0) first, SIGN(1),
LAUNCH(2), MOBILIZE(3), then WAIT_FOR_ELECTION(4) LAST -- i.e. the two non-acting codes already
bookend the list (first AND last position), with all three acting codes sandwiched in the middle.
That is itself a concrete, testable mechanism for a first/last-position bias toward exactly the
two codes this investigation found the model always picks.

Protocol (fixed before running): replay the same 5 reference cases with the acting codes moved to
the front of the table (SIGN, LAUNCH, MOBILIZE, then NOTHING, WAIT_FOR_ELECTION last) -- flips
which codes hold the primacy/recency positions -- size=1, think=False, temperature=0.0 (unchanged
from production, isolates this ONE variable). Nothing else about the prompt changes: same
CONTRAINTE ABSOLUE line, same "0/4 legitimate" sentence (already shown insufficient alone, but not
removed here either -- only the table order changes), same motif table, same everything else.

Pre-registered criterion:
- If the collapse pattern shifts meaningfully with the reordering -> a primacy/recency effect is
  confirmed, fixable independently and cheaply (a prompt reorder, not a redesign) regardless of
  which of the three bigger redesigns gets prioritized.
- If no change -> ruled out, do not revisit.

Usage:
    python fast_api_voter/scripts/check_pressure_action_order_diagnostic.py
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
# Acting codes first, non-acting last -- the opposite bookend arrangement from production's
# NOTHING-first/WAIT_FOR_ELECTION-last order.
_REORDERED_CODE_SEQUENCE = [1, 2, 3, 0, 4]

_CASES: list[dict[str, int | float | str]] = [
    {"cid": 6, "self_gap": 0.2802, "blank_threshold": 0.0663, "baseline_act": 0, "role": "should-ACT (extreme)"},
    {"cid": 152, "self_gap": 0.3458, "blank_threshold": 0.1064, "baseline_act": 4, "role": "should-ACT (extreme)"},
    {"cid": 270, "self_gap": 0.4825, "blank_threshold": 0.1871, "baseline_act": 4, "role": "should-ACT (extreme)"},
    {"cid": 146, "self_gap": 0.4161, "blank_threshold": 0.1736, "baseline_act": 4, "role": "should-ACT (extreme)"},
    {"cid": 158, "self_gap": 0.086, "blank_threshold": 0.487, "baseline_act": 0, "role": "should-NOT-act (control)"},
]


def _build_reordered_system_prompt(consulted: list[Citizen], config: PolityConfig) -> str:
    """Byte-identical to build_pressure_system_prompt except the act table's line order is
    _REORDERED_CODE_SEQUENCE instead of PressureAct's declaration order. Built from the same
    imported constants as production, only the table's row order changes -- isolates ordering as
    the single variable, per the pre-registered protocol."""
    cid_list = ",".join(str(c.citizen_id) for c in consulted)
    legal = menu_acts(config.pressure_menu)
    lines_by_code = {int(line.split(" = ")[0]): line for line in PRESSURE_ACT_PROMPT_TABLE.splitlines()}
    legal_table = "\n".join(lines_by_code[code] for code in _REORDERED_CODE_SEQUENCE if code in legal)
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
        "0 (ne rien faire) et 4 (attendre la prochaine election) sont des "
        "resultats legitimes et journalises, jamais des echecs -- la part "
        "des mecontents qui n'agissent pas est une mesure du modele, pas "
        "une erreur a eviter.\n"
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
                system_prompt=_build_reordered_system_prompt([citizen], config),
                user_prompt=build_pressure_user_prompt([citizen], {cid: ctx}),
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1),
                think=False,
            )
            decision = decode_pressure_batch(raw, [cid])[0]
            results[cid] = (decision.act, decision.motif)

    print("--- reordered-table results (acting codes first, non-acting last) vs. baseline (production order) ---")
    for case in _CASES:
        cid = int(case["cid"])
        role = str(case["role"])
        baseline_act = int(case["baseline_act"])
        ratio = float(case["self_gap"]) / float(case["blank_threshold"])
        new_act, new_motif = results[cid]
        flip = "FLIPPED to acting" if (new_act in _ACTING_CODES and baseline_act not in _ACTING_CODES) else (
            "FLIPPED to non-acting" if (new_act not in _ACTING_CODES and baseline_act in _ACTING_CODES) else "unchanged"
        )
        print(
            f"cid={cid:>4} [{role}] ratio={ratio:.3f} "
            f"baseline={_ACT_NAMES[baseline_act]} -> reordered={_ACT_NAMES[new_act]} "
            f"(motif={new_motif}) [{flip}]"
        )

    should_act_flips = sum(
        1 for case in _CASES
        if str(case["role"]).startswith("should-ACT")
        and results[int(case["cid"])][0] in _ACTING_CODES
    )
    should_act_total = sum(1 for case in _CASES if str(case["role"]).startswith("should-ACT"))
    control_case = next(case for case in _CASES if "control" in str(case["role"]))
    control_flipped_to_acting = results[int(control_case["cid"])][0] in _ACTING_CODES

    print(f"\nshould-act cases now choosing an acting code: {should_act_flips}/{should_act_total}")
    print(f"control case flipped to acting: {control_flipped_to_acting}")

    print("\n--- verdict, per the pre-registered criterion ---")
    if should_act_flips > 0 or control_flipped_to_acting:
        print(
            "The result moved with reordering -> a primacy/recency effect is confirmed. Fixable "
            "independently and cheaply (deploy the reordered table) regardless of which of the "
            "three bigger redesigns ends up prioritized."
        )
    else:
        print(
            "Zero change -> table order is ruled out as a factor here. Priority goes to the three "
            "redesign paths (binary-then-lever, primary-language + algorithmic translation, "
            "few-shot), not a reordering fix."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
