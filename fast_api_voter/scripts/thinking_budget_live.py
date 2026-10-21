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

def _done(arm_dir: Path) -> set[tuple[int, int]]:
    log = arm_dir / CALL_LOG_FILENAME
    if not log.is_file():
        return set()
    return {(c["unit_ids"][0], c["attempt"]) for c in read_calls(log) if c.get("kind") == "decision" and not c.get("error")}


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
    An answer that does not parse scores every such voter wrong on both."""
    try:
        voters = {v["cid"]: v for v in json.loads(case["user"])["voters"]}
        decisions = {d["cid"]: d for d in json.loads(content or "")["decisions"] if isinstance(d, dict)}
    except (ValueError, KeyError, TypeError):
        decisions = {}
        voters = {v["cid"]: v for v in json.loads(case["user"])["voters"]}
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
    return {(c["unit_ids"][0], c["attempt"]): c for c in read_calls(log) if c.get("kind") == "decision"}


def unit_table(cases: Sequence[Mapping[str, Any]], arm: Mapping[tuple[int, int], Mapping[str, Any]]) -> dict[tuple[int, int, int], tuple[bool, bool]]:
    """(case, repeat, voter) -> (E1, E2) for the vote cases of an arm."""
    table: dict[tuple[int, int, int], tuple[bool, bool]] = {}
    for case in cases:
        if case["decision_type"] != "vote_cast":
            continue
        for repeat in range(REPEATS["vote_cast"]):
            call = arm.get((case["case_id"], repeat))
            if call is None:
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


def report(out: Path) -> int:
    cases = read_cases(out)
    arms = {b: load_arm(out, b) for b in ARMS}
    tables = {b: unit_table(cases, arms[b]) for b in ARMS}
    lines = ["# Thinking budget on live prompts (thinking_budget_live.py report)\n", f"{len(cases)} cases from {', '.join(RUNS)}.\n"]
    lines += ["## Votes: units where the rule says a candidate is acceptable\n",
              "| budget | units | E1 blank | E2 wrong first choice | noise floor (E2, repeat 0 vs 1) | reasoning p50 | at budget | truncated |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    e2: dict[int | None, float] = {}
    reasoning: dict[int | None, float] = {}
    for b in ARMS:
        t = tables[b]
        calls = [arms[b][(c["case_id"], r)] for c in cases if c["decision_type"] == "vote_cast" for r in range(REPEATS["vote_cast"]) if (c["case_id"], r) in arms[b]]
        if not t:
            lines.append(f"| {arm_name(b)} | 0 | - | - | - | - | - | - |")
            continue
        e2[b] = sum(v[1] for v in t.values()) / len(t)
        reasoning[b] = _p50([c.get("reasoning_tokens") or 0 for c in calls])
        floor = noise_floor(cases, arms[b])
        cut = sum(at_budget(c) for c in calls) / len(calls) if calls else 0.0
        trunc = sum(c.get("finish_reason") == "length" for c in calls) / len(calls) if calls else 0.0
        lines.append(f"| {arm_name(b)} | {len(t)} | {sum(v[0] for v in t.values()) / len(t):.1%} | {e2[b]:.1%} | "
                     f"{'-' if floor is None else f'{floor:.1%}'} | {reasoning[b]:.0f} | {cut:.0%} | {trunc:.0%} |")
    lines += ["", "## Against the 2048 arm (exact McNemar on unit pairs; Holm over the six)\n",
              "| arm | outcome | 2048 wrong, arm right | arm wrong, 2048 right | p | Holm |", "|---|---|---:|---:|---:|---|"]
    tests = {(b, name): mcnemar(tables[2048], tables[b], i) for b in (4096, 8192, None) for i, name in enumerate(("E1", "E2")) if tables[b] and tables[2048]}
    rejected = holm({f"{arm_name(b)} {name}": p for (b, name), (_, _, p) in tests.items()})
    for (b, name), (fixed, broken, p) in tests.items():
        lines.append(f"| {arm_name(b)} | {name} | {fixed} | {broken} | {p:.3g} | {'rejected' if f'{arm_name(b)} {name}' in rejected else '-'} |")
    lines += ["", "## Cases that ended under the budget originally (the internal check)\n"]
    under = [c for c in cases if c["decision_type"] == "vote_cast" and not c["original_at_budget"]]
    for b in ARMS:
        t = {k: v for k, v in tables[b].items() if k[0] in {c["case_id"] for c in under}}
        lines.append(f"- {arm_name(b)}: E2 {sum(v[1] for v in t.values()) / len(t):.1%} over {len(t)} units" if t else f"- {arm_name(b)}: no units")
    lines += ["", "## Chamber (descriptive; no rule-truth)\n", "| budget | calls | units | units with a shift | reasoning p50 | at budget | truncated |", "|---|---:|---:|---:|---:|---:|---:|"]
    for b in ARMS:
        calls = [arms[b][(c["case_id"], r)] for c in cases if c["decision_type"] == "chamber_deliberation" for r in range(REPEATS["chamber_deliberation"]) if (c["case_id"], r) in arms[b]]
        parsed = [o for o in (chamber_outcome(c.get("content")) for c in calls) if o]
        units = sum(u for u, _ in parsed)
        lines.append(f"| {arm_name(b)} | {len(calls)} | {units} | {sum(s for _, s in parsed) / units:.1%} | "
                     f"{_p50([c.get('reasoning_tokens') or 0 for c in calls]):.0f} | {sum(at_budget(c) for c in calls) / len(calls):.0%} | "
                     f"{sum(c.get('finish_reason') == 'length' for c in calls) / len(calls):.0%} |" if units and calls else f"| {arm_name(b)} | {len(calls)} | 0 | - | - | - | - |")
    floor_2048 = noise_floor(cases, arms[2048])
    lines += ["", "## Verdict (pre-registered)\n"]
    if floor_2048 is not None and floor_2048 > NOISE_LIMIT:
        lines.append(f"- unresolved: the 2048 arm's own repeats disagree on {floor_2048:.1%} of units (limit {NOISE_LIMIT:.0%})")
    elif None in e2 and 2048 in e2:
        lines.append(f"- {verdict(e2, reasoning)}")
    else:
        lines.append("- not decidable: the 2048 or the 'none' arm has no scored units")
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
