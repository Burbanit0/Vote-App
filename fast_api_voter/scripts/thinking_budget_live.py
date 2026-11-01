"""Does the 2,048-token thinking budget cause the 8B's wrong votes? Logged live prompts re-sent under other budgets.

The rule, outcomes, tests and decision were written down before any call: thinking_budget_live_preregistration.md.

    python scripts/thinking_budget_live.py sample --out DIR      # cases.jsonl from the runs' logged calls and prompts
    python scripts/thinking_budget_live.py run --out DIR          # every case under 2048 / 4096 / 8192 / none (the GPU)
    python scripts/thinking_budget_live.py report --out DIR       # the tables and the pre-registered verdict

`run` needs the local vLLM server (the 8B) and nothing else on it. It resumes: a (case, arm, repeat) already in an arm's
call log is not sent again. Each arm's calls land in DIR/arm-<budget>/llm_calls.jsonl, like any run's call log
(`unit_ids` = [case index], `attempt` = the repeat).
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.decision_audit import at_budget, vote_rule  # noqa: E402
from api.domain.polity.llm_call_log import (  # noqa: E402
    CALL_LOG_FILENAME, PROMPT_LOG_FILENAME, CallLoggingClient, CallLogWriter, call_context, read_calls, read_prompts,
)
from api.domain.polity.llm_client import LlmResponseError, build_json_client  # noqa: E402
from api.domain.polity.llm_time_attribution import kept_calls  # noqa: E402
from schema_order_live_report import holm  # noqa: E402

POLITY_RUNS = Path("~/Documents/Dev/polity-runs").expanduser()
RUNS = {
    "baseline": POLITY_RUNS / "rtxpro6000-8b-baseline/baseline-8y-p100-qwen3-8b-w24-seed42/run/baseline-8y-p100-qwen3-8b-w24-seed42",
    "p500-s1": POLITY_RUNS / "full/full-30y-p500-seed1-20260926/run/full-30y-p500-seed1-20260926",
    "p500-s2": POLITY_RUNS / "full/full-30y-p500-seed2-20260926/run/full-30y-p500-seed2-20260926",
    "p500-s42": POLITY_RUNS / "full/full-30y-p500-seed42-20260926/run/full-30y-p500-seed42-20260926",
}
SAMPLE_SEED = 20261021
VOTE_AT, VOTE_UNDER, CHAMBER_AT = 67, 13, 25
ARMS: tuple[int | None, ...] = (2048, 4096, 8192, None)
REPEATS = {"vote_cast": 2, "chamber_deliberation": 3}
WORKERS = 8
NOISE_LIMIT = 0.05
TOLERANCE = 0.02  # E2(b) - E2(none) at most this, in the decision rule
CASES_FILE = "cases.jsonl"


def arm_name(budget: int | None) -> str:
    return "none" if budget is None else str(budget)


# ── sample ────────────────────────────────────────────────────────────────

def _first_attempts(calls: Sequence[Mapping[str, Any]], decision_type: str) -> list[Mapping[str, Any]]:
    return [c for c in calls if c.get("kind") == "decision" and c.get("decision_type") == decision_type and not c.get("attempt")]


def sample_cases(label: str, run: Path, rng: random.Random) -> list[dict[str, Any]]:
    """The run's sampled calls with everything needed to send them again."""
    calls = kept_calls(read_calls(run / CALL_LOG_FILENAME))
    prompts = read_prompts(run / PROMPT_LOG_FILENAME)
    votes, chambers = _first_attempts(calls, "vote_cast"), _first_attempts(calls, "chamber_deliberation")
    if label == "baseline":
        picked = votes
    else:
        cut = [c for c in votes if at_budget(c)]
        free = [c for c in votes if not at_budget(c)]
        picked = rng.sample(cut, min(VOTE_AT, len(cut))) + rng.sample(free, min(VOTE_UNDER, len(free)))
    cut_chamber = [c for c in chambers if at_budget(c)]
    picked += rng.sample(cut_chamber, min(CHAMBER_AT, len(cut_chamber)))
    cases = []
    for call in picked:
        prompt = prompts.get(call["call_id"])
        if prompt is None:
            continue
        cases.append({
            "run": label, "call_id": call["call_id"], "decision_type": call["decision_type"], "units": call.get("unit_ids"),
            "system": prompt["system"], "user": prompt["user"], "schema": prompt["schema"], "max_tokens": call["max_tokens"],
            "think": call["think"], "temperature": call.get("temperature"), "seed": call.get("seed"),
            "original_budget": (call.get("extra_body") or {}).get("thinking_token_budget"),
            "original_reasoning_tokens": call.get("reasoning_tokens"), "original_at_budget": at_budget(call),
        })
    return cases


def sample(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SAMPLE_SEED)
    cases = [dict(case, case_id=i) for i, case in enumerate(c for label, run in RUNS.items() for c in sample_cases(label, run, rng))]
    (out / CASES_FILE).write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for c in cases:
        counts[(c["run"], c["decision_type"], "at" if c["original_at_budget"] else "under")] += 1
    print(f"{len(cases)} cases -> {out / CASES_FILE}")
    for key, n in sorted(counts.items()):
        print("  ", *key, n)
    return 0


def read_cases(out: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (out / CASES_FILE).read_text(encoding="utf-8").splitlines() if line.strip()]


# ── run ───────────────────────────────────────────────────────────────────

def read_log(path: Path) -> list[dict[str, Any]]:
    """The records of a call log; a torn last line (a run killed mid-write) is skipped, not fatal."""
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


def _done(arm_dir: Path) -> set[tuple[int, int]]:
    """(case, repeat) already answered or refused: a call the client rejected (cut by max_tokens, no valid JSON) fails
    the same way again and costs minutes, so a resume does not send it twice."""
    log = arm_dir / CALL_LOG_FILENAME
    if not log.is_file():
        return set()
    return {(c["unit_ids"][0], c["attempt"]) for c in read_log(log) if c.get("kind") == "decision"}


def run_arm(client: Any, cases: Sequence[Mapping[str, Any]], budget: int | None, arm_dir: Path, workers: int = WORKERS) -> None:
    arm_dir.mkdir(parents=True, exist_ok=True)
    done = _done(arm_dir)
    todo = [(c, repeat) for c in cases for repeat in range(REPEATS[c["decision_type"]]) if (c["case_id"], repeat) not in done]
    extra = {"thinking_token_budget": budget} if budget is not None else None
    with CallLogWriter(arm_dir / CALL_LOG_FILENAME) as writer:
        logged = CallLoggingClient(client, writer, tick_source=lambda: None)

        def send(item: tuple[Mapping[str, Any], int]) -> None:
            case, repeat = item
            kwargs: dict[str, Any] = {"system_prompt": case["system"], "user_prompt": case["user"], "json_schema": case["schema"],
                                      "max_tokens": case["max_tokens"], "think": case["think"], "extra_body": extra}
            if case["temperature"] is not None:
                kwargs["temperature"] = case["temperature"]
            if case["seed"] is not None:
                kwargs["seed"] = case["seed"]
            with call_context(kind="decision", decision_type=case["decision_type"], unit_ids=[case["case_id"]], attempt=repeat):
                try:
                    logged.complete_json(**kwargs)
                except LlmResponseError:
                    pass  # logged with its error; the report counts it

        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(send, todo))


def run(out: Path) -> int:
    from bakeoff_cases import reference_config

    config = reference_config()
    client = build_json_client(config.llm, seed=config.run.seed)
    cases = read_cases(out)
    for budget in ARMS:
        print(f"arm {arm_name(budget)}: {sum(REPEATS[c['decision_type']] for c in cases)} calls", flush=True)
        run_arm(client, cases, budget, out / f"arm-{arm_name(budget)}")
    return 0


# ── report ────────────────────────────────────────────────────────────────

def vote_outcomes(case: Mapping[str, Any], content: str | None) -> dict[int, tuple[bool, bool]]:
    """cid -> (E1 blank, E2 wrong first choice) for the voters where the rule says a candidate is acceptable.
    A voter the answer leaves out, or an answer that does not parse, scores wrong on both."""
    voters = {v["cid"]: v for v in json.loads(case["user"])["voters"]}
    decisions: dict[Any, dict[str, Any]] = {}
    try:
        for d in json.loads(content or "")["decisions"]:
            if isinstance(d, dict) and isinstance(d.get("cid"), int):
                decisions[d["cid"]] = d
    except (ValueError, KeyError, TypeError):
        decisions = {}
    out: dict[int, tuple[bool, bool]] = {}
    for cid, voter in voters.items():
        rule_blank, nearest = vote_rule(voter)
        if rule_blank:
            continue
        d = decisions.get(cid)
        blank = d is None or bool(d.get("blank"))
        ranking = [] if d is None else d.get("ranking") or []
        out[cid] = (blank, blank or not ranking or ranking[0] != nearest)
    return out


def chamber_outcome(content: str | None) -> tuple[int, int] | None:
    """(units, units with a non-empty shifts list) of a chamber answer, None when it does not parse."""
    try:
        raw = json.loads(content or "")["decisions"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(raw, list):
        return None
    decisions = [d for d in raw if isinstance(d, dict)]
    return len(decisions), sum(bool(d.get("shifts")) for d in decisions)


def load_arm(out: Path, budget: int | None) -> dict[tuple[int, int], dict[str, Any]]:
    log = out / f"arm-{arm_name(budget)}" / CALL_LOG_FILENAME
    if not log.is_file():
        return {}
    return {(c["unit_ids"][0], c["attempt"]): c for c in read_log(log) if c.get("kind") == "decision"}


def unit_table(
    cases: Sequence[Mapping[str, Any]], arm: Mapping[tuple[int, int], Mapping[str, Any]], *, finished_only: bool = False,
) -> dict[tuple[int, int, int], tuple[bool, bool]]:
    """(case, repeat, voter) -> (E1, E2) for the vote cases of an arm. A call the client rejected (cut by max_tokens,
    no valid JSON) scores every voter wrong unless `finished_only`, which leaves it out. The pre-registration is silent
    on such calls: the first analysis scores them wrong, the sensitivity analysis leaves them out."""
    table: dict[tuple[int, int, int], tuple[bool, bool]] = {}
    for case in cases:
        if case["decision_type"] != "vote_cast":
            continue
        for repeat in range(REPEATS["vote_cast"]):
            call = arm.get((case["case_id"], repeat))
            if call is None or (finished_only and call.get("error")):
                continue
            for cid, outcome in vote_outcomes(case, None if call.get("error") else call.get("content")).items():
                table[(case["case_id"], repeat, cid)] = outcome
    return table


def mcnemar(base: Mapping[Any, tuple[bool, bool]], other: Mapping[Any, tuple[bool, bool]], index: int) -> tuple[int, int, float]:
    """(base wrong & other right, base right & other wrong, exact two-sided p) over the unit pairs both arms have."""
    pairs = [(base[k][index], other[k][index]) for k in base.keys() & other.keys()]
    worse_base = sum(a and not b for a, b in pairs)
    worse_other = sum(b and not a for a, b in pairs)
    discordant = worse_base + worse_other
    p = 1.0 if not discordant else float(stats.binomtest(worse_base, discordant, 0.5).pvalue)
    return worse_base, worse_other, p


def noise_floor(cases: Sequence[Mapping[str, Any]], arm: Mapping[tuple[int, int], Mapping[str, Any]]) -> float | None:
    table = unit_table(cases, arm)
    pairs = [(table[(c, 0, v)][1], table[(c, 1, v)][1]) for (c, r, v) in table if r == 0 and (c, 1, v) in table]
    return sum(a != b for a, b in pairs) / len(pairs) if pairs else None


def verdict(e2: Mapping[int | None, float], reasoning: Mapping[int | None, float]) -> str:
    """The pre-registered decision (thinking_budget_live_preregistration.md)."""
    for budget in (2048, 4096, 8192):
        if budget in e2 and None in e2 and e2[budget] - e2[None] <= TOLERANCE and reasoning[budget] < reasoning[None]:
            if budget == 2048:
                return "keep 2048: the budget is not the cause of the error; it is the model's"
            return f"candidate budget {budget}: the smallest within {TOLERANCE:.0%} of 'none' on E2 at lower reasoning cost"
    return "no tested budget removes the error: it is the model's, or needs more thinking than 'none' allows"


def _p50(values: Sequence[float]) -> float:
    return float(statistics.median(values)) if values else float("nan")


def _vote_calls(cases: Sequence[Mapping[str, Any]], arm: Mapping[tuple[int, int], Mapping[str, Any]], *, finished_only: bool) -> list[Mapping[str, Any]]:
    keys = [(c["case_id"], r) for c in cases if c["decision_type"] == "vote_cast" for r in range(REPEATS["vote_cast"])]
    return [arm[k] for k in keys if k in arm and not (finished_only and arm[k].get("error"))]


def _vote_rows(cases: Sequence[Mapping[str, Any]], arms: Mapping[int | None, Mapping[Any, Mapping[str, Any]]], *, finished_only: bool) -> tuple[list[str], dict[int | None, float], dict[int | None, float]]:
    lines = ["| budget | units | E1 blank | E2 wrong first choice | noise floor (E2, repeat 0 vs 1) | reasoning p50 | at budget | truncated |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    e2: dict[int | None, float] = {}
    reasoning: dict[int | None, float] = {}
    for b in ARMS:
        t = unit_table(cases, arms[b], finished_only=finished_only)
        calls = _vote_calls(cases, arms[b], finished_only=finished_only)
        if not t:
            lines.append(f"| {arm_name(b)} | 0 | - | - | - | - | - | - |")
            continue
        e2[b] = sum(v[1] for v in t.values()) / len(t)
        reasoning[b] = _p50([c["reasoning_tokens"] for c in calls if c.get("reasoning_tokens") is not None])
        floor = noise_floor(cases, arms[b])
        cut = sum(at_budget(c) for c in calls) / len(calls) if calls else 0.0
        trunc = sum(c.get("finish_reason") == "length" for c in calls) / len(calls) if calls else 0.0
        lines.append(f"| {arm_name(b)} | {len(t)} | {sum(v[0] for v in t.values()) / len(t):.1%} | {e2[b]:.1%} | "
                     f"{'-' if floor is None else f'{floor:.1%}'} | {reasoning[b]:.0f} | {cut:.0%} | {trunc:.0%} |")
    return lines, e2, reasoning


def under_budget_check(cases: Sequence[Mapping[str, Any]], arms: Mapping[int | None, Mapping[Any, Mapping[str, Any]]]) -> tuple[list[str], bool | None]:
    """The pre-registered internal check: on the cases that ended under the budget originally, E2 may differ between arms
    by no more than the noise floor; if it does the experiment is void. (lines, passed); passed is None without units."""
    ids = {c["case_id"] for c in cases if c["decision_type"] == "vote_cast" and not c["original_at_budget"]}
    rates: dict[int | None, float] = {}
    floors: list[float] = []
    lines = []
    for b in ARMS:
        t = {k: v for k, v in unit_table(cases, arms[b]).items() if k[0] in ids}
        if t:
            rates[b] = sum(v[1] for v in t.values()) / len(t)
            lines.append(f"- {arm_name(b)}: E2 {rates[b]:.1%} over {len(t)} units")
        else:
            lines.append(f"- {arm_name(b)}: no units")
        floor = noise_floor(cases, arms[b])
        if floor is not None:
            floors.append(floor)
    if len(rates) < 2 or not floors:
        return lines, None
    spread, limit = max(rates.values()) - min(rates.values()), max(floors)
    lines.append(f"- spread across arms {spread:.1%} against the largest arm noise floor {limit:.1%}: "
                 + ("within it" if spread <= limit else "**beyond it: the experiment is void**"))
    return lines, spread <= limit


def _chamber_rows(cases: Sequence[Mapping[str, Any]], arms: Mapping[int | None, Mapping[Any, Mapping[str, Any]]]) -> list[str]:
    """Like for like: only the (case, repeat) calls that finished in every arm, so a budget that cuts calls off is not
    compared on a different, easier set."""
    keys = [(c["case_id"], r) for c in cases if c["decision_type"] == "chamber_deliberation" for r in range(REPEATS["chamber_deliberation"])]
    common = [k for k in keys if all(k in arms[b] and not arms[b][k].get("error") and chamber_outcome(arms[b][k].get("content")) for b in ARMS)]
    lines = [f"{len(common)} of {len(keys)} calls finished in all four arms; the table is on those.\n",
             "| budget | calls | units | units with a shift | reasoning p50 | at budget | failed in this arm (of all) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for b in ARMS:
        calls = [arms[b][k] for k in common]
        parsed = [o for o in (chamber_outcome(c.get("content")) for c in calls) if o]
        units = sum(u for u, _ in parsed)
        failed = sum(bool(arms[b][k].get("error")) for k in keys if k in arms[b])
        lines.append(f"| {arm_name(b)} | {len(calls)} | {units} | {sum(x for _, x in parsed) / units:.1%} | "
                     f"{_p50([c.get('reasoning_tokens') or 0 for c in calls]):.0f} | {sum(at_budget(c) for c in calls) / len(calls):.0%} | {failed} of {len(keys)} |"
                     if units and calls else f"| {arm_name(b)} | {len(calls)} | 0 | - | - | - | {failed} of {len(keys)} |")
    return lines


def report(out: Path) -> int:
    cases = read_cases(out)
    arms = {b: load_arm(out, b) for b in ARMS}
    tables = {b: unit_table(cases, arms[b]) for b in ARMS}
    lines = ["# Thinking budget on live prompts (thinking_budget_live.py report)\n", f"{len(cases)} cases from {', '.join(RUNS)}.\n"]
    rows, e2, reasoning = _vote_rows(cases, arms, finished_only=False)
    lines += ["## Votes: units where the rule says a candidate is acceptable (a rejected call scores every voter wrong)\n", *rows]
    lines += ["", "## Against the 2048 arm (exact McNemar on unit pairs; Holm over the six)\n",
              "| arm | outcome | 2048 wrong, arm right | arm wrong, 2048 right | p | Holm |", "|---|---|---:|---:|---:|---|"]
    tests = {(b, name): mcnemar(tables[2048], tables[b], i) for b in (4096, 8192, None) for i, name in enumerate(("E1", "E2")) if tables[b] and tables[2048]}
    rejected = holm({f"{arm_name(b)} {name}": p for (b, name), (_, _, p) in tests.items()})
    for (b, name), (fixed, broken, p) in tests.items():
        lines.append(f"| {arm_name(b)} | {name} | {fixed} | {broken} | {p:.3g} | {'rejected' if f'{arm_name(b)} {name}' in rejected else '-'} |")
    sens_rows, sens_e2, sens_reasoning = _vote_rows(cases, arms, finished_only=True)
    lines += ["", "## Sensitivity: calls the client rejected left out (the pre-registration is silent on them)\n", *sens_rows]
    lines += ["", "## Cases that ended under the budget originally (the internal check)\n"]
    check_lines, passed = under_budget_check(cases, arms)
    lines += check_lines
    lines += ["", "## Chamber (descriptive; no rule-truth)\n", *_chamber_rows(cases, arms)]
    floor_2048 = noise_floor(cases, arms[2048])
    lines += ["", "## Verdict (pre-registered)\n"]
    if passed is False:
        lines.append("- void: the cases that ended under the budget originally differ between arms by more than the noise floor")
    elif floor_2048 is not None and floor_2048 > NOISE_LIMIT:
        lines.append(f"- unresolved: the 2048 arm's own repeats disagree on {floor_2048:.1%} of units (limit {NOISE_LIMIT:.0%})")
    elif None in e2 and 2048 in e2:
        lines.append(f"- {verdict(e2, reasoning)}")
    else:
        lines.append("- not decidable: the 2048 or the 'none' arm has no scored units")
    if None in e2 and 2048 in e2 and None in sens_e2:
        lines += ["", "What the decision rule gives when it is applied anyway, to show how much rests on the noise guard (not a verdict):",
                  f"- all calls, rejected ones scored wrong: {verdict(e2, reasoning)}",
                  f"- rejected calls left out: {verdict(sens_e2, sens_reasoning)}"]
    text = "\n".join(lines) + "\n"
    (out / "report.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("sample", "run", "report"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    return {"sample": sample, "run": run, "report": report}[args.command](args.out)


if __name__ == "__main__":
    raise SystemExit(main())
