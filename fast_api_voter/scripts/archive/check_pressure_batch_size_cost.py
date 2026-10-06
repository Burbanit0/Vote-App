"""
scripts/check_pressure_batch_size_cost.py

Phase D of the approved plan (docs/polity-decision-contracts.md): the
real wall-clock cost of pressure_action's candidate batch sizes, measured
rather than modelled -- the number this whole investigation has been
building toward. Phase C found calibration works, cleanly, at batch size
1, and fails at every larger size tested. Whether that is shippable
depends entirely on what batch size 1 actually costs.

Two arms per size, both using the CALIBRATED builders (Phase B) with
PRESSURE_THRESHOLD_SIGNAL -- the cheapest of the four variants Phase C
validated, and the one this measures a real shipping candidate against,
not a strawman:

  - "fixed"  -- the real, current build_pressure_*_prompt_calibrated
    (§3.B.7 already applied, previous commit in this investigation).
  - "legacy" -- a local reconstruction of what those same functions
    looked like BEFORE that fix: the per-chunk cid list embedded in the
    system prompt. Kept ONLY in this file, as a controlled comparison
    artifact -- never a live code path, and the reason it can be
    reconstructed exactly is that it is simply the diff this
    investigation's own git history already shows.

This isolates specifically what the prefix-cache fix bought, at exactly
the batch size (1) where an unfixed system prompt differing on every
single call would hurt most.

Measures, per (size, arm): real wall-clock for the full population burst,
real prompt token count (via count_prompt_tokens, no estimation), and
vLLM's own prefix-cache hit-rate log line, read directly.

Extrapolation uses two real anchors, not a guess: this project's own
Phase 7 scale-probe measured 137 real pressure_action decisions in one
real tick (plan-flagship-30y-run.md), and polity_config.yaml's own
ticks_per_year=4 x duration_years=30 = 120 ticks for the shipped flagship
shape. The ~35.6h sequential baseline is that same plan's own vLLM-based
projection for the full run at every decision type combined, not
pressure_action alone -- the extrapolation below only says what batch
size 1 would ADD or REMOVE relative to the shipped batch size 25, not a
new total run estimate.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_batch_size_cost.py
"""
from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import PRESSURE_ACT_PROMPT_TABLE, PRESSURE_MOTIF_PROMPT_TABLE  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PRESSURE_THRESHOLD_SIGNAL,
    PressureContext,
    build_pressure_system_prompt_calibrated,
    build_pressure_user_prompt_calibrated,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_TARGET_CID = 999
_TICKS_TO_ELECTION = 10
_MANDATE_DEV = 0.1
_POPULATION = 25  # the shipped llm.max_batch_size -- the realistic per-tick cohort this compares against
_SIZES = [25, 5, 3, 1]

# Real anchors, not guesses -- see this module's own docstring.
_REAL_PRESSURE_DECISIONS_PER_TICK = 137
_CALLS_PER_TICK_AT_SHIPPED_BATCH = -(-_REAL_PRESSURE_DECISIONS_PER_TICK // 25)  # ceil division, batch=25
_TOTAL_TICKS = 120


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _probe_citizen(cid: int, self_gap: float) -> tuple[Citizen, PressureContext]:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
    )
    context = PressureContext(
        cid=cid, target=_TARGET_CID, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
        ticks_to_election=_TICKS_TO_ELECTION, available=(0, 4),
        petition_open=False, petition_expires_at_tick=None, already_signed=False, neighbors_acting=None,
    )
    return citizen, context


def _legacy_system_prompt_calibrated(consulted, config, signals) -> str:
    """build_pressure_system_prompt_calibrated's OWN body exactly as
    written before this investigation's §3.B.7 fix -- the per-chunk cid
    list embedded near the end, instead of a reference to expected_cids.
    Reconstructed here only as a controlled comparison artifact for this
    cost measurement; not a live code path."""
    cid_list = ",".join(str(c.citizen_id) for c in consulted)
    legal = menu_acts(config.pressure_menu)
    legal_table = "\n".join(
        line for line in PRESSURE_ACT_PROMPT_TABLE.splitlines() if int(line.split(" = ")[0]) in legal
    )
    neighbors_acting_line = (
        "ctx.neighbors_acting : toujours null dans cette simulation (aucun "
        "graphe social suivi), jamais zero -- null signifie que cette "
        "information n'existe pas du tout ici, PAS que les voisins sont "
        "inactifs ou absents. Ne rien en deduire sur le voisinage : ignorer "
        "ce champ dans le raisonnement, ne jamais l'interpreter comme un "
        "signal.\n"
    )
    signal_lines = "".join(signal.definition for signal in signals)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen mecontent recu "
        "(pressure_action), decide son action envers l'elu cible, en te "
        "basant sur son propre ecart de mecontentement (ctx) et le menu "
        "constitutionnel actif.\n"
        f"CONTRAINTE ABSOLUE : le champ act de CHAQUE decision doit valoir "
        f"UN DES CODES SUIVANTS, et aucun autre : {list(legal)}. Tout autre "
        "code invalide le batch entier.\n"
        f"act (les seuls codes autorises ce tick) :\n{legal_table}\n"
        "0 (ne rien faire) et 4 (attendre la prochaine election) sont des "
        "resultats legitimes et journalises, jamais des echecs -- la part "
        "des mecontents qui n'agissent pas est une mesure du modele, pas "
        "une erreur a eviter.\n"
        f"Motifs valides (code court obligatoire) :\n{PRESSURE_MOTIF_PROMPT_TABLE}\n"
        "ctx.self_gap : ecart pondere entre mes propres positions et la "
        "position actuelle de l'elu cible.\n"
        "ctx.mandate_dev : ecart pondere entre la promesse de l'elu et sa "
        "position actuelle -- une information sur l'elu, pas sur moi.\n"
        f"{neighbors_acting_line}"
        "ctx.ticks_to_election : nombre de ticks avant la prochaine "
        "election presidentielle, null si aucune election prevue.\n"
        f"{signal_lines}"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(consulted)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois, et chaque "
        f"act doit appartenir a {list(legal)}.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def _legacy_user_prompt_calibrated(consulted, contexts, signal_values) -> str:
    """build_pressure_user_prompt_calibrated's own body before §3.B.7 --
    same as the current one, minus the `expected_cids` field."""
    citizen_blocks = []
    for citizen in consulted:
        context = contexts[citizen.citizen_id]
        payload = context.to_payload()
        for field, values in signal_values.items():
            payload[field] = round(values[citizen.citizen_id], 4)
        citizen_blocks.append({
            "cid": citizen.citizen_id, "target": context.target, "ctx": payload,
            "available": list(context.available),
            "petition": {"open": context.petition_open, "expires_at_tick": context.petition_expires_at_tick,
                         "already_signed": context.already_signed},
        })
    return json.dumps({"consulted": citizen_blocks}, sort_keys=True, separators=(",", ":"))


def _chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _read_hit_rate() -> str:
    logs = subprocess.run(
        ["docker", "logs", "vllm-polity", "--since", "20s"], capture_output=True, text=True, check=False,
    ).stdout
    lines = [line for line in logs.splitlines() if "Prefix cache hit rate" in line]
    if not lines:
        return "n/a"
    return lines[-1].split("hit rate: ")[-1].strip()


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)

    citizens, contexts = [], {}
    for i in range(_POPULATION):
        gap = 0.05 + i * (2.2 / _POPULATION)
        cid = 6000 + i
        c, ctx = _probe_citizen(cid, gap)
        citizens.append(c)
        contexts[cid] = ctx
    signals = [PRESSURE_THRESHOLD_SIGNAL]
    signal_values = {"blank_threshold": {c.citizen_id: c.blank_threshold for c in citizens}}

    print(f"pressure_action batch-size cost: population={_POPULATION}, sizes={_SIZES}, "
          f"model={config.llm.model}")
    print(f"real anchor: {_REAL_PRESSURE_DECISIONS_PER_TICK} pressure_action decisions measured "
          f"in one real tick (Phase 7 scale-probe) -> {_CALLS_PER_TICK_AT_SHIPPED_BATCH} calls/tick "
          f"at the shipped batch=25, x {_TOTAL_TICKS} ticks for the full 30y run")

    results: dict[tuple[int, str], dict] = {}
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for size in _SIZES:
            chunks = _chunks(citizens, size)
            for arm in ("legacy", "fixed"):
                start = time.perf_counter()
                total_prompt_tokens = 0
                for chunk in chunks:
                    chunk_contexts = {c.citizen_id: contexts[c.citizen_id] for c in chunk}
                    if arm == "fixed":
                        system_prompt = build_pressure_system_prompt_calibrated(chunk, config, signals)
                        user_prompt = build_pressure_user_prompt_calibrated(chunk, chunk_contexts, signal_values)
                    else:
                        system_prompt = _legacy_system_prompt_calibrated(chunk, config, signals)
                        user_prompt = _legacy_user_prompt_calibrated(chunk, chunk_contexts, signal_values)
                    total_prompt_tokens += client.count_prompt_tokens(
                        system_prompt=system_prompt, user_prompt=user_prompt, think=False,
                    )
                    client.complete_json(
                        system_prompt=system_prompt, user_prompt=user_prompt,
                        json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(len(chunk)), think=False,
                    )
                elapsed = time.perf_counter() - start
                hit_rate = _read_hit_rate()
                results[(size, arm)] = {
                    "elapsed": elapsed, "n_calls": len(chunks),
                    "mean_prompt_tokens": total_prompt_tokens / len(chunks), "hit_rate": hit_rate,
                }
                print(f"  size={size:>2} arm={arm:>6}: {len(chunks):>2} calls, "
                      f"{elapsed:>6.2f}s total, {elapsed/len(chunks)*1000:>6.1f}ms/call, "
                      f"mean_prompt_tokens={total_prompt_tokens/len(chunks):>6.1f}, "
                      f"hit_rate={hit_rate}")

    print("\n== cost of batch size 1 relative to the shipped batch size 25, per arm ==")
    for arm in ("legacy", "fixed"):
        base = results[(25, arm)]["elapsed"]
        one = results[(1, arm)]["elapsed"]
        if base > 0:
            print(f"  {arm:>6}: batch=25 took {base:.2f}s, batch=1 took {one:.2f}s -> {one / base:.1f}x")
        else:
            print(f"  {arm:>6}: batch=25 elapsed was 0, cannot ratio")

    fixed_1 = results[(1, "fixed")]["elapsed"]
    legacy_1 = results[(1, "legacy")]["elapsed"]
    if legacy_1 > 0:
        print(f"\nthe §3.B.7 fix's own contribution AT BATCH SIZE 1: "
              f"legacy {legacy_1:.2f}s vs fixed {fixed_1:.2f}s ({fixed_1 / legacy_1:.1%} of legacy's time)")

    # Extrapolation: real calls/tick at each batch size (from the real
    # 137-decision/tick anchor, not this script's own 25-citizen burst
    # size) x this script's own measured per-call cost at that batch size
    # (per-call cost depends on batch size, not on total population, so
    # it transfers even though the call COUNT does not).
    real_calls_at_batch1 = _REAL_PRESSURE_DECISIONS_PER_TICK
    real_calls_at_batch25 = _CALLS_PER_TICK_AT_SHIPPED_BATCH
    per_call_batch1 = results[(1, "fixed")]["elapsed"] / results[(1, "fixed")]["n_calls"]
    per_call_batch25 = results[(25, "fixed")]["elapsed"] / results[(25, "fixed")]["n_calls"]
    time_per_tick_batch1 = real_calls_at_batch1 * per_call_batch1
    time_per_tick_batch25 = real_calls_at_batch25 * per_call_batch25
    extra_seconds_per_tick = time_per_tick_batch1 - time_per_tick_batch25

    print(f"\nextrapolation for the full 30y/pop500/seats75 shape ({_TOTAL_TICKS} ticks), using the "
          f"fixed arm's own measured per-call cost and the real "
          f"{_REAL_PRESSURE_DECISIONS_PER_TICK}-decision/tick anchor:")
    print(f"  batch=25 (shipped): {real_calls_at_batch25} calls/tick x {per_call_batch25*1000:.1f}ms/call "
          f"= {time_per_tick_batch25:.2f}s/tick")
    print(f"  batch=1 (calibrated): {real_calls_at_batch1} calls/tick x {per_call_batch1*1000:.1f}ms/call "
          f"= {time_per_tick_batch1:.2f}s/tick")
    print(f"  difference: {extra_seconds_per_tick:+.2f}s/tick, "
          f"{extra_seconds_per_tick * _TOTAL_TICKS / 3600:+.2f}h over the full run "
          f"(against the ~35.6h whole-run baseline, all decision types combined)")
    print("\nThis is a linear extrapolation from one real per-tick anchor and this script's own "
          "measured per-call cost, not a second full measured run -- report it as that, not as a "
          "re-measured flagship total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
