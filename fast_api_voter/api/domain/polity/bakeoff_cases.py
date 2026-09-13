"""The model bake-off's case bank (S2.2): frozen, content-hashed requests every model
answers, generated from the existing probes and ground-truth rules.

A case is one request exactly as production sends it. It is never rebuilt from
copied prompt code: each family runs a production `decide_*` function against
`CapturingClient`, which records the first attempt of every request and then fails
it, so the engine moves on to its next chunk. The case keeps that request's
prompts, schema and thinking mode, plus what scoring needs: the ground truth from the
deterministic rule (`simple_rules`), or the contrast level a probe varied, or the
renumbering a permutation pair applied.

The token budget is the one part of a request that depends on the model. Where
production sizes it from a prompt-token probe or a model-profile allowance, the case
stores that rule rather than the reference model's number, and `resolve_max_tokens`
applies it for whichever model answers.

Families (see `FAMILIES` for the scenarios and where each comes from):

- `logprob_gate`: vote_cast, 16 voters, 8 whose sincere ballot is blank -- the
  alignment gate of check_logprob_blank_calibration.py.
- `candidacy_p500`, `vote_first_choice`, `pressure_act`: ground truth.
- `response_sweep`, `coalition_diagonal`, `reaction_scandal`, `chamber_poles`,
  `positioning_poles`: contrasts from the collapse-signature probes.
- `nomination_permutation`: the same party blocks with citizen ids renumbered
  (observations.md OBS-013).
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import hashlib
import json
import logging
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api.domain.polity import llm_schemas
from api.domain.polity.accountability import mandate_deviation, self_gap
from api.domain.polity.citizen import Citizen, generate_population
from api.domain.polity.codebook import EventType
from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_behavior_engine import (
    ChamberContext,
    ReactionContext,
    ResponseContext,
    _dynamic_max_tokens,
    cast_votes,
    compute_max_tokens,
    decide_campaign_positioning,
    decide_candidacies,
    decide_chamber_deliberation,
    decide_coalition,
    decide_party_nominations,
    decide_pressure_actions,
    decide_reaction_to_event,
    decide_representative_response,
    sorted_candidates,
)
from api.domain.polity.llm_call_log import current_call_context, decision_type_for_schema
from api.domain.polity.llm_client import LlmClientProtocol, LlmResponseError
from api.domain.polity.model_profiles import model_profile
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.run_polity_simulation import _pressure_context
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    assign_party_affiliation,
    build_ranking,
    candidate_label,
    decide_candidacy,
    declare_candidacy,
    select_party_nominee_from_declared,
)

BANK_VERSION = 1
LOGPROB_GATE_FAMILY = "logprob_gate"

SCHEMAS: dict[str, dict[str, Any]] = {
    "vote_cast": llm_schemas.VOTE_CAST_JSON_SCHEMA,
    "candidacy_considered": llm_schemas.CANDIDACY_JSON_SCHEMA,
    "party_nomination_choice": llm_schemas.PARTY_NOMINATION_JSON_SCHEMA,
    "campaign_positioning": llm_schemas.POSITIONING_JSON_SCHEMA,
    "representative_response": llm_schemas.RESPONSE_JSON_SCHEMA,
    "pressure_action": llm_schemas.PRESSURE_JSON_SCHEMA,
    "reaction_to_event": llm_schemas.REACTION_JSON_SCHEMA,
    "chamber_deliberation": llm_schemas.CHAMBER_JSON_SCHEMA,
    "coalition_decision": llm_schemas.COALITION_JSON_SCHEMA,
}

# Which model-profile allowance a probed or allowance-sized request adds to its floor.
_PROBE_ALLOWANCE = {"vote_cast": "vote_think_allowance", "chamber_deliberation": "chamber_think_allowance"}
_PROFILE_ALLOWANCE = {"campaign_positioning": "positioning_think_allowance"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Case:
    case_id: str
    family: str
    decision_type: str
    system_prompt: str
    user_prompt: str
    think: bool
    budget: dict[str, Any]
    """{"rule": "fixed", "max_tokens": n}, or {"rule": "probe" | "allowance", "chunk_size": n,
    "allowance": <ModelProfile field>} -- see resolve_max_tokens."""
    unit_ids: tuple[int, ...]
    """The citizens (or parties) the request decides for, in the order it lists them."""
    labels: dict[str, Any]
    """What scoring needs; `labels["kind"]` is "truth", "contrast" or "permutation"."""

    def to_json(self) -> dict[str, Any]:
        return {**dataclasses.asdict(self), "unit_ids": list(self.unit_ids)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Case:
        return cls(**{**data, "unit_ids": tuple(data["unit_ids"])})


def make_case(
    *, family: str, decision_type: str, system_prompt: str, user_prompt: str, think: bool,
    budget: dict[str, Any], unit_ids: Sequence[int], labels: dict[str, Any],
) -> Case:
    body = {
        "family": family, "decision_type": decision_type, "system_prompt": system_prompt, "user_prompt": user_prompt,
        "think": think, "budget": budget, "unit_ids": list(unit_ids), "labels": labels,
    }
    return Case(
        case_id=_sha256(_canonical(body))[:16], family=family, decision_type=decision_type, system_prompt=system_prompt,
        user_prompt=user_prompt, think=think, budget=budget, unit_ids=tuple(unit_ids), labels=labels,
    )


@dataclass(frozen=True)
class CaseBank:
    reference: dict[str, Any]
    """The model and config the requests were rendered for."""
    cases: tuple[Case, ...]
    schemas: dict[str, dict[str, Any]] = field(default_factory=lambda: dict(SCHEMAS))
    version: int = BANK_VERSION

    @property
    def content_sha256(self) -> str:
        return _sha256(_canonical({
            "version": self.version, "reference": self.reference, "schemas": self.schemas,
            "cases": [case.to_json() for case in self.cases],
        }))

    def families(self) -> list[str]:
        return sorted({case.family for case in self.cases})


class BankIntegrityError(ValueError):
    """A case bank file whose content no longer matches the hash it was frozen with."""


def write_bank(bank: CaseBank, path: Path) -> None:
    """JSON Lines: a header line (version, reference, schemas, hash), then one case per line."""
    header = {"version": bank.version, "reference": bank.reference, "schemas": bank.schemas, "content_sha256": bank.content_sha256}
    lines = [_canonical(header)] + [_canonical(case.to_json()) for case in bank.cases]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_bank(path: Path) -> CaseBank:
    header_line, *case_lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    header = json.loads(header_line)
    bank = CaseBank(
        reference=header["reference"], schemas=header["schemas"], version=header["version"],
        cases=tuple(Case.from_json(json.loads(line)) for line in case_lines),
    )
    if bank.content_sha256 != header["content_sha256"]:
        raise BankIntegrityError(
            f"{path}: content hash {bank.content_sha256[:16]} does not match the frozen {header['content_sha256'][:16]}"
        )
    return bank


# ── capture ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapturedRequest:
    decision_type: str
    system_prompt: str
    user_prompt: str
    max_tokens: int
    think: bool
    unit_ids: tuple[int, ...]
    probed: bool
    """Whether production sized this request's budget from a prompt-token probe."""


class CapturingClient:
    """Records each request's first attempt (retries carry a retry temperature and seed),
    then fails it with LlmResponseError so production code falls back and moves on."""

    PROMPT_TOKENS = 1000

    def __init__(self) -> None:
        self.requests: list[CapturedRequest] = []
        self._probed: set[str] = set()

    def count_prompt_tokens(self, *, system_prompt: str, user_prompt: str, think: bool = True) -> int:
        self._probed.add(_sha256(system_prompt + "\x00" + user_prompt))
        return self.PROMPT_TOKENS

    def complete_json(
        self, *, system_prompt: str, user_prompt: str, json_schema: dict[str, Any], max_tokens: int,
        think: bool = True, temperature: float | None = None, seed: int | None = None,
    ) -> str:
        if temperature is None and seed is None:
            context = current_call_context()
            unit_ids = tuple(context.unit_ids) if context is not None and context.unit_ids is not None else ()
            self.requests.append(CapturedRequest(
                decision_type=decision_type_for_schema(json_schema), system_prompt=system_prompt,
                user_prompt=user_prompt, max_tokens=max_tokens, think=think, unit_ids=unit_ids,
                probed=_sha256(system_prompt + "\x00" + user_prompt) in self._probed,
            ))
        raise LlmResponseError("request captured for the bake-off case bank")


def capture(decide: Callable[[LlmClientProtocol], object]) -> list[CapturedRequest]:
    """Every first-attempt request `decide` sends, in order. The engine logs each failed
    capture as a retry and a fallback; those logs say nothing here, so they are muted."""
    client = CapturingClient()
    logging.disable(logging.ERROR)
    try:
        with contextlib.suppress(LlmResponseError):
            decide(client)
    finally:
        logging.disable(logging.NOTSET)
    return client.requests


def budget_rule(request: CapturedRequest) -> dict[str, Any]:
    chunk_size = len(request.unit_ids)
    if request.probed:
        return {"rule": "probe", "chunk_size": chunk_size, "allowance": _PROBE_ALLOWANCE[request.decision_type]}
    if request.decision_type in _PROFILE_ALLOWANCE:
        return {"rule": "allowance", "chunk_size": chunk_size, "allowance": _PROFILE_ALLOWANCE[request.decision_type]}
    return {"rule": "fixed", "max_tokens": request.max_tokens}


def resolve_max_tokens(case: Case, client: LlmClientProtocol, config: PolityConfig) -> int:
    """The case's max_tokens for the model `config.llm` names, by the rule production uses."""
    budget = case.budget
    if budget["rule"] == "fixed":
        return int(budget["max_tokens"])
    allowance = int(getattr(model_profile(config.llm.provider, config.llm.model), budget["allowance"]))
    if budget["rule"] == "allowance":
        return compute_max_tokens(int(budget["chunk_size"])) + allowance
    return _dynamic_max_tokens(
        client, config, system_prompt=case.system_prompt, user_prompt=case.user_prompt,
        chunk_size=int(budget["chunk_size"]), flat_allowance=allowance,
        decision_type=case.decision_type, unit_ids=case.unit_ids,
    )


def cases_from(
    requests: Iterable[CapturedRequest], family: str, labels_for: Callable[[CapturedRequest], dict[str, Any]],
) -> list[Case]:
    return [
        make_case(
            family=family, decision_type=request.decision_type, system_prompt=request.system_prompt,
            user_prompt=request.user_prompt, think=request.think, budget=budget_rule(request),
            unit_ids=request.unit_ids, labels=labels_for(request),
        )
        for request in requests
    ]


# ── scenarios ─────────────────────────────────────────────────────────────

def _population(config: PolityConfig, size: int, seed: int | None = None) -> list[Citizen]:
    return generate_population(config.citizens, size, config.run.seed if seed is None else seed)


def _with_parties(config: PolityConfig, citizens: list[Citizen], seed: int | None = None) -> list[Party]:
    parties = initialize_parties(citizens, config.parties.initial_count, config.run.seed if seed is None else seed)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)
    return parties


def candidacy_p500(config: PolityConfig) -> list[Case]:
    """The Stage 3 / Track B3 candidacy measurement: the whole p500 population at the run
    seed, ground truth the ambition threshold (202/500 declared, 318/500 agreeing)."""
    population = _population(config, 500)
    truth = {c.citizen_id: int(decide_candidacy(c, config.candidacy)) for c in population}
    requests = capture(lambda client: decide_candidacies(population, config, client))
    return cases_from(requests, "candidacy_p500", lambda r: {
        "kind": "truth", "truth": {str(cid): truth[cid] for cid in r.unit_ids},
    })


def _vote_scenario(config: PolityConfig) -> tuple[list[Citizen], list[Citizen], dict[int, Any]]:
    """check_logprob_blank_calibration.py's electorate: 300 citizens, five parties, each
    party's most ambitious member nominated; truth is each voter's sincere first choice."""
    citizens = _population(config, 300)
    parties = _with_parties(config, citizens)
    everyone = {c.citizen_id for c in citizens}
    nominees = sorted_candidates(
        [n for p in parties if (n := select_party_nominee_from_declared(p.party_id, citizens, everyone)) is not None]
    )
    for nominee in nominees:
        declare_candidacy(nominee)
    nominee_ids = {n.citizen_id for n in nominees}
    voters = [c for c in citizens if c.citizen_id not in nominee_ids]
    return voters, nominees, {voter.citizen_id: _sincere_first_choice(voter, nominees) for voter in voters}


def _sincere_first_choice(voter: Citizen, nominees: list[Citizen]) -> Any:
    """"blank", or the listed position (1-based, as vote_cast's ranking) of the voter's sincere favourite."""
    first = build_ranking(voter, nominees)[0]
    positions = {candidate_label(c): i for i, c in enumerate(nominees, start=1)}
    return "blank" if first == BLANK_LABEL else positions[first]


def _balanced(voters: list[Citizen], truth: dict[int, Any], per_class: int, skip: int) -> list[Citizen]:
    blank = [v for v in voters if truth[v.citizen_id] == "blank"][skip:skip + per_class]
    ranked = [v for v in voters if truth[v.citizen_id] != "blank"][skip:skip + per_class]
    if len(blank) < per_class or len(ranked) < per_class:
        raise ValueError(f"the vote scenario has too few voters for {per_class} per class after skipping {skip}")
    return sorted(blank + ranked, key=lambda c: c.citizen_id)


def _vote_cases(config: PolityConfig, family: str, per_class: int, skip: int) -> list[Case]:
    voters, nominees, truth = _vote_scenario(config)
    chosen = _balanced(voters, truth, per_class, skip)
    requests = capture(lambda client: cast_votes(chosen, nominees, config, client))
    return cases_from(requests, family, lambda r: {
        "kind": "truth", "truth": {str(cid): truth[cid] for cid in r.unit_ids},
        "field": "blank", "value": "1", "reading": "binary",
    })


def logprob_gate(config: PolityConfig) -> list[Case]:
    return _vote_cases(config, LOGPROB_GATE_FAMILY, per_class=8, skip=0)


def vote_first_choice(config: PolityConfig) -> list[Case]:
    return _vote_cases(config, "vote_first_choice", per_class=20, skip=8)


def pressure_act(config: PolityConfig) -> list[Case]:
    """check_pressure_calibration_matrix.py's unambiguous citizens: a president pledged at
    the centre who drifted +0.3 on every issue; truth is whether the citizen's own gap is
    far above their tolerance (act) or far below it (don't), 12 of each, asked one at a time."""
    citizens = _population(config, 300)
    issues = config.citizens.issue_count
    holder = Citizen(citizen_id=10_000, issue_positions=(0.5,) * issues, issue_priorities=(1 / issues,) * issues,
                     blank_threshold=0.5, ambition_score=0.5)
    declare_candidacy(holder)
    holder.revealed_position = (0.8,) * issues
    gaps = {c.citizen_id: self_gap(c, holder) for c in citizens}
    below = [c for c in citizens if gaps[c.citizen_id] < 0.5 * c.blank_threshold][:12]
    above = [c for c in citizens if gaps[c.citizen_id] > 1.5 * c.blank_threshold][:12]
    consulted = sorted(below + above, key=lambda c: c.citizen_id)
    deviation = mandate_deviation(holder, config.mandate)
    contexts = {
        c.citizen_id: _pressure_context(c, holder, gaps[c.citizen_id], tick=0, mandate_dev=deviation, config=config,
                                        can_sign=False, can_launch=True)
        for c in consulted
    }
    should_act = {c.citizen_id: c in above for c in consulted}
    requests = capture(lambda client: decide_pressure_actions(consulted, contexts, config, client))
    return cases_from(requests, "pressure_act", lambda r: {
        "kind": "truth", "truth": {str(cid): should_act[cid] for cid in r.unit_ids}, "match": "acts",
    })


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def response_sweep(config: PolityConfig) -> list[Case]:
    """check_logprob_response_stance_tracking.py / check_response_calibration.py: nine
    points from no pressure (L=0.95, no deviation, no street) to crisis (L=0.05,
    deviation 0.8, street 3.0), one holder each; reads P(stance=1, CONCESSION)."""
    cases = []
    for step in range(9):
        t = step / 8
        cid = 6000 + step
        holder = Citizen(citizen_id=cid, issue_positions=tuple((cid * 0.019 + d * 0.011) % 1.0 for d in range(20)),
                         issue_priorities=(1 / 20,) * 20, blank_threshold=0.5, ambition_score=0.5)
        declare_candidacy(holder)
        context = ResponseContext(
            cid=cid, legitimacy=_lerp(0.95, 0.05, t), mandate_dev=_lerp(0.0, 0.8, t), street=_lerp(0.0, 3.0, t),
            lame_duck=False, ticks_left=round(_lerp(20, 2, t)),
        )
        requests = capture(lambda client: decide_representative_response([holder], {cid: context}, config, client))
        cases += cases_from(requests, "response_sweep", lambda r: {
            "kind": "contrast", "group": "pressure", "t": t, "units": list(r.unit_ids), "field": "stance", "value": "1",
        })
    return cases


def coalition_diagonal(config: PolityConfig) -> list[Case]:
    """check_logprob_coalition_action_tracking.py: five responder parties from identical to
    maximally distant from the initiator, and five calls from a large seat shortfall to one
    seat short; each call is read on the responder whose distance matches its shortfall.
    (The probe's last two points had no shortfall; production asks nobody then, so the
    diagonal stops one seat short.)"""
    issues = config.citizens.issue_count
    initiator = 0
    responders = [1, 2, 3, 4, 5]
    platforms = {initiator: (0.5,) * issues}
    for i, pid in enumerate(responders):
        offset = 0.4 * i / (len(responders) - 1)
        platforms[pid] = tuple(0.5 + offset if d % 2 == 0 else 0.5 - offset for d in range(issues))
    parties = [Party(party_id=pid, platform=platform) for pid, platform in platforms.items()]
    cases = []
    for i, shortfall in enumerate((25, 19, 13, 7, 1)):
        t = i / (len(responders) - 1)
        initiator_seats = 50 - shortfall
        rest = 100 - initiator_seats
        seats = {initiator: initiator_seats, **{pid: rest // 5 + (1 if k < rest % 5 else 0) for k, pid in enumerate(responders)}}
        votes = {pid: s / 100 for pid, s in seats.items()}
        focus = responders[i]
        requests = capture(lambda client: decide_coalition(parties, seats, votes, config, client))
        cases += cases_from(requests[:1], "coalition_diagonal", lambda r: {
            "kind": "contrast", "group": "join_to_decline", "t": t, "units": [focus], "field": "action", "value": "1",
        })
    return cases


def reaction_scandal(config: PolityConfig) -> list[Case]:
    """check_vllm_reaction_to_event_collapse_signature.py's poles (event salience 0.0 vs
    0.9), for a production-size chunk of 25 reactors."""
    population = _population(config, 190)
    reactors = [c for c in population if c.citizen_id != 5][:25]
    cases = []
    for t, salience in ((0.0, 0.0), (1.0, 0.9)):
        contexts = {c.citizen_id: ReactionContext(cid=c.citizen_id, event_salience=salience) for c in reactors}
        requests = capture(lambda client: decide_reaction_to_event(
            reactors, contexts, EventType.SCANDAL, config, client, target=5, magnitude=0.0,
        ))
        cases += cases_from(requests, "reaction_scandal", lambda r: {
            "kind": "contrast", "group": "prior_salience", "t": t, "units": list(r.unit_ids), "field": None, "value": None,
        })
    return cases


def chamber_poles(config: PolityConfig) -> list[Case]:
    """check_chamber_deliberation_collapse_signature.py's poles: members whose chamber
    position equals their sincere one, and the same members drifted +0.3 on one issue.
    Reads P(motif=70[2], DELIBERATIVE_SHIFT) at the digit where 701 and 702 differ."""
    population = _population(config, 190)
    cases = []
    for t, drift in ((0.0, 0.0), (1.0, 0.3)):
        members = [copy.copy(population[cid]) for cid in (1, 2, 3, 4, 5)]
        for member in members:
            shifted = list(member.issue_positions)
            shifted[0] = min(1.0, shifted[0] + drift)
            member.chamber_position = tuple(shifted)
        contexts = {m.citizen_id: ChamberContext(cid=m.citizen_id, ticks_left=15) for m in members}
        requests = capture(lambda client: decide_chamber_deliberation(members, contexts, config, client))
        cases += cases_from(requests, "chamber_poles", lambda r: {
            "kind": "contrast", "group": "drift", "t": t, "units": list(r.unit_ids),
            "field": "motif", "value": "2", "value_char_offset": 2,
        })
    return cases


def positioning_poles(config: PolityConfig) -> list[Case]:
    """check_campaign_positioning_collapse_signature.py's poles: the three citizens nearest
    the electorate mean, then the three farthest, as one nominee batch each."""
    citizens = _population(config, 300)
    parties = _with_parties(config, citizens)
    mean = tuple(sum(c.issue_positions[d] for c in citizens) / len(citizens) for d in range(config.citizens.issue_count))
    ranked = sorted(citizens, key=lambda c: math.dist(c.issue_positions, mean))
    parties_by_id = {p.party_id: p for p in parties}
    cases = []
    for t, nominees in ((0.0, ranked[:3]), (1.0, ranked[-3:])):
        requests = capture(lambda client: decide_campaign_positioning(nominees, citizens, parties_by_id, config, client))
        cases += cases_from(requests, "positioning_poles", lambda r: {
            "kind": "contrast", "group": "distance_to_electorate", "t": t, "units": list(r.unit_ids),
            "field": None, "value": None,
        })
    return cases


def _renumbered(citizens: list[Citizen]) -> tuple[list[Citizen], dict[int, int]]:
    """The same citizens with ids reversed, so every party's candidates are listed in the opposite order."""
    top = max(c.citizen_id for c in citizens)
    mapping = {c.citizen_id: top - c.citizen_id for c in citizens}
    renamed = [dataclasses.replace(c, citizen_id=mapping[c.citizen_id]) for c in citizens]
    return sorted(renamed, key=lambda c: c.citizen_id), mapping


def _nomination_labels(pair: str, rendering: str, request: CapturedRequest, identity: dict[int, int]) -> dict[str, Any]:
    """Per party: which original citizen sits at each listed position."""
    blocks = json.loads(request.user_prompt)["parties"]
    listed = {
        str(block["party_id"]): {str(c["position"]): identity[c["cid"]] for c in block["candidates"]}
        for block in blocks
    }
    return {"kind": "permutation", "pair": pair, "rendering": rendering, "units": list(request.unit_ids), "listed": listed}


def nomination_permutation(config: PolityConfig) -> list[Case]:
    """observations.md OBS-013: party nominations over the ambition-threshold declarers of
    five p100 populations, each rendered twice -- original ids, and ids reversed so every
    candidate list is listed backwards. A pick that follows the candidate names the same
    citizen both times; one that follows the listed position does not."""
    cases = []
    for seed in (1, 2, 3, 4, 42):
        citizens = _population(config, 100, seed)
        parties = _with_parties(config, citizens, seed)
        declared = {c.citizen_id for c in citizens if decide_candidacy(c, config.candidacy)}
        renamed, mapping = _renumbered(citizens)
        renamed_declared = {mapping[cid] for cid in declared}
        back = {new: old for old, new in mapping.items()}
        for rendering, people, chosen, identity in (
            ("original", citizens, declared, {cid: cid for cid in mapping}),
            ("renumbered", renamed, renamed_declared, back),
        ):
            requests = capture(lambda client: decide_party_nominations(people, parties, chosen, config, client))
            cases += cases_from(requests[:1], "nomination_permutation",
                                lambda r: _nomination_labels(f"seed{seed}", rendering, r, identity))
    return cases


FAMILIES: dict[str, Callable[[PolityConfig], list[Case]]] = {
    LOGPROB_GATE_FAMILY: logprob_gate,
    "candidacy_p500": candidacy_p500,
    "vote_first_choice": vote_first_choice,
    "pressure_act": pressure_act,
    "response_sweep": response_sweep,
    "coalition_diagonal": coalition_diagonal,
    "reaction_scandal": reaction_scandal,
    "chamber_poles": chamber_poles,
    "positioning_poles": positioning_poles,
    "nomination_permutation": nomination_permutation,
}


def generate_bank(config: PolityConfig, *, families: Iterable[str] | None = None) -> CaseBank:
    """Every family rendered for `config` -- in practice the flagship runner's config on
    the reference model, so the requests are the ones production sends it."""
    selected = list(FAMILIES) if families is None else list(families)
    cases = [case for name in selected for case in FAMILIES[name](config)]
    reference = {"provider": config.llm.provider, "model": config.llm.model, "seed": config.run.seed,
                 "max_batch_size": config.llm.max_batch_size}
    return CaseBank(reference=reference, cases=tuple(cases))


def drift(bank: CaseBank, current: CaseBank) -> dict[str, list[str]]:
    """Case ids in the frozen bank that production no longer renders, and new ones it does."""
    frozen = {case.case_id for case in bank.cases}
    now = {case.case_id for case in current.cases}
    return {"no_longer_rendered": sorted(frozen - now), "newly_rendered": sorted(now - frozen)}
