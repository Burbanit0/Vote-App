"""
scripts/check_agent_prompt_neutrality.py

Is an agent prompt neutral enough to leave the choice to the agent? Three live measurements per
prompt, on real citizens, against the shipped prompt and a meaning-preserving paraphrase of it.

Why this exists. Every agent prompt defect found so far was found by accident, reading a run
(OBS-022, OBS-028, OBS-029, OBS-030), and the fixes were argued from the wording rather than
measured. Two of them turned out not to be about wording at all: the schema decides. An optional
`extra_legal` field is never filled (0/30) while the free-text `other_initiative` is (7/30); make
`extra_legal` required and it flips (6/30 refusals, 0/30 initiatives). A prompt is a measurable
object, so measure it.

The three checks, per prompt:

  SENSITIVITY   The choice distribution must move with the state it depends on. Two cells differ
                in exactly one state variable (a president's approval, how many citizens would
                co-found with this one, whether a proposal serves its proposer). A prompt whose
                answers are the same in both cells is not letting the state be perceived --
                contract clause C3 of polity-decision-contracts.md. The bar is the measurement's
                own binomial noise, not a fixed number of points: a shift inside the band is
                reported UNRESOLVED (raise --n), because an act taken 8% of the time cannot move
                15 points however well the prompt is written.

  DEAD OPTION   No option may sit at 0% or 100% across every cell. A legal act the model never
                takes is a prescriptive prompt in disguise (C4): the menu says the act exists and
                the prose has already decided against it. This is exactly OBS-029 (`found`: 0 in
                ~1,590 forum turns) and the optional-field finding above.

  WORDING       A paraphrase that changes no fact must move the distribution LESS than the state
                does. If rewording outweighs the state, the prompt is measuring the author's
                phrasing, not the agent's situation (OBS-019 showed prompts alone move the macro
                picture).

The paraphrases are built by string substitution on the prompt the production builder returned, in
memory. No production module is edited, and the substitutions assert their target is present, so a
prompt edit that invalidates a paraphrase fails loudly here instead of silently testing nothing.

Not a pytest: it needs a live model, and its output is a judgement about prompts rather than a
pass/fail on code. Run it after editing any agent prompt, and record the table in the observation
log the way OBS-030 does.

Usage:
    uvicorn-free; needs vLLM on config.llm.base_url (POLITY_CHECKPOINT overrides the citizens).

    python fast_api_voter/scripts/check_agent_prompt_neutrality.py              # all probes, n=30
    python fast_api_voter/scripts/check_agent_prompt_neutrality.py --n 60
    python fast_api_voter/scripts/check_agent_prompt_neutrality.py --probe forum
    python fast_api_voter/scripts/check_agent_prompt_neutrality.py --probe threshold --n 60   # PLAN_BEYOND_CI W2.1's gate
    python fast_api_voter/scripts/check_agent_prompt_neutrality.py --probe threshold --n 60 --gate-log answers.jsonl --gate-wording count   # OBS-045
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import math
import os
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.bakeoff_statistics import mcnemar_exact  # noqa: E402
from api.domain.polity.agents import (  # noqa: E402
    PRESIDENT_TURN,
    NOMINEE_TURN,
    NomineeBriefing,
    PresidentBriefing,
    ballot_system_prompt,
    ballot_user_prompt,
    decide_ballot,
    decide_forum,
    decide_turn,
    forum_system_prompt,
    forum_words,
    forum_user_prompt,
    nominee_system_prompt,
    nominee_user_prompt,
    party_roll,
    stand_line,
    president_system_prompt,
    president_user_prompt,
    ballot_proposer_text,
)
from api.domain.polity.checkpoint import _citizen_from_dict, _party_from_dict  # noqa: E402
from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import PolityConfig, validate_config  # noqa: E402
from api.domain.polity.constitution import Proposal, article_value  # noqa: E402
from api.domain.polity.llm_behavior_engine import ResponseContext  # noqa: E402
from api.domain.polity.llm_client import LlmClientProtocol, build_json_client  # noqa: E402
from api.domain.polity.llm_schemas import ForumTurn  # noqa: E402
from api.domain.polity.parties import Party  # noqa: E402
from api.domain.polity.simple_rules import cofounders  # noqa: E402

_DEFAULT_CHECKPOINT = (
    Path.home() / "Documents/Dev/polity-runs/phase4/eng-8y-p100-seed2/run/eng-8y-p100-seed2/checkpoint.json"
)
SENSITIVITY_SIGMAS = 2.0
"""How many standard errors the state's shift must clear. A fixed percentage-point floor cannot
work across probes: an act taken 8% of the time cannot shift 15 points however well the prompt is
written, so the bar is the noise of the measurement itself. Below it the answer is UNRESOLVED, not
FAIL -- "this n cannot tell" is not "the prompt is broken"."""

WORKERS = 8


# ── the population the probes run on ──────────────────────────────────────

def _load_citizens(path: Path) -> tuple[list[Citizen], list[Party]]:
    """Real citizens and parties from a finished run's checkpoint: the probes need the spread of
    a lived-in population (a generated one has no party history and no drift)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        [_citizen_from_dict(c) for c in payload["citizens"]],
        [_party_from_dict(p) for p in payload["parties"]],
    )


def _config() -> PolityConfig:
    """The exploration profile's own config, with every agent mechanism on."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_polity_flagship as flagship

    config = flagship._flagship_config(
        engine="llm", years=8, population=100, seats=15, seed=1, output_dir=Path("/tmp/prompt-neutrality"),
        max_batch_replays=2, provider="vllm", workers=1, profile="exploration",
    )
    # The act only exists for a president in their final term, so the probe's scenario needs one:
    # a 2-year term with a limit of 1 makes every president final-term, as the Phase 5.1 runs did.
    config = dataclasses.replace(
        config, institutions=dataclasses.replace(config.institutions, president_term_years=2, president_term_limit=1),
    )
    validate_config(config)
    return config


# ── a probe ───────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class Probe:
    """One prompt under test. `cells` are the two states that must be told apart; `paraphrase`
    rewords the shipped prompt without changing a fact; `ask` returns the agent's choice."""

    name: str
    options: tuple[str, ...]
    cells: tuple[str, str]
    state_axis: str
    paraphrase: Callable[[str], str]
    ask: Callable[[Citizen, str, bool, PolityConfig, LlmClientProtocol], str]


def _paraphrase(text: str, pairs: Sequence[tuple[str, str]]) -> str:
    """Substitute each pair, asserting the target is there: a prompt edit that moves the target
    fails here rather than quietly leaving the paraphrase equal to the shipped prompt."""
    for old, new in pairs:
        if old not in text:
            raise SystemExit(f"paraphrase target missing from the shipped prompt: {old!r}")
        text = text.replace(old, new, 1)
    return text


# ── probe 1: the forum's party move (OBS-029) ─────────────────────────────

_FORUM_PAIRS = (
    (
        "At an election, a party nominates only its own members.",
        "At an election, only its own members may be nominated by a party.",
    ),
)


def _forum_turn(
    citizen: Citizen, pairs: Sequence[tuple[str, str]], config: PolityConfig, client: LlmClientProtocol,
    *, population: list[Citizen], parties: list[Party], roll: str,
) -> ForumTurn | None:
    return decide_forum(
        citizen, system_prompt=_paraphrase(forum_system_prompt(citizen, config), pairs), config=config, client=client,
        user_prompt=forum_user_prompt(
            tick=5, member=False, feed="", memory="", roll=roll,
            stand=stand_line(citizen, population, parties, config),
        ),
    ).turn


def _forum_ask(
    citizen: Citizen, cell: str, paraphrased: bool, config: PolityConfig, client: LlmClientProtocol,
    *, population: list[Citizen], parties: list[Party], roll: str,
) -> str:
    del cell  # the forum's cell is which citizens these are
    turn = _forum_turn(
        citizen, _FORUM_PAIRS if paraphrased else (), config, client, population=population, parties=parties, roll=roll,
    )
    return turn.party_move if turn is not None else "fail"


# ── probe 2: the chamber's ballot (OBS-030) ───────────────────────────────

# The reason a live president actually writes (OBS-038's own run), not a candid one: a candidly
# self-serving reason is the easy case, and testing only it is what made OBS-030's fix look stronger
# than it was (80% -> 7% candid; 60% -> 47% framed as continuity).
_SELF_SERVING = (
    "institutions.president_term_limit", 3,
    "Allowing more terms ensures stability and continuity in defense and sovereignty policies",
)
_NEUTRAL = ("institutions.electoral_threshold", 0.03, "A slightly lower threshold lets more voices into the assembly.")

_BALLOT_PAIRS = (
    (
        "each member votes yes or no, for themselves: how you weigh your own convictions, your party and the public good is yours to decide.",
        "each member votes yes or no. Your convictions, your party and the public good are yours to weigh as you see fit.",
    ),
)


def _ballot_ask(
    citizen: Citizen, cell: str, paraphrased: bool, config: PolityConfig, client: LlmClientProtocol,
    *, members: int,
) -> str:
    article, value, reason = _SELF_SERVING if cell == "self-serving" else _NEUTRAL
    proposal = Proposal(article=article, value=value, proposer=0, tick=4, threshold=0.5, reason=reason)
    system = ballot_system_prompt(citizen, config)
    if paraphrased:
        system = _paraphrase(system, _BALLOT_PAIRS)
    # The proposer's standing is held constant across both cells, so only what the proposal does
    # to the proposer differs -- the asymmetry OBS-030 measured.
    # A proposer who has served every term the rules allow, so `lame_duck` is true of them and the
    # ballot's self-interest line fires on the self-serving cell exactly as it would in a run.
    president = dataclasses.replace(citizen, mandates_served=config.institutions.president_term_limit or 0)
    who = ballot_proposer_text(
        president, proposal, article_value(config, article), approval=0.35, ticks_left=4, lame_duck=True,
    )
    outcome = decide_ballot(
        citizen, system_prompt=system, config=config, client=client,
        user_prompt=ballot_user_prompt(
            proposal, tick=5, old=article_value(config, article), members=members, memory="", proposer=who,
        ),
    )
    return outcome.turn.vote if outcome.turn is not None else "fail"


# ── probe 3: the president's extra-legal act (ADR-022) ─────────────────────

_REGIME_PAIRS = (
    (
        "There is one further act, outside the constitution:",
        "One act more stands outside the constitution:",
    ),
)


def _president_ask(
    citizen: Citizen, cell: str, paraphrased: bool, config: PolityConfig, client: LlmClientProtocol,
) -> str:
    system = president_system_prompt(citizen, config)
    if paraphrased:
        system = _paraphrase(system, _REGIME_PAIRS)
    approval = 0.25 if cell == "low approval" else 0.75
    # The president of a real run reads their own approval history (AgentMemory renders a
    # legitimacy_updated line per tick), so a probe with an empty memory would test the prompt
    # without the one thing that gives approval a scale. Four ticks, flat at this cell's level.
    memory = "What you have done, and what happened:\n" + "\n".join(
        f"- t{tick} legitimacy {0.4 if approval < 0.5 else 0.7:.2f}, approval {approval:.2f}" for tick in range(3, 7)
    )
    positions = citizen.issue_positions
    briefing = PresidentBriefing(
        tick=7, ticks_per_year=config.run.ticks_per_year,
        context=ResponseContext(
            cid=citizen.citizen_id, legitimacy=0.5, mandate_dev=0.1, street=0.1, lame_duck=True, ticks_left=1,
        ),
        approval=approval, agenda_closed="a bill comes every 2 ticks", policy=None,
        public_median=positions, assembly_median=None, pledge=positions, stated=positions, constitution=None,
    )
    outcome = decide_turn(
        citizen, decision_type=PRESIDENT_TURN, system_prompt=system,
        user_prompt=president_user_prompt(briefing, memory), max_positions=config.mandate.max_response_shifts,
        agenda_open=False, config=config, client=client,
    )
    return getattr(outcome.turn, "extra_legal", "fail") if outcome.turn is not None else "fail"


_CAMPAIGN_PAIRS = (
    (
        "Citizens you reach weigh that issue more heavily when they compare candidates, and the rest of their concerns proportionally less.",
        "The issue counts for more, and their other concerns for proportionally less, when the citizens you reach compare candidates.",
    ),
)


def _campaign_ask(
    citizen: Citizen, cell: str, paraphrased: bool, config: PolityConfig, client: LlmClientProtocol,
    *, population: list[Citizen],
) -> str:
    """ADR-023: what a nominee campaigns on, and who it tries to reach. The cell is the nominee's
    standing in the poll -- behind, a campaign should look different from ahead."""
    system = nominee_system_prompt(citizen, config)
    if paraphrased:
        system = _paraphrase(system, _CAMPAIGN_PAIRS)
    rival = next(c for c in population if c.citizen_id != citizen.citizen_id)
    mine, theirs = (0.12, 0.55) if cell == "behind in the poll" else (0.55, 0.12)
    briefing = NomineeBriefing(
        tick=7, field=((citizen.citizen_id, citizen.party_affiliation), (rival.citizen_id, rival.party_affiliation)),
        poll={citizen.citizen_id: mine, rival.citizen_id: theirs}, blank=0.2, abstain=0.13,
        platform=citizen.issue_positions, public_median=tuple(0.5 for _ in citizen.issue_positions),
    )
    outcome = decide_turn(
        citizen, decision_type=NOMINEE_TURN, system_prompt=system,
        user_prompt=nominee_user_prompt(citizen, briefing), max_positions=config.campaign.max_positioning_shifts,
        agenda_open=False, config=config, client=client,
    )
    if outcome.turn is None:
        return "fail"
    plan = getattr(outcome.turn, "campaign", None)
    return "none" if plan is None else plan.audience


def _probes(citizens: list[Citizen], parties: list[Party]) -> dict[str, Probe]:
    roll = party_roll(parties, citizens)
    return {
        "forum": Probe(
            name="forum party move", options=("none", "join", "leave", "found"),
            cells=("too few would co-found", "enough would co-found"),
            state_axis="whether enough citizens would co-found a new party",
            paraphrase=lambda text: _paraphrase(text, _FORUM_PAIRS),
            ask=lambda c, cell, para, cfg, cl: _forum_ask(
                c, cell, para, cfg, cl, population=citizens, parties=parties, roll=roll,
            ),
        ),
        "ballot": Probe(
            name="chamber amendment ballot", options=("yes", "no"),
            cells=("self-serving", "neutral"), state_axis="whether the proposal serves its proposer",
            paraphrase=lambda text: _paraphrase(text, _BALLOT_PAIRS),
            ask=lambda c, cell, para, cfg, cl: _ballot_ask(c, cell, para, cfg, cl, members=30),
        ),
        "campaign": Probe(
            name="nominee campaign audience", options=("none", "base", "undecided"),
            cells=("behind in the poll", "ahead in the poll"), state_axis="the nominee's standing",
            paraphrase=lambda text: _paraphrase(text, _CAMPAIGN_PAIRS),
            ask=lambda c, cell, para, cfg, cl: _campaign_ask(c, cell, para, cfg, cl, population=citizens),
        ),
        "president": Probe(
            name="president extra-legal act", options=("none", "refuse_to_leave"),
            cells=("low approval", "high approval"), state_axis="the president's approval",
            paraphrase=lambda text: _paraphrase(text, _REGIME_PAIRS),
            ask=_president_ask,
        ),
    }


def _with_threshold(config: PolityConfig, threshold: float) -> PolityConfig:
    return dataclasses.replace(
        config, institutions=dataclasses.replace(config.institutions, electoral_threshold=threshold),
    )


GATE_LOW, GATE_HIGH, GATE_ALPHA = 0.03, 0.07, 0.05


def _threshold_gate(
    citizens: list[Citizen], parties: list[Party], n: int, config: PolityConfig, client: LlmClientProtocol,
    log: Path | None = None, wording: str = "shipped",
) -> bool:
    """PLAN_BEYOND_CI W2.1's gate: does founding follow the seat threshold a founder is told (D2)?
    The same citizens -- only those who could found; for the others `found` is refused anyway --
    answer once told 3% and once told 7%, in the shipped wording or, for OBS-045, with the founding
    rule stated as a count. Paired, so the test is an exact
    McNemar on who founds at one bar and not the other; the gate passes when founding moves at
    p < 0.05 (in either direction: the wrong sign is a finding too, and is printed as such)."""
    able = _split_by_backing(citizens, parties, n, config)["enough would co-found"]
    if not able:
        raise SystemExit("threshold gate: no citizen in this checkpoint could found a party; use another --checkpoint")
    low, high = _with_threshold(config, GATE_LOW), _with_threshold(config, GATE_HIGH)
    roll = party_roll(parties, citizens)
    # OBS-045: founders cite "the 5% threshold" -- the founding rule -- and never the seat bar. "count" states the
    # founding rule as the same fact without its percentage (the party roll still gives each party's share as one).
    needed = math.ceil(config.parties.founding_ratio * len(citizens))
    pairs = () if wording == "shipped" else (
        (f"at least {config.parties.founding_ratio:.0%} of the citizens", f"at least {needed} of the {len(citizens)} citizens"),
    )
    jobs = [(citizen, cfg) for citizen in able for cfg in (low, high)]
    with ThreadPoolExecutor(WORKERS) as pool:
        turns = list(pool.map(
            lambda job: _forum_turn(job[0], pairs, job[1], client, population=citizens, parties=parties, roll=roll),
            jobs,
        ))
    found_low = [t is not None and t.party_move == "found" for t in turns[0::2]]
    found_high = [t is not None and t.party_move == "found" for t in turns[1::2]]
    backing = [len(cofounders(citizen, citizens, parties)) for citizen in able]
    test = mcnemar_exact(found_low, found_high)
    moved = test.p_value < GATE_ALPHA
    direction = "fewer at the higher bar" if sum(found_high) < sum(found_low) else "more at the higher bar"
    print(f"\nW2.1 gate: does founding follow the stated seat threshold? ({len(able)} able founders, each told "
          f"{GATE_LOW:.0%} then {GATE_HIGH:.0%}; founding rule worded: {wording})")
    print(f"  found at {GATE_LOW:.0%}: {sum(found_low)}/{len(able)}    found at {GATE_HIGH:.0%}: {sum(found_high)}/{len(able)}")
    print(f"  only at {GATE_LOW:.0%}: {test.first_only}   only at {GATE_HIGH:.0%}: {test.second_only}   "
          f"exact McNemar p = {test.p_value:.3g}")
    print(*_by_backing(backing, found_low, found_high), sep="\n")
    if log is not None:
        backing_of = {citizen.citizen_id: count for citizen, count in zip(able, backing)}
        log.write_text("".join(
            json.dumps({"citizen": citizen.citizen_id, "backing": backing_of[citizen.citizen_id],
                        "told": cfg.institutions.electoral_threshold,
                        "party_move": turn.party_move if turn is not None else "fail", **forum_words(turn)}) + "\n"
            for (citizen, cfg), turn in zip(jobs, turns)
        ), encoding="utf-8")
        print(f"  every answer, with its backing: {log} (what they cite: check_observations.py founders)")
    print(f"  GATE  {'PASS' if moved else 'STOP'}  " + (
        f"founding moves with the threshold ({direction})" if moved
        else "founding does not move with the threshold at this n: the experiment stops here (PLAN_BEYOND_CI W2.1)"
    ))
    return moved


def _by_backing(backing: Sequence[int], found_low: Sequence[bool], found_high: Sequence[bool]) -> list[str]:
    """Founding at each bar against how many would co-found (OBS-045): a founder whose backing is below
    the higher bar's seat share should found less there, if the threshold is applied to their own party."""
    rows: dict[int, list[int]] = collections.defaultdict(lambda: [0, 0, 0])
    for count, low, high in zip(backing, found_low, found_high):
        rows[count][0] += 1
        rows[count][1] += low
        rows[count][2] += high
    return [
        f"  {'backing':>7}  {'n':>2}  {f'found at {GATE_LOW:.0%}':>11}  {f'found at {GATE_HIGH:.0%}':>11}",
        *(f"  {count:>7}  {n:>2}  {low:>11}  {high:>11}" for count, (n, low, high) in sorted(rows.items())),
    ]


# ── running one probe ─────────────────────────────────────────────────────

def _split_by_backing(
    citizens: list[Citizen], parties: list[Party], n: int, config: PolityConfig,
) -> dict[str, list[Citizen]]:
    """The forum's cells are two groups of citizens, not two prompts: founding turns on how many
    others stand nearer to them than to their own party (simple_rules.cofounders), so that count,
    against the number the rule needs, is the state a party move should follow."""
    needed = math.ceil(config.parties.founding_ratio * len(citizens))
    short: list[Citizen] = []
    enough: list[Citizen] = []
    for citizen in citizens:
        (enough if len(cofounders(citizen, citizens, parties)) >= needed else short).append(citizen)
    return {"too few would co-found": short[:n], "enough would co-found": enough[:n]}


def _shares(choices: Sequence[str], options: Sequence[str]) -> dict[str, float]:
    counted = collections.Counter(choices)
    total = len(choices) or 1
    return {option: counted[option] / total for option in (*options, "fail")}


def _run_probe(
    probe: Probe, key: str, citizens: list[Citizen], parties: list[Party], n: int,
    config: PolityConfig, client: LlmClientProtocol,
) -> dict[tuple[str, bool], dict[str, float]]:
    cells = (
        _split_by_backing(citizens, parties, n, config) if key == "forum"
        else {cell: citizens[:n] for cell in probe.cells}
    )
    jobs = [
        (cell, paraphrased, citizen)
        for cell in probe.cells for paraphrased in (False, True) for citizen in cells[cell]
    ]
    with ThreadPoolExecutor(WORKERS) as pool:
        answers = list(pool.map(lambda job: probe.ask(job[2], job[0], job[1], config, client), jobs))
    grouped: dict[tuple[str, bool], list[str]] = collections.defaultdict(list)
    for (cell, paraphrased, _), answer in zip(jobs, answers):
        grouped[(cell, paraphrased)].append(answer)
    return {key_: _shares(values, probe.options) for key_, values in grouped.items()}


def _largest_shift(left: dict[str, float], right: dict[str, float], options: Sequence[str]) -> float:
    return max(abs(left[option] - right[option]) for option in options)


def _noise(left: dict[str, float], right: dict[str, float], options: Sequence[str], n: int) -> float:
    """One standard error of the difference of the two shares that moved most -- the band inside
    which a shift says nothing. Binomial, so it shrinks only with the square root of n."""
    option = max(options, key=lambda o: abs(left[o] - right[o]))
    return math.sqrt(sum(p * (1 - p) / max(n, 1) for p in (left[option], right[option])))


def _verdicts(probe: Probe, shares: dict[tuple[str, bool], dict[str, float]], n: int) -> list[str]:
    low, high = probe.cells
    options = probe.options
    state_shift = _largest_shift(shares[(low, False)], shares[(high, False)], options)
    band = SENSITIVITY_SIGMAS * _noise(shares[(low, False)], shares[(high, False)], options, n)
    wording_shift = max(
        _largest_shift(shares[(cell, False)], shares[(cell, True)], options) for cell in probe.cells
    )
    rows = [shares[(cell, para)] for cell in probe.cells for para in (False, True)]
    taken = {option for option in options if any(row[option] > 0 for row in rows)}
    always = {option for option in options if all(row[option] == 1 for row in rows)}
    lines = [
        f"  SENSITIVITY  {'PASS' if state_shift >= band else 'UNRESOLVED'}"
        f"  largest shift {state_shift:.0%} across {probe.state_axis}"
        f" (noise band {band:.0%} at n={n}; raise --n to resolve a smaller one)",
        f"  DEAD OPTION  {'PASS' if not (options and (set(options) - taken or always)) else 'FAIL'}"
        f"  never taken: {sorted(set(options) - taken) or 'none'}; always taken: {sorted(always) or 'none'}",
        f"  WORDING      {'PASS' if wording_shift < max(state_shift, band) else 'FAIL'}"
        f"  paraphrase moves {wording_shift:.0%}, the state moves {state_shift:.0%}",
    ]
    return lines


def _print_probe(probe: Probe, shares: dict[tuple[str, bool], dict[str, float]], verdicts: list[str]) -> None:
    print(f"\n{probe.name}")
    header = "  cell".ljust(28) + "wording".ljust(12) + "".join(o.rjust(16) for o in probe.options)
    print(header)
    for cell in probe.cells:
        for paraphrased in (False, True):
            row = shares[(cell, paraphrased)]
            label = "paraphrase" if paraphrased else "shipped"
            print(
                f"  {cell}".ljust(28) + label.ljust(12)
                + "".join(f"{row[o]:.0%}".rjust(16) for o in probe.options)
            )
    for line in verdicts:
        print(line)
    if not any("FAIL" in line for line in verdicts):
        print("  -> neutral on all three checks")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=30, help="citizens per cell per wording (default 30)")
    parser.add_argument("--probe", action="append", help="only this probe (forum, threshold, ballot, campaign, president)")
    parser.add_argument("--gate-log", type=Path, default=None,
                        help="threshold gate: write every answer, with the founder's backing, as JSON lines (OBS-045)")
    parser.add_argument("--gate-wording", choices=("shipped", "count"), default="shipped",
                        help="threshold gate: 'count' states the founding rule as a number of citizens, not a percentage (OBS-045)")
    parser.add_argument("--checkpoint", type=Path, default=Path(os.environ.get("POLITY_CHECKPOINT", _DEFAULT_CHECKPOINT)))
    args = parser.parse_args(argv)
    if args.probe is not None and "threshold" not in args.probe and (args.gate_log or args.gate_wording != "shipped"):
        parser.error("--gate-log and --gate-wording apply to the threshold probe only")
    if args.gate_log is not None and not args.gate_log.parent.is_dir():
        parser.error(f"--gate-log: no directory {args.gate_log.parent}")

    if not args.checkpoint.exists():
        raise SystemExit(f"no checkpoint at {args.checkpoint} -- pass --checkpoint or set POLITY_CHECKPOINT")
    citizens, parties = _load_citizens(args.checkpoint)
    config = _config()
    client = build_json_client(config.llm, seed=config.run.seed)
    probes = _probes(citizens, parties)
    chosen = args.probe or list(probes)
    gate = "threshold" in chosen
    chosen = [key for key in chosen if key != "threshold"]
    unknown = sorted(set(chosen) - set(probes))
    if unknown:
        raise SystemExit(f"unknown probe(s) {unknown}; known: {sorted(probes)}")

    print(
        f"{len(citizens)} citizens from {args.checkpoint.parent.name}, {args.n} per cell per wording, "
        f"model {config.llm.model} at temperature {config.agents.turn_temperature}"
    )
    failures = 0
    for key in chosen:
        probe = probes[key]
        shares = _run_probe(probe, key, citizens, parties, args.n, config, client)
        verdicts = _verdicts(probe, shares, args.n)
        _print_probe(probe, shares, verdicts)
        failures += sum("FAIL" in line for line in verdicts)
    if gate and not _threshold_gate(citizens, parties, args.n, config, client, args.gate_log, args.gate_wording):
        failures += 1
    print(f"\n{failures} check(s) failed across {len(chosen) + gate} probe(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
