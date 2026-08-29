"""
api.domain.polity.config — typed loader for polity_config.yaml (Lot 1).

Single source of truth for every polity institutional parameter (D9 of
audit-precision-plan.md): nothing here is hardcoded elsewhere. Sections that
only activate at a later palier ([v1]..[v8]) are still parsed and structurally
validated so a typo in them fails loudly now rather than silently at the
palier that turns them on — but v0 code only reads the typed sections below.

A malformed file (missing key, wrong type, unknown enum value) raises
PolityConfigError with a message naming the offending path — never a bare
KeyError/TypeError from a caller three frames away.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "polity_config.yaml"

_PRESIDENTIAL_METHODS = {
    "plurality", "two_round", "borda", "irv", "coombs", "bucklin",
    "minimax", "schulze", "kemeny_young", "copeland", "nanson", "baldwin",
    "approval", "simple_score", "star", "median", "majority_judgment",
}
_SEAT_ALLOCATIONS = {"dhondt", "sainte_lague", "largest_remainder"}
_ASSEMBLY_MODES = {"party_list", "candidate_multiwinner"}
_COALITION_INITIATORS = {"largest_seats", "largest_votes"}
_COALITION_TIEBREAK_KEYS = {"seats", "votes", "party_id"}
_PARTY_INIT_STRATEGIES = {"kmeans_on_citizens", "random", "manual"}
_LLM_PROVIDERS = {"ollama", "vllm", "api"}
_LLM_SHARDINGS = {"static", "dynamic"}
_LLM_CACHE_BACKENDS = {"redis", "sqlite", "none"}
_LLM_RATIONALE_MODES = {"codes", "free_text", "hybrid"}


class PolityConfigError(ValueError):
    """Raised when polity_config.yaml is missing, malformed, or invalid."""


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise PolityConfigError(f"'{name}': expected a mapping, got {type(value).__name__}")
    return value


def _get(section: dict[str, Any], path: str, key: str, expected: type | tuple[type, ...]) -> Any:
    if key not in section:
        raise PolityConfigError(f"'{path}.{key}': missing required field")
    value = section[key]
    # bool is a subclass of int — reject bool where an int/float was requested.
    if isinstance(expected, type) and expected in (int, float) and isinstance(value, bool):
        raise PolityConfigError(f"'{path}.{key}': expected {expected.__name__}, got bool")
    if not isinstance(value, expected):
        expected_name = (
            expected.__name__ if isinstance(expected, type) else " or ".join(t.__name__ for t in expected)
        )
        raise PolityConfigError(f"'{path}.{key}': expected {expected_name}, got {type(value).__name__}")
    return value


def _get_enum(section: dict[str, Any], path: str, key: str, allowed: set[str]) -> str:
    value = str(_get(section, path, key, str))
    if value not in allowed:
        raise PolityConfigError(f"'{path}.{key}': '{value}' is not one of {sorted(allowed)}")
    return value


def _get_optional_int(section: dict[str, Any], path: str, key: str) -> int | None:
    if key not in section:
        raise PolityConfigError(f"'{path}.{key}': missing required field")
    value = section[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PolityConfigError(f"'{path}.{key}': expected int or null, got {type(value).__name__}")
    return int(value)


def _get_ratio(section: dict[str, Any], path: str, key: str) -> float:
    """A float or int expected to live in [0, 1] (a threshold or ratio)."""
    value = _get(section, path, key, (int, float))
    ratio = float(value)
    if not 0.0 <= ratio <= 1.0:
        raise PolityConfigError(f"'{path}.{key}': {ratio} is outside the valid range [0, 1]")
    return ratio


def _get_positive_int(section: dict[str, Any], path: str, key: str) -> int:
    value = int(_get(section, path, key, int))
    if value <= 0:
        raise PolityConfigError(f"'{path}.{key}': must be a positive integer, got {value}")
    return value


def _get_nonneg_int(section: dict[str, Any], path: str, key: str) -> int:
    """Unlike _get_positive_int, 0 is legal -- for counts that can
    legitimately be "none" (e.g. llm.max_batch_replays: 0 = no replay,
    v4 Lot 8's shipped default)."""
    value = int(_get(section, path, key, int))
    if value < 0:
        raise PolityConfigError(f"'{path}.{key}': must be a non-negative integer, got {value}")
    return value


@dataclass(frozen=True)
class RunConfig:
    seed: int
    ticks_per_year: int
    duration_years: int
    population_size: int
    run_label: str

    @property
    def total_ticks(self) -> int:
        return self.ticks_per_year * self.duration_years


@dataclass(frozen=True)
class InstitutionsConfig:
    president_term_years: int
    assembly_term_years: int
    assembly_offset_years: int
    president_term_limit: int | None
    assembly_term_limit: int | None
    presidential_method: str
    assembly_seats: int
    assembly_mode: str
    seat_allocation: str
    electoral_threshold: float
    blank_vote_enabled: bool
    blank_vote_competitive: bool
    blank_invalidation_threshold: float
    reelection_delay_ticks: int
    reelection_max_attempts: int
    barred_from_immediate_rerun: bool


@dataclass(frozen=True)
class PartiesConfig:
    initial_count: int
    init_strategy: str
    manual_platforms: list[Any]
    birth_enabled: bool
    death_enabled: bool
    split_enabled: bool
    coalition_initiator: str
    coalition_tiebreak: tuple[str, ...]
    coalition_majority_ratio: float
    coalition_max_negotiation_rounds: int


@dataclass(frozen=True)
class CitizensConfig:
    issue_count: int
    position_dist: str
    priority_dist: str
    blank_threshold_dist: str
    ambition_dist: str
    base_threshold_dist: str
    static_population: bool
    memory_window_terms: int


@dataclass(frozen=True)
class CandidacyConfig:
    ambition_threshold: float
    rupture_path_enabled: bool
    rupture_base_probability: float
    rupture_signature_ratio: float
    max_candidates_hard_cap: int


@dataclass(frozen=True)
class CampaignConfig:
    """v2 increment 4 (campaign_positioning, dt=5) tunables — a nominee's
    LLM-chosen shift away from their sincere position is bounded on both
    axes: how many dimensions it can touch (max_positioning_shifts) and how
    far on each (max_positioning_delta). Enforced in llm_behavior_engine.py's
    validate_positioning_decision, not here -- Pydantic's own schema bound
    is intentionally looser (a structural ceiling), since the real,
    config-driven cap can't be baked into a schema defined at import time."""

    max_positioning_delta: float
    max_positioning_shifts: int


@dataclass(frozen=True)
class LegitimacyConfig:
    """§7 — inactive until v4. `recall_floor_indexed_on_L0` is TRANCHÉ false
    in the design doc (§7.2: a moving floor destroys the external legibility
    the mechanism exists for) — _parse_legitimacy rejects `true` outright,
    the same "parse it so a typo fails loudly, but the feature itself is a
    rejected design, not a pending one" precedent as rupture_path_enabled
    before v1. `recall_cooldown_ticks` is a DIFFERENT cooldown from
    petition.cooldown_ticks (this one gates repeat recalls of the same
    office; that one gates repeat petitions against the same target)."""

    enabled: bool
    decay: float
    recall_floor: float
    recall_floor_indexed_on_l0: bool
    recall_cooldown_ticks: int
    passive_erosion_weight: float


@dataclass(frozen=True)
class PressureMenuConfig:
    """§7bis.2 — the constitutional menu of pressure levers available to
    citizens between elections. §7bis.8: a single 4-modality experimental
    variable (electoral_only / petition-only / mobilization-only / both),
    not two independent booleans -- validated as such in _parse_pressure_menu
    (electoral_only=true forces both levers off)."""

    petition_enabled: bool
    mobilization_enabled: bool
    electoral_only: bool


@dataclass(frozen=True)
class MandateConfig:
    """§7bis.5 — mandate deviation: information, never itself a lever.
    `max_response_delta`/`max_response_shifts` bound representative_response's
    (dt=6) position delta -- deliberately separate fields from
    campaign.max_positioning_delta/max_positioning_shifts: mid-term drift and
    campaign-time strategy are different effects and must stay analytically
    separable, even though the shipped defaults happen to match."""

    enabled: bool
    pledge_scope: str
    pledge_top_k: int
    deviation_metric: str
    deviation_log_threshold: float
    max_response_delta: float
    max_response_shifts: int


@dataclass(frozen=True)
class PetitionConfig:
    """§7bis.4a. `concurrent_allowed` is TRANCHÉ false in v4 (single open
    petition per target -- also removes a wire-schema ambiguity: `act=1
    sign` needs no petition_id field) -- _parse_petition rejects `true`."""

    enabled: bool
    signature_threshold: float
    cooldown_ticks: int
    petition_lifespan_ticks: int
    confidence_vote_format: str
    concurrent_allowed: bool
    weight_in_ecart: float


@dataclass(frozen=True)
class StreetPressureConfig:
    """§7bis.4b. `weight_in_ecart` + petition.weight_in_ecart must sum to
    1.0 -- validated in load_config, since it's a cross-section rule."""

    enabled: bool
    decay: float
    weight_in_ecart: float
    visible_to_representative: bool


@dataclass(frozen=True)
class AwakeningContextModulation:
    mandate_deviation: bool
    ticks_to_election: bool
    neighbors_acting: bool
    event_salience: bool


@dataclass(frozen=True)
class AwakeningConfig:
    """§7bis.9d — the awakening threshold: a sampling GATE (who gets
    consulted), never itself a decision. `no_consultation_cap` is TRANCHÉ
    true in v4 (§15bis.1: no cap, self-hosted inference means a spike costs
    time, not money) -- _parse_awakening rejects `false`."""

    enabled: bool
    source: str
    context_modulation: AwakeningContextModulation
    modulation_amplitude: float
    no_consultation_cap: bool


@dataclass(frozen=True)
class EventsConfig:
    """§8 — exogenous events (v5). Two independently toggleable
    sub-mechanisms under one master switch: scandal (a Poisson arrival
    process targeting the sitting president) and economic shock (a light
    AR(1) climate variable, population-wide). `enabled` is cross-validated
    in load_config as `scandal_enabled or economic_shock_enabled` -- a
    single derived fact, not a third independently-settable flag, so the
    two sub-toggles can't silently drift from their own master switch the
    way pressure_menu's two flags are guarded against drifting from
    petition.enabled/street_pressure.enabled.

    `scandal_magnitude`/`max_reaction_delta` are v5's own fields, deliberately
    not reused from mandate.max_response_delta or campaign.max_positioning_delta
    -- mid-term mandate drift, campaign-time strategy, and shock reaction are
    three different effects that must stay analytically separable (v4 Lot 6's
    own precedent), even where shipped defaults happen to match.

    `economy_shock_threshold` is the anti-saturation gate (§16.3 style) for
    journaling `economic_shock_tick`, and doubles as the first concrete
    trigger definition for point ouvert n°5 (persona regeneration "après un
    choc économique majeur") -- a partial resolution, not a full one; the
    rest of the persona schema stays open (§9)."""

    enabled: bool
    scandal_enabled: bool
    scandal_rate_per_tick: float
    scandal_magnitude: float
    economic_shock_enabled: bool
    economy_ar1_phi: float
    economy_ar1_sigma: float
    economy_shock_threshold: float
    salience_decay: float
    max_reaction_delta: float


@dataclass(frozen=True)
class SocialGraphConfig:
    """§5 — social graph (v6). Feeds `pressure_action`'s (dt=10)
    `neighbors_acting` field and, once
    `awakening.context_modulation.neighbors_acting` is also true (cross-
    validated in load_config), a fourth term in `awakening_threshold`'s
    `f(context)` -- Granovetter-style threshold diffusion read as another
    continuous modulation of the same gate, never a hard rule (§3.3).

    `evolving` (homophily-driven graph rewiring) is parsed so a typo fails
    loudly, but `_parse_social_graph` rejects `true` outright -- the design
    doc's own 🔴 "static or evolving?" point (§5) stays genuinely open;
    this is a TRANCHÉ parse-time guard, not a resolution, the same
    precedent as `recall_floor_indexed_on_l0`/`petition.concurrent_allowed`."""

    enabled: bool
    topology: str
    mean_degree: int
    rewiring_prob: float
    evolving: bool


@dataclass(frozen=True)
class SortitionChamberConfig:
    """§6bis.3 — the sortition chamber (v6b), the only 🔴-marked ("most
    open") section in the whole design doc. v6b's own scope is a genuine
    control-group cohort: uniform-random selection, non-renewable short
    terms, structurally immune to every §7bis pressure channel -- compared
    against the elected president's own dt=6 mandate_deviation trajectory
    (§6bis.5's own "groupe de contrôle élu vs tiré-au-sort" framing).

    `veto_power`/`veto_delay_ticks` are parsed here (so a typo fails
    loudly) but consumed by NOTHING in v6b -- point ouvert n°11 (veto
    power) needs a lawmaking concept this codebase has never built, and is
    deferred to its own, separately-authorized future palier.

    `selection`/`overlaps_with_assembly`/`renewable` are all TRANCHÉ
    parse-time guards, the same precedent as
    `recall_floor_indexed_on_l0`/`social_graph.evolving`:
    - `selection: stratified_demographic` -- not yet implemented.
    - `overlaps_with_assembly: true` -- legislative "seats" in this
      codebase are a party-level vote-allocation abstraction
      (`legislative_result.payload.seats`); no individual deputy
      `Citizen` is ever tracked (`Office.DEPUTY` is reserved, never
      assigned), so there is no individual legislative membership for a
      sortition seat to overlap with -- `false` is already true by
      construction, and `true` asks for per-deputy tracking that doesn't
      exist.
    - `renewable: true` -- v6b's own selection design is built around
      strict one-shot-ever eligibility (a `Citizen.sortition_terms_served`
      counter, `> 0` meaning permanently ineligible); a `true` value asks
      for a re-eligibility rule this MVP never designs."""

    enabled: bool
    seats: int
    term_years: int
    renewable: bool
    selection: str
    overlaps_with_assembly: bool
    veto_power: str
    veto_delay_ticks: int
    # v6b Lot 3 (§6bis.3, dt=11): the deliberation-shift bound Lot 1 missed reserving --
    # every other position-shift-bearing decision type has one (mandate.max_response_delta/
    # max_response_shifts for dt=6, campaign.max_positioning_delta/max_positioning_shifts for
    # dt=5). Shipped at the same magnitude as mandate.*'s own values so Lot 4's own comparison
    # isolates the effect of pressure-insulation, not a different drift ceiling.
    max_deliberation_delta: float
    max_deliberation_shifts: int


@dataclass(frozen=True)
class JournalConfig:
    enabled: bool
    format: str
    output_dir: str
    snapshot_every_ticks: int
    log_non_events: bool
    index_after_run: bool
    decode_codebook_on_index: bool


@dataclass(frozen=True)
class MetricsConfig:
    """§10 — v0's four rows plus v4 Lot 8's six. `platform_convergence`
    ([v2]), `mobilization_nonlinearity` and `polarization` ([v6]) are not
    fields here: indexer.py doesn't implement them, so _parse_metrics
    rejects `true` for any of the three (same TRANCHÉ-guard style as
    legitimacy.recall_floor_indexed_on_L0) rather than silently accepting a
    flag that would produce nothing."""

    compute_every_ticks: int
    effective_parties: bool
    cohabitation_rate: bool
    coalition_lifespan: bool
    mandate_deviation: bool
    lame_duck_deviation_delta: bool
    inaction_rate: bool
    pressure_lever_mix: bool
    petition_success_rate: bool
    stance_distribution: bool


@dataclass(frozen=True)
class LlmConfig:
    """§3/§12 — inactive (enabled=false) until v2's vote_cast increment.
    Typed in full even though most fields are still unused (cache_backend,
    personas_count) — config.py's own contract is that a typo in a
    not-yet-active section fails loudly now, not silently at activation.

    max_batch_replays (v4 Lot 8, §3.6.10): extra attempts on a batch
    LlmResponseError, shipped 0 (today's exact behavior -- no replay).
    See llm_behavior_engine._complete_and_decode_with_replay.

    recycle_after_n_calls: forces an Ollama model unload+reload (resetting
    llama.cpp's own prompt-cache pool) after this many complete_json calls,
    shipped null (disabled). See OllamaJsonClient's own docstring for the
    measured evidence -- a call reliably degenerates once the cache pool
    approaches its observed capacity, and this stays off by default because
    that capacity was measured for one specific prompt shape, not proven
    general."""

    enabled: bool
    provider: str
    base_url: str
    model: str
    temperature: float
    max_batch_size: int
    batch_sharding: str
    cache_backend: str
    cache_url: str
    rationale_mode: str
    codebook_version: str
    personas_count: int
    max_batch_replays: int
    recycle_after_n_calls: int | None


@dataclass(frozen=True)
class ParallelConfig:
    runs_in_parallel: int
    intra_run_workers: int


@dataclass(frozen=True)
class PolityConfig:
    """The typed v0 view of polity_config.yaml, plus the full raw mapping
    (`raw`) so a later palier can read its own not-yet-typed section without
    a schema change here."""

    run: RunConfig
    institutions: InstitutionsConfig
    parties: PartiesConfig
    citizens: CitizensConfig
    candidacy: CandidacyConfig
    campaign: CampaignConfig
    legitimacy: LegitimacyConfig
    pressure_menu: PressureMenuConfig
    mandate: MandateConfig
    petition: PetitionConfig
    street_pressure: StreetPressureConfig
    awakening: AwakeningConfig
    events: EventsConfig
    social_graph: SocialGraphConfig
    sortition_chamber: SortitionChamberConfig
    journal: JournalConfig
    metrics: MetricsConfig
    llm: LlmConfig
    parallel: ParallelConfig
    raw: dict[str, Any]


def _parse_run(raw: dict[str, Any]) -> RunConfig:
    s = _section(raw, "run")
    return RunConfig(
        seed=_get(s, "run", "seed", int),
        ticks_per_year=_get_positive_int(s, "run", "ticks_per_year"),
        duration_years=_get_positive_int(s, "run", "duration_years"),
        population_size=_get_positive_int(s, "run", "population_size"),
        run_label=_get(s, "run", "run_label", str),
    )


def _parse_institutions(raw: dict[str, Any]) -> InstitutionsConfig:
    s = _section(raw, "institutions")
    blank_vote_enabled = _get(s, "institutions", "blank_vote_enabled", bool)
    blank_vote_competitive = _get(s, "institutions", "blank_vote_competitive", bool)
    if blank_vote_competitive and not blank_vote_enabled:
        raise PolityConfigError(
            "'institutions.blank_vote_competitive': true requires 'institutions.blank_vote_enabled' "
            "to also be true (v4 Lot 9, §6bis.2 -- nothing to be competitive about if blank isn't "
            "itself a choice)"
        )
    return InstitutionsConfig(
        president_term_years=_get_positive_int(s, "institutions", "president_term_years"),
        assembly_term_years=_get_positive_int(s, "institutions", "assembly_term_years"),
        assembly_offset_years=_get(s, "institutions", "assembly_offset_years", int),
        president_term_limit=_get_optional_int(s, "institutions", "president_term_limit"),
        assembly_term_limit=_get_optional_int(s, "institutions", "assembly_term_limit"),
        presidential_method=_get_enum(s, "institutions", "presidential_method", _PRESIDENTIAL_METHODS),
        assembly_seats=_get_positive_int(s, "institutions", "assembly_seats"),
        assembly_mode=_get_enum(s, "institutions", "assembly_mode", _ASSEMBLY_MODES),
        seat_allocation=_get_enum(s, "institutions", "seat_allocation", _SEAT_ALLOCATIONS),
        electoral_threshold=_get_ratio(s, "institutions", "electoral_threshold"),
        blank_vote_enabled=blank_vote_enabled,
        blank_vote_competitive=blank_vote_competitive,
        blank_invalidation_threshold=_get_ratio(s, "institutions", "blank_invalidation_threshold"),
        # v4 Lot 9: was plain _get(..., int) while the field was inert. Under
        # the tick-loop's calendar-suspension design, a value of 0 (or
        # negative) would compute next_tick <= tick, which can never be
        # reached again -- the presidency deadlocks vacant for the rest of
        # the run, silently. Now that this lot makes the field live, a
        # positive value is enforced.
        reelection_delay_ticks=_get_positive_int(s, "institutions", "reelection_delay_ticks"),
        reelection_max_attempts=_get_positive_int(s, "institutions", "reelection_max_attempts"),
        barred_from_immediate_rerun=_get(s, "institutions", "barred_from_immediate_rerun", bool),
    )


def _parse_parties(raw: dict[str, Any]) -> PartiesConfig:
    s = _section(raw, "parties")
    tiebreak = _get(s, "parties", "coalition_tiebreak", list)
    if not tiebreak or not all(isinstance(k, str) for k in tiebreak):
        raise PolityConfigError("'parties.coalition_tiebreak': must be a non-empty list of strings")
    unknown = set(tiebreak) - _COALITION_TIEBREAK_KEYS
    if unknown:
        raise PolityConfigError(f"'parties.coalition_tiebreak': unknown key(s) {sorted(unknown)}")
    if len(set(tiebreak)) != len(tiebreak):
        raise PolityConfigError("'parties.coalition_tiebreak': duplicate keys")
    return PartiesConfig(
        initial_count=_get_positive_int(s, "parties", "initial_count"),
        init_strategy=_get_enum(s, "parties", "init_strategy", _PARTY_INIT_STRATEGIES),
        manual_platforms=_get(s, "parties", "manual_platforms", list),
        birth_enabled=_get(s, "parties", "birth_enabled", bool),
        death_enabled=_get(s, "parties", "death_enabled", bool),
        split_enabled=_get(s, "parties", "split_enabled", bool),
        coalition_initiator=_get_enum(s, "parties", "coalition_initiator", _COALITION_INITIATORS),
        coalition_tiebreak=tuple(tiebreak),
        coalition_majority_ratio=_get_ratio(s, "parties", "coalition_majority_ratio"),
        coalition_max_negotiation_rounds=_get_positive_int(s, "parties", "coalition_max_negotiation_rounds"),
    )


def _parse_citizens(raw: dict[str, Any]) -> CitizensConfig:
    s = _section(raw, "citizens")
    return CitizensConfig(
        issue_count=_get_positive_int(s, "citizens", "issue_count"),
        position_dist=_get(s, "citizens", "position_dist", str),
        priority_dist=_get(s, "citizens", "priority_dist", str),
        blank_threshold_dist=_get(s, "citizens", "blank_threshold_dist", str),
        ambition_dist=_get(s, "citizens", "ambition_dist", str),
        base_threshold_dist=_get(s, "citizens", "base_threshold_dist", str),
        static_population=_get(s, "citizens", "static_population", bool),
        memory_window_terms=_get(s, "citizens", "memory_window_terms", int),
    )


def _parse_candidacy(raw: dict[str, Any]) -> CandidacyConfig:
    s = _section(raw, "candidacy")
    return CandidacyConfig(
        ambition_threshold=_get_ratio(s, "candidacy", "ambition_threshold"),
        rupture_path_enabled=_get(s, "candidacy", "rupture_path_enabled", bool),
        rupture_base_probability=_get_ratio(s, "candidacy", "rupture_base_probability"),
        rupture_signature_ratio=_get_ratio(s, "candidacy", "rupture_signature_ratio"),
        max_candidates_hard_cap=_get_positive_int(s, "candidacy", "max_candidates_hard_cap"),
    )


def _parse_campaign(raw: dict[str, Any]) -> CampaignConfig:
    s = _section(raw, "campaign")
    return CampaignConfig(
        max_positioning_delta=_get_ratio(s, "campaign", "max_positioning_delta"),
        max_positioning_shifts=_get_positive_int(s, "campaign", "max_positioning_shifts"),
    )


def _parse_legitimacy(raw: dict[str, Any]) -> LegitimacyConfig:
    s = _section(raw, "legitimacy")
    if _get(s, "legitimacy", "recall_floor_indexed_on_L0", bool):
        raise PolityConfigError(
            "'legitimacy.recall_floor_indexed_on_L0': true is not supported -- §7.2 is TRANCHÉ, "
            "the recall floor is fixed by design (a moving floor destroys external legibility)"
        )
    return LegitimacyConfig(
        enabled=_get(s, "legitimacy", "enabled", bool),
        decay=_get_ratio(s, "legitimacy", "decay"),
        recall_floor=_get_ratio(s, "legitimacy", "recall_floor"),
        recall_floor_indexed_on_l0=False,
        recall_cooldown_ticks=_get_positive_int(s, "legitimacy", "recall_cooldown_ticks"),
        passive_erosion_weight=_get_ratio(s, "legitimacy", "passive_erosion_weight"),
    )


def _parse_pressure_menu(raw: dict[str, Any]) -> PressureMenuConfig:
    s = _section(raw, "pressure_menu")
    petition_enabled = _get(s, "pressure_menu", "petition_enabled", bool)
    mobilization_enabled = _get(s, "pressure_menu", "mobilization_enabled", bool)
    electoral_only = _get(s, "pressure_menu", "electoral_only", bool)
    if electoral_only and (petition_enabled or mobilization_enabled):
        raise PolityConfigError(
            "'pressure_menu.electoral_only': true requires both petition_enabled and "
            "mobilization_enabled to be false (§7bis.8 -- one 4-modality variable, not two "
            "independent booleans)"
        )
    return PressureMenuConfig(
        petition_enabled=petition_enabled,
        mobilization_enabled=mobilization_enabled,
        electoral_only=electoral_only,
    )


_MANDATE_PLEDGE_SCOPES = {"top_k_priorities", "full_platform"}
_MANDATE_DEVIATION_METRICS = {"weighted_euclidean"}


def _parse_mandate(raw: dict[str, Any]) -> MandateConfig:
    s = _section(raw, "mandate")
    return MandateConfig(
        enabled=_get(s, "mandate", "enabled", bool),
        pledge_scope=_get_enum(s, "mandate", "pledge_scope", _MANDATE_PLEDGE_SCOPES),
        pledge_top_k=_get_positive_int(s, "mandate", "pledge_top_k"),
        deviation_metric=_get_enum(s, "mandate", "deviation_metric", _MANDATE_DEVIATION_METRICS),
        deviation_log_threshold=_get_ratio(s, "mandate", "deviation_log_threshold"),
        max_response_delta=_get_ratio(s, "mandate", "max_response_delta"),
        max_response_shifts=_get_positive_int(s, "mandate", "max_response_shifts"),
    )


_CONFIDENCE_VOTE_FORMATS = {"binary"}


def _parse_petition(raw: dict[str, Any]) -> PetitionConfig:
    s = _section(raw, "petition")
    if _get(s, "petition", "concurrent_allowed", bool):
        raise PolityConfigError(
            "'petition.concurrent_allowed': true is not supported in v4 -- single open petition "
            "per target only (also keeps act=1 sign unambiguous with no petition_id on the wire)"
        )
    return PetitionConfig(
        enabled=_get(s, "petition", "enabled", bool),
        signature_threshold=_get_ratio(s, "petition", "signature_threshold"),
        cooldown_ticks=_get_positive_int(s, "petition", "cooldown_ticks"),
        petition_lifespan_ticks=_get_positive_int(s, "petition", "petition_lifespan_ticks"),
        confidence_vote_format=_get_enum(s, "petition", "confidence_vote_format", _CONFIDENCE_VOTE_FORMATS),
        concurrent_allowed=False,
        weight_in_ecart=_get_ratio(s, "petition", "weight_in_ecart"),
    )


def _parse_street_pressure(raw: dict[str, Any]) -> StreetPressureConfig:
    s = _section(raw, "street_pressure")
    return StreetPressureConfig(
        enabled=_get(s, "street_pressure", "enabled", bool),
        decay=_get_ratio(s, "street_pressure", "decay"),
        weight_in_ecart=_get_ratio(s, "street_pressure", "weight_in_ecart"),
        visible_to_representative=_get(s, "street_pressure", "visible_to_representative", bool),
    )


_AWAKENING_SOURCES = {"persona_base_threshold"}
_SOCIAL_GRAPH_TOPOLOGIES = {"watts_strogatz", "erdos_renyi", "barabasi_albert"}
_SORTITION_SELECTION_MODES = {"uniform_random", "stratified_demographic"}
_SORTITION_VETO_POWERS = {"suspensive_limited", "consultative_only"}


def _parse_awakening(raw: dict[str, Any]) -> AwakeningConfig:
    s = _section(raw, "awakening")
    modulation = _section(s, "context_modulation")
    if not _get(s, "awakening", "no_consultation_cap", bool):
        raise PolityConfigError(
            "'awakening.no_consultation_cap': false is not supported -- §15bis.1 is TRANCHÉ, no "
            "cap on consultations per tick (self-hosted inference: a spike costs time, not money)"
        )
    return AwakeningConfig(
        enabled=_get(s, "awakening", "enabled", bool),
        source=_get_enum(s, "awakening", "source", _AWAKENING_SOURCES),
        context_modulation=AwakeningContextModulation(
            mandate_deviation=_get(modulation, "awakening.context_modulation", "mandate_deviation", bool),
            ticks_to_election=_get(modulation, "awakening.context_modulation", "ticks_to_election", bool),
            neighbors_acting=_get(modulation, "awakening.context_modulation", "neighbors_acting", bool),
            event_salience=_get(modulation, "awakening.context_modulation", "event_salience", bool),
        ),
        modulation_amplitude=_get_ratio(s, "awakening", "modulation_amplitude"),
        no_consultation_cap=True,
    )


def _parse_events(raw: dict[str, Any]) -> EventsConfig:
    s = _section(raw, "events")
    scandal_enabled = _get(s, "events", "scandal_enabled", bool)
    economic_shock_enabled = _get(s, "events", "economic_shock_enabled", bool)
    enabled = _get(s, "events", "enabled", bool)
    if enabled != (scandal_enabled or economic_shock_enabled):
        raise PolityConfigError(
            "'events.enabled' must equal 'events.scandal_enabled or events.economic_shock_enabled' "
            "-- these describe the same fact (§8) and must not drift apart"
        )
    return EventsConfig(
        enabled=enabled,
        scandal_enabled=scandal_enabled,
        scandal_rate_per_tick=_get_ratio(s, "events", "scandal_rate_per_tick"),
        scandal_magnitude=_get_ratio(s, "events", "scandal_magnitude"),
        economic_shock_enabled=economic_shock_enabled,
        economy_ar1_phi=_get_ratio(s, "events", "economy_ar1_phi"),
        economy_ar1_sigma=_get_ratio(s, "events", "economy_ar1_sigma"),
        economy_shock_threshold=_get_ratio(s, "events", "economy_shock_threshold"),
        salience_decay=_get_ratio(s, "events", "salience_decay"),
        max_reaction_delta=_get_ratio(s, "events", "max_reaction_delta"),
    )


def _parse_social_graph(raw: dict[str, Any]) -> SocialGraphConfig:
    s = _section(raw, "social_graph")
    if _get(s, "social_graph", "evolving", bool):
        raise PolityConfigError(
            "'social_graph.evolving': true is not supported -- homophily-driven graph evolution is "
            "an open design point (§5), not yet implemented"
        )
    return SocialGraphConfig(
        enabled=_get(s, "social_graph", "enabled", bool),
        topology=_get_enum(s, "social_graph", "topology", _SOCIAL_GRAPH_TOPOLOGIES),
        mean_degree=_get_positive_int(s, "social_graph", "mean_degree"),
        rewiring_prob=_get_ratio(s, "social_graph", "rewiring_prob"),
        evolving=False,
    )


def _parse_sortition_chamber(raw: dict[str, Any]) -> SortitionChamberConfig:
    s = _section(raw, "sortition_chamber")
    selection = _get_enum(s, "sortition_chamber", "selection", _SORTITION_SELECTION_MODES)
    if selection != "uniform_random":
        raise PolityConfigError(
            "'sortition_chamber.selection': 'stratified_demographic' is not supported -- v6b's MVP "
            "only implements uniform_random (§6bis.3)"
        )
    if _get(s, "sortition_chamber", "overlaps_with_assembly", bool):
        raise PolityConfigError(
            "'sortition_chamber.overlaps_with_assembly': true is not supported -- no individual "
            "deputy Citizen is tracked in this codebase (Office.DEPUTY is reserved, never assigned), "
            "so there is no legislative membership to overlap with"
        )
    if _get(s, "sortition_chamber", "renewable", bool):
        raise PolityConfigError(
            "'sortition_chamber.renewable': true is not supported -- v6b's selection design assumes "
            "strict one-shot-ever eligibility (§6bis.3)"
        )
    return SortitionChamberConfig(
        enabled=_get(s, "sortition_chamber", "enabled", bool),
        seats=_get_positive_int(s, "sortition_chamber", "seats"),
        term_years=_get_positive_int(s, "sortition_chamber", "term_years"),
        renewable=False,
        selection="uniform_random",
        overlaps_with_assembly=False,
        veto_power=_get_enum(s, "sortition_chamber", "veto_power", _SORTITION_VETO_POWERS),
        veto_delay_ticks=_get_positive_int(s, "sortition_chamber", "veto_delay_ticks"),
        max_deliberation_delta=_get_ratio(s, "sortition_chamber", "max_deliberation_delta"),
        max_deliberation_shifts=_get_positive_int(s, "sortition_chamber", "max_deliberation_shifts"),
    )


def _parse_journal(raw: dict[str, Any]) -> JournalConfig:
    s = _section(raw, "journal")
    return JournalConfig(
        enabled=_get(s, "journal", "enabled", bool),
        format=_get_enum(s, "journal", "format", {"jsonl", "parquet"}),
        output_dir=_get(s, "journal", "output_dir", str),
        snapshot_every_ticks=_get_positive_int(s, "journal", "snapshot_every_ticks"),
        log_non_events=_get(s, "journal", "log_non_events", bool),
        index_after_run=_get(s, "journal", "index_after_run", bool),
        decode_codebook_on_index=_get(s, "journal", "decode_codebook_on_index", bool),
    )


def _parse_metrics(raw: dict[str, Any]) -> MetricsConfig:
    s = _section(raw, "metrics")
    for unimplemented_key, palier in (
        ("platform_convergence", "v2"),
        ("mobilization_nonlinearity", "v6"),
        ("polarization", "v6"),
    ):
        if _get(s, "metrics", unimplemented_key, bool):
            raise PolityConfigError(
                f"'metrics.{unimplemented_key}': true is not supported -- indexer.py does not "
                f"implement this [{palier}] metric yet"
            )
    return MetricsConfig(
        compute_every_ticks=_get_positive_int(s, "metrics", "compute_every_ticks"),
        effective_parties=_get(s, "metrics", "effective_parties", bool),
        cohabitation_rate=_get(s, "metrics", "cohabitation_rate", bool),
        coalition_lifespan=_get(s, "metrics", "coalition_lifespan", bool),
        mandate_deviation=_get(s, "metrics", "mandate_deviation", bool),
        lame_duck_deviation_delta=_get(s, "metrics", "lame_duck_deviation_delta", bool),
        inaction_rate=_get(s, "metrics", "inaction_rate", bool),
        pressure_lever_mix=_get(s, "metrics", "pressure_lever_mix", bool),
        petition_success_rate=_get(s, "metrics", "petition_success_rate", bool),
        stance_distribution=_get(s, "metrics", "stance_distribution", bool),
    )


def _parse_llm(raw: dict[str, Any]) -> LlmConfig:
    s = _section(raw, "llm")
    enabled = _get(s, "llm", "enabled", bool)

    base_url = _get(s, "llm", "base_url", str)
    if not base_url or not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise PolityConfigError(f"'llm.base_url': must start with http:// or https://, got {base_url!r}")
    base_url = base_url.rstrip("/")

    model = _get(s, "llm", "model", str)
    if ":" not in model or model.endswith(":latest"):
        raise PolityConfigError(
            f"'llm.model': must be pinned to a specific, non-'latest' tag (e.g. 'qwen3:8b'), got {model!r}"
        )

    # Design doc §4.2 (B2): temperature=0 is a hard determinism requirement
    # once the LLM path is actually enabled — reject rather than silently
    # accept a config that would produce irreproducible runs.
    temperature = float(_get(s, "llm", "temperature", (int, float)))
    if enabled and temperature != 0.0:
        raise PolityConfigError(f"'llm.temperature': must be 0.0 when llm.enabled is true, got {temperature}")

    recycle_after_n_calls = _get_optional_int(s, "llm", "recycle_after_n_calls")
    if recycle_after_n_calls is not None and recycle_after_n_calls <= 0:
        raise PolityConfigError(
            f"'llm.recycle_after_n_calls': must be a positive integer or null, got {recycle_after_n_calls}"
        )

    return LlmConfig(
        enabled=enabled,
        provider=_get_enum(s, "llm", "provider", _LLM_PROVIDERS),
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_batch_size=_get_positive_int(s, "llm", "max_batch_size"),
        batch_sharding=_get_enum(s, "llm", "batch_sharding", _LLM_SHARDINGS),
        cache_backend=_get_enum(s, "llm", "cache_backend", _LLM_CACHE_BACKENDS),
        cache_url=_get(s, "llm", "cache_url", str),
        rationale_mode=_get_enum(s, "llm", "rationale_mode", _LLM_RATIONALE_MODES),
        codebook_version=_get(s, "llm", "codebook_version", str),
        personas_count=_get_positive_int(s, "llm", "personas_count"),
        max_batch_replays=_get_nonneg_int(s, "llm", "max_batch_replays"),
        recycle_after_n_calls=recycle_after_n_calls,
    )


def _parse_parallel(raw: dict[str, Any]) -> ParallelConfig:
    s = _section(raw, "parallel")
    return ParallelConfig(
        runs_in_parallel=_get_positive_int(s, "parallel", "runs_in_parallel"),
        intra_run_workers=_get_positive_int(s, "parallel", "intra_run_workers"),
    )


def load_config(path: Path | str | None = None) -> PolityConfig:
    """Load and validate polity_config.yaml. Raises PolityConfigError on any
    structural problem — never lets a malformed file fail silently or with a
    bare stdlib exception several frames away from the offending key."""
    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise PolityConfigError(f"config file not found: {config_path}")

    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolityConfigError(f"could not read {config_path}: {exc}") from exc

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolityConfigError(f"invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise PolityConfigError(f"{config_path}: top level must be a mapping, got {type(raw).__name__}")

    run = _parse_run(raw)
    legitimacy = _parse_legitimacy(raw)
    pressure_menu = _parse_pressure_menu(raw)
    petition = _parse_petition(raw)
    street_pressure = _parse_street_pressure(raw)
    awakening = _parse_awakening(raw)
    events = _parse_events(raw)
    social_graph = _parse_social_graph(raw)
    sortition_chamber = _parse_sortition_chamber(raw)

    # Cross-section rules (§7bis.2/§7bis.6) -- each section parses in
    # isolation above; these are the invariants that only make sense once
    # more than one section is known, so they live here rather than in any
    # single _parse_* function.
    if pressure_menu.petition_enabled != petition.enabled:
        raise PolityConfigError(
            "'pressure_menu.petition_enabled' and 'petition.enabled' disagree -- these two keys "
            "describe the same fact (§7bis.2) and must not drift apart"
        )
    if pressure_menu.mobilization_enabled != street_pressure.enabled:
        raise PolityConfigError(
            "'pressure_menu.mobilization_enabled' and 'street_pressure.enabled' disagree -- "
            "these two keys describe the same fact (§7bis.2) and must not drift apart"
        )
    weight_sum = petition.weight_in_ecart + street_pressure.weight_in_ecart
    if abs(weight_sum - 1.0) > 1e-9:
        raise PolityConfigError(
            f"'petition.weight_in_ecart' + 'street_pressure.weight_in_ecart' must sum to 1.0 "
            f"(w_pet + w_mob, §7bis.6), got {weight_sum}"
        )
    if (petition.enabled or street_pressure.enabled) and not legitimacy.enabled:
        raise PolityConfigError(
            "'legitimacy.enabled' must be true when 'petition.enabled' or 'street_pressure.enabled' "
            "is true -- écart(t) from either lever has nowhere to go without L(t) tracked (§7bis.6)"
        )
    if (petition.enabled or street_pressure.enabled) and not awakening.enabled:
        raise PolityConfigError(
            "'awakening.enabled' must be true when 'petition.enabled' or 'street_pressure.enabled' "
            "is true -- a citizen lever with nobody ever consulted (§7bis.9d) is a silently dead "
            "experiment, indistinguishable from 'pressure_menu.electoral_only'"
        )
    if events.enabled and not awakening.enabled:
        raise PolityConfigError(
            "'awakening.enabled' must be true when 'events.enabled' is true -- a shock with nobody "
            "ever consulted (§7bis.9d) is a silently dead experiment (v5 §8)"
        )
    if events.enabled and not awakening.context_modulation.event_salience:
        raise PolityConfigError(
            "'awakening.context_modulation.event_salience' must be true when 'events.enabled' is "
            "true -- a shock with nothing in the awakening gate to modulate is a silently dead "
            "experiment (v5 §8)"
        )
    if awakening.context_modulation.neighbors_acting and not social_graph.enabled:
        raise PolityConfigError(
            "'social_graph.enabled' must be true when "
            "'awakening.context_modulation.neighbors_acting' is true -- there is no graph to "
            "compute the term from otherwise (§5/§7bis.9f). The reverse is not required: "
            "'social_graph.enabled' alone (without this flag) is a real arm -- the graph still "
            "feeds pressure_action's ctx.neighbors_acting without also modulating who gets "
            "consulted"
        )
    if sortition_chamber.enabled and run.population_size < sortition_chamber.seats:
        raise PolityConfigError(
            "'sortition_chamber.seats' cannot exceed 'run.population_size' when "
            "'sortition_chamber.enabled' is true -- a config that can't seat even one full chamber "
            "is a degenerate arm (§6bis.3)"
        )

    return PolityConfig(
        run=run,
        institutions=_parse_institutions(raw),
        parties=_parse_parties(raw),
        citizens=_parse_citizens(raw),
        candidacy=_parse_candidacy(raw),
        campaign=_parse_campaign(raw),
        legitimacy=legitimacy,
        pressure_menu=pressure_menu,
        mandate=_parse_mandate(raw),
        petition=petition,
        street_pressure=street_pressure,
        awakening=awakening,
        events=events,
        social_graph=social_graph,
        sortition_chamber=sortition_chamber,
        journal=_parse_journal(raw),
        metrics=_parse_metrics(raw),
        llm=_parse_llm(raw),
        parallel=_parse_parallel(raw),
        raw=raw,
    )
