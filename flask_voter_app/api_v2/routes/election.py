"""
api_v2/routes/election.py — FastAPI routes for the Election Lab.

Phase 2 coverage:
    POST /api/v2/election/simulate

Phase 3 batch 1 (this file):
    POST /api/v2/election/combined-effects
    POST /api/v2/election/campaign-sensitivity

Each route follows the same template:
    1. Validate input via existing Pydantic schemas (app/schemas/election.py).
    2. Hand the dict to the appropriate domain function via asyncio.to_thread
       (compute-bound code released from the event loop, no eventlet anywhere).
    3. Format the (body, status) tuple as a typed response or HTTPException.

Backend layering (top to bottom):
    routes (this file)            ─── HTTP adapter: validate + call service
        ↓
    api_v2.domain.election        ─── pure-Python compute (no Flask/FastAPI/DB)
        ↓
    app.utils.simulation_*        ─── primitives (voting methods, electorate, ...)
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# Re-uses the Pydantic models defined in Phase 1. Single source of truth
# shared with the Flask side via the openapi-typescript pipeline.
from app.schemas import (
    AbstentionRequest,
    AbstentionResponse,
    AffectivePolarizationRequest,
    BallotComplexityRequest,
    BehavioralBiasesRequest,
    CampaignSensitivityRequest,
    CampaignSensitivityResponse,
    CascadeRequest,
    ChoiceOverloadRequest,
    CoalitionRequest,
    CoalitionResponse,
    CombinedEffectsRequest,
    CombinedEffectsResponse,
    CompulsoryVotingRequest,
    DeliberationRequest,
    DemographicTurnoutRequest,
    ElectoralFatigueRequest,
    HotellingRequest,
    JuryRequest,
    NotaRequest,
    PartyDynamicsRequest,
    PolarizationRequest,
    ShyVoterRequest,
    SimulateRequest,
    SimulateResponse,
    SortitionRequest,
)

from api_v2.domain.election import (
    abstention as abstention_domain,
    affective_polarization as affective_polarization_domain,
    ballot_complexity as ballot_complexity_domain,
    behavioral_biases as behavioral_biases_domain,
    campaign_sensitivity as campaign_sensitivity_domain,
    cascade as cascade_domain,
    choice_overload as choice_overload_domain,
    coalition as coalition_domain,
    combined_effects as combined_effects_domain,
    compulsory_voting as compulsory_voting_domain,
    deliberation as deliberation_domain,
    demographic_turnout as demographic_turnout_domain,
    electoral_fatigue as electoral_fatigue_domain,
    hotelling as hotelling_domain,
    jury as jury_domain,
    nota as nota_domain,
    party_dynamics as party_dynamics_domain,
    polarization as polarization_domain,
    shy_voter as shy_voter_domain,
    simulate as simulate_domain,
    sortition as sortition_domain,
)

router = APIRouter(prefix="/api/v2/election", tags=["election"])


# ── Shared helper ───────────────────────────────────────────────────────────

async def _run_typed(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
    response_model: type[BaseModel],
) -> BaseModel:
    """Run a domain compute function in a worker thread and adapt its
    (body, status) contract to FastAPI's exception-based error model.

    - 200 → parse body through `response_model` and return it.
    - 400 → raise HTTPException(400) (domain-level validation, distinct from
            Pydantic 422 which fires BEFORE the worker is even called).
    - other → raise HTTPException(500).
    """
    body, status_code = await asyncio.to_thread(domain_fn, request.model_dump())
    if status_code == 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=body.get("error", "Bad request"),
        )
    if status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=body.get("error", "Internal error"),
        )
    return response_model.model_validate(body)


async def _run_passthrough(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
) -> Dict[str, Any]:
    """Like _run_typed but returns the body dict unchanged (no response_model).

    Used for endpoints where the response shape is large, loosely-typed, or
    not worth pinning down (typical of Perturber endpoints with curves
    and method-comparison dicts). The frontend keeps its own TypeScript
    interface for the response.
    """
    body, status_code = await asyncio.to_thread(domain_fn, request.model_dump())
    if status_code == 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=body.get("error", "Bad request"),
        )
    if status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=body.get("error", "Internal error"),
        )
    return body


# ── /simulate ───────────────────────────────────────────────────────────────

@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="Run the unified election simulation",
    response_description="Simulation result with all 17 voting methods, "
                         "Condorcet winner, blank rate, and inter-method agreement.",
)
async def simulate_endpoint(request: SimulateRequest) -> SimulateResponse:
    """Pure-compute election. Same seed = same result.

    The heavy simulation runs in a real OS thread (`asyncio.to_thread`)
    so it doesn't block the FastAPI event loop. That replaces the
    `eventlet.tpool.execute(...)` pattern from the Flask side — no more
    eventlet anywhere on the v2 path.
    """
    return await _run_typed(simulate_domain, request, SimulateResponse)


# ── /combined-effects ───────────────────────────────────────────────────────

@router.post(
    "/combined-effects",
    response_model=CombinedEffectsResponse,
    summary="2³ factorial — isolate each model's contribution to divergence",
    response_description="One row per combination (blank × campaign × info), "
                         "plus per-factor agreement delta and disruptive ranking.",
)
async def combined_effects_endpoint(
    request: CombinedEffectsRequest,
) -> CombinedEffectsResponse:
    """8 simulations on the same electorate, with each model factor toggled
    independently. Identifies which factor disrupts inter-method agreement
    the most. Heaviest single endpoint (8 × full election pipeline)."""
    return await _run_typed(
        combined_effects_domain, request, CombinedEffectsResponse,
    )


# ── /campaign-sensitivity ───────────────────────────────────────────────────

@router.post(
    "/campaign-sensitivity",
    response_model=CampaignSensitivityResponse,
    summary="Snapshot the election at multiple campaign days",
    response_description="Per-method stability score over the campaign timeline.",
)
async def campaign_sensitivity_endpoint(
    request: CampaignSensitivityRequest,
) -> CampaignSensitivityResponse:
    """Runs the same electorate at multiple campaign snapshots (days 0, 7,
    14, 21, 28, 'final' by default) to measure how each voting method's
    winner changes over the campaign."""
    return await _run_typed(
        campaign_sensitivity_domain, request, CampaignSensitivityResponse,
    )


# ── /coalition ──────────────────────────────────────────────────────────────

@router.post(
    "/coalition",
    response_model=CoalitionResponse,
    summary="Per-method D'Hondt + greedy coalition formation",
    response_description="One coalition analysis per voting method, with "
                         "coalition_spread (ideological variance) and "
                         "most_centrist / most_divergent method rankings.",
)
async def coalition_endpoint(request: CoalitionRequest) -> CoalitionResponse:
    """For each voting method, allocates `total_seats` proportionally via
    D'Hondt then greedily picks the smallest ideologically-coherent
    coalition that crosses `government_threshold * total_seats`."""
    return await _run_typed(coalition_domain, request, CoalitionResponse)


# ── /abstention ─────────────────────────────────────────────────────────────

@router.post(
    "/abstention",
    response_model=AbstentionResponse,
    summary="Iterated abstention model with poll feedback",
    response_description="Round-by-round turnout, vote shares, and winner. "
                         "Includes per-method comparison (sincere vs final) "
                         "so the Lab matrix can show how abstention shifts "
                         "winners across all methods.",
)
async def abstention_endpoint(request: AbstentionRequest) -> AbstentionResponse:
    """Round 0 is sincere. From round 1 onwards, voters whose preferred
    candidate is trailing in the previous round's polls abstain with
    probability ∝ demobilization_factor × poll_influence."""
    return await _run_typed(abstention_domain, request, AbstentionResponse)


# ── Perturber endpoints (Phase 3 batch 3) ──────────────────────────────────
# Responses are passed through as dicts — the frontend has its own
# TypeScript interfaces and the worker outputs are large compound shapes
# (curves, per-method comparisons) not worth pinning to Pydantic models.

@router.post(
    "/nota",
    summary="NOTA (None Of The Above) as a ballot option",
    response_description=(
        "Sincere winner, NOTA percentage, election validity per the "
        "constitutional rule, NOTA-vs-threshold curve, and a "
        "per-method comparison of NOTA inclusiveness."
    ),
)
async def nota_endpoint(request: NotaRequest) -> Dict[str, Any]:
    """A voter casts NOTA when their max-utility for any candidate is below
    nota_threshold. Three constitutional outcomes after NOTA wins:
    `invalidate` (null election), `runoff` (new candidates), or
    `winner_take_all` (seat NOTA, Nevada-style)."""
    return await _run_passthrough(nota_domain, request)


@router.post(
    "/ballot-complexity",
    summary="Null-vote rate per method as a function of ballot complexity",
    response_description=(
        "Per-method null rate, winner with and without nulls, and a "
        "curve of null rate as the candidate count grows."
    ),
)
async def ballot_complexity_endpoint(
    request: BallotComplexityRequest,
) -> Dict[str, Any]:
    """P(null | method) = error_base × candidate_factor × education_factor
    × first_time_voter_factor. Complex ballots (Schulze, IRV) exclude
    more voters than simple ones (Plurality)."""
    return await _run_passthrough(ballot_complexity_domain, request)


@router.post(
    "/shy-voter",
    summary="Bradley / Shy Tory effect — socially-sensitive candidates underpolled",
    response_description=(
        "Real vs polled winner, systematic poll error, and a "
        "social-desirability-vs-systematic-error curve."
    ),
)
async def shy_voter_endpoint(request: ShyVoterRequest) -> Dict[str, Any]:
    """Voters intending to vote for the 'sensitive' candidate (index
    `shy_candidate_idx`) declare a more acceptable preference in polls
    with probability `social_desirability_factor`, but vote sincerely
    in the booth."""
    return await _run_passthrough(shy_voter_domain, request)


@router.post(
    "/electoral-fatigue",
    summary="Turnout decay across repeated elections",
    response_description=(
        "Per-election turnout, winner, ideology drift, and a "
        "representation-gap measure of how much the residual electorate "
        "diverges from the full population."
    ),
)
async def electoral_fatigue_endpoint(
    request: ElectoralFatigueRequest,
) -> Dict[str, Any]:
    """P(vote | election k) = max(engaged_voter_pct, 1 - k × fatigue_rate).
    Engaged voters (top engaged_voter_pct by max-utility) always vote;
    casual voters drop out faster each election, shifting the residual
    electorate toward partisans."""
    return await _run_passthrough(electoral_fatigue_domain, request)


# ── Perturber endpoints (Phase 3 batch 4) ──────────────────────────────────

@router.post(
    "/cascade",
    summary="Sequential voting with information cascades",
    response_description="Sincere vs cascade winner, vote sequence with timeline, "
                         "cascade-strength sensitivity curve.",
)
async def cascade_endpoint(request: CascadeRequest) -> Dict[str, Any]:
    """Each voter observes the last `observation_window` votes and may follow
    the public signal instead of their sincere preference with probability
    `cascade_strength`. Bikhchandani, Hirshleifer, Welch (1992)."""
    return await _run_passthrough(cascade_domain, request)


@router.post(
    "/behavioral-biases",
    summary="Expressive voting + bullet voting + primacy effect",
    response_description="Sincere vs biased winner, per-method sensitivity, "
                         "and breakdown of which voters were affected.",
)
async def behavioral_biases_endpoint(
    request: BehavioralBiasesRequest,
) -> Dict[str, Any]:
    """Three empirical biases stacked: expressive voting (Fiorina 1976),
    bullet voting (collapses Approval to Plurality for affected voters),
    primacy effect (Krosnick 1991, first-listed candidate bonus)."""
    return await _run_passthrough(behavioral_biases_domain, request)


@router.post(
    "/choice-overload",
    summary="Heuristics dominate beyond overload_threshold candidates",
    response_description="Per-candidate-count winners, regret curve, "
                         "most/least robust method.",
)
async def choice_overload_endpoint(
    request: ChoiceOverloadRequest,
) -> Dict[str, Any]:
    """Schwartz 2004 paradox of choice: beyond `overload_threshold`
    candidates, voters use heuristics (notoriety / primacy / partisan
    affiliation) instead of their sincere preferences. Compares method
    robustness."""
    return await _run_passthrough(choice_overload_domain, request)


@router.post(
    "/deliberation",
    summary="DeGroot opinion update across a network, then vote",
    response_description="Pre vs post-deliberation winner, opinion convergence "
                         "rate, polarisation change, per-round trace.",
)
async def deliberation_endpoint(request: DeliberationRequest) -> Dict[str, Any]:
    """Voters update their ideology toward a network-weighted mean for
    `deliberation_rounds` rounds, then vote. `network_type` echo_chamber
    amplifies polarisation; bridge / complete reduce it."""
    return await _run_passthrough(deliberation_domain, request)


# ── Perturber endpoints (Phase 3 batch 5) ──────────────────────────────────

@router.post(
    "/jury",
    summary="Condorcet Jury Theorem under N voting methods",
    response_description="Per-method accuracy, theoretical majority-rule accuracy, "
                         "and a competence-curve sensitivity chart.",
)
async def jury_endpoint(request: JuryRequest) -> Dict[str, Any]:
    """Voters with individual competence p > 0.5 aggregate collectively
    toward the 'correct' option. Runs `num_simulations` Monte Carlo
    trials and compares plurality, IRV, Borda, Schulze, MJ on the same
    juries."""
    return await _run_passthrough(jury_domain, request)


@router.post(
    "/hotelling",
    summary="Hotelling-Downs iterative best-response (Nash equilibrium)",
    response_description="Iteration-by-iteration candidate positions, "
                         "convergence status, equilibrium type.",
)
async def hotelling_endpoint(request: HotellingRequest) -> Dict[str, Any]:
    """Each candidate iteratively moves in the direction (±x, ±y) that
    maximises their vote score under `method`. Converges when no
    candidate can improve by moving by `step_size`."""
    return await _run_passthrough(hotelling_domain, request)


@router.post(
    "/polarization",
    summary="Per-ideology Esteban-Ray index + voting-method robustness",
    response_description="One result per ideology distribution: ER index, "
                         "Condorcet rate, inter-method agreement, regret by method.",
)
async def polarization_endpoint(request: PolarizationRequest) -> Dict[str, Any]:
    """For each voter distribution in `ideology_range`, computes the
    Esteban-Ray polarisation index and runs `num_simulations` Monte
    Carlo elections to measure how method agreement and Condorcet
    rate degrade with polarisation."""
    return await _run_passthrough(polarization_domain, request)


@router.post(
    "/sortition",
    summary="Elected vs sortition pure vs sortition stratified",
    response_description="Per-method assembly: representativity, diversity, "
                         "decision regret, Gini of representation, Monte Carlo variance.",
)
async def sortition_endpoint(request: SortitionRequest) -> Dict[str, Any]:
    """Compares three assembly-selection methods on the same population:
    elected (electoral bias), sortition pure (random sample), sortition
    stratified (demographically balanced random sample)."""
    return await _run_passthrough(sortition_domain, request)


# ── Perturber endpoints (Phase 3 batch 6) ──────────────────────────────────

@router.post(
    "/affective-polarization",
    summary="Iyengar 2019: in/out-group hostility distorts voting",
    response_description="Sincere vs affective winners, method sensitivity, "
                         "hostility-vs-agreement affect curve.",
)
async def affective_polarization_endpoint(
    request: AffectivePolarizationRequest,
) -> Dict[str, Any]:
    """Voters penalise candidates from the opposing political camp
    proportionally to `affect_hostility`. `camp_threshold` defines the
    x-axis distance for in/out-group splitting."""
    return await _run_passthrough(affective_polarization_domain, request)


@router.post(
    "/demographic-turnout",
    summary="Full population vs effective electorate via age × education gaps",
    response_description="Biased vs corrected winner, representation gap, "
                         "demographic breakdown.",
)
async def demographic_turnout_endpoint(
    request: DemographicTurnoutRequest,
) -> Dict[str, Any]:
    """Distortion between the real electorate and the effective electorate
    driven by differential turnout across demographic groups. The
    `correct_for_turnout` flag toggles the turnout-correction model
    on/off so the user can compare both."""
    return await _run_passthrough(demographic_turnout_domain, request)


@router.post(
    "/compulsory-voting",
    summary="Voluntary vs compulsory voting on the same electorate",
    response_description="Per-system winner, vote shares, null rate, voter "
                         "profile, representation improvement, quality degradation.",
)
async def compulsory_voting_endpoint(
    request: CompulsoryVotingRequest,
) -> Dict[str, Any]:
    """Voluntary turnout is right-biased (empirical pattern); compulsory
    elections add reluctant left-leaning voters who may vote null,
    randomly, or sincerely."""
    return await _run_passthrough(compulsory_voting_domain, request)


@router.post(
    "/party-dynamics",
    summary="Multi-election party-system evolution (Duverger's Law)",
    response_description="Per-election parties, effective parties curve, "
                         "final system (bipartite vs multipartite), convergence speed.",
)
async def party_dynamics_endpoint(
    request: PartyDynamicsRequest,
) -> Dict[str, Any]:
    """Parties adapt positions (Hotelling), get eliminated below
    `survival_threshold`, and new parties may emerge. Tactical voting
    squeezes small parties under FPTP, driving the system toward
    bipartism."""
    return await _run_passthrough(party_dynamics_domain, request)
