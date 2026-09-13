"""The bake-off scorecard as Markdown (S2.2). Generated from `bakeoff_scorecard.scorecard`'s
JSON, never written by hand."""
from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


def _pct(rate: dict[str, Any] | None) -> str:
    if not rate or rate["rate"] is None:
        return "–"
    low, high = rate["wilson95"]
    return f"{rate['successes']}/{rate['trials']} = {100 * rate['rate']:.1f}% [{100 * low:.1f}, {100 * high:.1f}]"


def _num(value: float | None, digits: int = 3) -> str:
    return "–" if value is None else f"{value:+.{digits}f}" if digits == 3 else f"{value:.{digits}f}"


def _yes(value: bool | None) -> str:
    return {True: "yes", False: "**no**", None: "unmeasured"}[value]


def _row(cells: Iterable[Any]) -> str:
    return "| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |"


def _table(header: list[str], rows: Iterable[Iterable[Any]]) -> list[str]:
    return [_row(header), _row(["---"] * len(header)), *(_row(r) for r in rows)]


def _think(gate: dict[str, Any] | None) -> str:
    if not gate:
        return "not run"
    return f"{_yes(gate['passed'])} (on {gate['think_true_reasoning_tokens']}, off {gate['think_false_reasoning_tokens']})"


def _logprob(gate: dict[str, Any]) -> str:
    if not gate["aligned"]:
        return "unmeasured"
    return f"{_yes(gate['passed'])}: {gate['aligned']}/{gate['units']} aligned, {gate['threshold_call_correct']} correct, separation {_num(gate['separation'])}"


def _session_rows(sessions: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [s["label"], f"{s['metadata'].get('provider', '?')}/{s['metadata'].get('model', '?')}", s["metadata"].get("weights", "–"),
         _yes(s["bank_matches"]), _think(s["gates"]["think"]), _logprob(s["gates"]["logprob"]),
         f"output {_pct(s['noise_floor']['identical_output'])}; units {_pct(s['noise_floor']['unit_agreement'])}"]
        for s in sessions
    ]


def _group_summary(name: str, group: dict[str, Any]) -> str:
    varies = f"{group['distinct_answers']} distinct answer(s) over {group['levels']} levels"
    if group["p_by_t"] is None:
        return f"{name}: {varies}"
    curve = ", ".join(f"{float(t):g}→{p:.3f}" for t, p in group["p_by_t"].items())
    return f"{name}: {varies}; P by level {curve}; separation {_num(group['separation'])} ({'flat' if group['flat'] else 'moves'})"


def _controls_summary(group: str, controls: dict[str, Any]) -> str:
    """S2.5: each control's agreement with the production rendering, and whether it reads flat."""
    parts = [
        f"{name} agrees {_pct(control['agreement_with_base'])}, {'unread' if control['flat'] is None else 'flat' if control['flat'] else 'moves'}"
        for name, control in controls.items()
    ]
    return f"{group} controls: " + ", ".join(parts)


def family_summary(family: str, score: dict[str, Any]) -> str:
    if score["kind"] == "truth":
        answers = ", ".join(f"{json.loads(a)}×{n}" for a, n in score["answers"].items())
        return f"{family}: accuracy {_pct(score['accuracy'])}; answers {answers}"
    if score["kind"] == "contrast":
        base = [_group_summary(f"{family}/{g}", group) for g, group in score["groups"].items()]
        return "; ".join(base + [_controls_summary(g, controls) for g, controls in score.get("controls", {}).items()])
    return (f"{family}: same candidate {_pct(score['same_candidate'])}; same listed position "
            f"{_pct(score['same_listed_position'])}; last listed {_pct(score['last_listed_position'])}")


def _cost(cost: dict[str, Any]) -> str:
    latency = "–" if cost["latency_s_mean"] is None else f"{cost['latency_s_mean']:.1f} s"
    tokens = "/".join(_num(cost[key], 0) for key in ("prompt_tokens_mean", "completion_tokens_mean", "reasoning_tokens_mean"))
    return f"{latency}; tokens in/out/reasoning {tokens}; truncated {cost['truncated']}"


def _decision_type_sections(sessions: list[dict[str, Any]]) -> list[str]:
    types = sorted({dt for s in sessions for dt in s["decision_types"]})
    lines: list[str] = []
    for decision_type in types:
        rows = [
            [s["label"], _pct(scored["validity"]), "<br>".join(family_summary(f, fs) for f, fs in scored["families"].items()), _cost(scored["cost"])]
            for s in sessions if (scored := s["decision_types"].get(decision_type)) is not None
        ]
        lines += ["", f"## {decision_type}", "", *_table(["session", "validity", "accuracy / sensitivity", "cost per request"], rows)]
    return lines


def _statistic(test: dict[str, Any]) -> str:
    if test["test"] == "mcnemar_exact":
        return f"McNemar exact, discordant {test['first_only']}/{test['second_only']}"
    return f"Cochran's Q = {test['q']:.2f}, df {test['df']}"


def render_markdown(card: dict[str, Any]) -> str:
    bank = card["bank"]
    reference = bank["reference"]
    lines = [
        "# Model bake-off scorecard",
        "",
        f"Case bank `{bank['sha256'][:16]}`: {bank['cases']} cases rendered for {reference['provider']}/{reference['model']} "
        f"(seed {reference['seed']}). Control: **{card['control']}**. Generated by `scripts/bakeoff_report.py`.",
        "",
        "## Sessions and gates",
        "",
        *_table(["session", "model", "weights", "bank matches", "thinking gate", "logprob gate", "noise floor (re-run)"],
                _session_rows(card["sessions"])),
        *_decision_type_sections(card["sessions"]),
        "",
        "## Comparisons (paired, Holm-corrected)",
        "",
    ]
    if card["comparisons"]:
        lines += _table(["test", "n", "statistic", "p", "p (Holm)"],
                        ([name, t["n"], _statistic(t), f"{t['p_value']:.4g}", f"{t['p_holm']:.4g}"] for name, t in card["comparisons"].items()))
    else:
        lines.append("One session: nothing to compare.")
    lines += ["", f"## Acceptance on {card['control']}", ""]
    lines += _table(["check", "expected", "observed", "passed"],
                    ([c["check"], c["expected"], json.dumps(c["observed"]), _yes(c["passed"])] for c in card["acceptance"]))
    return "\n".join(lines) + "\n"
