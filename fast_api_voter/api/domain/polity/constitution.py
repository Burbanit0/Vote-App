"""api.domain.polity.constitution -- the rules in force (ADR-015).

The run's config is the constitution as it was founded; an amendment changes one of its
articles (config.ARTICLES) from a tick on. What is in force is the founding config with
every amendment laid over it, rebuilt each tick for TickContext.config -- so every phase,
which reads its rules from there, reads the rules in force, and the founding config (and
its checkpoint hash) never moves. The history lives in the journal's constitution_amended
events; the state keeps only what is needed to rebuild the rules.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from api.domain.polity.config import ARTICLES, PolityConfig, amended


@dataclass(frozen=True)
class Proposal:
    """An amendment the chamber has yet to vote. The threshold is the one in force when it was
    proposed: a proposal to lower it is still judged by the old one."""

    article: str
    value: Any
    proposer: int
    tick: int
    threshold: float
    reason: str


@dataclass(frozen=True)
class Constitution:
    version: int = 0
    """0 is the founding constitution; each amendment adds one."""
    values: Mapping[str, Any] = field(default_factory=dict)
    """Article path -> the value an amendment gave it."""
    pending: Proposal | None = None


def in_force(founding: PolityConfig, constitution: Constitution | None) -> PolityConfig:
    """The rules in force: the founding config with every amended article laid over it."""
    config = founding
    for path, value in (constitution.values if constitution is not None else {}).items():
        config = amended(config, path, value)
    return config


def amend(constitution: Constitution | None, path: str, value: Any) -> Constitution:
    """The constitution with one more amendment. The caller has checked that the article
    exists and allows the value (config.ARTICLES), and that the rules still hold."""
    assert ARTICLES[path].allows(value)
    current = constitution or Constitution()
    return Constitution(version=current.version + 1, values={**current.values, path: value})


def propose(constitution: Constitution | None, proposal: Proposal) -> Constitution:
    return replace(constitution or Constitution(), pending=proposal)


def close_proposal(constitution: Constitution) -> Constitution | None:
    """Without the pending proposal; None when that leaves the founding constitution."""
    return Constitution(constitution.version, constitution.values) if constitution.version else None


def threshold_for(config: PolityConfig, article: str) -> float:
    """The share of the chamber an amendment to `article` must beat: the general threshold, or
    the article's own when it is entrenched higher."""
    return max(config.constitution.amendment_threshold, config.constitution.entrenched.get(article, 0.0))


def article_value(config: PolityConfig, path: str) -> Any:
    section, key = path.split(".")
    return getattr(getattr(config, section), key)
