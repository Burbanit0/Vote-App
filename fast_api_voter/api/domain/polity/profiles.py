"""The run profiles: how a flagship config is built, and what each --profile does to it.

Moved out of scripts/run_polity_flagship.py, where scripts and tests imported them from a launcher.
`flagship_config` is the one place a run's config is assembled from polity_config.yaml and a run's
parameters; `PROFILES` maps --profile to what it does on top (flagship, exploration, scenario). No behaviour
changed in the move: the block is verbatim apart from the underscore dropped from four names.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from pathlib import Path

from api.domain.polity.config import ARTICLES, PolityConfig, load_config

LLM_TURNOUT_COST = 0.04
"""S4.1 on the LLM path (plan-polity-build-order.md, "Result of step 2"), kept through OBS-042's rule.
Adopted when a voter stayed home if their two best options were close, a rule that kept more voters
home the larger the field. Under the rule that replaced it (best candidate against the blank ballot)
it keeps about a tenth of voters home whatever the field's size -- the property the change was made
for -- and was kept for that on 2026-10-06, against ADR-011's turnout fact: on the deterministic twin,
which has no disengagement, it gives 90% turnout, past the 85% ceiling. 0.15 is where all four facts
hold on the twin (scripts/calibrate_turnout_rule_results.md), but keeps 44% home with 2 candidates and
28% with 30. In the exploration profile, where agents run, ADR-021's disengagement already keeps about
a quarter of citizens home. The deterministic twin, which shares polity_config.yaml, qualified nothing
in S4.1, so the file keeps 0."""


def flagship_config(
    *,
    engine: str,
    years: int,
    population: int,
    seats: int,
    seed: int,
    output_dir: Path,
    max_batch_replays: int,
    provider: str | None,
    workers: int,
    staggered_election: bool = False,
    model: str | None = None,
    reproducibility: str = "strict",
    vote_mode: str | None = None,
    profile: str = "flagship",
    base_url: str | None = None,
    threshold: float | None = None,
    freeze_amendments: bool = False,
    without: Sequence[str] = (),
) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(
            config.run,
            seed=seed,
            duration_years=years,
            population_size=population,
            run_label=f"flagship-{years}y-p{population}",
        ),
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        # --- full richness: every substantive mechanism on ---
        # Three flags here are shipped `false` and are NOT merely defaults left
        # alone -- all three are implemented, consequential mechanisms, and the
        # flagship is the run that is supposed to exercise them:
        #   * candidacy.rupture_path_enabled -- the §2.4 rare path by which a
        #     citizen declares against their own party. Without it the candidate
        #     field is a flat one-nominee-per-party at every scale, which is also
        #     why `max_candidates_hard_cap` can never bind and why Class B counts
        #     zero rupture declarations (measured: polity_scale_gate_pop500_
        #     results.md).
        #   * institutions.blank_vote_competitive -- v4 Lot 9's live mechanism
        #     letting a blank plurality invalidate a presidential election and
        #     force a rerun with the previous field barred. It is bounded by
        #     reelection_max_attempts=2, so it cannot loop.
        #   * institutions.snap_election_on_recall -- Track A3 (2026-09-11,
        #     lets-build-a-solid-spicy-otter.md). Without it Stage 3's own scale
        #     probe sat vacant 15 of 32 ticks (office_occupancy=0.5152) after a
        #     single recall, and its deterministic twin sat vacant WORSE
        #     (0.2727, two recalls) -- the vacancy is structural to
        #     simple_rules.py's own recall logic, not an LLM artifact, so a
        #     flagship run with this left off would spend a large fraction of
        #     its wall-clock on a polity with no accountability layer running
        #     at all (pressure_action/representative_response/petitions all
        #     require a sitting president). Bounded the same way blank-vote
        #     reruns already are: reuses PendingRerun, capped by
        #     reelection_max_attempts, cannot loop.
        # Deliberately still OFF: social_graph.evolving / sortition_chamber.renewable,
        # which load_config rejects outright as designs this codebase decided against.
        candidacy=dataclasses.replace(config.candidacy, rupture_path_enabled=True),
        institutions=dataclasses.replace(
            config.institutions,
            blank_vote_competitive=True,
            snap_election_on_recall=True,
            # Track E, wired 2026-09-13 -- opt-in via --staggered-election, and
            # deliberately NOT force-enabled like the three flags above.
            # Turning it on changes the RNG draw order, so a run with it on is
            # not comparable to the p100 seed sweep or to Phase 7 Stage 3,
            # both of which ran without it. Same single-variable discipline as
            # the version-pin decision in plan-distribution-positions-seeds.md
            # §4.2: this makes Track E *runnable* from the flagship harness,
            # it does not silently change what the next run measures.
            staggered_election=staggered_election,
        ),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        social_graph=dataclasses.replace(config.social_graph, enabled=True),
        events=dataclasses.replace(
            config.events, enabled=True, scandal_enabled=True, economic_shock_enabled=True
        ),
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(
                config.awakening.context_modulation,
                # both required by config.validate_config once
                # events/social_graph are on
                event_salience=True,
                neighbors_acting=True,
            ),
        ),
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=seats),
        pressure_menu=dataclasses.replace(
            config.pressure_menu,
            electoral_only=False,
            petition_enabled=True,
            mobilization_enabled=True,
        ),
        parallel=dataclasses.replace(config.parallel, intra_run_workers=workers),
    )

    if engine == "llm":
        llm = dataclasses.replace(config.llm, enabled=True, max_batch_replays=max_batch_replays, reproducibility=reproducibility)
        config = dataclasses.replace(config, vote=dataclasses.replace(config.vote, turnout_cost=LLM_TURNOUT_COST))
        if provider is not None:
            # Baseline A/B only (plan Phase 0): the shipped default is the
            # single source of truth for which provider production uses --
            # this override exists to time the OTHER one, not to make the
            # choice configurable per run.
            provider_url = {
                "vllm": "http://localhost:8000/v1",
                "ollama": "http://localhost:11434/v1",
            }[provider]
            llm = dataclasses.replace(llm, provider=provider, base_url=provider_url)
        if base_url is not None:
            # A server that is not on localhost: an SSH-tunnelled rented GPU, or another port.
            llm = dataclasses.replace(llm, base_url=base_url)
        if model is not None:
            # S2.3: the name the server serves the weights under. validate_config refuses a
            # model with no profile in model_profiles.py -- its chunk sizes and thinking
            # switch would otherwise be another model's.
            llm = dataclasses.replace(llm, model=model)
        config = dataclasses.replace(config, llm=llm)
    config = PROFILES[profile](config)
    if engine == "llm" and vote_mode is not None:
        # S4.1 (ADR-011): the shipped utility mode asks the model for an audit sample of ballots only;
        # `llm` has it cast every ballot, as every run before S4.1 did. A flag outranks the profile, so a
        # contradiction (the scenario profile and --vote-mode llm) reaches validate_config and is refused
        # there instead of being silently rewritten.
        config = dataclasses.replace(config, vote=dataclasses.replace(config.vote, mode=vote_mode))
    return experiment_overrides(config, threshold=threshold, freeze_amendments=freeze_amendments, without=without)


WITHOUT = {"forward-stakes": "forward_stakes", "ambition-goal": "ambition_goal"}
"""OBS-048's arms: a mechanism `--without` turns off, and the agents switch that does it."""


def experiment_overrides(
    config: PolityConfig, *, threshold: float | None, freeze_amendments: bool, without: Sequence[str] = (),
) -> PolityConfig:
    """PLAN_BEYOND_CI W2.1's two knobs, applied after the profile, which sets amendments and
    regime from llm.enabled and would otherwise overwrite them. `threshold` is the seat bar
    under test. `freeze_amendments` keeps it there: the chamber can no longer amend the
    constitution (OBS-040's seed 1 lowered its own bar mid-run), so regime acts go too
    (config.py: they are a field of the president's amendment turn), and so do
    referendums on the voting method, and so do scripted amendments."""
    if threshold is not None:
        article = ARTICLES["institutions.electoral_threshold"]
        if not article.allows(threshold):
            raise ValueError(
                f"--threshold {threshold}: the article allows {article.low} to {article.high} (a share: 0.03 for 3%)"
            )
        config = dataclasses.replace(
            config, institutions=dataclasses.replace(config.institutions, electoral_threshold=threshold),
        )
    if freeze_amendments:
        config = dataclasses.replace(
            config,
            agents=dataclasses.replace(config.agents, amendments=False, amendment_stakes=False),
            regime=dataclasses.replace(config.regime, enabled=False),
            constitution=dataclasses.replace(config.constitution, referendum="never", scripted=()),
        )
    for name in without:  # OBS-048's arms; checked after the freeze, which would leave them nothing to turn off
        if name not in WITHOUT:
            raise ValueError(f"--without {name!r}: one of {sorted(WITHOUT)}")
        if not (config.agents.amendment_stakes if name == "forward-stakes" else config.agents.president):
            raise ValueError(f"--without {name}: nothing to turn off -- it needs the "
                             f"{'amendment stakes' if name == 'forward-stakes' else 'president agent'} (the exploration profile, unfrozen)")
        config = dataclasses.replace(config, agents=dataclasses.replace(config.agents, **{WITHOUT[name]: False}))
    return config


def scenario_config(config: PolityConfig) -> PolityConfig:
    """plan-scenarios-v1 step 2: the exploration profile with the crowd by rule and the model playing
    the agents only (llm.crowd off: the utility ballot, the ambition rule for candidacy, the
    deterministic pressure rule, form_coalition unless the leaders negotiate, no chamber shifts),
    the forum capped at 10 speakers a tick (it was 60% of an exploration run's model time), and
    views that move: drift 0.18 (ADR-032's random-walk arm; 0.02, ADR-012's smallest, left a four-year
    panel correlation of 0.996, citizens who never change their minds; 0.18 puts it at 0.88, inside
    ADR-012's D1 band of 0.70 to 0.90), ADR-033's radicalisation (once events have shaken the polity, angry citizens
    step away from the president; anger narrows what they listen to), and ADR-034's economic voting (voters
    weigh the economy at the election, so good and bad times move the incumbent's approval and the vote; a
    scenario's own crises go in `events.scripted`) at 0.3, not ADR-034's 1.0: the term is the same for every
    voter, and at 1.0 it swung whole blocs between elections (mean legislative volatility 0.36, inside the
    band in 35% of runs, on ADR-038's 60-point sample; ADR-038 takes the largest weight that keeps two thirds of the runs inside it), voters who abstain when
    their best candidate is within 0.02 of the blank ballot on the deterministic engine (ADR-039: at 0 nobody abstained
    out of indifference, and turnout sat above the band's 0.85 in 42% of runs; the model engine keeps LLM_TURNOUT_COST), and ADR-035's generational replacement (3% of the citizens
    a year are replaced by newcomers drawn around their circle, spread 0.35: over thirty years the spread of
    positions grows by 83% instead of 133%, and the ten-seed labels go from 0.47 to 1.36 bits, measured with economic voting
    at 1.0 and the version-2 labels; see the ADR). On the deterministic engine it is
    the exploration profile plus those."""
    explored = exploration_config(config)
    return dataclasses.replace(
        explored,
        llm=dataclasses.replace(explored.llm, crowd=False),
        vote=dataclasses.replace(
            # ADR-039: the twin's cost; the model engine keeps its own (LLM_TURNOUT_COST, a decision of its own)
            explored.vote, mode="utility", economic_voting=0.3,
            turnout_cost=explored.vote.turnout_cost if explored.llm.enabled else 0.02,
        ),
        agents=dataclasses.replace(explored.agents, forum_size=10),
        dynamics=dataclasses.replace(explored.dynamics, drift_std=0.18, radical_step=0.5, anger_narrows_bound=0.3),
        citizens=dataclasses.replace(
            explored.citizens, static_population=False, replacement_per_year=0.03, newcomer_spread=0.35
        ),
    )


def exploration_config(config: PolityConfig) -> PolityConfig:
    """The agency roadmap's exploration profile (plan-polity-agency-roadmap.md, D4): the
    flagship plus the mechanisms that ship off, turned on without their calibration gate.
    Phase 1.1: the approval loop -- approval feeds legitimacy, the vote judges the record
    (S4.1's top measured `approval`) and the policy of the term (ADR-009's lowest
    nonzero `policy_retrospection`), legislation runs, and a former president runs on
    their conduct in office. Phases 1.2-1.4: the president and the presidential nominees are
    agents (ADR-014) -- they need the LLM engine, so the deterministic twin keeps the formula --
    whose turns are sampled at 0.6, Qwen3's recommended temperature in thinking mode. Phase 2.2-2.3:
    the president proposes amendments to the constitution and the sortition chamber votes them
    (ADR-015); the flagship's chamber is already on. Phase 3: the chamber and the recent petition launchers post on a forum (ADR-016) and may change
    their minds there, on a population whose views also drift toward their neighbours' (ADR-012, ADR-017).
    Phase 4.1: they may also join, leave or found a party (ADR-018). Phase 4.2: party
    leaders negotiate the coalition in place of the collapsed crowd batch (ADR-019). Phase 4.3: the citizens vote on a
    voting-method change when enough of them petition against it (ADR-020). Phase 4.4: a citizen
    angry enough for long enough stops voting and signing, and may leave for good (ADR-021). Phase 5.1: a president in their last term may refuse to leave, and the
    kernel rolls whether they stay (ADR-022). Phase 5.2: a nominee may campaign on one issue, and the
    citizens it reaches come to weigh that issue more when they compare candidates (ADR-023). At a legislative
    election a voter whose party the sincere vote leaves below the threshold may desert it for the best party
    above it (ADR-024); 0.07 is the median cost of that move to the stranded voters of phase11's final populations.
    A president is recalled when the population is against them, not a mobilised few (ADR-025, OBS-047): pressure
    weighs on legitimacy like support does, and legitimacy under the floor calls a confidence vote that only a
    majority against the president loses."""
    return dataclasses.replace(
        config,
        legitimacy=dataclasses.replace(
            config.legitimacy, approval_weight=0.5, pressure_like_support=True, floor_calls_vote=True,
        ),
        vote=dataclasses.replace(
            config.vote, approval=0.1, approval_party_carryover=0.5, policy_retrospection=2.0, strategic_margin=0.07,
        ),
        legislation=dataclasses.replace(config.legislation, enabled=True),
        candidacy=dataclasses.replace(config.candidacy, incumbent_keeps_record=True),
        constitution=dataclasses.replace(config.constitution, referendum="petition"),
        agents=dataclasses.replace(
            config.agents, president=config.llm.enabled, nominees=config.llm.enabled, amendments=config.llm.enabled,
            amendment_stakes=config.llm.enabled,
            forum=config.llm.enabled, coalition=config.llm.enabled, stance_step=0.25 if config.llm.enabled else 0.0,
            turn_temperature=0.6, party_moves=config.llm.enabled,
        ),
        parties=dataclasses.replace(config.parties, birth_enabled=config.llm.enabled, death_enabled=config.llm.enabled),
        emotions=dataclasses.replace(config.emotions, enabled=True, disengage_anger=0.4, return_anger=0.2, exit_anger=0.85),
        dynamics=dataclasses.replace(config.dynamics, enabled=True, susceptibility=0.9, influence_step=0.1),
        regime=dataclasses.replace(config.regime, enabled=config.llm.enabled),
        campaign=dataclasses.replace(
            config.campaign, salience_step=0.15 if config.llm.enabled else 0.0, max_reached=12 if config.llm.enabled else 0,
        ),
    )


PROFILES: dict[str, Callable[[PolityConfig], PolityConfig]] = {
    "flagship": lambda config: config,
    "exploration": exploration_config,
    "scenario": scenario_config,
}
"""--profile: what each profile does to the flagship config. run_polity_seed_sweep.py reads the keys."""
