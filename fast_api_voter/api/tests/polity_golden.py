"""Golden references for the polity simulation: every request the engine sends to
the model, and every event it writes, for two small fixed scenarios.

The byte-identity tests in test_polity_run_simulation.py compare two runs of the
same code, so a change that reorders events, renames a payload key or edits a
prompt still passes them. These references are committed, so that change fails
test_polity_golden.py until it is regenerated on purpose with
`python scripts/gen_polity_golden.py` and explained in the commit.

Checked before relying on this (2026-09-13): the journal is byte-identical across
processes with different PYTHONHASHSEED values, for both engines, so committed
hashes do not depend on the process that produced them.

Not across CPUs, though. Population positions come from BLAS matrix products, whose
kernel OpenBLAS picks per CPU, and a different kernel changes the last bits of those
floats. Journal payloads that carry raw positions then differ in their digits alone
(mandate_pledge_declared on some GitHub runners; chamber_deliberation locally under
OPENBLAS_CORETYPE=Prescott), and the golden test failed on those runners only. Journal
summaries therefore hash each event with every float rounded to FLOAT_SIGNIFICANT_DIGITS
-- far above BLAS last-bit noise, far below any change a real edit would make. Checked:
the manifest is identical under the default, Haswell, Sandybridge and Prescott kernels.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.llm_call_log import decision_type_for_schema, request_sha256
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient

GOLDEN_MANIFEST = Path(__file__).parent / "golden" / "polity_golden.json"

GOLDEN_SEED = 42
GOLDEN_YEARS = 2
GOLDEN_POPULATION = 40  # candidacy chunking refuses batches under 20 citizens
GOLDEN_SEATS = 5
# Poisson scandal rate raised so reaction_to_event is certain to fire in 8 ticks;
# every other decision type fires under the flagship's own overrides.
GOLDEN_SCANDAL_RATE = 0.5

LLM_DECISION_TYPES = (
    "vote_cast",
    "candidacy_considered",
    "party_nomination_choice",
    "campaign_positioning",
    "representative_response",
    "pressure_action",
    "reaction_to_event",
    "chamber_deliberation",
    "coalition_decision",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256(text: str | bytes) -> str:
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


class RecordingClient:
    """Wraps a fake client and hashes every complete_json request in call order,
    labelled by the decision type its JSON schema belongs to."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.requests: list[tuple[str, str]] = []

    def count_prompt_tokens(self, *, system_prompt: str, user_prompt: str, think: bool = True) -> int:
        return int(self._inner.count_prompt_tokens(system_prompt=system_prompt, user_prompt=user_prompt, think=think))

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        think: bool = True,
        temperature: float | None = None,
        seed: int | None = None,
        extra_body: Mapping[str, Any] | None = None,
    ) -> str:
        digest = request_sha256(
            system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema,
            max_tokens=max_tokens, think=think, temperature=temperature, seed=seed, extra_body=extra_body,
        )
        self.requests.append((decision_type_for_schema(json_schema), digest))
        return str(
            self._inner.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=json_schema,
                max_tokens=max_tokens,
                think=think,
                temperature=temperature,
                seed=seed,
            )
        )


def golden_config(output_dir: Path, *, llm: bool) -> PolityConfig:
    """The flagship runner's full-mechanism overrides (run_polity_flagship.py's
    _flagship_config), at a size small enough for the regular test suite."""
    config = load_config()
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(
            config.run, seed=GOLDEN_SEED, duration_years=GOLDEN_YEARS,
            population_size=GOLDEN_POPULATION, run_label="golden",
        ),
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, rupture_path_enabled=True),
        institutions=dataclasses.replace(
            config.institutions, blank_vote_competitive=True, snap_election_on_recall=True,
        ),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        social_graph=dataclasses.replace(config.social_graph, enabled=True),
        events=dataclasses.replace(
            config.events, enabled=True, scandal_enabled=True, economic_shock_enabled=True,
            scandal_rate_per_tick=GOLDEN_SCANDAL_RATE,
        ),
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(
                config.awakening.context_modulation, event_salience=True, neighbors_acting=True,
            ),
        ),
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=GOLDEN_SEATS),
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True,
        ),
        parallel=dataclasses.replace(config.parallel, intra_run_workers=1),
    )
    if llm:
        config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    return config


FLOAT_SIGNIFICANT_DIGITS = 9


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return float(f"{value:.{FLOAT_SIGNIFICANT_DIGITS}g}")
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    return value


def _canonical_event(line: bytes) -> tuple[str, str]:
    """(event_type, the event as canonical JSON with floats rounded) -- see the module
    docstring for why the raw line is not hashed."""
    event = json.loads(line)
    return event["event_type"], _canonical(_round_floats(event))


def _journal_summary(journal_path: Path) -> dict[str, Any]:
    events = [_canonical_event(line) for line in journal_path.read_bytes().splitlines() if line.strip()]
    lines_by_type: dict[str, list[str]] = {}
    for event_type, canonical in events:
        lines_by_type.setdefault(event_type, []).append(canonical)
    return {
        "events_sha256": _sha256("\n".join(canonical for _, canonical in events)),
        "event_count": len(events),
        "by_event_type": {
            event_type: {"count": len(lines), "sha256": _sha256("\n".join(lines))}
            for event_type, lines in sorted(lines_by_type.items())
        },
    }


def _request_summary(requests: list[tuple[str, str]]) -> dict[str, Any]:
    by_type: dict[str, list[str]] = {}
    for decision_type, digest in requests:
        by_type.setdefault(decision_type, []).append(digest)
    return {
        "count": len(requests),
        "sequence_sha256": _sha256("\n".join(digest for _, digest in requests)),
        "by_decision_type": {
            decision_type: {"count": len(digests), "sha256": _sha256("\n".join(digests))}
            for decision_type, digests in sorted(by_type.items())
        },
    }


def compute_manifest(work_dir: Path) -> dict[str, Any]:
    deterministic_journal = run_simulation(golden_config(work_dir / "deterministic", llm=False), run_id="golden")
    client = RecordingClient(_ElectingFakeLlmClient())
    llm_journal = run_simulation(golden_config(work_dir / "fake_llm", llm=True), run_id="golden", llm_client=client)
    return {
        "_generated_by": "scripts/gen_polity_golden.py -- regenerate on purpose, never hand-edit",
        "scenario": {
            "seed": GOLDEN_SEED, "years": GOLDEN_YEARS, "population": GOLDEN_POPULATION,
            "seats": GOLDEN_SEATS, "scandal_rate_per_tick": GOLDEN_SCANDAL_RATE,
        },
        "deterministic": _journal_summary(deterministic_journal),
        "fake_llm": {**_journal_summary(llm_journal), "requests": _request_summary(client.requests)},
    }


def describe_drift(expected: dict[str, Any], actual: dict[str, Any]) -> str:
    """Name what changed -- which scenario, which event types, which decision
    types' requests -- so a failure points at the cause instead of a bare hash."""
    lines: list[str] = []
    for scenario in ("deterministic", "fake_llm"):
        exp, act = expected.get(scenario, {}), actual.get(scenario, {})
        exp_events, act_events = exp.get("by_event_type", {}), act.get("by_event_type", {})
        for event_type in sorted(set(exp_events) | set(act_events)):
            if exp_events.get(event_type) != act_events.get(event_type):
                lines.append(
                    f"  {scenario} journal, {event_type}: "
                    f"{exp_events.get(event_type, {}).get('count', 0)} -> {act_events.get(event_type, {}).get('count', 0)} events"
                    + (" (content changed)" if event_type in exp_events and event_type in act_events else "")
                )
        exp_req = exp.get("requests", {}).get("by_decision_type", {})
        act_req = act.get("requests", {}).get("by_decision_type", {})
        for decision_type in sorted(set(exp_req) | set(act_req)):
            if exp_req.get(decision_type) != act_req.get(decision_type):
                lines.append(
                    f"  {scenario} requests, {decision_type}: "
                    f"{exp_req.get(decision_type, {}).get('count', 0)} -> {act_req.get(decision_type, {}).get('count', 0)} calls"
                    + (" (prompt/schema/params changed)" if decision_type in exp_req and decision_type in act_req else "")
                )
        if (
            not lines
            and exp.get("requests", {}).get("sequence_sha256") != act.get("requests", {}).get("sequence_sha256")
        ):
            lines.append(f"  {scenario} requests: same content per decision type, different call order")
    if expected.get("scenario") != actual.get("scenario"):
        lines.append(f"  scenario parameters: {expected.get('scenario')} -> {actual.get('scenario')}")
    return "\n".join(lines) if lines else "  (manifests differ outside the tracked sections)"
