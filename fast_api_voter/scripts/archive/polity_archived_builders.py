"""Prompt builders archived out of llm_behavior_engine.py: no live code calls them.

Each was written for one experiment and is still imported by that experiment's
archived script (check_candidacy_calibration, check_toon_pressure_action_ab,
check_coalition_calibration); the results notes stay in scripts/. Moved verbatim.
Not maintained, not type-checked. Their tests are in test_archived_prompt_builders.py
(pytest scripts/archive/test_archived_prompt_builders.py -o addopts="" runs them).
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import (
    CANDIDACY_MOTIF_PROMPT_TABLE,
    COALITION_ACTION_PROMPT_TABLE,
    COALITION_MOTIF_PROMPT_TABLE,
    PRESSURE_ACT_PROMPT_TABLE,
    PRESSURE_MOTIF_PROMPT_TABLE,
)
from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_behavior_engine import (
    PressureContext,
    menu_acts,
)
from api.domain.polity.llm_toon_encoding import encode_toon_array


def build_candidacy_system_prompt_toon_calibrated(
    citizens: Sequence[Citizen], mean_ambition: float
) -> str:
    """Track B3 (2026-09-11, lets-build-a-solid-spicy-otter.md): C3 for
    dt=2. `candidacy_considered` is not a content-blind collapse like B1/B2
    -- 202/500 (40.4%) declared against a pre-registered bar of <5%, real
    differentiation (64% accuracy against ground truth), just far too
    permissive. `ambition_score` (`citizens.ambition_dist`, shipped
    beta(2,8)) is sent as a bare float in [0,1] with no reference at all --
    `perceived_support` is already self-scaling (a sympathizer_ratio, a
    population fraction by construction), so it is not this fix's target.

    Unlike mandate_dev's exact geometric ceiling (B1) or distance_to_
    initiator's empirical dispersion (B2): ambition_score's distribution
    is not fixed by this module -- `citizens.ambition_dist` is a config
    string (ADR-002, `_parse_beta_params`), so no constant can be
    hardcoded here. `mean_ambition` is computed once by the caller, over
    the SAME `population` used for `support` (decide_candidacies's own
    "never recomputed per-chunk" discipline, so this number cannot drift
    across chunk boundaries either) -- the same empirical-reference shape
    as B2's mean pairwise distance, not a mathematical bound like B1's.

    C4-compliant: states where a score sits relative to the population,
    never what that should mean for the decision -- no threshold, no
    "declare only if above this".

    C3 CALIBRATION ATTEMPTED AND FAILED, verified live 2026-09-11
    (`scripts/check_candidacy_calibration_results.md`): a real p500
    population (`generate_population` against the shipped config,
    unfiltered -- matching `_declare_nominees_llm`'s own call site)
    declared MORE with this prompt (238/500, 47.6%) than the uncalibrated
    baseline (202/500, 40.4%, which reproduces Stage 3's real production
    figure exactly), and LESS accurately against ground truth (58.4% vs
    63.6%). Both are an order of magnitude above the pre-registered <5%
    bar. NOT wired into `decide_candidacies` for this reason -- it still
    calls the uncalibrated `build_candidacy_system_prompt_toon`. Reading:
    stating the population MEAN gives the model a comparison point that
    argues in the wrong direction ("above-average ambition" reads as a
    reason TO run, when real candidacy needs a far rarer combination of
    traits than merely above-average) -- unlike B1's exact geometric
    ceiling, a mean is the wrong reference shape here. See that results
    doc for why an ambition-feedback/cooldown mechanism (the plan's other
    proposed fix) was also ruled out as an answer to this specific bar:
    it can only suppress REPEAT candidacy, and this probe's population
    has no election history to have lost anything from, yet still
    over-declares."""
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide "
        "s'il se presente comme candidat (outcome=1) ou renonce "
        "(outcome=0), a partir de son ambition et du soutien qu'il "
        "percoit.\n"
        "Le message utilisateur n'est PAS du JSON : il utilise le format "
        "TOON. La premiere ligne 'citizens[N]{cid,ambition_score,"
        "perceived_support}:' annonce le nombre d'enregistrements (N) et "
        "l'ordre des champs. Chaque ligne suivante est UN enregistrement, "
        "ses valeurs separees par des virgules, dans cet ordre exact. "
        "Exemple : 'citizens[2]{cid,ambition_score,perceived_support}:\\n"
        "0,0.52,0.31\\n1,0.68,0.44' decrit exactement 2 citoyens : "
        "cid=0 (ambition_score=0.52, perceived_support=0.31) et "
        "cid=1 (ambition_score=0.68, perceived_support=0.44).\n"
        f"ambition_score : intensite personnelle a se presenter -- pour "
        f"reference, l'ambition MOYENNE dans la population actuelle de "
        f"citoyens est d'environ {mean_ambition:.4f}. Ce nombre ne "
        "prescrit aucune decision ; il situe seulement chaque score "
        "individuel par rapport au niveau d'ambition reel de cette "
        "population, plutot que sur l'echelle abstraite [0,1].\n"
        "Motifs valides (code court obligatoire) :\n"
        f"{CANDIDACY_MOTIF_PROMPT_TABLE}\nIMPORTANT : la liste decisions "
        f"doit contenir EXACTEMENT ces {len(citizens)} cid, chacun une "
        f"seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse "
        "avant de la finaliser : chaque cid de cette liste doit apparaitre "
        "exactement une fois.\nReponds UNIQUEMENT avec un objet JSON "
        "conforme au schema fourni."
    )


def build_pressure_system_prompt_toon(
    consulted: Sequence[Citizen], config: PolityConfig
) -> str:
    """plan-llm-protocol-and-theory-program.md §5.E: NOT shipped, NOT wired
    into decide_pressure_actions -- diagnostic-only, same "not wired into
    any decide_* entry point" framing as every §5.C/§5.E primitive this
    session. Output stays JSON (xgrammar/PRESSURE_JSON_SCHEMA, unchanged).

    Pairs with build_pressure_user_prompt_toon's own hoisting: under the
    architecture this project's shipped config actually has (a single
    consulted officeholder per tick, config-derived `available`, no
    social graph), `target`/`mandate_dev`/`ticks_to_election`/`available`
    are call-level facts, not per-citizen ones -- build_pressure_user_
    prompt's own JSON repeats them on every citizen block regardless, but
    that repetition is not information, it is the SAME fact copied N
    times. This system prompt explains the resulting two-section TOON
    shape (a one-row 'call' section for the shared facts, then a
    per-citizen 'pressure' section carrying only what genuinely varies:
    cid and self_gap) with a worked, generic example -- not real values,
    same discipline as build_candidacy_system_prompt_toon's own example.

    Differs from build_pressure_system_prompt ONLY in replacing the ctx-
    field explanations with the TOON-shape explanation covering the same
    facts; the menu constraint, the legal-act table, the motif table, and
    the verbatim expected-cid self-check are unchanged, so a live A/B
    isolates the format change specifically."""
    cid_list = ",".join(str(c.citizen_id) for c in consulted)
    legal = menu_acts(config.pressure_menu)
    legal_table = "\n".join(
        line
        for line in PRESSURE_ACT_PROMPT_TABLE.splitlines()
        if int(line.split(" = ")[0]) in legal
    )
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen mecontent recu "
        "(pressure_action), decide son action envers l'elu cible, en te "
        "basant sur son propre ecart de mecontentement et le menu "
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
        "Le message utilisateur n'est PAS du JSON : il utilise le format "
        "TOON, en DEUX sections. La premiere, 'call[1]{target,mandate_dev,"
        "ticks_to_election}:', donne UNE seule ligne de faits partages par "
        "TOUS les citoyens de cet appel : target (le cid de l'elu cible), "
        "mandate_dev (ecart pondere entre la promesse de l'elu et sa "
        "position actuelle -- une information sur l'elu, pas sur moi), et "
        "ticks_to_election (nombre de ticks avant la prochaine election "
        "presidentielle). La seconde, 'pressure[N]{cid,self_gap}:', donne "
        "N lignes, une par citoyen, chacune son propre cid et son propre "
        "self_gap (ecart pondere entre mes propres positions et la "
        "position actuelle de l'elu cible). Exemple : 'call[1]{target,"
        "mandate_dev,ticks_to_election}:\\n7,0.15,12\\npressure[2]{cid,"
        "self_gap}:\\n0,0.08\\n1,1.42' decrit un appel ou l'elu cible est "
        "le citoyen 7 (mandate_dev=0.15, 12 ticks avant l'election), et "
        "deux citoyens consultes : cid=0 (self_gap=0.08) et cid=1 "
        "(self_gap=1.42).\n"
        "Aucune autre donnee n'est envoyee : aucune petition n'est ouverte "
        "sous ce regime constitutionnel, et aucun voisinage social n'est "
        "suivi dans cette simulation -- n'en deduis rien, ignore ces deux "
        "aspects dans ton raisonnement.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(consulted)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois, et chaque "
        f"act doit appartenir a {list(legal)}.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_pressure_user_prompt_toon(
    consulted: Sequence[Citizen], contexts: Mapping[int, PressureContext]
) -> str:
    """The TOON-encoded twin of build_pressure_user_prompt -- hoists the
    fields that are call-level constants under this project's SHIPPED
    architecture (single consulted officeholder per tick, config-derived
    `available`, no social graph, no open petitions under electoral_only)
    out of the per-citizen rows entirely, into a single one-row 'call'
    section; only `cid`/`self_gap` genuinely vary per citizen and get
    their own 'pressure' rows. See build_pressure_system_prompt_toon's
    own docstring for the full two-section shape this produces and why
    it is not an artifact of any one test's own construction.

    Raises ValueError (never silently drops real information) if any of
    those assumed-constant fields is NOT actually constant across
    `consulted`, or not at the exact shipped-regime value this encoding
    assumes -- a future caller with a genuinely heterogeneous batch (a
    social graph enabled, or an open petition) needs a different
    encoding, not this one silently mis-describing its own input."""
    ctxs = [contexts[c.citizen_id] for c in consulted]
    target, ticks_to_election = _toon_pressure_call_constants(ctxs)
    for ctx in ctxs:
        _check_toon_pressure_context(ctx)
    call_block = encode_toon_array(
        "call",
        ("target", "mandate_dev", "ticks_to_election"),
        [(target, round(ctxs[0].mandate_dev, 4), ticks_to_election)],
    )
    pressure_block = encode_toon_array(
        "pressure",
        ("cid", "self_gap"),
        [(c.citizen_id, round(contexts[c.citizen_id].self_gap, 4)) for c in consulted],
    )
    return f"{call_block}\n{pressure_block}"


def _toon_pressure_call_constants(ctxs: Sequence[PressureContext]) -> tuple[int, int]:
    """(target, ticks_to_election), which the TOON encoding sends once per call."""
    targets = {ctx.target for ctx in ctxs}
    mandate_devs = {ctx.mandate_dev for ctx in ctxs}
    ticks = {ctx.ticks_to_election for ctx in ctxs}
    if len(targets) != 1 or len(mandate_devs) != 1 or len(ticks) != 1:
        raise ValueError(
            "build_pressure_user_prompt_toon assumes target/mandate_dev/ticks_to_election are "
            "call-level constants (true under the shipped architecture: one consulted officeholder "
            "per tick) -- got heterogeneous values across this chunk"
        )
    ticks_to_election = ticks.pop()
    if ticks_to_election is None:
        raise ValueError(
            "build_pressure_user_prompt_toon does not support a null ticks_to_election"
        )
    return targets.pop(), ticks_to_election


def _check_toon_pressure_context(ctx: PressureContext) -> None:
    if ctx.available != (0, 4):
        raise ValueError(
            f"build_pressure_user_prompt_toon assumes the shipped closed menu (0,4), got {ctx.available!r}"
        )
    if (
        ctx.petition_open
        or ctx.already_signed
        or ctx.petition_expires_at_tick is not None
    ):
        raise ValueError(
            "build_pressure_user_prompt_toon assumes no petition is open (shipped electoral_only)"
        )
    if ctx.neighbors_acting is not None:
        raise ValueError(
            "build_pressure_user_prompt_toon assumes neighbors_acting is untracked (shipped default)"
        )


def build_coalition_system_prompt_calibrated(
    responder_party_ids: Sequence[int],
    initiator: int,
    initiator_seats: int,
    total_seats: int,
    majority_seats_threshold: float,
    party_platforms: dict[int, tuple[float, ...]],
    round_number: int = 1,
) -> str:
    """Track B2 (2026-09-11, lets-build-a-solid-spicy-otter.md): C3 for
    dt=9. check_logprob_coalition_action_tracking_results.md measured
    P(action=1, JOIN) staying within 0.965-0.999 across the entire
    join-obvious<->decline-obvious spectrum -- `distance_to_initiator`
    (build_coalition_user_prompt) is sent with no reference at all,
    polity-decision-contracts.md's own dt=9 entry names the gap exactly:
    "distance_to_initiator n'a aucune reference."

    Unlike mandate_dev's exact [0,1] geometric bound (Track B1):
    `distance_to_initiator` is `math.dist` (form_coalition's own UNWEIGHTED
    convention, no priority weighting), whose geometric maximum is
    sqrt(issue_count) -- a real number, but not an informative one, for the
    same reason pressure_action's own calibration work rejected an abstract
    bound in favour of an empirical one: two real citizen-generated
    platforms essentially never land at that theoretical extreme (every
    dimension differing maximally), so stating it would be true but
    useless. polity-decision-contracts.md's own §3 already names the
    better reference: "la distance moyenne entre partis de l'assemblee" --
    an empirical, in-context anchor, the same shape as campaign_
    positioning's own non-collapsing electorate_mean (a population
    reality, not a geometric ceiling).

    Computed here, from `party_platforms` restricted to the SEATED parties
    this call actually knows about (`{initiator} | responder_party_ids` --
    decide_coalition's own `responders = [pid for pid in seated if pid !=
    initiator]` makes this exactly the seated set, never a superset
    including unseated parties who have no bearing on this negotiation).
    One number for the whole call, like mandate_dev/street in Track B1 --
    not a per-responder value, so (like B1) no companion "_calibrated" user
    prompt is needed: build_coalition_user_prompt's existing
    distance_to_initiator values are unchanged, this just gives them a
    scale to be read against."""
    seated_ids = [initiator, *responder_party_ids]
    pairwise_distances = [
        math.dist(party_platforms[a], party_platforms[b])
        for i, a in enumerate(seated_ids)
        for b in seated_ids[i + 1 :]
    ]
    mean_distance = (
        sum(pairwise_distances) / len(pairwise_distances) if pairwise_distances else 0.0
    )
    party_id_list = ",".join(str(pid) for pid in responder_party_ids)
    round_sentence = (
        ""
        if round_number == 1
        else (
            f"Ceci est le tour {round_number} d'une negociation multi-tours : ta reponse au "
            "tour precedent et l'etat provisoire de la coalition te sont rappeles ci-dessous. "
            "Tu peux maintenir ta decision precedente ou en changer, a la lumiere de cet etat.\n"
        )
    )
    return (
        f"Tu es un moteur de simulation. Le parti {initiator} (avec "
        f"{initiator_seats} sieges) vient d'etre designe formateur et "
        "cherche a former une coalition gouvernementale. Pour chaque parti "
        "recu, decide s'il rejoint cette coalition (action=1) ou refuse "
        "(action=2), a partir de sa propre position, de sa proximite avec "
        "le formateur, de son nombre de sieges, et de ce qu'il manque au "
        f"formateur pour la majorite.\n{round_sentence}L'assemblee compte {total_seats} "
        "sieges au total ; la coalition doit depasser strictement "
        f"{majority_seats_threshold} sieges pour atteindre la majorite.\n"
        f"distance_to_initiator (donnee dans le contexte de chaque parti) : distance non "
        "ponderee entre les positions -- la distance MOYENNE entre partis de cette assemblee "
        f"(tous partis sieges confondus, formateur compris) est d'environ {mean_distance:.4f}. "
        "Ce nombre ne prescrit aucune reaction ; il situe seulement chaque distance individuelle "
        "par rapport a la dispersion reelle de cette assemblee.\n"
        f"Actions valides :\n{COALITION_ACTION_PROMPT_TABLE}\nMotifs "
        f"valides (code court obligatoire) :\n{COALITION_MOTIF_PROMPT_TABLE}\n"
        "CONTRAINTE STRICTE : le motif doit correspondre a l'action -- 501 "
        "ou 502 si action=1, 504 ou 505 si action=2. Toute autre "
        "combinaison sera rejetee.\nIMPORTANT : la liste decisions doit "
        f"contenir EXACTEMENT ces {len(responder_party_ids)} party_id, "
        f"chacun une seule fois, dans cet ordre : [{party_id_list}]. "
        "Verifie ta reponse avant de la finaliser : chaque party_id de "
        "cette liste doit apparaitre exactement une fois.\nReponds "
        "UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )
