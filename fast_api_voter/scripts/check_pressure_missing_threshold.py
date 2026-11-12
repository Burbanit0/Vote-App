"""
scripts/check_pressure_missing_threshold.py

Tests a plainer explanation for pressure_action's collapse than anything
§2 or §3.A considered: **the discriminating information may simply not be
in the prompt.**

The observation that prompted this. `simple_rules.deterministic_pressure_
action` decides by comparing `gap < citizen.blank_threshold`. But
`PressureContext.to_payload()` sends only {self_gap, mandate_dev,
neighbors_acting, ticks_to_election} -- **`blank_threshold` is never sent**.
The model is asked to judge "is this citizen discontented enough to act"
while never being told what "enough" is for that citizen: a raw self_gap
number with no per-citizen scale reference.

Contrast with `vote_cast`, the one decision type this project rates
reliable (23/24 against real ground truth). Its prompt supplies all three
ingredients: the quantity (`distances`, pre-computed so the model needn't
derive it), the per-voter threshold (`blank_threshold`), AND the rule,
stated explicitly -- "Un candidat est ACCEPTABLE si et seulement si sa
distance est INFERIEURE OU EGALE au 'blank_threshold' de l'electeur."

If that difference is what separates them, then pressure_action's collapse
is not a model pathology at all: it is a well-posed question being asked
without the information needed to answer it, and a constant answer is
close to the only reasonable response.

Three arms, same 17-citizen geometry as every prior measurement, one call
each, everything else held identical:

  A  baseline   -- exactly the production prompts, unmodified.
  B  +threshold -- production plus each citizen's own blank_threshold in
                   its ctx. Data only, no instruction added.
  C  +rule      -- B plus one sentence stating the comparison rule, phrased
                   as closely to vote_cast's own as the domain allows.

A/B isolates whether the missing DATA is the problem; B/C isolates whether
the missing INSTRUCTION is. The decisive statistic is not correlation --
check_per_citizen_sampling_premise_results.md showed correlation can be
real while the distribution stays pinned -- but whether P(act=4) develops
genuine SPREAD: mean p(1-p), and how many decisions actually change.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_missing_threshold.py
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import PRESSURE_ACT_PROMPT_TABLE, PRESSURE_MOTIF_PROMPT_TABLE, PressureAct  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    binary_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import deterministic_pressure_action  # noqa: E402

_TARGET_CID = 999
_BLANK_THRESHOLD = 0.5
_MANDATE_DEV = 0.1
_TICKS_TO_ELECTION = 10
_SELF_GAPS = [
    0.02, 0.05, 0.08, 0.10, 0.15, 0.18,
    0.42, 0.47,
    0.53, 0.58,
    0.60, 0.80, 1.00, 1.30, 1.60, 1.90, 2.20,
]


def _vllm_config():
    shipped = load_config()
    model = os.environ.get("POLITY_PROBE_MODEL", shipped.llm.model)
    return dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1", model=model),
    )


def _probe_citizen(cid: int, self_gap: float) -> tuple[Citizen, PressureContext]:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=_BLANK_THRESHOLD,
        ambition_score=0.5,
    )
    context = PressureContext(
        cid=cid, target=_TARGET_CID, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
        ticks_to_election=_TICKS_TO_ELECTION, available=(0, 4),
        petition_open=False, petition_expires_at_tick=None, already_signed=False, neighbors_acting=None,
    )
    return citizen, context


def _user_prompt_with_threshold(consulted, contexts) -> str:
    """build_pressure_user_prompt's own payload, with each citizen's
    `blank_threshold` added to its ctx and nothing else changed -- same
    key order discipline (sort_keys) and same rounding."""
    blocks = []
    for citizen in consulted:
        ctx = contexts[citizen.citizen_id]
        payload = ctx.to_payload()
        payload["blank_threshold"] = round(citizen.blank_threshold, 4)
        blocks.append({
            "cid": citizen.citizen_id,
            "target": ctx.target,
            "ctx": payload,
            "available": list(ctx.available),
            "petition": {
                "open": ctx.petition_open,
                "expires_at_tick": ctx.petition_expires_at_tick,
                "already_signed": ctx.already_signed,
            },
        })
    return json.dumps({"consulted": blocks}, sort_keys=True, separators=(",", ":"))


def _system_prompt_with_rule(consulted, config) -> str:
    """build_pressure_system_prompt's own text with ONE sentence added,
    stating the comparison rule -- deliberately phrased as closely to
    build_system_prompt's own vote_cast wording as this domain allows, so
    that what is being tested is the presence of a stated rule and not a
    new tone or a new strategy hint."""
    base = build_pressure_system_prompt(consulted, config)
    rule = (
        "ctx.blank_threshold : le seuil d'acceptabilite PROPRE a ce citoyen, "
        "sur la meme echelle que ctx.self_gap. Ce citoyen juge la situation "
        "INACCEPTABLE si et seulement si son self_gap est STRICTEMENT "
        "SUPERIEUR a son propre blank_threshold ; en dessous ou egal, il la "
        "juge acceptable.\n"
    )
    marker = "IMPORTANT : la liste decisions"
    return base.replace(marker, rule + marker, 1)


def _system_prompt_with_act_mapping(consulted, config) -> str:
    """Arm D -- a CAPABILITY CONTROL, deliberately not a proposal. Arm C
    states a rule from self_gap to *acceptability* but never bridges
    acceptability to the *act* choice, so a model could apply it perfectly
    and still pick either act. This arm closes that gap by stating the
    mapping outright, which is simply `deterministic_pressure_action`'s own
    rule written into the prompt.

    Shipping this would make the LLM a slow reimplementation of a two-line
    deterministic function and defeat the point of asking a model at all.
    Its only purpose here is to separate CANNOT from WAS-NEVER-TOLD: if
    proxy-agreement goes to 17/17, the model can execute the comparison and
    the problem is that no criterion was ever specified; if it does not,
    something deeper is wrong."""
    base = build_pressure_system_prompt(consulted, config)
    rule = (
        "ctx.blank_threshold : le seuil d'acceptabilite PROPRE a ce citoyen, "
        "sur la meme echelle que ctx.self_gap. REGLE : si self_gap est "
        "STRICTEMENT SUPERIEUR a blank_threshold, ce citoyen agit et tu "
        "reponds act=4 (attendre la prochaine election) ; si self_gap est "
        "INFERIEUR OU EGAL a blank_threshold, ce citoyen est satisfait et tu "
        "reponds act=0 (ne rien faire).\n"
    )
    marker = "IMPORTANT : la liste decisions"
    return base.replace(marker, rule + marker, 1)


def _stats(rows):
    ps = [p for _g, p in rows]
    gaps = [g for g, _p in rows]
    n = len(ps)
    below = [p for g, p in rows if g < _BLANK_THRESHOLD]
    above = [p for g, p in rows if g >= _BLANK_THRESHOLD]
    sep = sum(above) / len(above) - sum(below) / len(below)
    mv = sum(p * (1 - p) for p in ps) / n
    flips = sum(min(p, 1 - p) for p in ps)
    mg, mp = sum(gaps) / n, sum(ps) / n
    cov = sum((g - mg) * (p - mp) for g, p in zip(gaps, ps))
    vg = sum((g - mg) ** 2 for g in gaps)
    vp = sum((p - mp) ** 2 for p in ps)
    r = cov / math.sqrt(vg * vp) if vg > 0 and vp > 0 else 0.0
    return sep, r, mv, flips, mp


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)
    assert PRESSURE_ACT_PROMPT_TABLE and PRESSURE_MOTIF_PROMPT_TABLE  # imported for provenance

    citizens, contexts, proxy = [], {}, {}
    for i, gap in enumerate(_SELF_GAPS):
        cid = 4000 + i
        citizen, context = _probe_citizen(cid, gap)
        citizens.append(citizen)
        contexts[cid] = context
        proxy[cid] = int(deterministic_pressure_action(citizen, gap, config.pressure_menu))
    proxy_wait = sum(1 for v in proxy.values() if v == int(PressureAct.WAIT_FOR_ELECTION))

    arms = {
        "A baseline": (build_pressure_system_prompt(citizens, config),
                       build_pressure_user_prompt(citizens, contexts)),
        "B +threshold": (build_pressure_system_prompt(citizens, config),
                         _user_prompt_with_threshold(citizens, contexts)),
        "C +rule": (_system_prompt_with_rule(citizens, config),
                    _user_prompt_with_threshold(citizens, contexts)),
        "D +act mapping (capability control)": (
            _system_prompt_with_act_mapping(citizens, config),
            _user_prompt_with_threshold(citizens, contexts)),
    }

    print(f"missing-threshold test: model={config.llm.model} n={len(citizens)} "
          f"blank_threshold={_BLANK_THRESHOLD} (fixed) — proxy says act=4 for {proxy_wait}/{len(citizens)}")

    wait, nothing_ = int(PressureAct.WAIT_FOR_ELECTION), int(PressureAct.NOTHING)
    results = {}
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for label, (sys_p, usr_p) in arms.items():
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=sys_p, user_prompt=usr_p,
                json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(len(citizens)),
                think=False, top_logprobs=10,
            )
            try:
                probes = locate_decision_field_logprobs(content, tokens, field="act")
            except LogprobAlignmentError as exc:
                print(f"  {label}: ALIGNMENT FAILED: {exc}")
                continue
            rows = sorted((contexts[pr.cid].self_gap,
                           binary_probability(pr.token, true_value=str(wait), false_value=str(nothing_)))
                          for pr in probes)
            agree = sum(1 for g, p in rows
                        if ((wait if p > 0.5 else nothing_) == (wait if g >= _BLANK_THRESHOLD else nothing_)))
            results[label] = (rows, _stats(rows), agree)

    for label, (rows, (sep, r, mv, flips, mp), agree) in results.items():
        print(f"\n=== {label} ===")
        print("  " + "  ".join(f"{g:.2f}:{p:.3f}" for g, p in rows))
        print(f"  mean P={mp:.4f}  separation={sep:+.4f}  r={r:+.4f}  "
              f"mean p(1-p)={mv:.5f}  E[flips]/{len(rows)}={flips:.2f}  proxy-agreement={agree}/{len(rows)}")

    # ── Solo control on arm D ─────────────────────────────────────────
    # Arm D failing at batch size 17 has two very different explanations:
    # the model cannot apply the stated rule at all, or it does not read
    # per-citizen fields when many records share one call. Asking about ONE
    # citizen, with the same arm-D prompt, discriminates them.
    print("\n=== D solo control (arm D's prompt, one citizen per call) ===")
    solo = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for gap in (_SELF_GAPS[0], _SELF_GAPS[-1]):
            citizen, context = _probe_citizen(4100 + int(gap * 100), gap)
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=_system_prompt_with_act_mapping([citizen], config),
                user_prompt=_user_prompt_with_threshold([citizen], {citizen.citizen_id: context}),
                json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(1),
                think=False, top_logprobs=10,
            )
            try:
                pr = locate_decision_field_logprobs(content, tokens, field="act")[0]
            except LogprobAlignmentError as exc:
                print(f"  self_gap={gap}: ALIGNMENT FAILED: {exc}")
                continue
            p_wait = binary_probability(pr.token, true_value=str(wait), false_value=str(nothing_))
            expected = wait if gap >= _BLANK_THRESHOLD else nothing_
            got = wait if p_wait > 0.5 else nothing_
            solo.append((gap, p_wait, got, expected))
            print(f"  self_gap={gap:.2f}  threshold={_BLANK_THRESHOLD}  P(act=4)={p_wait:.6f}  "
                  f"chose={got}  rule says={expected}  {'OK' if got == expected else 'VIOLATES THE STATED RULE'}")
    if len(solo) == 2:
        print(f"  solo separation = {solo[1][1] - solo[0][1]:+.6f}")

    print("\nWhat to read: separation/r say whether P tracks self_gap at all; mean p(1-p) and "
          "E[flips] say whether it does so with enough magnitude to change any decision; "
          "proxy-agreement says whether the threshold-calls actually land where the "
          "deterministic rule says they should.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
