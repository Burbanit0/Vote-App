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
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.agents import (  # noqa: E402
    PRESIDENT_TURN,
    PresidentBriefing,
    ballot_system_prompt,
    ballot_user_prompt,
    decide_ballot,
    decide_forum,
    decide_turn,
    forum_system_prompt,
    forum_user_prompt,
    party_roll,
    stand_line,
    president_system_prompt,
    president_user_prompt,
    proposer_line,
)
from api.domain.polity.checkpoint import _citizen_from_dict, _party_from_dict  # noqa: E402
from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config, validate_config  # noqa: E402
from api.domain.polity.constitution import Proposal, article_value  # noqa: E402
from api.domain.polity.llm_behavior_engine import ResponseContext  # noqa: E402
from api.domain.polity.llm_client import LlmClientProtocol, build_json_client  # noqa: E402
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
        "At an election, citizens weigh a candidate of their own party more favourably, and a party nominates only its own members.",
        "At an election a candidate of a citizen's own party is weighed more favourably, and only its own members may be nominated by a party.",
    ),
)


def _forum_ask(
    citizen: Citizen, cell: str, paraphrased: bool, config: PolityConfig, client: LlmClientProtocol,
    *, population: list[Citizen], parties: list[Party], roll: str,
) -> str:
    del cell  # the cell is which citizens these are (how many would co-found), not a prompt change
    system = forum_system_prompt(citizen, config)
    if paraphrased:
        system = _paraphrase(system, _FORUM_PAIRS)
    outcome = decide_forum(
        citizen, system_prompt=system, config=config, client=client,
        user_prompt=forum_user_prompt(
            tick=5, member=False, feed="", memory="", roll=roll,
            stand=stand_line(citizen, population, parties, config),
        ),
    )
    return outcome.turn.party_move if outcome.turn is not None else "fail"


# ── probe 2: the chamber's ballot (OBS-030) ───────────────────────────────

_SELF_SERVING = ("institutions.president_term_limit", 3, "Experienced leadership serves the country; a third term lets me finish my programme.")
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
    who = proposer_line(citizen, approval=0.35, ticks_left=4, lame_duck=True)
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
        "One more act is open to you, and the constitution forbids it:",
        "There is one further act, outside the constitution:",
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
        "president": Probe(
            name="president extra-legal act", options=("none", "refuse_to_leave"),
            cells=("low approval", "high approval"), state_axis="the president's approval",
            paraphrase=lambda text: _paraphrase(text, _REGIME_PAIRS),
            ask=_president_ask,
        ),
    }


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
    parser.add_argument("--probe", action="append", help="only this probe (forum, ballot, president)")
    parser.add_argument("--checkpoint", type=Path, default=Path(os.environ.get("POLITY_CHECKPOINT", _DEFAULT_CHECKPOINT)))
    args = parser.parse_args(argv)

    if not args.checkpoint.exists():
        raise SystemExit(f"no checkpoint at {args.checkpoint} -- pass --checkpoint or set POLITY_CHECKPOINT")
    citizens, parties = _load_citizens(args.checkpoint)
    config = _config()
    client = build_json_client(config.llm, seed=config.run.seed)
    probes = _probes(citizens, parties)
    chosen = args.probe or list(probes)
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
    print(f"\n{failures} check(s) failed across {len(chosen)} probe(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
