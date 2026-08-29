"""
scripts/run_v6b_acceptance.py

v6b Lot 4's acceptance deliverable: the elected-vs-sortition comparison design doc §6bis.3 itself
frames as its whole reason for existing --

    "Interet scientifique direct : groupe de controle insensible a toute pression electorale
    (aucune reelection possible), comparable a la chambre elue soumise aux trois canaux du §7bis.
    Hypothese a tester : l'absence de pression electorale produit-elle des decisions plus
    « sinceres » (alignees sur ses propres issue_positions) ou plus erratiques (aucun garde-fou de
    responsabilite) ?"

-- and §6bis.5's own interaction table names it explicitly: "Groupe de controle elu vs tire au
sort." Unlike v6a Lot 4 (which isolated ONE variable, neighbors_acting, and could therefore cite an
already-committed run as its own atomized reference), this comparison needs BOTH quantities
(mandate_deviation for the elected side, chamber_deviation for the sortition side) from the SAME
run, at the SAME ticks -- there is no existing acceptance row that already carries both, so this
lot runs one new, single, self-contained comparison rather than citing a prior one.

The elected side reuses run_acceptance_comparison.py's own "both" arm shape verbatim (full pressure
menu -- petition + mobilization, legitimacy/mandate/awakening all enabled, ambition_threshold=0.0
guaranteeing a real elected president) -- NOT electoral_only/mobilization_only/petition_only:
§6bis.3's own comparison is against a president "soumise aux TROIS canaux du §7bis", all three, not
one isolated lever, unlike v6a Lot 4's own single-variable-isolation goal. social_graph.enabled and
events.enabled both stay at their shipped-off default -- the same confound-avoidance call v5 Lot 5
and v6a Lot 4 already made independently, restated here for a third time: neither is part of
§6bis.3's own comparison, and adding either would introduce a second, simultaneously-changing
variable this lot's own comparison doesn't ask for.

sortition_chamber stays at every shipped default (seats=30, term_years=1, max_deliberation_delta=0.3,
max_deliberation_shifts=3) -- a measurement of the shipped configuration, not a calibration sweep;
v6b Lot 2's own sortition_calibration_results.md already measured chamber-size behavior at exactly
these values.

chamber_deviation itself required a small, deliberate production-code change (v6b Lot 4's own PR,
run_polity_simulation.py's _run_chamber_deliberation): the already-shipped-but-never-called
accountability.chamber_deviation(member) is now journaled as a new "chamber_deviation" key on every
chamber_deliberation event's own payload, computed AFTER chamber_position is updated (the
POST-decision value, mirroring mandate_deviation_recorded's own already-established convention) --
unlike v6a Lot 4 and v5 Lot 5, which both touched zero files under api/, this lot's own one addition
is what makes this comparison possible at all: chamber_deviation had no journal path before it.

Calibration-before-commit is a go/no-go CHECKPOINT here, not a sweep (the same shape v6a Lot 4
used): every value is already shipped and already measured independently (v4 Lot 8's own "both"
arm, v6b Lot 2's own pool-exhaustion calibration). Run --engine deterministic first (near-free,
seconds); confirm it produces the expected shape (zero chamber_deliberation events -- the
deterministic fallback IS the absence of the call, v6b Lot 3's own precedent -- sortition_rotation
events present, and a recall count / final mean_legitimacy in the same range as
both/deterministic/8y's own committed anchor, scripts/acceptance_v4_results.md: legitimacy_floor=2,
mean L 0.345 at 8y) before proceeding to the expensive --engine llm run.

Wall-clock forecast (not a promise -- the real run reports its own elapsed time, exactly like every
prior acceptance script): both/llm/8y's own already-measured 6311.7s (acceptance_v4_results.md) is
the elected side's own closest real anchor. The chamber side adds sortition_chamber.enabled=True at
shipped defaults -- _run_chamber_deliberation runs EVERY tick, not just rotation ticks, chunked at
_CHAMBER_MAX_CHUNK_SIZE=10 (v6b Lot 3's own finding) => 3 chunks/tick. The reliability spike measured
a chunk of 10 at ~79.5-80s (lot3_chamber_reliability_results.md, confirmatory diagnostics table). At
duration_years=8 (33 ticks, 0..32, matching every prior LLM acceptance run's own established
minimum-observability floor): 33 * 3 * ~80s ~= 7920s (~2.2h) for the chamber alone. Forecast total:
~6312s + 7920s ~= 14232s ~= 3.95h -- the most expensive single acceptance run in this palier's own
history, but not disproportionate: electoral_only/llm/8y already measured 11776.3s (~3.27h) in v4
Lot 8.

Usage:
    # calibration dry-run, deterministic, seconds -- compare its own printed recall count / final
    # mean_legitimacy against both/deterministic/8y's own committed anchor before proceeding
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine deterministic --output-dir scripts/acceptance_v6b_runs

    # the real qwen3:8b run, once the deterministic dry-run above looks safe
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine llm --max-batch-replays 2 --output-dir scripts/acceptance_v6b_runs

    # render the committed results doc from both arms' metrics.json/chamber.json
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --summarize scripts/acceptance_v6b_runs --results scripts/acceptance_v6b_results.md

--recall-floor (added 2026-08-22, second targeted run) -- the first run's own "both" arm confounded
§6bis.3's comparison: legitimacy.recall_floor's shipped value (0.2) combined with the "both" menu's
simultaneous petition+mobilization pressure crashed L below the floor within 1-2 ticks of BOTH
elections (the awakening gate's own post-election `proximity` term maximizes consultation at
exactly the worst moment for two independently-weighted, simultaneous levers to compound) --
office-occupancy ~6-9% of the run, nowhere near enough for representative_response/dt=6 to
accumulate a comparable mandate_deviation series. Pre-registered hypothesis: with recall_floor=0.0
and everything else about the "both" arm unchanged (same seed, same duration, same pressure menu),
office-occupancy rises enough for the comparison to actually run. Decision criterion, fixed before
launch: office-occupancy (fraction of ticks with a representative_response event) >= 70% -- met,
report mandate_deviation vs chamber_deviation directly; not met, report honestly and stop rather
than force a conclusion. recall_floor=0.0 is not a guess: crosses_floor's own docstring
(legitimacy.py) already proves, given update_legitimacy's [0,1] clamp, that the legitimacy-floor
recall provably never fires at this value -- a guarantee, not an empirical hope. The confidence-vote
recall path is deliberately left untouched (drift-linked, a genuine part of "l'apparat complet", not
the pathology being routed around). Runs into a SEPARATE --output-dir from the first arm (different
pre-registered question, not a rejoue -- mixing the two into one --summarize table would misleadingly
imply they answer the same question):

    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine deterministic --recall-floor 0.0 --output-dir scripts/acceptance_v6b_runs_recallfloor0
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine llm --recall-floor 0.0 --max-batch-replays 2 \\
        --output-dir scripts/acceptance_v6b_runs_recallfloor0
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --summarize scripts/acceptance_v6b_runs_recallfloor0 \\
        --results scripts/acceptance_v6b_recallfloor0_results.md

--menu (added later, third targeted run) -- the recall_floor=0.0 run above DID resolve the vacancy
confound (office_occupancy=1.0, zero recalls) and DID surface a real mandate_deviation metric bug
(pledge_scope=top_k_priorities, see accountability.py's own docstrings) -- but a literal zero floor
is scientifically inelegant: it doesn't test accountability, it switches accountability off and
says so in the config. A better-principled fix already exists in this project's own established
experimental design, needing no override at all: under pressure_menu.electoral_only=True,
petition_pressure(holder, ...) returns 0.0 structurally (no petition can ever be open),
holder.street_pressure stays permanently 0.0 (only ever written under street_pressure.enabled,
which electoral_only forces false via load_config's own cross-section rule), and the shipped
legitimacy.passive_erosion_weight is 0.0 -- so compose_ecart(0.0, 0.0, deviation, ...) ≡ 0.0
regardless of mandate.enabled, update_legitimacy reduces to L(t) = decay*L(t-1) + (1-decay)*m,
converging geometrically to the fixed point m, never dipping below min(L0, m). crosses_floor can
only fire if m < recall_floor -- which v4 Lot 8's own three electoral_only acceptance rows already
falsify empirically at the UNTOUCHED shipped recall_floor=0.2 (mean L 0.510/0.510/0.710 across
deterministic-30y, deterministic-8y and llm-8y, empty recalls column in all three;
acceptance_v4_results.md). THEORY.md §10.5 states the same property directly.

This costs nothing in exposure: _run_representative_responses (dt=6, the mechanism that produces
mandate_deviation drift) is gated on `config.llm.enabled and config.mandate.enabled` -- NEVER on
pressure_menu -- so it fires exactly as often under electoral_only as under both. v4 Lot 8's own
electoral_only/llm/8y row already shows a "ctx"-sourced mandate_dev series (source label present,
not absent -- dt=6 genuinely ran). The one real difference reaching the representative's own
decision context: ResponseContext.street becomes None rather than 0.0 ("a representative blind to
the street") -- legitimacy, mandate_dev, lame_duck, ticks_left all stay populated exactly as under
both.

What is genuinely unknown, and what this run exists to answer: whether drift MAGNITUDE stays
comparably informative once the street signal leaves the representative's own decision context.
v4's electoral_only/llm/8y row reported mandate_dev(last)=0.000(ctx) -- but under the TOP-K scope
(now known to be structurally blind), and only a last-tick value at that; no mean/max was ever
computed for that arm. Pre-registered expectation, fixed BEFORE launch:

STRUCTURAL (near-certain, falsifiable): recalls_by_trigger == {} at the untouched recall_floor=0.2;
office_occupancy == 1.0 on the llm arm with mandate_deviation_source == "ctx"; mean L flat within
each term in the 0.5-0.7 band (not the 0.345/0.405 the both arms produced); the chamber side
essentially unchanged from the recall_floor=0.0 run (chamber_deviation mean ~0.000036, ~99.7%
SINCERE_POSITION, last_seated_size==30, 990 chamber_deliberation events) -- ChamberContext carries
only ticks_left and sortition_rng is its own independent default_rng(seed) stream, architecturally
insulated from the pressure path. Falsifiers, named in advance: ANY recalled event falsifies the
structural argument and must be investigated before reporting; fewer than 33 representative_response
events or a non-"ctx" source means dt=6 didn't fire as predicted; a materially different chamber-side
result indicates an unpredicted coupling between the pressure path and the chamber, catchable for
free at the deterministic dry-run stage (check 5 below).

EMPIRICAL (genuinely open, NO number registered): the unified mandate deviation's own mean/max over
33 ticks. Three outcome branches, all informative, all named in advance: (a) comparable to the
recall_floor=0.0 run's own 0.1496/0.2312 -- drift is not street-driven, the strongest possible
corroboration, and the branch that lets §10.9 stop depending on the artificial recall_floor=0.0;
(b) materially lower but clearly nonzero -- street pressure was the dominant driver of the model's
own concessions, narrowing the headline claim to "the pressure channel", not "being elected" per se
-- still a real, publishable result; (c) ~0.000 -- without a pressure signal the representative has
no reason to move at all, a negative result about the mechanism itself. The decision criterion for
this run is NOT "the unified mean must exceed X" -- it is: report the number with whichever branch
it landed in, decided in advance of seeing it.

Deterministic dry run FIRST (~2-3s, near-free) -- nine checks, all read-only, before the LLM arm is
ever launched: (1) wall clock ~1.5-3s; (2) recalls_by_trigger == {} at the untouched recall_floor=0.2
-- the free, load-bearing structural check, contrasted against the both-menu deterministic arm's own
2 recalls at the same floor; (3) mean_legitimacy's last value ~0.51 (the electoral_only anchor), NOT
~0.345 (the both anchor) -- the check that distinguishes "the flag actually took effect" from "a
flag that silently did nothing"; (4) zero petition/mobilization-shaped events in the journal itself;
(5) sortition_rotation events byte-identical to the recall_floor=0.0 run's own deterministic arm
(same ticks, seated, vacated, pool_relaxed) -- provable since the sortition RNG stream, pool logic
and elections are all menu-blind and zero recalls in both runs implies identical incumbents implies
identical exclusions; any discrepancy here means the chamber isn't actually insulated from the
pressure path and the control design needs re-examining BEFORE four hours are spent; (6) config.json
records every expected field (menu, petition/street disabled, floor untouched at 0.2,
mandate/legitimacy/awakening/sortition_chamber all enabled, social_graph/events both off);
(7) chamber.json shows known_zero_by_construction: true; (8) office_occupancy is null on this arm,
correctly (no dt=6 without the LLM); (9) mandate_deviation_unified is None here too (no dt=6 events
to carry the key).

Wall-clock forecast, reasoned from measured numbers, not guessed. The naive shortcut -- v6b
both/llm/8y (recall_floor=0.0 run) measured 15874.6s; v4 both/llm/8y measured 6311.7s; the 9562.9s
difference is "what v6b adds on top of a v4 both baseline"; add that to v4's own electoral_only/
llm/8y anchor (11776.3s) for ~21339s (~5.9h) -- double-counts twice over: (1) occupancy is already
in BOTH terms being added (v4's both/llm/8y had 2 recalls i.e. partial vacancy i.e. fewer dt=6/dt=10
calls; v4's electoral_only row had zero recalls i.e. full occupancy, which is most of why it already
costs 1.87x the both arm; the recall_floor=0.0 run also had office_occupancy=1.0 -- so the "full
occupancy premium" is counted in both halves of the sum); (2) the two v4 rows predate this project's
current batching regime (commit ca02344 cut _CHAMBER_MAX_CHUNK_SIZE/_VOTE_CAST_MAX_CHUNK_SIZE from
10/25 down to 1; the recall_floor=0.0 run's own llm arm started AFTER that fix, the v4 rows are from
before it). The better-grounded anchor: this run differs from the recall_floor=0.0 run in exactly
one configured variable (the menu), and every dominant cost component is menu-independent in call
count, counted directly from that run's own journal: 990 chamber_deliberation calls (chunk 1,
architecturally insulated from the menu -- ChamberContext has one field, ticks_left), 300 vote_cast
calls (chunk 1, 100 voters x 3 elections, menu-blind), 300 candidacy_considered, 33
representative_response batches (occupancy 1.0 in both runs); only pressure_action (1358 events in
that run) is menu-sensitive, and only indirectly (the awakening gate itself is menu-blind; the menu
only restricts which acts appear in each citizen's own `available` list). The dominant single block
-- 990 chamber calls at a measured mean of ~6.9s each (lot3_chamber_reliability_results.md) -- alone
accounts for ~6900s, ~43% of that run's own total, invariant across menus by construction. Forecast:
~15900s (~4.4h), plausible band ~3.9-5.9h -- lower edge if a smaller mandate_dev raises the awakening
threshold and shrinks the consulted cohort, upper edge retained as the pessimistic (naive,
double-counted) anchor rather than discarded. Not a promise -- the run reports its own real elapsed
time.

--menu and --recall-floor stay ORTHOGONAL, not mutually exclusive: they compose freely (a
`--menu electoral_only --recall-floor 0.0` combination is redundant, never incoherent, and remains a
legitimate belt-and-braces diagnostic if a future run ever contradicts the structural argument
above) -- but run_arm prints an explicit stderr NOTE (not a warning) when the floor is overridden
under electoral_only, since it is provably inert there.

Naming note: this second run's own docstring section above prescribed
`--results scripts/acceptance_v6b_recallfloor0_results.md`, but that run was actually rendered into
`scripts/acceptance_v6b_results.md` (which documents runs 1 and 2 together) -- do not rename a
committed evidence doc to match a docstring; this third run writes its own file instead. Runs into
its own separate --output-dir, same "different pre-registered question, not a rejoue" reasoning as
--recall-floor's own section above -- do NOT --summarize scripts/acceptance_v6b_runs or
scripts/acceptance_v6b_runs_recallfloor0 after this lands; neither directory's metrics.json files
carry `_meta["menu"]`/`mandate_deviation_unified`, and a re-render would silently degrade
acceptance_v6b_results.md's own hand-written figures to "—":

    # 1 -- calibration dry run, deterministic, ~2-3s. Work through all nine checks above
    #      BEFORE launching anything expensive.
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine deterministic --menu electoral_only \\
        --output-dir scripts/acceptance_v6b_runs_electoral_only

    # 2 -- the real qwen3:8b arm. Forecast ~15900s (~4.4h), band ~3.9-5.9h.
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine llm --menu electoral_only --max-batch-replays 2 \\
        --output-dir scripts/acceptance_v6b_runs_electoral_only

    # 3 -- render THIS directory only.
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --summarize scripts/acceptance_v6b_runs_electoral_only \\
        --results scripts/acceptance_v6b_electoral_only_results.md

--recall-floor is deliberately ABSENT from all three -- the untouched shipped 0.2 is the entire
point of this run. Running the LLM arm above and writing up its results is a separate, later,
SEPARATELY AUTHORIZED step -- this docstring section designs and code-readies the run only.
THEORY.md §10.9/§10.10 must not be touched until the run exists and its numbers are in hand.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.indexer import RunMetrics, index_run, read_journal  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from ollama_uptime_guard import ensure_fresh_container  # noqa: E402


def _config_for_v6b_run(
    engine: str, *, duration_years: int, output_dir: Path, max_batch_replays: int,
    recall_floor: float = 0.2, menu: str = "both",
) -> PolityConfig:
    config = load_config()

    # menu="electoral_only": run_acceptance_comparison.py's own already-established
    # electoral_only shape (v4 Lot 8), copied verbatim -- petition/street_pressure are
    # left UNMODIFIED, not explicitly set enabled=False. Their shipped .enabled is
    # already false, and load_config's own cross-section rule already requires
    # pressure_menu.petition_enabled == petition.enabled (and the mobilization/street
    # equivalent) -- an explicit enabled=False here would state the same invariant a
    # second time, in a second place that can drift from the first. See this module's
    # own --menu docstring section for the full electoral_only derivation.
    if menu == "electoral_only":
        pressure_menu = dataclasses.replace(
            config.pressure_menu, electoral_only=True, petition_enabled=False, mobilization_enabled=False
        )
        petition = config.petition
        street_pressure = config.street_pressure
    elif menu == "both":
        pressure_menu = dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        )
        petition = dataclasses.replace(config.petition, enabled=True)
        street_pressure = dataclasses.replace(config.street_pressure, enabled=True)
    else:
        raise ValueError(f"unsupported menu {menu!r}, expected 'both' or 'electoral_only'")

    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=duration_years),
        # recall_floor defaults to the shipped value (0.2) -- the original arm's own
        # behavior, unchanged. See this module's own --recall-floor docstring section
        # for why 0.0 is the second, targeted run's own single changed variable, and
        # its own --menu section for why the floor is structurally INERT under
        # electoral_only regardless of its own value.
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True, recall_floor=recall_floor),
        # mandate/awakening/legitimacy all stay enabled under BOTH menus, exactly as
        # run_acceptance_comparison._config_for_arm does for every one of its own four
        # arms: mandate.enabled is what makes dt=6 fire at all (its own gate is
        # llm.enabled and mandate.enabled, never pressure_menu -- turning it off would
        # remove the very series either menu exists to measure); legitimacy.enabled
        # keeps L journaled and the "flat at m" claim falsifiable; awakening.enabled
        # keeps the consulted cohort (and pressure_action series) alive, restricted to
        # whichever menu's own legal acts.
        mandate=dataclasses.replace(config.mandate, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=pressure_menu,
        petition=petition,
        street_pressure=street_pressure,
        # social_graph / events stay at their shipped-off default -- deliberately,
        # see this module's own docstring.
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True),
    )
    if engine == "llm":
        config = dataclasses.replace(
            config,
            llm=dataclasses.replace(
                config.llm, enabled=True, max_batch_replays=max_batch_replays,
                # bug 4 mitigation (llm_batching_determinism_results_gpu.md,
                # 2026-08-20): recycle the Ollama model every 6 calls, safely
                # under the measured risk zone (cache>=7). Not wiring this in
                # is exactly what let the first real-run attempt of this lot
                # die on campaign_positioning's very first think=True call.
                recycle_after_n_calls=6,
            ),
        )
    return config


def _metrics_to_json(metrics: RunMetrics) -> dict[str, Any]:
    return {
        "run_id": metrics.run_id,
        "total_ticks": metrics.total_ticks,
        "terms": [dataclasses.asdict(t) for t in metrics.terms],
        "mean_legitimacy": metrics.mean_legitimacy,
        "recalls_by_trigger": metrics.recalls_by_trigger,
        "recalls_per_term": metrics.recalls_per_term,
        "mandate_deviation": metrics.mandate_deviation,
        "mandate_deviation_source": metrics.mandate_deviation_source,
        "mandate_deviation_coverage": metrics.mandate_deviation_coverage,
        "inaction_rate": metrics.inaction_rate,
        "pressure_lever_mix": metrics.pressure_lever_mix,
        "pressure_lever_counts": metrics.pressure_lever_counts,
        "stance_distribution": metrics.stance_distribution,
        "petition_downgrades": metrics.petition_downgrades,
        "petition_success_rate": metrics.petition_success_rate,
        "petition_removal_rate": metrics.petition_removal_rate,
        "mandate_deviation_unified": metrics.mandate_deviation_unified,
        "chamber_deviation": metrics.chamber_deviation,
    }


def _compute_chamber_metrics(journal_path: Path, total_ticks: int) -> dict[str, Any]:
    """The one computation this lot needs that indexer.py doesn't already
    provide -- single consumer (this script), stays ad hoc here rather than
    becoming a new indexer.py/metrics.py row, per calibrate_*.py/
    run_v5_acceptance.py/run_v6a_acceptance.py's own precedent.

    Iterates the FULL tick range (0..total_ticks inclusive), not just ticks
    that happen to have an event -- a tick with zero chamber_deliberation
    events is a real, informative observation (run_v5_acceptance.
    _compute_spark's own already-learned lesson), not an absent one.

    The deterministic arm's own special case: llm.enabled=False means
    _run_chamber_deliberation returns before any journal write at all --
    zero chamber_deliberation events exist, not because chamber_deviation
    is unknown, but because it is KNOWN to be 0.0 by construction (v6b
    Lot 3's own already-unit-tested deterministic-fallback guarantee:
    chamber_position stays pinned to issue_positions forever). Reported as
    an explicit 0.0 with a note, never None (which would read as "not
    tracked" when it is in fact a certain value) and never silently
    omitted."""
    deviations_by_tick: dict[int, list[float]] = {}
    motif_counts: dict[str, int] = {"701": 0, "702": 0}
    rotations: list[dict[str, int]] = []
    for event in read_journal(journal_path):
        if event["event_type"] == "chamber_deliberation":
            tick = event["tick"]
            deviations_by_tick.setdefault(tick, []).append(event["payload"]["chamber_deviation"])
            motif = event["motif"]
            motif_counts[motif] = motif_counts.get(motif, 0) + 1
        elif event["event_type"] == "sortition_rotation":
            rotations.append({"tick": event["tick"], "seated": len(event["payload"]["seated"])})

    # bool(...): `not X and Y` returns Y itself (Python's and/or return an
    # operand, not necessarily a bool), so an un-wrapped expression here
    # would silently serialize the rotations list instead of a boolean.
    known_zero_by_construction = bool(not deviations_by_tick and rotations)
    all_ticks = range(total_ticks + 1)
    per_tick_means = [
        (sum(deviations_by_tick[tick]) / len(deviations_by_tick[tick])) if tick in deviations_by_tick else 0.0
        for tick in all_ticks
    ]
    all_values = [v for values in deviations_by_tick.values() for v in values]

    total_motif = sum(motif_counts.values())
    motif_mix = (
        {code: count / total_motif for code, count in sorted(motif_counts.items())} if total_motif else None
    )

    return {
        "known_zero_by_construction": known_zero_by_construction,
        "chamber_deviation_mean": sum(all_values) / len(all_values) if all_values else 0.0,
        "chamber_deviation_max": max(all_values) if all_values else 0.0,
        "chamber_deviation_per_tick_mean": sum(per_tick_means) / len(per_tick_means),
        "chamber_motif_mix": motif_mix,
        "chamber_motif_counts": motif_counts,
        "rotations": rotations,
        "last_seated_size": rotations[-1]["seated"] if rotations else None,
    }


def run_arm(
    engine: str, *, duration_years: int, output_dir: Path, max_batch_replays: int, recall_floor: float = 0.2,
    menu: str = "both",
) -> Path:
    # Journal opens its file in append mode (journal.py, §16.1's deliberate
    # append-only contract) -- a pre-existing run_dir must fail loudly rather
    # than silently concatenate two runs into one journal (run_v5_acceptance.py's
    # own already-learned lesson).
    run_dir = output_dir / f"sortition-{engine}-{duration_years}y"
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} already exists -- remove it before re-running this arm.")
    run_dir.mkdir(parents=True)

    # 2026-08-22 (post-crash): a pragmatic mitigation, not a response to this run's own prior
    # crash specifically -- that crash's cause is confirmed (an external `wsl --shutdown` in a
    # sibling worktree, unrelated to container uptime; see llm_batching_determinism_results_gpu.md's
    # dated section), so a restart schedule would not have prevented it. This hedges against a
    # separate, independently-documented risk (WSL2/Docker Desktop connectivity degrading over
    # long container uptime, see ollama_uptime_guard.py's own docstring) before committing to an
    # hours-long --engine llm run. Cheap and safe for --engine deterministic too, so it is not
    # gated on engine == "llm".
    ensure_fresh_container()
    config = _config_for_v6b_run(
        engine, duration_years=duration_years, output_dir=run_dir / "run", max_batch_replays=max_batch_replays,
        recall_floor=recall_floor, menu=menu,
    )
    (run_dir / "config.json").write_text(json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8")

    if menu == "electoral_only" and recall_floor != 0.2:
        print(
            f"NOTE: --recall-floor {recall_floor} is INERT under --menu electoral_only: "
            "petition_pressure and street_pressure are both structurally 0.0 and "
            "passive_erosion_weight ships at 0.0, so écart(t) ≡ 0, L(t) converges to m, "
            "and crosses_floor cannot fire at ANY floor value. Recorded in config.json "
            "for provenance; it is not a second changed variable.",
            file=sys.stderr,
        )

    replay_handler = None
    if engine == "llm":
        engine_logger = logging.getLogger("api.domain.polity.llm_behavior_engine")
        replay_handler = logging.FileHandler(run_dir / "replays.log", encoding="utf-8")
        replay_handler.setLevel(logging.WARNING)
        engine_logger.addHandler(replay_handler)
        engine_logger.setLevel(logging.WARNING)

    start = time.monotonic()
    try:
        journal_path = run_simulation(config, run_id=f"sortition-{engine}-{duration_years}y", llm_client=None)
    finally:
        elapsed = time.monotonic() - start
        if replay_handler is not None:
            logging.getLogger("api.domain.polity.llm_behavior_engine").removeHandler(replay_handler)
            replay_handler.close()

    replay_count = 0
    replays_log = run_dir / "replays.log"
    if replays_log.is_file():
        replay_count = sum(1 for _ in replays_log.read_text(encoding="utf-8").splitlines())

    metrics = index_run(journal_path, config)
    payload = _metrics_to_json(metrics)
    payload["_meta"] = {
        "engine": engine, "duration_years": duration_years,
        "elapsed_seconds": round(elapsed, 1), "replay_count": replay_count,
        "menu": menu, "recall_floor": recall_floor,
    }
    metrics_path = run_dir / "metrics.json"

    chamber = _compute_chamber_metrics(journal_path, config.run.total_ticks)
    chamber_path = run_dir / "chamber.json"
    chamber_path.write_text(json.dumps(chamber, indent=2), encoding="utf-8")

    recalls = metrics.recalls_by_trigger or {}
    total_recalls = sum(recalls.values())
    # Office-occupancy (this second run's own pre-registered PRIMARY decision
    # criterion, >= 0.70): len(mandate_deviation) when source=="ctx" is exactly
    # the count of presided ticks with a representative_response event -- the
    # ctx series IS "every presided tick's own dt=6 reading" (indexer.py), so
    # its length over total_ticks+1 is office-occupancy directly, no new
    # indexer.py row needed (ad hoc here, single consumer, same precedent as
    # _compute_chamber_metrics).
    occupancy = None
    if metrics.mandate_deviation_source == "ctx" and metrics.mandate_deviation:
        occupancy = len(metrics.mandate_deviation) / (config.run.total_ticks + 1)
    payload["_meta"]["office_occupancy"] = occupancy
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"sortition/{engine}/{duration_years}y/menu={menu}: {elapsed:.1f}s, {replay_count} replays, "
        f"recalls={total_recalls}, mean_legitimacy(last)={(metrics.mean_legitimacy or [(0, None)])[-1][1]}, "
        f"mandate_deviation(last)={(metrics.mandate_deviation or [(0, None)])[-1][1]}, "
        f"office_occupancy={occupancy}, "
        f"chamber_deviation(mean)={chamber['chamber_deviation_mean']:.4f}, "
        f"last_seated_size={chamber['last_seated_size']} "
        f"-- metrics={metrics_path}, chamber={chamber_path}"
    )
    if engine == "llm" and occupancy is not None and occupancy < 0.70:
        print(
            f"WARNING: office_occupancy={occupancy:.3f} is below this run's own pre-registered "
            "0.70 decision criterion -- the mandate_deviation/chamber_deviation comparison is NOT "
            "valid per that criterion. Report honestly, do not force a conclusion.",
            file=sys.stderr,
        )
    if engine == "deterministic" and total_recalls > 6:
        print(
            "WARNING: this arm recalled more than 3x both/deterministic/8y's own committed anchor "
            "(2 recalls) -- inspect before committing to the expensive --engine llm run; sortition "
            "rotation is architecturally independent of the presidency, so it should not perturb "
            "this number at all.",
            file=sys.stderr,
        )
    if menu == "electoral_only" and total_recalls > 0:
        print(
            f"WARNING: electoral_only produced {total_recalls} recall(s). This run's own "
            "pre-registered structural claim -- écart(t) ≡ 0 under electoral_only at "
            "passive_erosion_weight=0.0, therefore L(t) -> m and no floor can fire -- is "
            "FALSIFIED. Investigate before reporting; do not treat this as a normal run.",
            file=sys.stderr,
        )
    return metrics_path


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}={_fmt(v)}" for k, v in sorted(value.items()))
    return str(value)


def summarize(runs_dir: Path, results_path: Path | None) -> None:
    metrics_files = sorted(runs_dir.glob("*/metrics.json"))
    if not metrics_files:
        print(f"no metrics.json found under {runs_dir}", file=sys.stderr)
        return

    lines: list[str] = []

    def log(line: str) -> None:
        print(line)
        lines.append(line)

    first_meta = json.loads(metrics_files[0].read_text(encoding="utf-8"))["_meta"]
    menu = first_meta.get("menu", "both")

    log("# v6b acceptance run — elected vs. sortition (§6bis.3), Lot 4\n")
    # The elected side's own framing is menu-dependent, so it cannot be one fixed
    # paragraph: under `both` the president faces all three §7bis channels (§6bis.3's
    # own literal comparison), under `electoral_only` they face none of them, which is
    # what removes the office-vacancy confound the `both` runs hit -- saying "full
    # pressure menu" on an electoral_only directory would contradict the very next line.
    if menu == "electoral_only":
        elected_side = (
            "The elected side runs under `--menu electoral_only`: `écart(t) ≡ 0` by "
            "construction (no petition, no street pressure, `passive_erosion_weight: 0.0`), "
            "so `L(t)` converges to `m` and never crosses the shipped `recall_floor` -- the "
            "office stays occupied for the whole run. This removes the vacancy confound the "
            "`both` runs hit (`office_occupancy = 0.333`, `mandate_deviation_coverage = 0.0`) "
            "STRUCTURALLY, without disabling accountability the way `--recall-floor 0.0` did. "
            "The cost is stated rather than hidden: a president facing none of §7bis's three "
            "channels is not §6bis.3's own literal comparison subject, so any drift observed "
            "here is drift under NO measurable pressure at all."
        )
    else:
        elected_side = (
            "The elected side reuses `run_acceptance_comparison.py`'s own `both` arm shape "
            "(full pressure menu, legitimacy/mandate/awakening enabled) -- §6bis.3's own "
            "comparison is against a president \"soumise aux trois canaux du §7bis\", all "
            "three, not one isolated lever."
        )
    log(
        "n=1 (one seed, no Monte Carlo band), the same limit every prior acceptance run in this "
        f"project has already named. {elected_side} `social_graph.enabled`/`events.enabled` stay "
        "OFF throughout, the same confound-avoidance call v5 Lot 5 and v6a Lot 4 already made "
        "independently. Unlike v6a Lot 4, this comparison needs BOTH quantities from the SAME run "
        "at the SAME ticks, so there is no prior acceptance row to cite -- this is one new, "
        "self-contained run.\n"
    )
    log(
        f"This directory's own runs used `--menu {menu} "
        f"--recall-floor {first_meta.get('recall_floor', 0.2)}`.\n"
    )
    log(
        "| menu | engine | years | elapsed(s) | replays | office_occupancy | mean L (last) | recalls | "
        "mandate_dev (mean/max) | mandate_dev unified (mean/max) | chamber_dev (mean/max) | motif mix | "
        "last seated size |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        mean_l = payload["mean_legitimacy"]
        last_l = mean_l[-1][1] if mean_l else None
        deviation = payload["mandate_deviation"]
        dev_values = [v for _, v in deviation] if deviation else []
        dev_mean = sum(dev_values) / len(dev_values) if dev_values else None
        dev_max = max(dev_values) if dev_values else None
        # .get(): pre-dates the v6b production-wiring lot on the two already-committed
        # metrics.json files -- renders "—/—" rather than raising on those.
        unified = payload.get("mandate_deviation_unified")
        unified_values = [v for _, v in unified] if unified else []
        unified_mean = sum(unified_values) / len(unified_values) if unified_values else None
        unified_max = max(unified_values) if unified_values else None
        recalls = payload["recalls_by_trigger"]
        chamber_path = path.parent / "chamber.json"
        chamber = json.loads(chamber_path.read_text(encoding="utf-8")) if chamber_path.is_file() else {}
        note = " (known 0.0, no LLM call)" if chamber.get("known_zero_by_construction") else ""
        log(
            f"| {_fmt(meta.get('menu', 'both'))} | {meta['engine']} | {meta['duration_years']} | "
            f"{meta['elapsed_seconds']} | {meta['replay_count']} | {_fmt(meta.get('office_occupancy'))} | "
            f"{_fmt(last_l)} | {_fmt(recalls)} | "
            f"{_fmt(dev_mean)}/{_fmt(dev_max)} | {_fmt(unified_mean)}/{_fmt(unified_max)} | "
            f"{_fmt(chamber.get('chamber_deviation_mean'))}/{_fmt(chamber.get('chamber_deviation_max'))}{note} | "
            f"{_fmt(chamber.get('chamber_motif_mix'))} | {_fmt(chamber.get('last_seated_size'))} |"
        )

    log("\n## §6bis.3's own headline question\n")
    log(
        "*« L'absence de pression électorale produit-elle des décisions plus « sincères » "
        "(alignées sur ses propres issue_positions) ou plus erratiques (aucun garde-fou de "
        "responsabilité) ? »*"
    )
    log(
        "- Compare `mandate_dev (mean/max)` against `chamber_dev (mean/max)` in the `llm` row above: "
        "a materially LOWER chamber_deviation than mandate_deviation is the signature of insulation "
        "producing more sincere (less drifted) decisions; a comparable or higher chamber_deviation "
        "would say the opposite -- that accountability pressure alone doesn't explain the elected "
        "side's own drift."
    )
    log(
        "- `motif mix` (701 SINCERE_POSITION vs 702 DELIBERATIVE_SHIFT) is the model's own stated "
        "label for each decision -- not enforced by any coherence rule (v6b Lot 3's own removed "
        "validator), so it is informative but non-binding: a chamber that stays mostly 701 is "
        "sincere by its own account; a chamber that trends toward 702 is not, independent of "
        "whether the resulting `chamber_deviation` values are themselves large or small."
    )
    log(
        "- `last_seated_size` cross-checks v6b Lot 2's own pool-exhaustion calibration finding "
        "(`sortition_calibration_results.md`) lands the same way inside a real LLM run: the chamber "
        "should stay at or near `seats=30` for the whole run once the relaxed-pool fallback engages."
    )
    log(
        "- **Not claimed here**: the sortition chamber's own institutional consequence (veto power, "
        "design doc point ouvert n°11) -- this MVP is comparison-only, with no lawmaking concept "
        "for a veto to act on."
    )

    if results_path is not None:
        results_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n(full report written to {results_path})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["llm", "deterministic"])
    parser.add_argument("--duration-years", type=int, default=8)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument(
        "--recall-floor", type=float, default=0.2,
        help="legitimacy.recall_floor override (shipped default 0.2). See this module's own "
        "--recall-floor docstring section for the pre-registered 0.0 experiment.",
    )
    parser.add_argument(
        "--menu", choices=["both", "electoral_only"], default="both",
        help="pressure_menu modality (§7bis.8's own 4-modality variable, two of which are used "
        "here). 'both' reproduces the first two runs' shape. 'electoral_only' removes the "
        "office-vacancy confound STRUCTURALLY (écart(t) ≡ 0 => L(t) -> m => no recall at ANY "
        "floor), at the untouched shipped recall_floor -- see this module's own --menu "
        "docstring section.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/acceptance_v6b_runs"))
    parser.add_argument("--summarize", type=Path, help="render the results doc from every metrics.json under this dir")
    parser.add_argument("--results", type=Path, help="where --summarize writes the rendered markdown")
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize, args.results)
        return 0

    if not args.engine:
        parser.error("--engine is required unless --summarize is given")

    run_arm(
        args.engine, duration_years=args.duration_years,
        output_dir=args.output_dir, max_batch_replays=args.max_batch_replays,
        recall_floor=args.recall_floor, menu=args.menu,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
