"""
scripts/check_candidacy_calibration.py

Track B3 (lets-build-a-solid-spicy-otter.md, 2026-09-11): live verification of
`build_candidacy_system_prompt_toon_calibrated` against the actual measured problem.
Unlike B1/B2, `candidacy_considered` is NOT a content-blind collapse -- Stage 3 measured
real differentiation (64% accuracy against `simple_rules.decide_candidacy`'s ground
truth) -- the defect is a declared rate far above plausible: 202/500 (40.4%) against
this project's own pre-registered bar of **< 5%** (5 parties x 2-5 serious contenders
~= 2-5% of a p500 population, also roughly what real primary fields look like).

`ambition_score` (`citizens.ambition_dist`, shipped `beta(2,8)`) is sent as a bare
float in [0,1] with no reference at all -- `perceived_support` is already self-scaling
(a `sympathizer_ratio`, a population fraction by construction), so it is not this
fix's target. The calibrated prompt adds exactly one fact: the population's own MEAN
ambition_score, computed once over the same population `support` is computed over
(never per-chunk -- see `build_candidacy_system_prompt_toon_calibrated`'s own
docstring for why this must be a single population-wide number, not a per-chunk one).

Same population shape as the real Stage 3 run this bar came from: `generate_population`
against the SHIPPED config, full population (`decide_candidacies`'s own call site in
run_polity_simulation.py passes the whole `citizens` list unfiltered -- every citizen
in this model already has a party, so there is no party-affiliation subset to filter
to in practice). Same chunking (`llm.max_batch_size=25`), same think=False, same
CANDIDACY_JSON_SCHEMA output -- only the system prompt builder changes between the two
arms, isolating the fix. Sequential, not `run_chunks`-parallel: this is a one-off
measurement, not a production run, and sequential output is easier to watch live.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_candidacy_calibration.py [population_size]
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_candidacy_system_prompt_toon,
    build_candidacy_system_prompt_toon_calibrated,
    build_candidacy_user_prompt_toon,
    chunk_voters,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient, decode_candidacy_batch  # noqa: E402
from api.domain.polity.llm_schemas import CANDIDACY_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import decide_candidacy, sympathizer_ratio  # noqa: E402

_DEFAULT_POPULATION_SIZE = 500  # matches Stage 3's own scale -- the run the 40.4% bar came from


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _run_arm(
    label: str,
    client: VllmJsonClient,
    population: list[Citizen],
    support: dict[int, float],
    chunks: list[list[Citizen]],
    system_prompt_for_chunk,
) -> dict[int, bool]:
    declared: dict[int, bool] = {}
    for i, chunk in enumerate(chunks):
        expected_cids = [c.citizen_id for c in chunk]
        content = client.complete_json(
            system_prompt=system_prompt_for_chunk(chunk),
            user_prompt=build_candidacy_user_prompt_toon(chunk, support),
            json_schema=CANDIDACY_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)),
            think=False,
        )
        decisions = decode_candidacy_batch(content, expected_cids)
        for decision in decisions:
            declared[decision.cid] = bool(decision.outcome)
        chunk_declared = sum(declared[cid] for cid in expected_cids)
        print(f"  [{label}] chunk {i + 1}/{len(chunks)}: {chunk_declared}/{len(chunk)} declared")
    return declared


def main() -> int:
    population_size = int(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_POPULATION_SIZE
    config = _vllm_config()
    population = generate_population(config.citizens, population_size, config.run.seed)
    support = {c.citizen_id: sympathizer_ratio(c, population) for c in population}
    mean_ambition = sum(c.ambition_score for c in population) / len(population)
    truth = {c.citizen_id: decide_candidacy(c, config.candidacy) for c in population}
    chunks = chunk_voters(population, config.llm.max_batch_size)

    print(
        f"candidacy calibration check: {population_size} citizens, {len(chunks)} chunks of "
        f"<={config.llm.max_batch_size}, mean_ambition={mean_ambition:.4f}, "
        f"ambition_threshold={config.candidacy.ambition_threshold} (deterministic-path reference only, "
        f"NOT read by decide_candidacies -- ADR-002), "
        f"{sum(truth.values())} ground-truth declare / {len(truth) - sum(truth.values())} decline"
    )

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        results = {}
        for label, builder in [
            ("baseline", lambda chunk: build_candidacy_system_prompt_toon(chunk)),
            ("calibrated", lambda chunk: build_candidacy_system_prompt_toon_calibrated(chunk, mean_ambition)),
        ]:
            print(f"\n--- {label} ---")
            declared = _run_arm(label, client, population, support, chunks, builder)
            n_declared = sum(declared.values())
            correct = sum(1 for cid, outcome in declared.items() if outcome == truth[cid])
            results[label] = {"n_declared": n_declared, "correct": correct}
            print(
                f"  {label}: declared={n_declared}/{population_size} "
                f"({100 * n_declared / population_size:.1f}%) accuracy={correct}/{population_size} "
                f"({100 * correct / population_size:.1f}%)"
            )

    print("\n=== summary ===")
    for label in ("baseline", "calibrated"):
        n = results[label]["n_declared"]
        print(f"{label}: {n}/{population_size} declared ({100 * n / population_size:.1f}%) -- bar is < 5%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
