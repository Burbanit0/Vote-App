"""
scripts/check_coalition_negotiation_reliability.py

v7 Lot 3's live reliability spike for decide_coalition's new multi-round
negotiation loop (§3.4 Cas 2, plan-coalition-negotiation-v7.md), the
project's standing "spike before you trust it" discipline applied here for
the first time since Lot 2 shipped the round loop itself.

think=False (decide_coalition's own choice, unchanged by v7) means no
chain-of-thought budget is ever requested, so the Mode A/B truncation
history that drove the chamber_deliberation/vote_cast chunking decisions
structurally cannot recur here -- there is no reasoning trace to get stuck
in. The genuinely untested surface is the NEW round >= 2 prompt shape
(prior_decision + provisional_coalition_seats, build_coalition_user_prompt)
against a real model: does it stay schema-valid and motif/action-coherent,
and does the negotiation mechanism (fixed-point / hard-cap stop) behave
correctly end to end.

Four scenarios varying composition (tight/loose majority, fragmentation,
near-parity), plus one ("genuine_shortfall_forces_reconsideration")
deliberately engineered so two small close-platform responders plus the
initiator fall short of majority and two large far-platform responders are
individually decisive -- built to give round 2's shortfall context the
clearest possible chance to flip a decision. Run at max_batch_replays=0
(strict first-attempt measurement, matching every prior spike's own
discipline) and REPS_PER_SCENARIO reps each.

Result (2026-08-29, qwen3:8b, GPU): 30/30 formations completed without a
single LlmResponseError -- real network calls, both round shapes, zero
failures. But every one of the 30 converged in exactly 2 rounds with the
SAME decisions in round 1 and round 2, including the engineered shortfall
scenario, where all four responders joined immediately in round 1 despite
two of them being ideologically far from the initiator. No revision was
observed in any trial. Full writeup:
scripts/coalition_negotiation_v7_lot3_reliability_results.md.

Setup: Ollama container running, qwen3:8b pulled, POLITY_LLM_LIVE=1.
"""
from __future__ import annotations

import dataclasses
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import decide_coalition  # noqa: E402
from api.domain.polity.llm_client import LlmResponseError, OllamaJsonClient  # noqa: E402
from api.domain.polity.parties import Party  # noqa: E402


def _party(pid: int, dims: int) -> Party:
    platform = tuple((pid * 0.083 + i * 0.021) % 1.0 for i in range(dims))
    return Party(party_id=pid, platform=platform)


def _fixture(dims, seats_by_party):
    parties = [_party(pid, dims) for pid, _ in seats_by_party]
    seats = {pid: s for pid, s in seats_by_party}
    votes = {pid: float(s) for pid, s in seats_by_party}
    return parties, seats, votes


SCENARIOS = {
    # (name, seats_by_party) -- varied composition: tight/loose majority,
    # fragmentation, a near-indifferent responder (encourages a genuine
    # round-2 reconsideration rather than an obvious call every time).
    "shipped_5party_tight": [(0, 28), (1, 24), (2, 20), (3, 16), (4, 12)],
    "two_blocs_one_kingmaker": [(0, 38), (1, 34), (2, 28)],
    "fragmented_6party": [(0, 20), (1, 18), (2, 17), (3, 16), (4, 15), (5, 14)],
    "initiator_needs_almost_everyone": [(0, 26), (1, 19), (2, 19), (3, 18), (4, 18)],
    # v1 of this scenario put the intended "far kingmaker" at 40 seats,
    # accidentally making IT the initiator (coalition_initiator: largest_
    # seats) -- it then cleared majority alone with zero network calls,
    # testing nothing. v2 used 4 comparably-sized responders, which the
    # earlier "P0 is largest => P0+closest-one-or-two already clears 50%"
    # algebra defeats generically (verified: P0>Pi for any single
    # responder implies P0+Pi>threshold whenever the OTHER, unused
    # responders' combined seats don't outweigh P0+Pi -- true here with
    # only 4 similarly-sized responders). Fixed for real this time: the
    # two CLOSEST responders (party() distances .37/.74) are made tiny
    # (5 seats each) so even together with the initiator they fall well
    # short (36 < 43); the two FAR responders (distances 1.11/1.48) are
    # made large (25 seats each, still < initiator's 26) so EXACTLY ONE
    # of them is required to cross the threshold. Round 1 should plausibly
    # decline both far responders on proximity grounds alone, leaving
    # round 2 to show them a real, large (7-seat) shortfall -- the
    # strongest test this spike can construct for whether provisional_
    # coalition_seats context can actually flip a decision.
    "genuine_shortfall_forces_reconsideration": [(0, 26), (1, 5), (2, 5), (3, 25), (4, 25)],
}
REPS_PER_SCENARIO = 5
DECISIVE_SCENARIO_REPS = 10


def main():
    cfg = load_config()
    cfg = dataclasses.replace(cfg, llm=dataclasses.replace(cfg.llm, enabled=True, max_batch_replays=0))
    dims = cfg.citizens.issue_count

    with OllamaJsonClient.from_config(cfg.llm, seed=42) as client:
        print(f"warming up {cfg.llm.model}...")
        t0 = time.perf_counter()
        warm_parties, warm_seats, warm_votes = _fixture(dims, [(0, 45), (1, 30), (2, 25)])
        decide_coalition(warm_parties, warm_seats, warm_votes, cfg, client)  # real call, below majority alone
        print(f"  warm ({time.perf_counter()-t0:.1f}s)\n")

        total = 0
        failures = []
        rounds_used_counts: dict[int, int] = {}
        any_revision_seen = False

        for name, seats_by_party in SCENARIOS.items():
            reps = DECISIVE_SCENARIO_REPS if name == "genuine_shortfall_forces_reconsideration" else REPS_PER_SCENARIO
            for rep in range(reps):
                parties, seats, votes = _fixture(dims, seats_by_party)
                total += 1
                t0 = time.perf_counter()
                try:
                    outcome = decide_coalition(parties, seats, votes, cfg, client)
                except LlmResponseError as exc:
                    elapsed = time.perf_counter() - t0
                    print(f"{name:>32} rep{rep} FAIL  {elapsed:>6.1f}s  {exc}")
                    failures.append({"scenario": name, "rep": rep, "error": str(exc)})
                    continue
                elapsed = time.perf_counter() - t0
                n_rounds = len(outcome.rounds)
                rounds_used_counts[n_rounds] = rounds_used_counts.get(n_rounds, 0) + 1

                revised = False
                if n_rounds >= 2:
                    r1 = {d.party_id: d.action for d in outcome.rounds[0]}
                    rlast = {d.party_id: d.action for d in outcome.rounds[-1]}
                    revised = r1 != rlast
                    any_revision_seen = any_revision_seen or revised

                print(
                    f"{name:>32} rep{rep} ok    {elapsed:>6.1f}s  rounds={n_rounds}  "
                    f"aborted={outcome.aborted_at_round}  coalition={outcome.coalition}  revised={revised}"
                )
                if name == "genuine_shortfall_forces_reconsideration":
                    for i, round_decisions in enumerate(outcome.rounds, start=1):
                        actions = {d.party_id: d.action for d in round_decisions}
                        print(f"    round {i}: {actions}")

        print(f"\n{total - len(failures)}/{total} formations completed without an LlmResponseError")
        print(f"rounds_used distribution: {dict(sorted(rounds_used_counts.items()))}")
        print(f"at least one scenario showed a round-1-to-final revision: {any_revision_seen}")
        if failures:
            print("\nFAILURES:")
            for f in failures:
                print(f"  {f['scenario']} rep{f['rep']}: {f['error']}")


if __name__ == "__main__":
    main()
