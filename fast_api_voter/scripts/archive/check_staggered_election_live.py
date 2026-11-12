"""
scripts/check_staggered_election_live.py

Track E (lets-build-a-solid-spicy-otter.md, 2026-09-11): a real-vLLM sanity check
for `institutions.staggered_election`. The fake-client tests in
`test_polity_run_simulation.py` already exercise the actual novel code (the tick-
loop dispatch, the checkpoint round-trip, the recall-interruption self-heal) at
the Python level -- `_consider_candidacies_llm`/`_nominate_and_position_llm` call
the exact same, already-verified `decide_candidacies`/`decide_party_nominations`/
`decide_campaign_positioning` functions the atomic path always has, just from two
new call sites. This script's only job is confirming those calls still succeed
against a REAL model when invoked from those new positions, not re-litigating
prompt quality already covered elsewhere.

Small and cheap on purpose: population 20, president_term_years=1 (against the
shipped ticks_per_year=4) so the SECOND election (tick 4) has a real staggered
window (declare at tick 2, nominate+position at tick 3, vote at tick 4) within an
8-tick run -- no need for the shipped 16-tick term to see one.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_staggered_election_live.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.indexer import read_journal  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402


def main() -> int:
    config = load_config()
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        institutions=dataclasses.replace(config.institutions, staggered_election=True, president_term_years=1),
        run=dataclasses.replace(config.run, population_size=20, duration_years=2),
    )

    journal_path = run_simulation(config, run_id="check-staggered-election-live")
    events = list(read_journal(journal_path))

    def ticks_for(event_type: str) -> set[int]:
        return {e["tick"] for e in events if e["event_type"] == event_type}

    considered = ticks_for("candidacy_considered")
    nominated = ticks_for("party_nomination_choice")
    positioned = ticks_for("campaign_positioning")
    voted = ticks_for("vote_cast")
    elected = [e for e in events if e["event_type"] == "elected"]

    print(f"candidacy_considered ticks: {sorted(considered)}")
    print(f"party_nomination_choice ticks: {sorted(nominated)}")
    print(f"campaign_positioning ticks: {sorted(positioned)}")
    print(f"vote_cast ticks: {sorted(voted)}")
    print(f"elected: {[(e['tick'], e['citizen_id']) for e in elected]}")

    checks = {
        "tick 0 (first election, atomic) declared": 0 in considered,
        "tick 0 nominated": 0 in nominated,
        "tick 0 voted": 0 in voted,
        "tick 2 (second election, staggered) declared": 2 in considered,
        "tick 2 NOT nominated": 2 not in nominated,
        "tick 3 nominated": 3 in nominated,
        "tick 3 positioned": 3 in positioned,
        "tick 3 NOT declared": 3 not in considered,
        "tick 4 voted": 4 in voted,
        "tick 4 NOT declared": 4 not in considered,
        "tick 4 NOT nominated": 4 not in nominated,
    }
    print("\nchecks:")
    all_ok = True
    for name, ok in checks.items():
        print(f"  {'OK' if ok else 'FAIL'}: {name}")
        all_ok = all_ok and ok

    print(f"\n{'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
