"""api.domain.polity.amendments -- how the polity amends its constitution (ADR-015).

The president proposes one amendment at a time; the next tick the sortition chamber's members
each vote yes or no in a turn of their own, and it is ratified when more than the share the
procedure in force asked for voted yes. What these functions hold is the part that needs no
agent: the words that tell agents the articles, the checks a proposal must pass, the tally.
"""
from __future__ import annotations

import json

from api.domain.polity.config import ARTICLES, Article, PolityConfig, amended, broken_rule
from api.domain.polity.constitution import Constitution, article_value, threshold_for
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.llm_schemas import AmendmentProposal


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
