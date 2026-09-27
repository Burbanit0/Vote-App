"""S4.3 (docs/adr/ADR-012-dynamic-citizens.md): anger, anxiety and enthusiasm.

Each is in [0, 1] and moves every tick `1 - decay` of the way toward its appraisal:

- **anger** toward the sitting president: how far past the citizen's tolerance the
  president's revealed position stands, gap / blank_threshold - 1, clamped;
- **enthusiasm**: how far inside it, 1 - gap / blank_threshold, clamped;
- **anxiety**: the economy's distance from normal, |x| / economy_shock_threshold, clamped.

With no president (or for the president), anger and enthusiasm decay toward 0.

They act in two places, each weighted by EmotionsConfig: the awakening threshold, where
anger and anxiety lower it and enthusiasm raises it (`awakening_pull`, applied inside the
threshold's own bounded modulation), and the deterministic pressure rule's tolerance,
which anger lowers (`tolerance_scale`). A citizen whose emotions are untracked (None)
exerts neither.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from api.domain.polity.citizen import Citizen
from api.domain.polity.config import EmotionsConfig


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class Appraisal:
    anger: float
    anxiety: float
    enthusiasm: float


def appraise(gap: float | None, blank_threshold: float, economy_x: float, shock_threshold: float) -> Appraisal:
    """`gap` is the citizen's self_gap to the sitting president, None without one."""
    if gap is None:
        anger = enthusiasm = 0.0
    else:
        ratio = gap / blank_threshold if blank_threshold > 0 else (float("inf") if gap > 0 else 0.0)
        anger, enthusiasm = _clamp(ratio - 1.0), _clamp(1.0 - ratio)
    anxiety = _clamp(abs(economy_x) / shock_threshold) if shock_threshold > 0 else float(economy_x != 0.0)
    return Appraisal(anger=anger, anxiety=anxiety, enthusiasm=enthusiasm)


def feel(citizen: Citizen, appraisal: Appraisal, decay: float) -> None:
    """Move the citizen's emotions toward the appraisal; untracked emotions start at 0."""
    def blend(previous: float | None, target: float) -> float:
        return decay * (previous or 0.0) + (1.0 - decay) * target

    citizen.anger = blend(citizen.anger, appraisal.anger)
    citizen.anxiety = blend(citizen.anxiety, appraisal.anxiety)
    citizen.enthusiasm = blend(citizen.enthusiasm, appraisal.enthusiasm)


def mean_emotions(citizens: Sequence[Citizen]) -> Appraisal:
    """The population's mean emotions, an untracked one counting as 0."""
    count = max(len(citizens), 1)
    return Appraisal(
        anger=sum(c.anger or 0.0 for c in citizens) / count,
        anxiety=sum(c.anxiety or 0.0 for c in citizens) / count,
        enthusiasm=sum(c.enthusiasm or 0.0 for c in citizens) / count,
    )


def awakening_pull(citizen: Citizen, config: EmotionsConfig) -> float:
    """How much the citizen's emotions lower their awakening threshold's modulation
    (negative: raise it). 0.0 while untracked."""
    if citizen.anger is None or citizen.anxiety is None or citizen.enthusiasm is None:
        return 0.0
    return (
        config.awakening_anger * citizen.anger
        + config.awakening_anxiety * citizen.anxiety
        - config.awakening_enthusiasm * citizen.enthusiasm
    )


def tolerance_scale(citizen: Citizen, config: EmotionsConfig) -> float:
    """The factor anger applies to the blank threshold the deterministic pressure rule
    acts past. 1.0 while untracked."""
    return 1.0 if citizen.anger is None else 1.0 - config.mobilization_anger * citizen.anger
