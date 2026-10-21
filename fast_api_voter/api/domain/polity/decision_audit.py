"""Decision audit: how far a run's model decisions can be trusted, from the run's own files.

Three questions the other reports do not answer (2026-10-21 investigation, Q1/Q9):

- **Plumbing per decision type**: calls, retries, truncations, how many thinking calls ended at the
  thinking budget (the reasoning was cut, not finished), how many spent their reasoning looking for
  the output format (the 27B does, on nearly every call: OBS-053), and the fallback share of the
  journaled decisions.
- **Vote against the kernel's own rule.** The vote prompt states it: a candidate at distance
  <= blank_threshold is acceptable, blank only when none is. `vote_cast` answers are scored against
  it from the logged prompt, split by whether the call ended at the budget. Only first-attempt answers
  are scored (a retry replaces an answer the engine could not use); first attempts that are unreadable
  are counted as unscored, so the table says how much it left out. The 8B contradicts the
  rule in 10-20% of units when it finishes thinking and in about half when the budget cuts it. Since
  ADR-011 the counted ballots are the kernel's, so this audits the model, not the election.
- **Pressure against the kernel's rule.** `simple_rules.deterministic_pressure_action` acts past
  `blank_threshold x tolerance_scale`; the model's act is compared with it on the journaled context.
  A fallback decision IS that rule, so fallbacks are counted apart and left out of the comparison.

The vote needs `llm_prompts.jsonl` (POLITY_LOG_PROMPTS=1); without it that part says so. Nothing
here changes a run: it reads `llm_calls.jsonl`, `events.jsonl`, `config.json` and the prompts sidecar.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, PROMPT_LOG_FILENAME, read_prompts
from api.domain.polity.llm_time_attribution import kept_calls

BUDGET_ROOM = 2
"""A call whose reasoning tokens reach the budget minus this was cut by it, not finished."""
FORMAT_SEARCH = re.compile(r"\bschema\b|likely keys|need (to )?(output|produce) (a )?json|what (are the|fields)", re.I)
"""Reasoning that goes looking for the answer's shape (OBS-053's measure)."""
VOTE_TYPE = "vote_cast"
PRESSURE_TYPE = "pressure_action"
AT_BUDGET, UNDER_BUDGET = "at budget", "under budget"


@dataclass
class TypeStats:
    calls: int = 0
    retried: int = 0
    truncated: int = 0
    thinking: int = 0
    at_budget: int = 0
    format_search: int = 0


@dataclass
class VoteScore:
    units: int = 0
    rule_blank: int = 0
    model_blank: int = 0
    blank_though_acceptable: int = 0
    ranked: int = 0
    first_choice_right: int = 0


@dataclass
class PressureScore:
    units: int = 0
    rule_acts: int = 0
    model_acts: int = 0
    agree: int = 0
    fallbacks: int = 0
    """Consulted citizens whose act came from the deterministic fallback: not compared (it is the rule)."""


@dataclass
class RunAudit:
    types: dict[str, TypeStats] = field(default_factory=dict)
    journaled: Counter[str] = field(default_factory=Counter)
    fallbacks: Counter[str] = field(default_factory=Counter)
    vote: dict[str, VoteScore] | None = None
    """By budget state; None when the run kept no prompts."""
    vote_unscored: int = 0
    """First-attempt vote calls left out: no readable answer, or no prompt for them."""
    pressure: PressureScore | None = None


def _jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError:  # a torn last line of a killed run
                    continue


def at_budget(call: Mapping[str, Any]) -> bool:
    """True when a thinking call's reasoning ran into the thinking budget it was sent with."""
    budget = (call.get("extra_body") or {}).get("thinking_token_budget")
    return budget is not None and (call.get("reasoning_tokens") or 0) >= budget - BUDGET_ROOM


def type_stats(calls: list[dict[str, Any]]) -> dict[str, TypeStats]:
    stats: dict[str, TypeStats] = {}
    for call in calls:
        if call.get("kind") != "decision":
            continue
        s = stats.setdefault(str(call.get("decision_type")), TypeStats())
        s.calls += 1
        s.retried += bool(call.get("attempt"))
        s.truncated += call.get("finish_reason") == "length"
        if call.get("think"):
            s.thinking += 1
            s.at_budget += at_budget(call)
            s.format_search += bool(FORMAT_SEARCH.search(call.get("reasoning") or ""))
    return stats


def vote_rule(voter: Mapping[str, Any]) -> tuple[bool, int | None]:
    """(the rule says blank, the 1-based position of the nearest acceptable candidate) for one
    voter block of the vote prompt: `distances` per candidate in prompt order, `blank_threshold`."""
    distances = voter.get("distances") or []
    threshold = voter.get("blank_threshold")
    acceptable = [i for i, d in enumerate(distances) if threshold is not None and d <= threshold]
    if not acceptable:
        return True, None
    return False, min(acceptable, key=lambda i: distances[i]) + 1


def score_vote(score: VoteScore, voters: Mapping[int, Mapping[str, Any]], decisions: list[Any]) -> None:
    for decision in decisions:
        voter = voters.get(decision.get("cid", -1)) if isinstance(decision, dict) else None
        if voter is None:
            continue
        rule_blank, nearest = vote_rule(voter)
        model_blank = bool(decision.get("blank"))
        score.units += 1
        score.rule_blank += rule_blank
        score.model_blank += model_blank
        score.blank_though_acceptable += model_blank and not rule_blank
        if not model_blank and not rule_blank:
            ranking = decision.get("ranking") or []
            score.ranked += 1
            score.first_choice_right += bool(ranking) and ranking[0] == nearest


def _readable_prompts(run_dir: Path) -> dict[str, dict[str, Any]]:
    """call_id -> {"system", "user", "schema"} from the sidecar; empty when it is torn (a run still writing)."""
    try:
        return read_prompts(run_dir / PROMPT_LOG_FILENAME)
    except (ValueError, KeyError):
        return {}


def _score_call(scores: dict[str, VoteScore], call: Mapping[str, Any], prompt: str | None) -> bool:
    """One first-attempt vote call into the score of its budget state; False when it cannot be scored
    (no prompt, or an answer or prompt that is not the object the engine writes)."""
    try:
        request = json.loads(prompt or "")
        answer = json.loads(call.get("content") or "")
        voters = {v["cid"]: v for v in request["voters"]}
        decisions = answer["decisions"]
    except (ValueError, KeyError, TypeError, AttributeError):
        return False
    score_vote(scores[AT_BUDGET if at_budget(call) else UNDER_BUDGET], voters, decisions)
    return True


def audit_votes(run_dir: Path, calls: list[dict[str, Any]]) -> tuple[dict[str, VoteScore], int] | None:
    """(scores by budget state, first-attempt vote calls left unscored); None when the run kept no prompts."""
    if not (run_dir / PROMPT_LOG_FILENAME).is_file():
        return None
    votes = [c for c in calls if c.get("kind") == "decision" and c.get("decision_type") == VOTE_TYPE and not c.get("attempt")]
    prompts = _readable_prompts(run_dir)
    scores = {AT_BUDGET: VoteScore(), UNDER_BUDGET: VoteScore()}
    unscored = sum(not _score_call(scores, c, (prompts.get(c["call_id"]) or {}).get("user")) for c in votes)
    return scores, unscored


def rule_acts(context: Mapping[str, Any], mobilization_anger: float) -> bool:
    """Whether `simple_rules.deterministic_pressure_action` acts for a consulted citizen, on the
    journaled context: past blank_threshold x tolerance_scale (emotions.tolerance_scale)."""
    scale = 1.0 - mobilization_anger * (context.get("anger") or 0.0)
    return bool(context["self_gap"] >= context["blank_threshold"] * scale)


def audit_events(run_dir: Path, mobilization_anger: float) -> tuple[Counter[str], Counter[str], PressureScore]:
    journaled: Counter[str] = Counter()
    fallbacks: Counter[str] = Counter()
    pressure = PressureScore()
    for event in _jsonl(run_dir / "events.jsonl"):
        payload = event.get("payload") or {}
        if "llm_fallback" in payload:
            journaled[event["event_type"]] += 1
            fallbacks[event["event_type"]] += int(payload["llm_fallback"] or 0)
        if event["event_type"] == PRESSURE_TYPE and payload.get("ctx"):
            if payload.get("llm_fallback"):
                pressure.fallbacks += 1
                continue
            rule, model = rule_acts(payload["ctx"], mobilization_anger), payload["act"] != 0
            pressure.units += 1
            pressure.rule_acts += rule
            pressure.model_acts += model
            pressure.agree += rule == model
    return journaled, fallbacks, pressure


def audit_run(run_dir: Path) -> RunAudit:
    """The audit of one run directory (events.jsonl, llm_calls.jsonl, config.json, and the
    prompts sidecar when it has one). A run without an LLM call log gives an empty audit."""
    calls_path = run_dir / CALL_LOG_FILENAME
    calls = kept_calls(list(_jsonl(calls_path))) if calls_path.is_file() else []
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8")) if (run_dir / "config.json").is_file() else {}
    anger = float((config.get("emotions") or {}).get("mobilization_anger", 0.0))
    audit = RunAudit(types=type_stats(calls))
    voted = audit_votes(run_dir, calls)
    if voted is not None:
        audit.vote, audit.vote_unscored = voted
    if (run_dir / "events.jsonl").is_file():
        audit.journaled, audit.fallbacks, pressure = audit_events(run_dir, anger)
        audit.pressure = pressure if pressure.units or pressure.fallbacks else None
    return audit


def _pct(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "-"


def _plumbing_table(audits: Mapping[str, RunAudit]) -> list[str]:
    types = sorted({t for a in audits.values() for t in a.types})
    lines = [
        "Thinking budget: share of thinking calls whose reasoning ended at the budget (cut, not finished); "
        "format search: share whose reasoning looked for the output's shape (OBS-053).\n",
        "| run | decision | calls | retried | truncated | thinking | at budget | format search |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, a in audits.items():
        for t in types:
            s = a.types.get(t)
            if s:
                lines.append(
                    f"| {label} | {t} | {s.calls} | {_pct(s.retried, s.calls)} | {_pct(s.truncated, s.calls)} | {s.thinking} | "
                    f"{_pct(s.at_budget, s.thinking)} | {_pct(s.format_search, s.thinking)} |"
                )
    return lines


def _fallback_table(audits: Mapping[str, RunAudit]) -> list[str]:
    """Fallbacks by the journal's own event type: the call log names decisions otherwise (agent_turn is president_turn
    and nominee_turn there), so the two are not joined."""
    lines = ["| run | journaled decision | decisions | fell back |", "|---|---|---:|---:|"]
    rows = [
        f"| {label} | {t} | {n} | {_pct(a.fallbacks.get(t, 0), n)} ({a.fallbacks.get(t, 0)}) |"
        for label, a in audits.items() for t, n in sorted(a.journaled.items()) if a.fallbacks.get(t, 0)
    ]
    return [*lines, *rows] if rows else ["- no journaled decision fell back to the deterministic baseline"]


def _vote_rows(label: str, audit: RunAudit) -> list[str]:
    return [
        f"| {label} | {state} | {v.units} | {_pct(v.rule_blank, v.units)} | {_pct(v.model_blank, v.units)} | "
        f"{_pct(v.blank_though_acceptable, v.units)} | {v.first_choice_right}/{v.ranked} |"
        for state, v in (audit.vote or {}).items() if v.units
    ]


def _vote_table(audits: Mapping[str, RunAudit]) -> list[str]:
    voted = {label: a for label, a in audits.items() if a.vote is not None}
    if not voted:
        return ["- no run kept its prompts (start runs with POLITY_LOG_PROMPTS=1): not scored"]
    lines = [
        "| run | budget state | units | rule says blank | model blank | blank though a candidate was acceptable | "
        "first choice = nearest acceptable |",
        "|---|---|---:|---:|---:|---:|---:|",
        *(row for label, a in voted.items() for row in _vote_rows(label, a)),
    ]
    unscored = [f"{label} {a.vote_unscored}" for label, a in voted.items() if a.vote_unscored]
    if unscored:
        lines += ["", "- first-attempt vote calls left unscored (unreadable answer or no prompt): " + ", ".join(unscored)]
    return lines


def _pressure_table(audits: Mapping[str, RunAudit]) -> list[str]:
    pressed = {label: a.pressure for label, a in audits.items() if a.pressure is not None}
    if not pressed:
        return ["- no pressure decisions journaled"]
    return [
        "| run | consulted | compared | rule acts | model acts | same decision | fell back (not compared) |",
        "|---|---:|---:|---:|---:|---:|---:|",
        *(
            f"| {label} | {p.units + p.fallbacks} | {p.units} | {_pct(p.rule_acts, p.units)} | {_pct(p.model_acts, p.units)} | "
            f"{_pct(p.agree, p.units)} | {p.fallbacks} |"
            for label, p in pressed.items()
        ),
    ]


def render_audit(audits: Mapping[str, RunAudit]) -> list[str]:
    """Markdown lines for a sweep summary or the CLI: one table per question, one row per run
    (or per decision type). Rates are shares of the run's own counts, never pooled across runs."""
    return [
        "## Decision audit (decision_audit.py; from each run's own files)\n",
        *_plumbing_table(audits),
        "",
        "### Fallbacks (journaled decisions that fell back to the deterministic baseline)\n",
        *_fallback_table(audits),
        "",
        "### Votes against the kernel's rule (audit ballots; the counted ballots are the kernel's)\n",
        *_vote_table(audits),
        "",
        "### Pressure against the kernel's rule (`deterministic_pressure_action`, on the journaled context)\n",
        *_pressure_table(audits),
        "",
    ]
