"""
scripts/check_vllm_vote_cast_retry_is_inert.py

Why the first real `provider: vllm` run of the polity simulator died 4 minutes
in, and which fix actually works.

## The failure

`plan-flagship-30y-run.md` Phase 0's very first LLM arm (2 years, pop 100, full
richness, `max_batch_replays=2`) crashed in tick 0's presidential election:

    LlmResponseError: batch failed schema validation: 1 validation error for
    VoteCastBatch decisions.0
      Value error, blank=1 requires an empty ranking (§3.6.1 hard rule)

The defect itself is old and documented: `cache_recycle_chunk_size_tension_
findings.md` characterises `blank=1` + non-empty `ranking` as a **deterministic,
per-voter-prompt** model error at temperature=0, and ships a mitigation --
`_VOTE_CAST_RETRY_TEMPERATURE = 0.3`, a deliberate, narrowly-scoped exception to
this project's temperature=0 rule, applied only at `cast_votes`'s call site, so a
retry can *resample past* an answer an identical retry would only reproduce.

**The mitigation does not work on vLLM.** The crashed run's own replay log shows
cid 24 failing attempt 1, being retried at temperature=0.3, and coming back
byte-identical (`blank=1`, `ranking=[4, 5, 1]`), then failing attempt 2 the same
way, until the run died.

## Why -- two independent causes, measured separately rather than conflated

The mitigation's unstated premise is that re-issuing a request resamples. That
premise holds on Ollama and fails on vLLM, for two reasons:

1. **The seed is pinned.** `VllmJsonClient._complete_json` sends
   `"seed": self._seed`, the same value every time, and vLLM honours it strictly:
   same prompt + same seed = same completion at ANY temperature.
2. **0.3 may be too peaked to escape anyway**, even with a varying seed.

Neither alone would necessarily explain the failure, and neither alone is
guaranteed to fix it -- so this script measures the full 2x2 rather than
confirming the first plausible half of the diagnosis. The seed axis is varied by
constructing a separate `VllmJsonClient` per seed (`from_config(..., seed=n)`),
which needs no production change and keeps every request otherwise byte-identical
to what `cast_votes` sends.

The reason this never surfaced on Ollama is recorded in the mitigation's own
document: *"temperature=0 + a pinned seed is not a reproducibility guarantee on
this inference backend"*. Ollama resamples whether asked to or not, so a retry
there varies. vLLM's strict determinism -- the property this project spent a week
verifying, and wants -- is precisely what makes the retry inert.

## What this measures

Against the real production path (`build_system_prompt`/`build_user_prompt`,
`VOTE_CAST_JSON_SCHEMA`, `decode_vote_batch`, the shipped token budget and
chunk-size-1 shape), on the real tick-0 world at the seed the crashed run used:

- **The base rate**: how often `blank`/`ranking` incoherence fires at all under
  vLLM/AWQ. A mitigation that recovers everything still matters differently at 4%
  than at 16%.
- **The 2x2 on the voters that actually fail**: {temperature 0.3, 1.0} x {seed
  pinned, seed varied} -- so the fix is chosen from measurement.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_vote_cast_retry_is_inert.py --voters 25
    python fast_api_voter/scripts/check_vllm_vote_cast_retry_is_inert.py \\
        --voters 25 --results scripts/check_vllm_vote_cast_retry_is_inert_results.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    _VOTE_CAST_RETRY_TEMPERATURE,
    _VOTE_THINK_TOKEN_ALLOWANCE,
    build_system_prompt,
    build_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import (  # noqa: E402
    LlmError,
    VllmJsonClient,
    decode_vote_batch,
)
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation, declare_candidacy  # noqa: E402


def _build_world(config: PolityConfig, population: int) -> tuple[list[Citizen], list[Citizen]]:
    """The crashed run's own tick-0 world: same seed, same population size, same
    party init and nominee rule, so these are the prompts that actually failed."""
    citizens = generate_population(config.citizens, population, config.run.seed)
    parties = initialize_parties(citizens, config.parties.initial_count, config.run.seed)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)
    nominees: list[Citizen] = []
    for party in parties:
        members = [c for c in citizens if c.party_affiliation == party.party_id]
        if members:
            nominees.append(max(members, key=lambda c: (c.ambition_score, -c.citizen_id)))
    for nominee in nominees:
        # build_user_prompt reads pledged_platform, which declare_candidacy pins
        # to the nominee's sincere position -- the same call _run_candidacies
        # makes before the election. Without it the prompt cannot be built at all.
        declare_candidacy(nominee)
    return citizens, sorted(nominees, key=lambda c: c.citizen_id)


def _attempt(
    config: PolityConfig, voter: Citizen, nominees: list[Citizen], *,
    temperature: float | None, seed: int,
) -> tuple[bool, str]:
    """One vote_cast call in production's exact shape. Returns (ok, detail)."""
    chunk = [voter]
    with VllmJsonClient.from_config(config.llm, seed=seed) as client:
        kwargs: dict = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            raw = client.complete_json(
                system_prompt=build_system_prompt(chunk, nominees),
                user_prompt=build_user_prompt(chunk, nominees),
                json_schema=VOTE_CAST_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1) + _VOTE_THINK_TOKEN_ALLOWANCE,
                think=True,
                **kwargs,
            )
        except LlmError as exc:
            return False, f"transport/response: {exc}"
    try:
        decisions = decode_vote_batch(raw, [voter.citizen_id])
    except LlmError as exc:
        return False, str(exc).splitlines()[-1].strip() or str(exc)[:160]
    d = decisions[0]
    return True, f"blank={d.blank} ranking={d.ranking} motif={d.motif}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--voters", type=int, default=25)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args(argv)

    config = load_config()
    base_seed = config.run.seed
    citizens, nominees = _build_world(config, args.population)
    probe = citizens[: args.voters]

    lines: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        lines.append(line)

    log("# vLLM: the `vote_cast` temperature-varied retry is inert — measured\n")
    log(f"`provider={config.llm.provider}`, `model={config.llm.model}`, "
        f"shipped `_VOTE_CAST_RETRY_TEMPERATURE={_VOTE_CAST_RETRY_TEMPERATURE}`, "
        f"seed={base_seed}, {len(nominees)} nominees, chunk size 1.\n")

    log("## Base rate — first attempt, production settings (temperature=0, pinned seed)\n")
    failures: list[Citizen] = []
    for voter in probe:
        ok, detail = _attempt(config, voter, nominees, temperature=None, seed=base_seed)
        if not ok:
            failures.append(voter)
            log(f"- cid {voter.citizen_id}: **FAIL** — {detail}")
    log(f"\n**{len(failures)} of {len(probe)} voters failed on the first attempt "
        f"({len(failures) / len(probe):.1%})**\n")

    if not failures:
        log("No first-attempt failure in this sample — nothing to retry, so the 2x2 below is skipped.")
    else:
        log("## The 2x2, on the voters that actually failed\n")
        log("Each cell: 3 attempts. `recovered` means at least one attempt decoded cleanly;")
        log("`identical` means every attempt returned the same failing answer.\n")
        log("| cid | temp 0.3, pinned seed (**shipped retry**) | temp 0.3, varied seed | temp 1.0, pinned seed | temp 1.0, varied seed |")
        log("|---|---|---|---|---|")
        for voter in failures:
            cells: list[str] = []
            for temperature, vary_seed in ((0.3, False), (0.3, True), (1.0, False), (1.0, True)):
                results = [
                    _attempt(config, voter, nominees, temperature=temperature,
                             seed=base_seed + (i + 1 if vary_seed else 0))
                    for i in range(3)
                ]
                oks = [ok for ok, _ in results]
                details = {detail for _, detail in results}
                if any(oks):
                    cells.append(f"**recovered {sum(oks)}/3**")
                elif len(details) == 1:
                    cells.append("identical 3/3")
                else:
                    cells.append(f"failed, {len(details)} distinct")
            log(f"| {voter.citizen_id} | " + " | ".join(cells) + " |")
        log()

    if args.results is not None:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nwrote {args.results}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
