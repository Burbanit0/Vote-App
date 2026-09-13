"""The bake-off scorecard (S2.2): what each model's session says, per decision type, and
how the models compare on the same cases.

Per model x decision type:
- **validity**: requests whose answer decodes into a batch production would accept;
- **accuracy** (ground-truth families): units whose answer matches the deterministic rule,
  with a Wilson interval -- an invalid request's units count as wrong;
- **sensitivity** (contrast families): whether answers vary across the contrast, and the
  probability read off the logprobs at each level, its separation between the poles and
  whether that is flat (|separation| < 0.10, S2.4's collapse bar); for the permutation
  family, how often a pick follows the candidate rather than the listed position;
- **cost**: latency and tokens per request, and truncations.

Per model: the thinking gate, the logprob alignment gate, and the noise floor from the
re-run tenth. Across models: McNemar against the control model and Cochran's Q over all
models, on accuracy and on validity, Holm-corrected over every test reported.
"""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from api.domain.polity.bakeoff_bank import BASE_CONTROL, LOGPROB_GATE_FAMILY, Case, CaseBank
from api.domain.polity.bakeoff_runner import GATES_FILENAME, RESULTS_FILENAME, SESSION_FILENAME, read_results
from api.domain.polity.bakeoff_statistics import cochrans_q, holm_adjust, mcnemar_exact, separation, spread, wilson_interval

FLAT_SEPARATION = 0.10


@dataclass(frozen=True)
class Session:
    label: str
    metadata: dict[str, Any]
    gates: dict[str, Any]
    results: list[dict[str, Any]]

    def by_case(self, pass_name: str = "main") -> dict[str, dict[str, Any]]:
        return {r["case_id"]: r for r in self.results if r["pass"] == pass_name}


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else {}


def load_session(session_dir: Path) -> Session:
    metadata = _read_json(session_dir / SESSION_FILENAME)
    return Session(
        label=str(metadata.get("label", session_dir.name)), metadata=metadata,
        gates=_read_json(session_dir / GATES_FILENAME), results=read_results(session_dir / RESULTS_FILENAME),
    )


def discover_sessions(root: Path) -> list[Session]:
    return [load_session(d) for d in sorted(root.iterdir()) if (d / RESULTS_FILENAME).is_file()]


def _rate(successes: int, trials: int) -> dict[str, Any]:
    interval = wilson_interval(successes, trials)
    return {"successes": successes, "trials": trials, "rate": successes / trials if trials else None,
            "wilson95": list(interval) if interval else None}


# ── per family ────────────────────────────────────────────────────────────

def _correct(labels: dict[str, Any], answer: Any, expected: Any) -> bool:
    if answer is None:
        return False
    if labels.get("match") == "acts":
        return bool(answer != 0) == bool(expected)
    return bool(answer == expected)


def truth_outcomes(cases: Iterable[Case], main: dict[str, dict[str, Any]]) -> dict[tuple[str, str], bool]:
    """(case_id, unit) -> correct, for every answered unit of every ground-truth case."""
    outcomes = {}
    for case in cases:
        result = main.get(case.case_id)
        if result is None:
            continue
        for unit, expected in case.labels["truth"].items():
            outcomes[(case.case_id, unit)] = _correct(case.labels, result["answers"].get(unit), expected)
    return outcomes


def score_truth(cases: Sequence[Case], main: dict[str, dict[str, Any]]) -> dict[str, Any]:
    outcomes = truth_outcomes(cases, main)
    answers = Counter(
        json.dumps(main[c.case_id]["answers"].get(unit)) for c in cases if c.case_id in main for unit in c.labels["truth"]
    )
    return {"kind": "truth", "accuracy": _rate(sum(outcomes.values()), len(outcomes)), "answers": dict(sorted(answers.items()))}


def _contrast_rows(cases: Sequence[Case], main: dict[str, dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """(group, control) -> one row per read unit, with the unit's canonical id; `cases` are all
    answered (score_decision_types keeps only those)."""
    rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        result = main[case.case_id]
        identity = case.labels.get("identity", {})
        key = (case.labels["group"], case.labels.get("control", BASE_CONTROL))
        for unit in case.labels["units"]:
            rows[key].append({"t": case.labels["t"], "unit": identity.get(str(unit), unit),
                              "answer": result["answers"].get(str(unit)), "p": (result["probabilities"] or {}).get(str(unit))})
    return rows


def _by_level(rows: Iterable[dict[str, Any]], key: str) -> dict[float, list[Any]]:
    grouped: dict[float, list[Any]] = defaultdict(list)
    for row in rows:
        grouped[row["t"]].append(row[key])
    return grouped


def _mean_probability_by_level(rows: Sequence[dict[str, Any]]) -> dict[float, float]:
    read = [row for row in rows if row["p"] is not None]
    return {t: statistics.fmean(ps) for t, ps in _by_level(read, "p").items()}


def _group_sensitivity(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    answers_by_t = _by_level(rows, "answer")
    mean_p = _mean_probability_by_level(rows)
    sep = separation(mean_p)
    return {
        "levels": len(answers_by_t),
        "distinct_answers": len({json.dumps(a) for a in (row["answer"] for row in rows)}),
        "answers_by_t": {str(t): [json.dumps(a) for a in answers] for t, answers in sorted(answers_by_t.items())},
        "p_by_t": {str(t): p for t, p in sorted(mean_p.items())} or None,
        "separation": sep,
        "spread": spread(list(mean_p.values())),
        "flat": None if sep is None else abs(sep) < FLAT_SEPARATION,
    }


def _agreement(rows: Sequence[dict[str, Any]], base_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """How often a control's answer is the base answer for the same level and the same citizen or party."""
    base = {(row["t"], row["unit"]): row["answer"] for row in base_rows}
    compared = [row["answer"] == base[(row["t"], row["unit"])] for row in rows if (row["t"], row["unit"]) in base]
    return _rate(sum(compared), len(compared))


def score_contrast(cases: Sequence[Case], main: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """`groups`: each contrast as production renders it. `controls` (S2.5): the same contrast
    under each control, and how often its answers agree with production's rendering."""
    rows = _contrast_rows(cases, main)
    base = {group: group_rows for (group, control), group_rows in rows.items() if control == BASE_CONTROL}
    controls: dict[str, dict[str, Any]] = defaultdict(dict)
    for (group, control), group_rows in sorted(rows.items()):
        if control != BASE_CONTROL:
            controls[group][control] = {**_group_sensitivity(group_rows), "agreement_with_base": _agreement(group_rows, base.get(group, []))}
    return {"kind": "contrast", "groups": {g: _group_sensitivity(r) for g, r in sorted(base.items())}, "controls": dict(controls)}


def _picks(case: Case, result: dict[str, Any]) -> dict[str, tuple[int, int | None, bool]]:
    """party -> (listed position picked, the original citizen at that position, whether it is the last)."""
    picks = {}
    for party, listed in case.labels["listed"].items():
        position = result["answers"].get(party)
        if position is not None:
            picks[party] = (position, listed.get(str(position)), position == len(listed))
    return picks


def score_permutation(cases: Sequence[Case], main: dict[str, dict[str, Any]]) -> dict[str, Any]:
    renderings: dict[str, dict[str, dict[str, tuple[int, int | None, bool]]]] = defaultdict(dict)
    for case in cases:
        if case.case_id in main:
            renderings[case.labels["pair"]][case.labels["rendering"]] = _picks(case, main[case.case_id])
    compared = same_candidate = same_position = last = picks = 0
    for pair in renderings.values():
        for picked in pair.values():
            picks += len(picked)
            last += sum(1 for _, _, is_last in picked.values() if is_last)
        original, renumbered = pair.get("original", {}), pair.get("renumbered", {})
        for party in original.keys() & renumbered.keys():
            compared += 1
            same_candidate += original[party][1] == renumbered[party][1]
            same_position += original[party][0] == renumbered[party][0]
    return {"kind": "permutation", "same_candidate": _rate(same_candidate, compared),
            "same_listed_position": _rate(same_position, compared), "last_listed_position": _rate(last, picks)}


_SCORERS = {"truth": score_truth, "contrast": score_contrast, "permutation": score_permutation}


# ── per decision type ─────────────────────────────────────────────────────

_VALUE_ERROR = re.compile(r"Value error, (?P<message>[^\[\n]+?)\s*\[")


def error_kind(error: str) -> str:
    """A failure's kind: a schema validator's own message (e.g. "blank=1 requires an empty
    ranking") where there is one, otherwise its first line with numbers blanked out."""
    match = _VALUE_ERROR.search(error)
    if match:
        return match["message"]
    return re.sub(r"\d+", "#", error.split("\n", 1)[0])[:120]


def score_validity(cases: Sequence[Case], main: dict[str, dict[str, Any]]) -> dict[str, Any]:
    answered = [main[c.case_id] for c in cases if c.case_id in main]
    errors = Counter(error_kind(r["error"]) for r in answered if not r["valid"] and r["error"])
    return {**_rate(sum(1 for r in answered if r["valid"]), len(answered)), "errors": dict(errors.most_common())}


def _mean(values: Iterable[Any]) -> float | None:
    present = [v for v in values if v is not None]
    return statistics.fmean(present) if present else None


def score_cost(cases: Sequence[Case], main: dict[str, dict[str, Any]]) -> dict[str, Any]:
    calls = [main[c.case_id]["call"] for c in cases if c.case_id in main]
    latency = _mean(call.get("latency_ms") for call in calls)
    return {
        "requests": len(calls),
        "latency_s_mean": latency / 1000 if latency is not None else None,
        "prompt_tokens_mean": _mean(call.get("prompt_tokens") for call in calls),
        "completion_tokens_mean": _mean(call.get("completion_tokens") for call in calls),
        "reasoning_tokens_mean": _mean(call.get("reasoning_tokens") for call in calls),
        "truncated": sum(1 for call in calls if call.get("finish_reason") == "length"),
    }


def _by(cases: Iterable[Case], attribute: str) -> dict[str, list[Case]]:
    grouped: dict[str, list[Case]] = defaultdict(list)
    for case in cases:
        grouped[getattr(case, attribute)].append(case)
    return dict(sorted(grouped.items()))


def score_decision_types(bank: CaseBank, session: Session) -> dict[str, Any]:
    main = session.by_case()
    scored = [c for c in bank.cases if c.family != LOGPROB_GATE_FAMILY and c.case_id in main]
    return {
        decision_type: {
            "validity": score_validity(cases, main),
            "cost": score_cost(cases, main),
            "families": {family: _SCORERS[fam_cases[0].labels["kind"]](fam_cases, main)
                         for family, fam_cases in _by(cases, "family").items()},
        }
        for decision_type, cases in _by(scored, "decision_type").items()
    }


# ── per session ───────────────────────────────────────────────────────────

def _gate_readings(bank: CaseBank, session: Session) -> tuple[int, list[tuple[bool, float]]]:
    """The gate's unit count, and (sincere ballot is blank, P(blank=1)) for each aligned unit."""
    main = session.by_case()
    units = 0
    readings = []
    for case in (c for c in bank.cases if c.family == LOGPROB_GATE_FAMILY):
        probabilities = (main.get(case.case_id) or {}).get("probabilities") or {}
        units += len(case.labels["truth"])
        readings += [(expected == "blank", probabilities[unit]) for unit, expected in case.labels["truth"].items() if unit in probabilities]
    return units, readings


def score_logprob_gate(bank: CaseBank, session: Session) -> dict[str, Any]:
    units, readings = _gate_readings(bank, session)
    p_blank = [p for blank, p in readings if blank]
    p_ranked = [p for blank, p in readings if not blank]
    gate_separation = statistics.fmean(p_blank) - statistics.fmean(p_ranked) if p_blank and p_ranked else None
    return {"units": units, "aligned": len(readings), "threshold_call_correct": sum(1 for blank, p in readings if (p > 0.5) == blank),
            "separation": gate_separation, "passed": len(readings) == units if readings else None}


def score_noise_floor(session: Session) -> dict[str, Any]:
    main = session.by_case()
    reruns = [r for r in session.results if r["pass"] == "rerun" and r["case_id"] in main]
    identical = sum(1 for r in reruns if r["content_sha256"] is not None and r["content_sha256"] == main[r["case_id"]]["content_sha256"])
    agree = total = 0
    for rerun in reruns:
        first = main[rerun["case_id"]]["answers"]
        for unit, answer in first.items():
            total += 1
            agree += rerun["answers"].get(unit) == answer
    return {"reruns": len(reruns), "identical_output": _rate(identical, len(reruns)), "unit_agreement": _rate(agree, total)}


def score_session(bank: CaseBank, session: Session) -> dict[str, Any]:
    return {
        "label": session.label,
        "metadata": session.metadata,
        "bank_matches": session.metadata.get("bank_sha256") == bank.content_sha256,
        "gates": {"think": session.gates.get("think"), "logprobs_available": session.gates.get("logprobs_available"),
                  "logprob": score_logprob_gate(bank, session)},
        "noise_floor": score_noise_floor(session),
        "decision_types": score_decision_types(bank, session),
    }


# ── across sessions ───────────────────────────────────────────────────────

def _paired(vectors: dict[str, dict[Any, bool]]) -> tuple[list[Any], dict[str, list[bool]]]:
    """The keys every session answered, and each session's outcomes on them in one order."""
    common = sorted(set.intersection(*(set(v) for v in vectors.values())), key=str) if vectors else []
    return common, {label: [v[key] for key in common] for label, v in vectors.items()}


def _pairwise(name: str, aligned: dict[str, list[bool]], control: str, n: int) -> dict[str, dict[str, Any]]:
    tests: dict[str, dict[str, Any]] = {}
    if n == 0:
        return tests  # no case every model answered: nothing to pair
    for label, outcomes in aligned.items():
        if label != control:
            result = mcnemar_exact(outcomes, aligned[control])
            tests[f"{name}: {label} vs {control}"] = {"test": "mcnemar_exact", "n": n, "first_only": result.first_only,
                                                     "second_only": result.second_only, "p_value": result.p_value}
    cochran = cochrans_q(list(aligned.values())) if len(aligned) >= 3 else None
    if cochran is not None:
        tests[f"{name}: all models"] = {"test": "cochrans_q", "n": n, "q": cochran.q,
                                        "df": cochran.degrees_of_freedom, "p_value": cochran.p_value}
    return tests


def _accuracy_tests(bank: CaseBank, sessions: Sequence[Session], control: str) -> dict[str, dict[str, Any]]:
    tests: dict[str, dict[str, Any]] = {}
    truth_cases = [c for c in bank.cases if c.labels["kind"] == "truth" and c.family != LOGPROB_GATE_FAMILY]
    for family, cases in _by(truth_cases, "family").items():
        common, aligned = _paired({s.label: truth_outcomes(cases, s.by_case()) for s in sessions})
        tests.update(_pairwise(f"accuracy/{family}", aligned, control, len(common)))
    return tests


def _validity_tests(bank: CaseBank, sessions: Sequence[Session], control: str) -> dict[str, dict[str, Any]]:
    tests: dict[str, dict[str, Any]] = {}
    scored = [c for c in bank.cases if c.family != LOGPROB_GATE_FAMILY]
    for decision_type, cases in _by(scored, "decision_type").items():
        ids = {c.case_id for c in cases}
        common, aligned = _paired({s.label: {cid: r["valid"] for cid, r in s.by_case().items() if cid in ids} for s in sessions})
        tests.update(_pairwise(f"validity/{decision_type}", aligned, control, len(common)))
    return tests


def compare_sessions(bank: CaseBank, sessions: Sequence[Session], control: str) -> dict[str, dict[str, Any]]:
    """Paired tests on the cases every session answered; empty with fewer than two sessions."""
    if len(sessions) < 2:
        return {}
    tests = {**_accuracy_tests(bank, sessions, control), **_validity_tests(bank, sessions, control)}
    adjusted = holm_adjust({name: test["p_value"] for name, test in tests.items()})
    return {name: {**test, "p_holm": adjusted[name]} for name, test in sorted(tests.items())}


# ── acceptance (S2.2, pre-registered in plan-polity-build-order.md) ────────

def _check(name: str, expected: str, observed: Any, passed: bool | None) -> dict[str, Any]:
    return {"check": name, "expected": expected, "observed": observed, "passed": passed}


def acceptance(session_score: dict[str, Any]) -> list[dict[str, Any]]:
    """S2.2's acceptance on the control model: the known Qwen3-8B-AWQ numbers."""
    types = session_score["decision_types"]
    candidacy = types.get("candidacy_considered", {}).get("families", {}).get("candidacy_p500")
    checks = []
    if candidacy is not None:
        declared = candidacy["answers"].get("1", 0)
        accuracy = candidacy["accuracy"]
        checks.append(_check("candidacy declared", "202 of 500", f"{declared} of {accuracy['trials']}", declared == 202 and accuracy["trials"] == 500))
        checks.append(_check("candidacy agreeing with the threshold", "318 of 500", f"{accuracy['successes']} of {accuracy['trials']}",
                             accuracy["successes"] == 318 and accuracy["trials"] == 500))
    coalition = types.get("coalition_decision", {}).get("families", {}).get("coalition_diagonal", {}).get("groups", {}).get("join_to_decline")
    if coalition is not None:
        checks.append(_check("coalition_decision flat", f"|separation| < {FLAT_SEPARATION}", coalition["separation"], coalition["flat"]))
    response = types.get("representative_response", {}).get("families", {}).get("response_sweep", {}).get("groups", {}).get("pressure")
    if response is not None:
        checks.append(_response_check(response))
    return checks


def _response_check(group: dict[str, Any]) -> dict[str, Any]:
    """Track B1's shipped reading: P(CONCESSION) flat wherever there is any pressure
    (t > 0: spread < 0.10), and below one half at the one point with none (t = 0)."""
    p_by_t = group["p_by_t"]
    if not p_by_t or "0.0" not in p_by_t:
        return _check("representative_response flat under pressure, silent without", "spread(t>0) < 0.10 and P(t=0) < 0.5", None, None)
    pressured = [p for t, p in p_by_t.items() if float(t) > 0]
    pressured_spread = spread(pressured)
    passed = pressured_spread is not None and pressured_spread < FLAT_SEPARATION and p_by_t["0.0"] < 0.5
    return _check("representative_response flat under pressure, silent without", "spread(t>0) < 0.10 and P(t=0) < 0.5",
                  {"spread_t_gt_0": pressured_spread, "p_t0": p_by_t["0.0"]}, passed)


def scorecard(bank: CaseBank, sessions: Sequence[Session], *, control: str | None = None) -> dict[str, Any]:
    control_label = control if control is not None else (sessions[0].label if sessions else None)
    scored = [score_session(bank, s) for s in sessions]
    return {
        "bank": {"sha256": bank.content_sha256, "reference": bank.reference, "cases": len(bank.cases), "families": bank.families()},
        "control": control_label,
        "sessions": scored,
        "comparisons": compare_sessions(bank, sessions, control_label) if control_label is not None else {},
        "acceptance": next((acceptance(s) for s in scored if s["label"] == control_label), []),
    }
