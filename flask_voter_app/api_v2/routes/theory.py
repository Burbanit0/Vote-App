"""
api_v2/routes/theory.py — FastAPI routes for /api/v2/theory/*.

Phase 4 batch 1: arrow / iia-rate / plott-chaos / judgment-aggregation.

Theory endpoints return TYPED responses (unlike most perturbers in
Phase 3): the frontend pedagogical text depends on stable shapes, and
the schemas are not too large. Deeply heterogeneous sub-objects (axiom
counterexamples, resolution-method dicts) stay `Dict[str, Any]`.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.schemas import (
    AgendaManipulationRequest,
    AgendaManipulationResponse,
    ApportionmentRequest,
    ApportionmentResponse,
    ArrowRequest,
    ArrowResponse,
    AssumptionTestingRequest,
    AssumptionTestingResponse,
    CollectiveWillRequest,
    CollectiveWillResponse,
    DemocraticBacksliddingRequest,
    DemocraticBacksliddingResponse,
    EpistocracyRequest,
    EpistocracyResponse,
    IdentityVotingRequest,
    IdentityVotingResponse,
    IIARateRequest,
    IIARateResponse,
    IntergenerationalRequest,
    IntergenerationalResponse,
    JudgmentAggregationRequest,
    JudgmentAggregationResponse,
    MajorityTyrannyRequest,
    MajorityTyrannyResponse,
    ManipulationAnalysisRequest,
    ManipulationAnalysisResponse,
    PlottChaosRequest,
    PlottChaosResponse,
    SenParadoxRequest,
    SenParadoxResponse,
)

from api_v2.domain.theory import (
    agenda_manipulation as agenda_manipulation_domain,
    apportionment as apportionment_domain,
    arrow as arrow_domain,
    assumption_testing as assumption_testing_domain,
    collective_will as collective_will_domain,
    democratic_backsliding as democratic_backsliding_domain,
    epistocracy as epistocracy_domain,
    identity_voting as identity_voting_domain,
    iia_rate as iia_rate_domain,
    intergenerational as intergenerational_domain,
    judgment_aggregation as judgment_aggregation_domain,
    majority_tyranny as majority_tyranny_domain,
    manipulation_analysis as manipulation_analysis_domain,
    plott_chaos as plott_chaos_domain,
    sen_paradox as sen_paradox_domain,
)

router = APIRouter(prefix="/api/v2/theory", tags=["theory"])


# ── Shared helper ───────────────────────────────────────────────────────────

async def _run_typed(
    domain_fn: Callable[[Dict[str, Any]], tuple[Dict[str, Any], int]],
    request: BaseModel,
    response_model: type[BaseModel],
) -> BaseModel:
    """Adapt (body, status) contract to FastAPI's exception-based model."""
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


# ── /arrow ──────────────────────────────────────────────────────────────────

@router.post(
    "/arrow",
    response_model=ArrowResponse,
    summary="Per-method Arrow axiom violation analysis",
    response_description="Per-axiom violation flag + minimal counterexamples + "
                         "human-readable summary + tradeoff type.",
)
async def arrow_endpoint(request: ArrowRequest) -> ArrowResponse:
    """For a voting method, lists which Arrow axioms it violates with a
    minimal counterexample for each. Pure lookup + boilerplate text;
    `seed` reserved for future randomized counterexamples."""
    return await _run_typed(arrow_domain, request, ArrowResponse)


# ── /iia-rate ───────────────────────────────────────────────────────────────

@router.post(
    "/iia-rate",
    response_model=IIARateResponse,
    summary="Empirical IIA violation rate vs number of candidates",
    response_description="Curve of (n_candidates, violation_rate) for "
                         "n in [2, max_candidates].",
)
async def iia_rate_endpoint(request: IIARateRequest) -> IIARateResponse:
    """Monte-Carlo simulation: for each n, generate `num_trials` random
    profiles, run plurality on the full profile then on the profile
    with one random candidate removed, count winner changes. Other
    methods are scaled from the plurality baseline."""
    return await _run_typed(iia_rate_domain, request, IIARateResponse)


# ── /plott-chaos ────────────────────────────────────────────────────────────

@router.post(
    "/plott-chaos",
    response_model=PlottChaosResponse,
    summary="Plott's Chaos Theorem in 2-D policy space",
    response_description="Condorcet-winner flag, top cycle (Smith set), and "
                         "two BFS paths showing the agenda-setter can reach "
                         "diametrically opposite outcomes from the same start.",
)
async def plott_chaos_endpoint(request: PlottChaosRequest) -> PlottChaosResponse:
    """In ≥2-D policy space with ≥3 voters, a Condorcet winner almost
    never exists, and from any starting point the agenda-setter can
    reach ANY other point via a sequence of majority votes."""
    return await _run_typed(plott_chaos_domain, request, PlottChaosResponse)


# ── /judgment-aggregation ──────────────────────────────────────────────────

@router.post(
    "/judgment-aggregation",
    response_model=JudgmentAggregationResponse,
    summary="Discursive dilemma (List & Pettit 2002)",
    response_description="Per-proposition collective vote + coherence "
                         "diagnosis + premise-based vs conclusion-based "
                         "resolution.",
)
async def judgment_aggregation_endpoint(
    request: JudgmentAggregationRequest,
) -> JudgmentAggregationResponse:
    """Majority rule on propositions can produce collectively incoherent
    results even when every individual voter is perfectly coherent.
    Pre-defined scenarios: legal liability, fiscal trilemma, climate."""
    return await _run_typed(
        judgment_aggregation_domain, request, JudgmentAggregationResponse,
    )


# ── Phase 4 batch 2 ─────────────────────────────────────────────────────────

@router.post(
    "/agenda-manipulation",
    response_model=AgendaManipulationResponse,
    summary="McKelvey-style agenda manipulation under binary elimination",
    response_description="Pairwise matrix + Condorcet winner + every achievable "
                         "outcome over all agenda permutations + manipulation power.",
)
async def agenda_manipulation_endpoint(
    request: AgendaManipulationRequest,
) -> AgendaManipulationResponse:
    """Enumerates all `n!` agendas for `n` alternatives and reports which
    outcomes the agenda-setter can engineer. A consequence of Plott's
    Chaos Theorem when no Condorcet winner exists."""
    return await _run_typed(
        agenda_manipulation_domain, request, AgendaManipulationResponse,
    )


@router.post(
    "/apportionment",
    response_model=ApportionmentResponse,
    summary="Apportionment methods + Balinski-Young impossibility",
    response_description="Per-method seat allocation + paradox flags + "
                         "Balinski-Young summary.",
)
async def apportionment_endpoint(
    request: ApportionmentRequest,
) -> ApportionmentResponse:
    """Hamilton + 4 divisor methods (Jefferson, Webster, Adams,
    Huntington-Hill) with quota-violation / Alabama / population
    paradox detection. Demonstrates Balinski-Young (1982): no method
    avoids all three paradoxes."""
    return await _run_typed(
        apportionment_domain, request, ApportionmentResponse,
    )


@router.post(
    "/sen-paradox",
    response_model=SenParadoxResponse,
    summary="Sen's Impossibility of a Paretian Liberal (1970)",
    response_description="Canonical Lady-Chatterley example + random "
                         "profiles + resolution options.",
)
async def sen_paradox_endpoint(request: SenParadoxRequest) -> SenParadoxResponse:
    """Sen 1970: no social choice rule satisfies Pareto efficiency AND
    minimal individual liberalism simultaneously. Tests the canonical
    case and samples random preference profiles to estimate paradox
    frequency."""
    return await _run_typed(
        sen_paradox_domain, request, SenParadoxResponse,
    )


@router.post(
    "/manipulation-analysis",
    response_model=ManipulationAnalysisResponse,
    summary="Gibbard-Satterthwaite manipulator identification",
    response_description="Per-voter best manipulation (strategy + utility gain) "
                         "+ key manipulator + pedagogical note.",
)
async def manipulation_analysis_endpoint(
    request: ManipulationAnalysisRequest,
) -> ManipulationAnalysisResponse:
    """For each voter, tests four manipulation strategies (compromising,
    burying, pushover, truncating) and keeps the one with the highest
    utility gain. Empirical demonstration of Gibbard-Satterthwaite."""
    return await _run_typed(
        manipulation_analysis_domain, request, ManipulationAnalysisResponse,
    )


# ── Phase 4 batch 3 ─────────────────────────────────────────────────────────

@router.post(
    "/majority-tyranny",
    response_model=MajorityTyrannyResponse,
    summary="Tocqueville's tyranny of the majority across decision rules",
    response_description="Per-rule minority-protection metrics + tyranny curve "
                         "(majority share 0.51 -> 0.80) + best/worst rule.",
)
async def majority_tyranny_endpoint(
    request: MajorityTyrannyRequest,
) -> MajorityTyrannyResponse:
    """Same electorate, 6 decision rules (simple majority, 2/3 + 3/4
    supermajorities, unanimous, QV, MJ). Measures how often a fixed
    majority can override a high-intensity minority."""
    return await _run_typed(
        majority_tyranny_domain, request, MajorityTyrannyResponse,
    )


@router.post(
    "/democratic-backsliding",
    response_model=DemocraticBacksliddingResponse,
    summary="Path toward autocracy across successive elections",
    response_description="Per-election state (vote shares, democratic quality, "
                         "guardrails triggered) + autocracy detection + tipping "
                         "points.",
)
async def democratic_backsliding_endpoint(
    request: DemocraticBacksliddingRequest,
) -> DemocraticBacksliddingResponse:
    """Models gerrymandering / media-capture / voter-suppression
    compounding across elections. Optional guardrails (constitutional
    court, free press, international pressure, supermajority lock-in)
    slow the decay."""
    return await _run_typed(
        democratic_backsliding_domain, request, DemocraticBacksliddingResponse,
    )


@router.post(
    "/intergenerational",
    response_model=IntergenerationalResponse,
    summary="Future-generation representation in long-horizon decisions",
    response_description="Per-decision outcome under 4 mechanisms (none / proxy "
                         "/ age_weighted / veto) + cross-mechanism aggregates.",
)
async def intergenerational_endpoint(
    request: IntergenerationalRequest,
) -> IntergenerationalResponse:
    """How institutional representation of future generations changes the
    adoption rate of decisions whose costs are present and benefits
    are future. Rawls' veil-of-ignorance heuristic."""
    return await _run_typed(
        intergenerational_domain, request, IntergenerationalResponse,
    )


@router.post(
    "/epistocracy",
    response_model=EpistocracyResponse,
    summary="Epistocratic voting vs standard democracy (Caplan / Brennan)",
    response_description="Per-scheme Bayesian regret + correct-choice rate + "
                         "voter competence stats + democracy-vs-expert delta.",
)
async def epistocracy_endpoint(
    request: EpistocracyRequest,
) -> EpistocracyResponse:
    """Compares 4 weighting schemes: equal democracy, competence-weighted
    voting, epistocratic (threshold-gated), and lottery. Models Caplan's
    4 systematic biases as a competence reduction. Reports the
    democracy-vs-expert tradeoff."""
    return await _run_typed(
        epistocracy_domain, request, EpistocracyResponse,
    )


# ── Phase 4 batch 4 (final) ─────────────────────────────────────────────────

@router.post(
    "/identity-voting",
    response_model=IdentityVotingResponse,
    summary="Green/Palmquist/Schickler 2002 identity-based voting",
    response_description="Sincere vs identity vs mixed winners + per-group "
                         "loyalty / ideology match + cross-pressured "
                         "abstention + identity-weight sweep curve.",
)
async def identity_voting_endpoint(
    request: IdentityVotingRequest,
) -> IdentityVotingResponse:
    """Models the empirical pattern where voters adopt their camp's
    positions instead of choosing camps from their positions. The
    `identity_weight` parameter sweeps from pure ideological voting
    (0.0) to pure identity voting (1.0)."""
    return await _run_typed(
        identity_voting_domain, request, IdentityVotingResponse,
    )


@router.post(
    "/assumption-testing",
    response_model=AssumptionTestingResponse,
    summary="Test spatial-model robustness by relaxing core assumptions",
    response_description="Per-assumption Monte-Carlo result + most fragile "
                         "assumption + overall robustness flag.",
)
async def assumption_testing_endpoint(
    request: AssumptionTestingRequest,
) -> AssumptionTestingResponse:
    """For each of single_peaked / stable_preferences / rational_voters /
    fixed_electorate / measurable_utilities, relaxes the assumption
    and measures how often the winner changes vs the baseline. Reports
    which assumption the result depends on most."""
    return await _run_typed(
        assumption_testing_domain, request, AssumptionTestingResponse,
    )


@router.post(
    "/collective-will",
    response_model=CollectiveWillResponse,
    summary="Does the general will exist, or is it a procedural artefact?",
    response_description="Per-method + per-agenda winners + Rousseau score "
                         "(=1 iff all procedures agree) + Condorcet check + "
                         "philosophical conclusion.",
)
async def collective_will_endpoint(
    request: CollectiveWillRequest,
) -> CollectiveWillResponse:
    """Same electorate, many methods, many binary-agenda orderings.
    Counts how many distinct winners emerge. A high count supports
    Schumpeter's procedural view; a low count supports Rousseau's
    general-will view. Cross-checks against the Condorcet winner."""
    return await _run_typed(
        collective_will_domain, request, CollectiveWillResponse,
    )
