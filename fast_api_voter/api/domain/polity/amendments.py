"""api.domain.polity.amendments -- how the polity amends its constitution (ADR-015).

The president proposes one amendment at a time; the next tick the sortition chamber's members
each vote yes or no in a turn of their own, and it is ratified when more than the share the
procedure in force asked for voted yes. What these functions hold is the part that needs no
agent: the words that tell agents the articles, the checks a proposal must pass, the tally.
"""
from __future__ import annotations

import json

from api.domain.polity.ballot_and_aggregation import allocate_seats, get_presidential_winner, seat_lot
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import ARTICLES, Article, PolityConfig, amended, broken_rule
from api.domain.polity.constitution import Constitution, article_value, threshold_for
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.legislation import Legislature
from api.domain.polity.llm_schemas import AmendmentProposal
from api.domain.polity.simple_rules import BLANK_LABEL, candidate_label, citizen_id_from_label


def value_text(value: object) -> str:
    """As the model must write it in an answer: JSON, so "two_round", null, 0.5."""
    return json.dumps(value)


def _allowed(article: Article) -> str:
    if article.choices:
        return ", ".join(value_text(v) for v in article.choices)
    if article.integer:
        return f"a whole number from {article.low:.0f} to {article.high:.0f}"
    return f"a number from {article.low:g} to {article.high:g}"


def articles_text(config: PolityConfig) -> str:
    """The articles that can be amended and the values each may take -- stable for a run, so
    it sits in a system prompt."""
    return "\n".join(
        f"- {path} -- {article.summary}; it may be: {_allowed(article)}" for path, article in ARTICLES.items()
    )


def proposal_closed(constitution: Constitution | None, members: int) -> str | None:
    """Why no amendment can be proposed now, in the words a briefing shows; None when one can."""
    if constitution is not None and constitution.pending is not None:
        pending = constitution.pending
        return f"the chamber is yet to vote on changing {pending.article} to {value_text(pending.value)}"
    if not members:
        return "no chamber has been drawn yet"
    return None


def constitution_text(config: PolityConfig, constitution: Constitution | None, members: int) -> str:
    """The constitution in force, what each article's amendment needs, and whether one can be
    proposed this tick -- the amendments part of a leader's briefing."""
    rows = [
        f"- {path}: {value_text(article_value(config, path))} (amending it needs more than "
        f"{threshold_for(config, path):.0%} of the chamber's {members} members)"
        for path in ARTICLES
    ]
    closed = proposal_closed(constitution, members)
    status = "You may propose an amendment this tick." if closed is None else f"No amendment can be proposed this tick: {closed}."
    return "The constitution in force:\n" + "\n".join(rows) + f"\n{status}"


def validate_amendment(proposal: AmendmentProposal, config: PolityConfig) -> None:
    """What the schema cannot say: the article exists, allows the value, the value is a change,
    and the rules still hold with it. An error is retried like any invalid turn."""
    article = ARTICLES.get(proposal.article)
    if article is None:
        raise LlmResponseError(f"amendment: {proposal.article!r} is not an article")
    if not article.allows(proposal.value):
        raise LlmResponseError(f"amendment: {proposal.value!r} is not a value {proposal.article} may take")
    if proposal.value == article_value(config, proposal.article):
        raise LlmResponseError(f"amendment: {proposal.article} is already {value_text(proposal.value)}")
    broken = broken_rule(amended(config, proposal.article, proposal.value))
    if broken is not None:
        raise LlmResponseError(f"amendment: the rules would not hold ({broken})")


def ratified(yes: int, members: int, threshold: float) -> bool:
    """More than `threshold` of all members voted yes; a member who did not vote counts against."""
    return yes > threshold * members


def referendum_count(ballots: list[list[str]], old: str, new: str) -> tuple[int, int] | None:
    """The last election's ballots re-counted under both methods: how many citizens ranked the
    new method's winner above the old one's (yes), and how many the reverse (no). None when both
    methods elect the same person, so the change would have altered nothing."""
    before, after = get_presidential_winner(ballots, old), get_presidential_winner(ballots, new)
    if before == after:
        return None
    gaps = [_rank(b, after) - _rank(b, before) for b in ballots]
    return sum(gap < 0 for gap in gaps), sum(gap > 0 for gap in gaps)


_THRESHOLD = ARTICLES["institutions.electoral_threshold"]
_BARS = tuple(float(bar) for bar in (_THRESHOLD.low, 0.03, 0.05, 0.08, _THRESHOLD.high) if bar is not None)
"""The electoral thresholds the stakes re-seat at: the article's own ends, and the usual bars between."""


def stakes_text(
    config: PolityConfig, president: Citizen, ballots: list[list[str]] | None, legislature: Legislature | None,
    *, barred: bool = False,
) -> str | None:
    """ADR-026: what the rules would give the president -- `ballots`, the citizens' ballots today over the last
    election's candidates (ADR-027: the next election, not the last), counted under each voting method; and the
    last legislative votes re-seated under each seat rule and threshold. Facts the kernel computes, so a
    self-interested proposal can be weighed (C3), with nothing said about which to propose (C4). None when there
    is nothing to count yet."""
    lines = [_method_stakes(president, ballots, config.institutions.presidential_method, barred) if ballots else None,
             _seat_stakes(config, president, legislature) if legislature is not None and legislature.votes else None]
    return "\n".join(line for line in lines if line) or None


def _method_stakes(president: Citizen, ballots: list[list[str]], in_force: str, barred: bool) -> str:
    elected: dict[str, list[str]] = {}
    for method in map(str, ARTICLES["institutions.presidential_method"].choices):
        label = f"{method} (in force)" if method == in_force else method
        elected.setdefault(_elected(get_presidential_winner(ballots, method), president), []).append(label)
    # Yours first and on its own: a president reading thirteen methods grouped by winner picked one that elected
    # the rival in every probed turn (ADR-027).
    yours = ", ".join(elected.pop("you", [])) or "no method"
    others = "; ".join(f"{who} under: {', '.join(methods)}" for who, methods in elected.items())
    limit = " -- but under the term limit in force you cannot stand again" if barred else ""
    return (f"If the last election's candidates stood again today, the citizens' ballots would elect you under: {yours}"
            f"{limit}." + (f" They would elect {others}." if others else ""))


def _seat_stakes(config: PolityConfig, president: Citizen, legislature: Legislature) -> str | None:
    """The votes as cast, re-seated: the mechanical effect of each rule. Under ADR-024 they were cast against the
    threshold in force, so a lower bar would also have kept some deserters home -- not shown."""
    votes, party = legislature.votes or {}, president.party_affiliation
    if party not in votes:
        return None
    institutions, cast, tick = config.institutions, {str(p): v for p, v in votes.items()}, legislature.votes_tick or 0

    def seats(method: str, threshold: float) -> int:  # ties drawn as the election drew them
        return allocate_seats(cast, institutions.assembly_seats, method, threshold, rng=seat_lot(config.run.seed, tick))[str(party)]


    by_rule = ", ".join(f"{rule} {seats(str(rule), institutions.electoral_threshold)}"
                        for rule in ARTICLES["institutions.seat_allocation"].choices)
    by_bar = ", ".join(f"{bar:.0%} {seats(institutions.seat_allocation, bar)}" for bar in _BARS)
    return (f"Re-seated from the last legislative election's votes, your party ({party}) wins "
            f"{seats(institutions.seat_allocation, institutions.electoral_threshold)} of {institutions.assembly_seats} "
            f"seats under the rules in force; under each seat allocation: {by_rule}; at an electoral threshold of {by_bar}.")


def _elected(label: str | None, president: Citizen) -> str:
    if label is None or label == BLANK_LABEL:
        return "no one"
    return "you" if label == candidate_label(president) else f"citizen {citizen_id_from_label(label)}"


def _rank(ballot: list[str], label: str | None) -> int:
    return ballot.index(label) if label in ballot else len(ballot)
