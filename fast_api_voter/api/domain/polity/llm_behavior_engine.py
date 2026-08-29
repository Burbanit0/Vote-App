"""
api.domain.polity.llm_behavior_engine — v2 increments 1-5: the LLM
replacement for build_ranking (voting), decide_candidacy (dominant-path
candidacy eligibility only), select_party_nominee_from_declared's tiebreak
when a party is contested (2+ declared candidates), declare_candidacy's
sincere-platform pin for dominant nominees (campaign_positioning), and
form_coalition's willingness-to-join step (coalition_decision). The rupture
candidacy path, the coalition initiator designation, and coalition
maintenance/rupture across ticks all stay on simple_rules.py / out of
scope — see decide_coalition's own docstring.

Design doc §11.4's baseline-vs-LLM comparison depends on simple_rules.py
staying untouched and always available -- this module is additive, never a
modification of it. See simple_rules.py's own module docstring.

decide_candidacies (increment 2) only ever evaluates party-affiliated
citizens along the dominant path -- the rupture path
(attempt_rupture_candidacy, simple_rules.py) is explicitly "independent of
perceived support by design" (a probability mechanic, not a judgment call)
and never reaches the LLM.

decide_party_nominations (increment 3) only arbitrates parties with 2+
declared candidates this tick -- a party with 0 or 1 never needs a judgment
call, and select_party_nominee_from_declared keeps handling those trivially
(and remains the full baseline when llm.enabled=False). Its batching is
deliberately NOT chunk_voters/MIN_SAFE_BATCH_SIZE-shaped: it batches
*contested parties* (a handful at most, most ticks zero), not citizens --
forcing it through the citizen-batch guard would make the feature
permanently unreachable. See its own docstring.

decide_campaign_positioning (increment 4) only ever positions dominant
nominees, the same set decide_party_nominations/select_party_nominee(_from_declared)
already resolves -- rupture candidates keep running on their sincere
position (attempt_rupture_candidacy's whole point is an unstrategized
protest candidacy) and never reach this function. Unlike every prior
decision type, this one changes an actual vote input (pledged_platform),
not just who's eligible or how a ballot is cast -- the first increment
where the LLM's choice can change who wins. Also deliberately NOT
chunk_voters-shaped, same reasoning as decide_party_nominations: it batches
this tick's *nominees* (a handful), not citizens.

decide_coalition (increment 5) only asks each seated, non-initiator party
whether it joins the designated formateur's coalition -- the initiator
itself is a deterministic institutional designation (tiebreak_key,
simple_rules.py), never an LLM output, and assemble_coalition resolves the
willing subset into a coalition using form_coalition's own distance-based
ordering, so the LLM's causal contribution is isolated to willingness only.
Formation only: coalition maintenance/rupture across subsequent ticks
(design doc §3.1's "maintien et rupture") is out of scope for this
increment -- see decide_coalition's own docstring for why.

decide_representative_response (v4 Lot 6, dt=6) is the first decision type
in this module that runs EVERY tick, not just at an election, and the first
one that mutates a sitting officeholder (revealed_position) rather than a
candidate. It is handed an already-frozen `Mapping[int, ResponseContext]`
built by its caller (run_polity_simulation._run_representative_responses)
and must never read a Citizen's live `street_pressure` itself -- the
one-tick lag §7bis.7 requires is a property of when that context was
captured, not of anything this function does, and this function has no way
to violate it by construction (it only sees the frozen snapshot).

decide_pressure_actions (v4 Lot 7, dt=10) is the second decision type that
runs every tick and the first since vote_cast to batch CITIZENS (the
consulted cohort, dozens strong on a busy tick) rather than a handful of
officeholders/nominees/parties -- so it is the first to reuse chunk_voters
since increment 1. It is handed an already-frozen
`Mapping[int, PressureContext]`, one per consulted citizen, built by its
caller; a decoded act that is menu-legal but stale against LIVE petition
state (opened/signed by someone else earlier in the same tick) is NOT
rejected here -- see accountability.applicable_pressure_act, which the
caller applies after this function returns. This module never sees or
mutates petition state; it only decides and validates against the menu.

decide_reaction_to_event (v5 Lot 4, dt=8) is the third population-wide-
broadcast decision type after vote_cast/decide_pressure_actions, and the
first to make TWO independent calls in one tick body (a tick where both a
scandal and an economic shock fire calls this twice, once per event_type,
never combined into one prompt). It has the smallest ctx of any decision
type in this module -- one float, event_salience -- because dt=8 must run
regardless of whether a president currently sits (self_gap/mandate_dev,
both officeholder-relative, are structurally uncomputable on a vacancy
tick and were dropped from the wire schema entirely, not merely made
optional; see llm_schemas.ReactionDecision's own docstring).

decide_chamber_deliberation (v6b Lot 3, dt=11) is the fourth 5-file LLM
decision type built from scratch this project's session, and the first
with no §3.6.x textual anchor at all -- §6bis.3 names chamber_deliberation
once, with no worked JSON example, so its wire shape is this lot's own
invention rather than a reading. Runs every tick the sortition chamber is
seated (not just rotation ticks), gated ONLY on config.llm.enabled --
unlike dt=6/dt=10, no section flag needs to accompany it, since the
chamber's own enablement (config.sortition_chamber.enabled) is checked by
the CALLER before this module is ever reached (run_polity_simulation's
_run_chamber_deliberation is dispatched directly from the tick loop, never
nested inside _run_accountability_phase -- see that function's own
docstring for why). Chunks via chunk_voters, but at its OWN measured
ceiling (_CHAMBER_MAX_CHUNK_SIZE=1, cut down from an original 10 -- via a
tried-and-failed intermediate of 5 -- after repeated token-budget overflows;
see that constant's own docstring), not config.llm.max_batch_size --
originally designed to never chunk at all (the cohort is capped at
sortition_chamber.seats, shipped 30, "a handful", the same category as
dt=5/dt=6), but this lot's own pre-flight spike measured that assumption
wrong: one call of 30 (and even a chunk of 15) silently drops all but the
last 6 decisions, a lower reliability ceiling than every other decision
type in this module, attributable to this prompt's own heavier per-member
payload (two 20-dim position arrays per member, unlike dt=10's scalar-only
ctx). See decide_chamber_deliberation's own docstring for the measured
numbers. No lag either, unlike dt=6: §6bis.3 requires a seated
member be insulated from every §7bis pressure channel, so there is no
same-tick external mutation for a lag to protect against -- ChamberContext
carries a single, already-stable field (ticks_left).

Deliberate simplifications versus the full design doc, documented rather
than silently made:
- No persona library (§9) yet: citizens are described to the LLM by their
  existing raw fields (issue_positions/issue_priorities/blank_threshold),
  not an archetype. §3.5's "group by archetype_id" batching criterion is
  therefore not literally implementable; chunk_voters() below uses a
  near-equal split by citizen_id instead.
- No cache (§4.2) yet: correctness comes from temperature=0 + a pinned
  model + serialized calls (llm_batching_determinism_results.md), not a
  cache. Deferred to a later increment.
- Blank ballots lose v0/v1's "still ranks every candidate below Blank"
  information (§3.6.1's hard rule: blank=1 means every other field is
  empty) -- a real, documented divergence from the deterministic baseline
  that partially confounds §11.4's "any deviation is attributable to the
  LLM" claim for blank voters specifically. See ballot_from_decision.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence, TypeVar

import numpy as np

from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import (
    CAMPAIGN_MOTIF_PROMPT_TABLE,
    CANDIDACY_MOTIF_PROMPT_TABLE,
    CHAMBER_MOTIF_PROMPT_TABLE,
    COALITION_ACTION_PROMPT_TABLE,
    COALITION_MOTIF_PROMPT_TABLE,
    PARTY_NOMINATION_MOTIF_PROMPT_TABLE,
    PRESSURE_ACT_PROMPT_TABLE,
    PRESSURE_MOTIF_PROMPT_TABLE,
    REACTION_MOTIF_PROMPT_TABLE,
    RESPONSE_MOTIF_PROMPT_TABLE,
    STANCE_PROMPT_TABLE,
    VOTE_MOTIF_PROMPT_TABLE,
    CoalitionAction,
    EventType,
    ReactionMotif,
    check_codebook_version,
)
from api.domain.polity.config import PolityConfig, PressureMenuConfig
from api.domain.polity.llm_client import (
    SUPPORTED_PROVIDERS,
    LlmClientProtocol,
    LlmResponseError,
    decode_candidacy_batch,
    decode_chamber_batch,
    decode_coalition_batch,
    decode_party_nomination_batch,
    decode_positioning_batch,
    decode_pressure_batch,
    decode_reaction_batch,
    decode_response_batch,
    decode_vote_batch,
    unsupported_provider_error,
)
from api.domain.polity.llm_schemas import (
    CANDIDACY_JSON_SCHEMA,
    CHAMBER_JSON_SCHEMA,
    COALITION_JSON_SCHEMA,
    PARTY_NOMINATION_JSON_SCHEMA,
    POSITIONING_JSON_SCHEMA,
    PRESSURE_JSON_SCHEMA,
    REACTION_JSON_SCHEMA,
    RESPONSE_JSON_SCHEMA,
    VOTE_CAST_JSON_SCHEMA,
    CandidacyDecision,
    ChamberDecision,
    CoalitionDecision,
    PartyNominationDecision,
    PositioningDecision,
    PositionShift,
    PressureDecision,
    ReactionDecision,
    ResponseDecision,
    VoteCastDecision,
)
from api.domain.polity.parties import Party
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    candidate_label,
    sympathizer_ratio,
    tiebreak_key,
    weighted_distance,
)

# Empirical threshold from ollama_structured_output_results.md's root-cause
# investigation: batches of <=12 citizens (holding dims/candidates fixed at
# the values used there) reliably produced zero visible output regardless
# of token budget; 15 worked reliably. This is a safety margin above that
# boundary, not the boundary itself -- real citizen data may shift it.
MIN_SAFE_BATCH_SIZE = 20

# v6b Lot 3's own measured ceiling for chamber_deliberation, DISTINCT from
# MIN_SAFE_BATCH_SIZE/config.llm.max_batch_size -- this lot's own pre-flight
# spike (scripts/lot3_chamber_reliability_results.md) found the real model
# reliably answers a batch of 10 chamber members but SILENTLY DROPS all but
# the last 6 decisions at 15 or 30, in one call OR chunked at 15 -- a lower
# ceiling than every other decision type, attributable to this prompt's own
# heavier per-member payload (sincere_position + chamber_position, two
# 20-dim float arrays per member, unlike dt=10's own scalar-only ctx).
# Originally shipped at 10 (3/3 chunks clean on the real 30-member cohort at
# the time).
#
# 10 turned out not to be a stable ceiling either, by direct analogy with
# _VOTE_CAST_MAX_CHUNK_SIZE's own history below: a real v6b acceptance run
# (2026-08-21/22, GPU) hit finish_reason='length' on a chunk_size=10 call,
# 3/3 (original + 2 replays), all landing EXACTLY on n_decoded=10136 --
# byte-for-byte identical across all three attempts, confirmed via docker
# logs (n_ctx_slot=16384, truncated=0, no context-shift; prompt=4754 tokens,
# 11630 tokens of real headroom to the actual context ceiling). This is
# compute_max_tokens(10) + _CHAMBER_THINK_TOKEN_ALLOWANCE = 2136 + 8000 =
# 10136 exactly -- the deterministic "hits the configured ceiling on the
# nose" signature (Mode B: budget too tight), not the "reasoning collapses
# and never converges regardless of budget" signature (Mode A) cast_votes's
# own per-voter arithmetic showed at increasing chunk sizes.
#
# Widening the budget again was rejected in favor of cutting the chunk size,
# for the same reason _VOTE_CAST_MAX_CHUNK_SIZE's own history already
# establishes: reasoning-token appetite scales with content, not a fixed
# ceiling -- vote_cast tried three successive widenings (4000/8000/12000)
# and never converged, while cutting chunk size did.
#
# Tried 5 first (halving, not vote_cast's own chunk_size=1 endpoint outright)
# on the reasoning that this was one exhaustion in 1258 journaled events, not
# a repeated failure to converge, and chamber_deliberation already runs every
# tick (chunk_size=1 would 10x its call count, 30/tick instead of 3, against
# a decision type already flagged as this run's own dominant cost driver).
# Validated directly against the real failing chunk before shipping
# (2026-08-22, GPU) -- and 5 did NOT hold: all three original chunk-of-10
# groups happened to complete cleanly on that pass (this backend's own
# already-documented temperature=0 non-determinism -- the exact overflow
# from the live run did not reproduce identically), but splitting each into
# chunk-of-5 halves for margin evidence reproduced the IDENTICAL failure on
# a different half (cids=[59,61,65,75,90]), 99.1s to fail, n_decoded landing
# at EXACTLY compute_max_tokens(5) + _CHAMBER_THINK_TOKEN_ALLOWANCE =
# 1836 + 8000 = 9836 -- the same "hits the ceiling on the nose" signature,
# just relocated, zero margin, not merely close to it. Exactly the vote_cast
# precedent this comment already cites: an intermediate chunk size (there,
# 3 and then 2) can still occasionally overflow.
#
# Cut to 1 (vote_cast's own endpoint) and re-validated against the SAME
# failing 5-citizen group, individually (2026-08-22, GPU): all 5 completed
# cleanly, 4.3-11.7s each -- an order of magnitude faster than the 99-108s
# overflow calls, real margin, not a near-miss. See
# scripts/lot3_chamber_reliability_results.md's "Lot 4 chunk_size=1
# validation" section for the full evidence chain (chunk=10 crash,
# chunk=5 re-failure, chunk=1 convergence).
_CHAMBER_MAX_CHUNK_SIZE = 1

# A real v6b acceptance run (2026-08-17, GPU) found cast_votes's own
# per-voter distance-threshold arithmetic -- correct at batch size 1 (5/5
# hand-verified against the real precomputed distances) -- collapses the
# instant multiple voters share one call: batches of 3 stayed 9/9 correct
# across three independent voter groups, batches of 4 dropped to 5/8, and
# the shipped chunk size (25, via config.llm.max_batch_size) reproduced the
# exact production failure -- 24/25 voters returned the literal identity
# ranking [1,2,3,4,5] (position order, not distance order), regardless of
# chunk size 25/20/15/13/12 or extra max_tokens. Not a truncation artifact:
# a batch of 5 given a full 12000-token budget still finished cleanly at
# only 2/5 correct. This supersedes MIN_SAFE_BATCH_SIZE's own historical
# note that vote_cast's prompt shape needs >=20 -- that CPU-era finding
# ("zero visible output regardless of token budget") was measured without
# the extra reasoning allowance below; with it, batches of 1-3 complete
# cleanly and correctly. See _VOTE_THINK_TOKEN_ALLOWANCE and cast_votes's
# own docstring for the full picture.
#
# 3 turned out not to be a hard floor either. Three consecutive live
# escalations of _VOTE_THINK_TOKEN_ALLOWANCE (4000 -> 8000 -> 12000, see
# that constant's own history) each hit finish_reason='length' again on a
# DIFFERENT chunk_size=3 batch -- no convergence, and 12000 already sits
# within ~500 tokens of the real OLLAMA_CONTEXT_LENGTH=16384 ceiling given
# the observed ~2100-token prompt, so raising it further risked resurrecting
# the already-fixed context-shift bug (ollama_context_window_results.md)
# instead of fixing this one. think=False was tested directly as an
# alternative to widening the budget further and rejected on its own
# quality grounds -- a live spike against real weighted_distance ground
# truth (2026-08-21) scored 1/15 correct, mostly a fixed-looking
# non-distance permutation, i.e. silent ballot corruption, worse than the
# current loud failure.
#
# Reducing chunk size was tested empirically instead (2026-08-21, GPU,
# think=True, the same 12000-token allowance, real production
# population/prompts, 8 chunks per size): chunk_size=2 still failed 1/8
# (finish_reason='length', 143.3s to get there -- a real, expensive budget
# exhaustion, not a fluke); chunk_size=1 was clean 8/8. The reasoning-token
# appetite scales with content, just not primarily via the flat
# 60-token/voter addend compute_max_tokens adds -- fewer voters per call
# measurably reduces how much the model has to reason about, unlike the
# flat _VOTE_THINK_TOKEN_ALLOWANCE budget on its own. Costs roughly 3x the
# number of cast_votes calls (95 voters/election at 1-per-call vs
# ceil(95/3)=32 at 3-per-call), forecast at ~+29 min added to a 3-election,
# 8-year acceptance run (~4h baseline) -- not the dominant cost driver
# (chamber_deliberation/pressure_action's own per-tick call volume is), and
# likely an overestimate since it assumes chunk_size=3 would have completed
# cleanly instead of repeatedly failing and burning replay attempts.
_VOTE_CAST_MAX_CHUNK_SIZE = 1

# cache_recycle_chunk_size_tension_findings.md's own 3-condition harness
# experiment (2026-08-22, GPU) found the chunk_size=1 fix above still
# fails at a real, deterministic ~6.7% rate (2/30 across A_none/B_six/
# C_three alike) -- always the SAME error (blank=1 + non-empty ranking,
# §3.6.1), never a truncation, and identically reproducible per-voter
# regardless of recycle_after_n_calls, which the experiment's own
# decision criteria conclusively ruled out as the operative variable (see
# that doc's own "Conclusion"). Since the failure is deterministic at
# temperature=0, an identical byte-for-byte retry (_complete_and_decode_
# with_replay's own shipped default) reproduces the identical wrong
# output rather than resampling past it -- exactly what the crashed
# acceptance run's own 2 failed replay attempts already demonstrated.
# Validated directly (2026-08-22) against the real production cast_votes
# path, using the same two known-reproducible cases (cid=7, cid=28) from
# that experiment: cid=7's first attempt failed with the IDENTICAL error
# text as every prior observation (same deterministic reproduction), and
# the retry at this temperature succeeded (blank=0, ranking=[2]) --
# retry_sampling_varied=True, a clean before/after confirmation. cid=28,
# by contrast, did NOT reproduce its earlier failure across 3 fresh calls
# in this validation (succeeded on the first, temperature=0 attempt every
# time) -- consistent with this module's own already-documented finding
# that temperature=0 + a pinned seed is NOT a reproducibility guarantee on
# this inference backend (llm_client.py's own module docstring,
# ollama_structured_output_results.md), not evidence against the
# mitigation, but honestly inconclusive as a second data point. One clean
# confirmatory case, one inconclusive case -- not an exhaustive sweep,
# per the deliberately quick validation this was scoped to. This is a
# deliberate, LOCAL, one-call-site exception to the project's own
# temperature=0 determinism requirement -- see _complete_and_decode_
# with_replay's own retry_temperature/retry_info docstring for why it
# does not change that requirement's own scope (config._parse_llm's rule
# governs the CONFIGURED value; this overrides only a retry attempt, on
# this one call site, never the first attempt).
_VOTE_CAST_RETRY_TEMPERATURE = 0.3

# Mirrors _POSITIONING_THINK_TOKEN_ALLOWANCE's own reasoning: a shared
# constant would either starve one caller or over-provision another, since
# each think=True prompt's reasoning-token appetite is measured
# independently. A batch of 5 at compute_max_tokens(5)+4000=5836 still hit
# finish_reason='length'; 4000 is what the reliable size<=3 range above was
# actually measured against.
#
# That "reliable" range turned out not to be a hard floor either: a real
# v6b acceptance run (2026-08-20, GPU, OLLAMA_CONTEXT_LENGTH=16384 already
# in effect) hit finish_reason='length' on a chunk_size=3 batch, deterministic
# at temp=0 (the replay hit the identical n_decoded=5716/5717 ceiling both
# times). Confirmed via docker logs this was NOT the context-window bug
# (ollama_context_window_results.md) -- n_ctx_slot=16384 throughout, no
# context-shift event, prompt ~2097 tokens, truncated=0. Simple budget
# exhaustion: the model's own reasoning ran past the allotted 4000-token
# ceiling before emitting a stop token. Same fix as
# _POSITIONING_THINK_TOKEN_ALLOWANCE's own identical live finding: doubled.
#
# Doubling to 8000 was ALSO not a hard floor: the very next relaunch of that
# same run (still 2026-08-20, GPU) hit finish_reason='length' again, on a
# different chunk_size=3 batch, 2/2 replay attempts, n_decoded landing right
# at the new 9716 ceiling both times -- same signature (n_ctx_slot=16384,
# no context-shift, truncated=0), just a batch whose reasoning ran even
# longer. Reasoning-token appetite for this decision type is evidently
# unbounded-in-practice, not just underestimated once. Rather than keep
# doubling reactively, sized directly against the actual constraint:
# OLLAMA_CONTEXT_LENGTH=16384 minus the observed ~2100-token prompt leaves
# roughly 14000 tokens of real headroom, so 12000 leaves a genuine margin
# (~2600 tokens) for prompt-size variance rather than sitting right at the
# ceiling like 4000/8000 both did.
_VOTE_THINK_TOKEN_ALLOWANCE = 12000

# think=False's own "3/3 on the real 30-member cohort" finding above did NOT
# generalize to every 10-member chunk: a real v6b acceptance run (2026-08-17,
# GPU) hit a specific 10-cid chunk that think=False dropped to 4/10 --
# reproduced 8/8 identical (same 4 survivors, byte-for-byte) direct against
# the real prompt, a fully deterministic degenerate mode, not sampling
# variance. Not a token-budget truncation (the JSON for the 4 returned
# entries was complete and well-formed, not cut off). Switching that exact
# chunk to think=True fixed it 6/6 -- the same think=False->True fix
# decide_campaign_positioning's own docstring already documents for an
# analogous duplicate/drop failure. See
# scripts/lot3_chamber_reliability_results.md's "Lot 4 correction" section
# for the measured evidence.
#
# That 4000 figure was itself wrong on its own stated terms: this constant's
# own docstring claims it "costs the same _CHAMBER_THINK_TOKEN_ALLOWANCE
# budget decide_campaign_positioning already pays" -- but
# _POSITIONING_THINK_TOKEN_ALLOWANCE is 8000, not 4000; the think=False->True
# switch above copied the pattern without copying the actual value. Confirmed
# live (2026-08-20, GPU, same run as _VOTE_THINK_TOKEN_ALLOWANCE's own fix
# above): a chunk_size=10 chamber_deliberation call hit finish_reason='length'
# 3/3 (original + 2 replays, all near-identical n_decoded), n_ctx_slot=16384
# throughout, no context-shift, prompt ~4771 tokens -- the same deterministic
# budget-exhaustion signature, not context corruption. Corrected to actually
# match the value the docstring already claimed.
_CHAMBER_THINK_TOKEN_ALLOWANCE = 8000

_TRUNCATION_THRESHOLD = 6
_TRUNCATE_TO = 5

_logger = logging.getLogger(__name__)

_BatchT = TypeVar("_BatchT")


@dataclass(frozen=True)
class VoteBatchOutcome:
    ballots: list[list[str]]
    decisions: list[VoteCastDecision]
    retry_sampling_varied: dict[int, bool] = field(default_factory=dict)
    """cid -> whether that voter's decision came from a temperature-varied
    RETRY (never the first attempt -- see _VOTE_CAST_RETRY_TEMPERATURE),
    per _complete_and_decode_with_replay's own retry_info contract. Since
    _VOTE_CAST_MAX_CHUNK_SIZE=1, one chunk == one voter == one completion,
    so this is unambiguous per cid. Defaults to an empty dict (every key
    absent means False) so every pre-existing VoteBatchOutcome(...)
    construction in this codebase's own tests keeps compiling unchanged."""


def _check_supported(config: PolityConfig) -> None:
    """Fail before any network call, mirroring run_simulation's existing
    top-of-function guard style -- never do partial work on a config this
    module can't actually honor.

    As of v4 (§15bis.6, vLLM switch), the provider check no longer gates an
    ERA -- it gates which providers actually have a client
    (llm_client.SUPPORTED_PROVIDERS). "ollama" and "vllm" both pass;
    "api" (hosted inference) is out of scope by design (§12), not merely
    unbuilt. Kept as the single source of truth shared with
    llm_client.build_json_client, the run-start dispatch point -- same
    error, same message, different time (this fires at the first decision,
    build_json_client fires earlier, at run start)."""
    if config.llm.provider not in SUPPORTED_PROVIDERS:
        raise unsupported_provider_error(config.llm.provider)
    if config.llm.batch_sharding != "static":
        raise NotImplementedError(
            f"llm.batch_sharding {config.llm.batch_sharding!r} is not supported -- "
            "dynamic sharding breaks reproducibility (§15bis.4a)"
        )
    if config.llm.rationale_mode != "codes":
        raise NotImplementedError(f"llm.rationale_mode {config.llm.rationale_mode!r} is not supported yet (§16.5)")
    if config.parallel.intra_run_workers != 1:
        raise NotImplementedError(
            "parallel.intra_run_workers > 1 is not supported -- concurrent batching breaks "
            "reproducibility (llm_batching_determinism_results.md)"
        )
    check_codebook_version(config.llm.codebook_version)


def _complete_and_decode_with_replay(
    client: LlmClientProtocol,
    *,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any],
    max_tokens: int,
    think: bool,
    decode: Callable[[str], _BatchT],
    replays: int,
    decision_type: str,
    retry_temperature: float | None = None,
    retry_info: dict[str, Any] | None = None,
) -> _BatchT:
    """§3.6.10's "un batch invalide est rejoue integralement, jamais
    corrige partiellement" -- the half of that rule the codebase never
    implemented (v4 Lot 8). `replays` is config.llm.max_batch_replays,
    shipped 0 -- today's exact behavior: one call, LlmResponseError
    propagates on the first bad decode, every existing test unmodified.

    Retries the BYTE-IDENTICAL request on LlmResponseError only, up to
    `replays` extra attempts, and logs every replay at WARNING with the
    decision type, attempt number and the rejected error -- never journals
    it (§16.3's canonical event list is about the polity, not the
    inference host). LlmTransportError is NOT caught here: the client
    already owns its own transport-level retries.

    Covers LlmResponseError from BOTH sources: `client.complete_json`
    itself (e.g. a truncated/incomplete generation -- done_reason != "stop"
    -- raised by llm_client.py's own _extract_content/_extract_native_content)
    and `decode` (decoding/schema-alignment, decode_*_batch). Both calls
    therefore sit inside the same try block -- NOT `complete_json` outside
    it, `decode` inside, which was this function's own shipped shape from
    v4 Lot 8 until a real v6b Lot 4 acceptance run caught it: a truncated
    chamber_deliberation generation raised LlmResponseError from
    complete_json itself, propagated on the very first attempt with no
    retry and no WARNING logged, silently defeating the whole replay
    feature for that entire failure class. The bug had zero test coverage
    because the test suite's own `_FlakyClient` fixture only ever fails
    by returning malformed JSON (a decode-time failure) -- it never raises
    from complete_json, so the untested branch was also the broken one.

    The subsequent config-bound validate_*_decision calls each caller makes
    stay outside the retry loop, on purpose. A validate_* failure (an
    out-of-bounds shift, an out-of-menu act) is the model's judgment being
    wrong in a way an identical retry at temperature=0 is not expected to
    fix, and several callers build side effects (ballots, resolved
    platforms) alongside their own validate_* loop that would need
    unwinding to retry safely -- unlike a truncated/misaligned response,
    which produces no such side effect to unwind.

    This softens, and deliberately does not overturn,
    LlmResponseError's own "NOT retried" ruling (llm_client.py): that
    ruling's operative objection is SILENT laundering of a real problem. A
    logged, bounded, opt-in, off-by-default replay is neither silent nor
    unbounded -- a replay makes the resulting journal depend on attempt
    count, so an LLM run with replays > 0 is not byte-reproducible, a
    property live LLM runs never had (§15bis.4) and the shipped default of
    0 leaves untouched.

    `retry_temperature` (default None, i.e. every existing call site's
    behavior: byte-identical retries at the client's own configured
    temperature=0) is a DELIBERATE, LOCAL exception to this project's own
    determinism requirement, not a general policy change -- see
    cache_recycle_chunk_size_tension_findings.md's own harness experiment,
    which found a real, reproducible cast_votes failure mode (a
    deterministic, per-voter-prompt blank/ranking schema incoherence,
    identical across recycle_after_n_calls settings, meaning an identical
    byte-for-byte retry at temperature=0 reproduces the identical wrong
    output rather than resampling past it). The FIRST attempt (attempt==0)
    always uses `temperature=None` (the client's own configured value) --
    this is unconditional and does not depend on `retry_temperature` being
    set, so a caller opting into this parameter never loses determinism on
    the common, successful-first-try path. Only a genuine retry (attempt
    >= 1) uses `retry_temperature`, when given.

    `retry_info` (default None) is an optional, caller-owned mutable dict
    this function writes into on success: `{"attempts": int, "sampling_
    varied": bool}`. `sampling_varied` is true iff the successful attempt
    was itself a retry AND `retry_temperature` was set for it -- the
    caller's own signal for whether to journal a `retry_sampling_varied`
    marker, so a future analysis of the journal cannot mistake a
    varied-sampling retry's decision for an ordinary, deterministic
    first-attempt one. Every existing call site passes neither parameter
    and is completely unaffected -- this dict is populated, never read, by
    this function.

    The `temperature` kwarg is passed to `client.complete_json` only when
    actually overriding (attempt >= 1 and `retry_temperature is not None`)
    -- never as an explicit `temperature=None` on every call. This keeps
    every fake/test client across this codebase's own test suite (whose
    `complete_json` signatures predate this parameter and don't accept it)
    working completely unchanged; only a caller that actually sets
    `retry_temperature` and actually reaches a retry needs its own fake
    client to accept the kwarg."""
    attempt = 0
    while True:
        call_kwargs: dict[str, Any] = {}
        if attempt > 0 and retry_temperature is not None:
            call_kwargs["temperature"] = retry_temperature
        try:
            raw = client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=json_schema,
                max_tokens=max_tokens,
                think=think,
                **call_kwargs,
            )
            result = decode(raw)
            if retry_info is not None:
                retry_info["attempts"] = attempt
                retry_info["sampling_varied"] = attempt > 0 and retry_temperature is not None
            return result
        except LlmResponseError as exc:
            if attempt >= replays:
                raise
            attempt += 1
            _logger.warning(
                "%s batch rejected on attempt %d/%d, replaying%s: %s",
                decision_type, attempt, replays + 1,
                f" at temperature={retry_temperature}" if retry_temperature is not None else "",
                exc,
            )


def chunk_voters(
    voters: Sequence[Citizen], max_batch_size: int, *, min_batch_size: int = MIN_SAFE_BATCH_SIZE
) -> list[list[Citizen]]:
    """Near-equal chunks by citizen_id, never a small fixed-size remainder.
    A pure function of (voter set, max_batch_size) -- independent of
    arrival order or timing, which is what config's `batch_sharding:
    static` actually needs to guarantee (§15bis.4a).

    Raises if the population is too small to chunk safely against
    `min_batch_size` (default MIN_SAFE_BATCH_SIZE) rather than silently
    producing a chunk in territory this project has observed the model
    fail on. `min_batch_size` is a keyword-only override (v4 Lot 7,
    dt=10): MIN_SAFE_BATCH_SIZE's boundary was measured on the vote_cast
    prompt shape through the /v1 think=True path, and
    scripts/lot6_batch_reliability_results.md measured a
    pressure_action-shaped schema clean at sizes 1/3/5/10 through the
    native think=False path -- direct counter-evidence in exactly the
    region the default floor forbids. decide_pressure_actions passes
    min_batch_size=1, since the consulted cohort is frequently below 20
    late-term and this is not a consultation cap (§15bis.1): every
    consulted citizen is still asked, chunking only changes the number of
    HTTP requests, never the number of citizens."""
    n = len(voters)
    if n == 0:
        return []
    num_chunks = -(-n // max_batch_size)  # ceil division
    base_size, remainder = divmod(n, num_chunks)
    if base_size < min_batch_size:
        raise NotImplementedError(
            f"population_size={n} with llm.max_batch_size={max_batch_size} would produce a "
            f"chunk of {base_size} citizens, below min_batch_size={min_batch_size} "
            "(ollama_structured_output_results.md: small batches reliably fail regardless of "
            "token budget) -- increase population_size or max_batch_size"
        )
    chunks = []
    start = 0
    for i in range(num_chunks):
        size = base_size + (1 if i < remainder else 0)
        chunks.append(list(voters[start:start + size]))
        start += size
    return chunks


def truncation_limit(candidate_count: int) -> int | None:
    """Design doc §3.6.1: full ranking if <=6 candidates, else top-5."""
    return None if candidate_count <= _TRUNCATION_THRESHOLD else _TRUNCATE_TO


def compute_max_tokens(chunk_size: int) -> int:
    """The addend is a flat reasoning allowance, not scaled by chunk size.
    A live consolidation run hit finish_reason='length' on a 20-citizen
    batch under the old `chunk_size*60+256` formula: Qwen3's internal
    <think> reasoning consumes the same completion budget as the visible
    JSON answer (ollama_structured_output_results.md's toy-batch failure
    showed a 512-token budget spent entirely on invisible reasoning), and
    that reasoning length is unpredictable, not proportional to the number
    of decisions to emit. 1536 gives real headroom above what the one
    successful full-size (25-citizen) live call actually used (1026
    completion tokens)."""
    return max(chunk_size * 60 + 1536, 1536)


_POSITIONING_THINK_TOKEN_ALLOWANCE = 8000
"""Extra budget decide_campaign_positioning adds on top of compute_max_tokens
once it moved to think=True (v4 Lot 8 live finding, see that function's
docstring). Measured, not guessed: a 5-nominee batch under
compute_max_tokens(5)+2000 (=3836) hit finish_reason='length' on one of three
live attempts; +4000 (=5836) cleared 3/3 at the time -- but a real v6b
acceptance run (2026-08-17/18, GPU) hit finish_reason='length' on the exact
same 5-nominee shape at +4000, 1/3 direct-replay attempts, confirming +4000
was never a hard floor, just a smaller live sample that happened not to hit
the tail. Root-caused alongside that same run: Ollama's OpenAI-compat
endpoint had been silently capped at a 4096-token context window this whole
project's history (see scripts/ollama_context_window_results.md) -- fixed at
the container level (OLLAMA_CONTEXT_LENGTH=16384), which is what makes a
larger allowance here safe rather than merely optimistic. Re-measured
directly against the real failing prompt: +8000 (=9836) cleared 5/5, each
completing in ~23s, well under budget -- not a near-miss. Kept as its own
named constant rather than folded into compute_max_tokens itself, since that
function's own 1536 addend was calibrated on vote_cast's think=True shape and
positioning's per-candidate strategic reasoning measured hungrier -- a shared
constant would either starve positioning or over-provision every other
think=True caller.

An earlier version of this fix also shortened decide_campaign_positioning's
own HTTP timeout to 240s (below OllamaJsonClient's 600s instance default),
reasoning that a live diagnostic had hit a request that never returned under
think=True against a synthetic test fixture. That override was reverted:
relaunching the real acceptance sweep at 240s made the SAME real nominee
combination that succeeded 5/5 in isolated diagnostics (at the untouched
600s default) fail consistently -- the shortened bound was cutting off
legitimate, slower-but-correct generations, not just genuinely stuck ones.
600s (unmodified, same as every other think=True caller in this codebase)
is what the evidence actually supports."""


def sorted_candidates(candidates: Sequence[Citizen]) -> list[Citizen]:
    """The single canonical candidate order every prompt/position-mapping
    must agree on (D-5): position N in build_user_prompt's candidate list
    must be the same candidate as position N when mapping the model's
    response back to a cid in cast_votes."""
    return sorted(candidates, key=lambda c: c.citizen_id)


def build_system_prompt(citizens: Sequence[Citizen], candidates: Sequence[Citizen]) -> str:
    """Enumerates the full expected voter cid list verbatim, not just a
    count -- ollama_structured_output_results.md Finding B: a bare 'return
    exactly N decisions' instruction was empirically insufficient, the
    model dropped the last citizen of a 25-item batch despite it. The
    explicit list + self-check instruction fixed it on the first try.

    `ranking` uses candidate *positions* (1..N), never candidate cids: a
    live consolidation run found the model conflates a candidate-cid-based
    ranking with the voter cid list above, because a candidate is also a
    citizen -- candidate and voter cids draw from the same number space
    and can collide (citizen 11 both votes and is a candidate). Telling
    the model to use positions instead removes the collision structurally
    rather than relying on wording alone to disambiguate two overlapping
    lists of raw cids.

    States the acceptability rule EXPLICITLY (distance <= blank_threshold,
    prefer the closest acceptable candidate over blank) -- v4 Lot 8's own
    live finding: a real acceptance run, at real population scale (100
    voters x 5 candidates x 20 issue dimensions), produced 100% blank
    ballots, reproduced with the RAW model response (not a decode bug).
    The prior prompt asked the model to judge "acceptable" from raw
    20-dimensional position/priority vectors with no worked definition --
    the same weighted-euclidean-vs-threshold arithmetic build_ranking
    computes exactly (simple_rules.weighted_distance), left for the model
    to approximate from scratch, batched across 25 voters at once. See
    build_user_prompt's own docstring for the fix (precomputed distances)
    this system prompt now explains how to read.

    States EXPLICITLY that `ranking` carries EVERY acceptable candidate,
    never just the closest one -- the sentence looks redundant next to the
    REGLE above it and is not: the REGLE's own wording ("classe les
    POSITIONS des candidats acceptables du plus proche au plus eloigne")
    is genuinely ambiguous between "rank the acceptable ones" and "rank,
    i.e. pick, the closest acceptable one", and that ambiguity was the
    root cause of a Mode A reasoning loop that aborted two consecutive
    v6b acceptance runs under citizens.position_dist: factor_structure.
    Diagnosed live at the raw-response level, not inferred: the model
    reaches the CORRECT answer within the first ~1500 characters of
    <think>, then spends the remaining ~62 000 characters repeating one
    near-identical paragraph re-quoting this prompt's own REGLE, never
    resolving the format question and never emitting JSON -- burning the
    entire 13 596-token budget (finish_reason='length', content empty).
    NOT a token-budget failure: _VOTE_THINK_TOKEN_ALLOWANCE had already
    been raised 4000 -> 8000 -> 12000 and the loop is non-convergent, so a
    fifth number would only move the ceiling. factor_structure does not
    create the ambiguity, it raises how often the triggering condition is
    met -- voters with >= 2 acceptable candidates go from 62% (uniform) to
    88%, and mean acceptable candidates per voter from 2.62 to 3.54, which
    is enough to make a ~6-7% per-call loop rate abort a full run
    reliably. Fix verified live before shipping: 25 iterations across the
    truncating voter (cid=8, x10), the previously flaky one (cid=7, x5)
    and the two tightest-margin all-acceptable voters (x5 each) -- 0
    loops, 25/25 rankings exactly equal to the full acceptable set sorted
    by ascending distance, cid=8 going from 13 596 tokens with no answer
    to 58 tokens in 6.1s. Ollama at temperature=0 with a pinned seed is
    NOT deterministic (ollama_structured_output_results.md), so this is a
    rate measurement, not a proof of impossibility."""
    candidate_count = len(candidates)
    truncate_at = truncation_limit(candidate_count)
    truncate_note = "" if truncate_at is None else f" (classer au plus les {truncate_at} meilleurs)"
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide son "
        f"vote parmi les candidats.\nIl y a {candidate_count} candidats. "
        "Chaque candidat est identifie par son champ 'position' (1 a "
        f"{candidate_count}) dans la liste 'candidates' du message "
        "utilisateur -- PAS par son cid.\n"
        "Chaque electeur porte un champ 'distances' : sa distance DEJA "
        "CALCULEE (ponderee par ses propres priorites) vers chaque "
        "candidat, dans le meme ordre que la liste 'candidates' (position "
        "1 a N) -- tu n'as PAS a recalculer cette distance toi-meme. Un "
        "candidat est ACCEPTABLE si et seulement si sa distance est "
        "INFERIEURE OU EGALE au 'blank_threshold' de l'electeur.\n"
        "REGLE : si au moins un candidat est acceptable pour cet electeur, "
        "classe les POSITIONS des candidats acceptables du plus proche "
        f"(distance la plus faible) au plus eloigne{truncate_note}, motif "
        "105 (ACCEPTABLE_MATCH) pour le cas usuel d'un vote sincere -- un "
        "candidat imparfait mais sous le seuil DOIT etre prefere au vote "
        "blanc, ce n'est pas un pis-aller.\n"
        "Le tableau 'ranking' doit OBLIGATOIREMENT contenir CHAQUE candidat "
        "juge acceptable, classe par ordre de preference. Ne te limite "
        "JAMAIS au seul candidat le plus proche si d'autres candidats "
        "passent aussi le seuil de l'electeur.\n"
        "Le vote blanc (blank=1, ranking vide, motif 101) est reserve au cas "
        "ou AUCUN candidat ne passe ce seuil pour cet electeur -- ce n'est "
        "pas une option par defaut.\n"
        f"Motifs valides (code court obligatoire) :\n{VOTE_MOTIF_PROMPT_TABLE}"
        "\nIMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(citizens)} cid de CITOYENS-ELECTEURS (jamais un cid de "
        f"candidat), chacun une seule fois, dans cet ordre : [{cid_list}]. "
        "Verifie ta reponse avant de la finaliser : chaque cid de cette "
        "liste doit apparaitre exactement une fois dans le champ "
        f"'cid' des decisions, et chaque ranking ne doit contenir que des "
        f"entiers entre 1 et {candidate_count} (des positions, jamais un "
        "cid).\nReponds UNIQUEMENT avec un objet JSON conforme au schema "
        "fourni."
    )


def build_user_prompt(voters: Sequence[Citizen], candidates: Sequence[Citizen]) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats) so
    the prompt is a pure function of the candidate *set* and voter *set*,
    never of iteration order -- required for the byte-for-byte
    reproducibility test (Lot 8). Candidates sorted by citizen_id (D-5):
    _declare_nominees assembles party nominees in party-iteration order
    then rupture candidates by citizen_id, and get_two_round_winner's
    Counter.most_common(2) tie-breaks by insertion order, so the prompt
    itself must not depend on that assembly order.

    Each candidate block carries its `position` (1-indexed, this sorted
    order) alongside its `cid` -- `ranking` in the response refers to
    `position`, `cid` here is informational context only (party/platform
    are still meaningful to the model per-candidate).

    Each voter block carries `distances`: that voter's own
    simple_rules.weighted_distance to every candidate's platform, in the
    SAME `position` order as `candidates` -- the exact quantity
    build_ranking already compares against `blank_threshold` on the
    deterministic path. v4 Lot 8 live finding: without this, the model was
    asked to judge candidate "acceptability" from raw 20-dimensional
    position/priority vectors alone, an arithmetic task it could not do
    reliably at real batch scale (100 voters x 5 candidates), and it
    collapsed to blank=1 for essentially the whole electorate -- confirmed
    at the raw model-response level, not a decode/journal artifact.
    Precomputing the distance turns "is this candidate acceptable" into a
    single number-vs-number comparison the model only has to read, the
    same pattern dt=10's PressureContext.self_gap already established
    (compute the weighted-distance-derived quantity outside the model,
    hand it a plain float) -- this is that same pattern applied to
    cast_votes, which had never used it despite being the oldest
    LLM-callable decision type in the codebase."""
    sorted_c = sorted_candidates(candidates)
    candidate_platforms = [_platform(c) for c in sorted_c]
    candidate_blocks = [
        {
            "position": i,
            "cid": c.citizen_id,
            "platform": [round(x, 4) for x in platform],
            "party": c.party_affiliation,
        }
        for i, (c, platform) in enumerate(zip(sorted_c, candidate_platforms), start=1)
    ]
    voter_blocks = [
        {
            "cid": v.citizen_id,
            "positions": [round(x, 4) for x in v.issue_positions],
            "priorities": [round(x, 4) for x in v.issue_priorities],
            "blank_threshold": round(v.blank_threshold, 4),
            "distances": [round(weighted_distance(v, platform), 4) for platform in candidate_platforms],
        }
        for v in voters
    ]
    return json.dumps(
        {"candidates": candidate_blocks, "voters": voter_blocks}, sort_keys=True, separators=(",", ":")
    )


def _platform(candidate: Citizen) -> tuple[float, ...]:
    if candidate.pledged_platform is None:
        raise ValueError(f"citizen {candidate.citizen_id} has not declared a candidacy")
    return candidate.pledged_platform


def validate_decision(decision: VoteCastDecision, candidate_count: int, truncate_at: int | None) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without knowing this batch's candidate count and truncation rule.
    `decision.ranking` holds 1-indexed positions into this batch's sorted
    candidate list (see build_user_prompt/sorted_candidates), not cids."""
    out_of_range = [p for p in decision.ranking if p > candidate_count]
    if out_of_range:
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks out-of-range position(s) {out_of_range} "
            f"(this batch has {candidate_count} candidates, positions 1..{candidate_count})"
        )
    if truncate_at is not None and len(decision.ranking) > truncate_at:
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks {len(decision.ranking)} candidates, "
            f"exceeding the truncation limit of {truncate_at}"
        )
    if len(decision.ranking) > candidate_count:
        raise LlmResponseError(
            f"decision for cid={decision.cid} ranks more candidates ({len(decision.ranking)}) "
            f"than exist in this batch ({candidate_count})"
        )


def ballot_from_decision(decision: VoteCastDecision, position_to_candidate: dict[int, Citizen]) -> list[str]:
    """Mirrors build_ranking's contract (Blank always present in the
    returned list) so ballot_and_aggregation.get_presidential_winner needs
    zero changes. blank=1 collapses to just [BLANK_LABEL] -- see the
    module docstring's note on this divergence from build_ranking, which
    ranks every candidate even for a voter beyond their own tolerance.
    `decision.ranking` holds positions (validate_decision has already
    checked they're in range); `position_to_candidate` is the same
    1-indexed, citizen_id-sorted mapping build_user_prompt presented."""
    if decision.blank == 1:
        return [BLANK_LABEL]
    return [candidate_label(position_to_candidate[p]) for p in decision.ranking] + [BLANK_LABEL]


def resolve_ranking_cids(decision: VoteCastDecision, candidates: Sequence[Citizen]) -> list[int]:
    """Translates decision.ranking (1-indexed positions into `candidates`
    sorted by citizen_id) back to real candidate cids -- for the journal,
    which must stay a self-contained, human-readable record. Positions are
    a wire-protocol-only device to dodge the voter/candidate cid collision
    (see build_system_prompt's docstring); they must never leak into a
    persisted event, where a reader has no reason to know a batch's
    internal candidate ordering."""
    ordered = sorted_candidates(candidates)
    return [ordered[p - 1].citizen_id for p in decision.ranking]


def cast_votes(
    voters: Sequence[Citizen],
    candidates: Sequence[Citizen],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> VoteBatchOutcome:
    """v2 increment 1's replacement for `[build_ranking(voter, candidates)
    for voter in voters]`. Pure aside from the injected client -- no
    journal writes here, matching this repo's pure-worker convention;
    run_polity_simulation.py owns every journal write.

    v4 Lot 8 live finding, fixed here via build_system_prompt/
    build_user_prompt rather than this function's own body: at real
    population scale this decision type collapsed to blank=1 for the
    entire electorate, reproduced at the raw model-response level. The fix
    precomputes each voter's simple_rules.weighted_distance to every
    candidate (the same quantity build_ranking already compares against
    blank_threshold) and states the acceptability rule explicitly in the
    system prompt, instead of asking the model to derive "is this
    candidate acceptable" from raw 20-dimensional vectors. See VoteMotif.
    ACCEPTABLE_MATCH (codebook.py) for the wire-level half of the fix.

    Correction (2026-08-17, GPU): that fix stopped the 100%-blank collapse
    but not a second, subtler one -- batching multiple voters into one call
    makes the model stop actually reading each voter's own `distances`
    field at all. Verified directly against the real precomputed distances,
    not just "did it produce valid JSON": a batch of 1 is 100% correct
    (5/5), a batch of 3 stayed 100% correct across three independent voter
    groups (9/9), and batches of 4+ degrade sharply (5/8 at 4, 0-2/5 at 5,
    a near-uniform identity-permutation collapse at the shipped chunk size
    of 25). Chunks at the dedicated _VOTE_CAST_MAX_CHUNK_SIZE, not
    config.llm.max_batch_size -- deliberately overriding chunk_voters's own
    min_batch_size floor down to 1, the same override dt=10/dt=11 already
    use for their own measured ceilings, and for the same reason: the
    shipped MIN_SAFE_BATCH_SIZE=20 floor was itself calibrated on this
    exact prompt shape, but without the extra reasoning budget below --
    with it, small batches don't truncate, they're just correct."""
    _check_supported(config)

    candidate_count = len(candidates)
    position_to_candidate = {i: c for i, c in enumerate(sorted_candidates(candidates), start=1)}
    truncate_at = truncation_limit(candidate_count)

    ballots: list[list[str]] = []
    decisions: list[VoteCastDecision] = []
    retry_sampling_varied: dict[int, bool] = {}
    for chunk in chunk_voters(voters, _VOTE_CAST_MAX_CHUNK_SIZE, min_batch_size=1):
        expected_cids = [voter.citizen_id for voter in chunk]
        retry_info: dict[str, Any] = {}
        chunk_decisions = _complete_and_decode_with_replay(
            client,
            system_prompt=build_system_prompt(chunk, candidates),
            user_prompt=build_user_prompt(chunk, candidates),
            json_schema=VOTE_CAST_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)) + _VOTE_THINK_TOKEN_ALLOWANCE,
            think=True,
            decode=lambda raw: decode_vote_batch(raw, expected_cids),
            replays=config.llm.max_batch_replays,
            decision_type="vote_cast",
            # A deliberate, local exception to temperature=0 determinism --
            # see _VOTE_CAST_RETRY_TEMPERATURE's own comment. Only ever
            # applies to a genuine retry (never the first attempt).
            retry_temperature=_VOTE_CAST_RETRY_TEMPERATURE,
            retry_info=retry_info,
        )
        sampling_varied = bool(retry_info.get("sampling_varied", False))
        for decision in chunk_decisions:
            validate_decision(decision, candidate_count, truncate_at)
            ballots.append(ballot_from_decision(decision, position_to_candidate))
            retry_sampling_varied[decision.cid] = sampling_varied
        decisions.extend(chunk_decisions)

    return VoteBatchOutcome(ballots=ballots, decisions=decisions, retry_sampling_varied=retry_sampling_varied)


@dataclass(frozen=True)
class CandidacyBatchOutcome:
    decisions: list[CandidacyDecision]


def build_candidacy_system_prompt(citizens: Sequence[Citizen]) -> str:
    """Mirrors build_system_prompt's "enumerate the full expected cid list
    verbatim" fix (Finding B, ollama_structured_output_results.md) -- a bare
    'return exactly N decisions' instruction was empirically insufficient
    for vote_cast, and there's no reason to assume a shorter boolean+motif
    decision is immune to the same failure mode without live evidence to the
    contrary (see this module's own docstring on live-verifying increment
    2)."""
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide "
        "s'il se presente comme candidat (outcome=1) ou renonce "
        "(outcome=0), a partir de son ambition et du soutien qu'il "
        "percoit.\nMotifs valides (code court obligatoire) :\n"
        f"{CANDIDACY_MOTIF_PROMPT_TABLE}\nIMPORTANT : la liste decisions "
        f"doit contenir EXACTEMENT ces {len(citizens)} cid, chacun une "
        f"seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse "
        "avant de la finaliser : chaque cid de cette liste doit apparaitre "
        "exactement une fois.\nReponds UNIQUEMENT avec un objet JSON "
        "conforme au schema fourni."
    )


def build_candidacy_user_prompt(chunk: Sequence[Citizen], support: dict[int, float]) -> str:
    """`support` is precomputed once against the full population, before
    chunking (see decide_candidacies) -- never recomputed per-chunk, or the
    "perceived support" signal would become an artifact of
    llm.max_batch_size/chunk boundaries instead of a stable, population-wide
    value. Canonical JSON (sort_keys, compact separators, rounded floats),
    same reproducibility discipline as build_user_prompt."""
    citizen_blocks = [
        {
            "cid": c.citizen_id,
            "ambition_score": round(c.ambition_score, 4),
            "perceived_support": round(support[c.citizen_id], 4),
        }
        for c in chunk
    ]
    return json.dumps({"citizens": citizen_blocks}, sort_keys=True, separators=(",", ":"))


def decide_candidacies(
    citizens: Sequence[Citizen],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> CandidacyBatchOutcome:
    """v2 increment 2's replacement for `decide_candidacy`'s bare
    ambition_score threshold, dominant path only (see this module's
    docstring for what stays out of scope). Pure aside from the injected
    client -- no journal writes here, matching cast_votes's convention;
    run_polity_simulation.py owns every journal write.

    `citizens` is expected to already be filtered to party-affiliated
    citizens by the caller (mirrors select_party_nominee's existing filter,
    unchanged) -- this function itself doesn't re-filter by party, it just
    batches whatever population it's given.

    Calls the client with think=False: a live investigation found this
    task's shorter, more subjective prompt ("should this citizen run?")
    makes qwen3:8b burn its entire completion budget on invisible <think>
    reasoning with zero visible output, regardless of budget size --
    unrelated to vote_cast's own reasoning-budget accounting
    (compute_max_tokens's flat allowance), which stays unaffected since
    cast_votes never sets this flag. See OllamaJsonClient's class docstring
    for why this needs an entirely different transport, not just a body
    flag."""
    _check_supported(config)

    population = list(citizens)
    support = {c.citizen_id: sympathizer_ratio(c, population) for c in population}

    decisions: list[CandidacyDecision] = []
    for chunk in chunk_voters(citizens, config.llm.max_batch_size):
        expected_cids = [c.citizen_id for c in chunk]
        decisions.extend(
            _complete_and_decode_with_replay(
                client,
                system_prompt=build_candidacy_system_prompt(chunk),
                user_prompt=build_candidacy_user_prompt(chunk, support),
                json_schema=CANDIDACY_JSON_SCHEMA,
                max_tokens=compute_max_tokens(len(chunk)),
                think=False,
                decode=lambda raw: decode_candidacy_batch(raw, expected_cids),
                replays=config.llm.max_batch_replays,
                decision_type="candidacy_considered",
            )
        )

    return CandidacyBatchOutcome(decisions=decisions)


@dataclass(frozen=True)
class PartyNominationBatchOutcome:
    decisions: list[PartyNominationDecision]
    winners: dict[int, int]
    """party_id -> winning citizen_id, already resolved from winner_position
    -- only this module has the position<->candidate mapping (contested's
    per-party sub-list order), so resolution happens here, not in the
    caller, mirroring how cast_votes resolves positions into ballots
    internally rather than exposing raw positions."""


def build_party_nomination_system_prompt(contested: dict[int, list[Citizen]]) -> str:
    """Mirrors build_candidacy_system_prompt's "enumerate the full expected
    id list verbatim + self-check" fix (Finding B) -- keyed on party_id,
    since the decision unit here is a contested party, not a citizen."""
    party_id_list = ",".join(str(party_id) for party_id in contested)
    return (
        "Tu es un moteur de simulation. Pour chaque parti recu, plusieurs "
        "de ses membres veulent se presenter mais le parti ne peut "
        "designer qu'un seul candidat officiel. Choisis lequel, a partir "
        "de son ambition, du soutien qu'il percoit, et de sa proximite "
        "avec la plateforme du parti. Chaque candidat est identifie par "
        "son champ 'position' (1 a N) dans la liste 'candidates' de CE "
        "parti -- PAS par son cid.\nMotifs valides (code court "
        f"obligatoire) :\n{PARTY_NOMINATION_MOTIF_PROMPT_TABLE}\nIMPORTANT "
        f": la liste decisions doit contenir EXACTEMENT ces {len(contested)} "
        f"party_id, chacun une seule fois, dans cet ordre : [{party_id_list}]. "
        "Verifie ta reponse avant de la finaliser : chaque party_id de "
        "cette liste doit apparaitre exactement une fois, et chaque "
        "winner_position doit etre une position valide (jamais un cid) "
        "parmi les candidats de ce parti.\nReponds UNIQUEMENT avec un "
        "objet JSON conforme au schema fourni."
    )


def build_party_nomination_user_prompt(
    contested: dict[int, list[Citizen]], parties_by_id: dict[int, Party], support: dict[int, float]
) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as build_user_prompt/build_candidacy_user_prompt.
    `support` is precomputed once by the caller against the full population
    (decide_party_nominations), same discipline as decide_candidacies'
    `support` -- never recomputed here. `platform_distance` reuses
    assign_party_affiliation's unweighted math.dist convention (simple_rules.py),
    not the voter-tolerance-specific weighted_distance."""
    party_blocks = [
        {
            "party_id": party_id,
            "candidates": [
                {
                    "position": i,
                    "cid": c.citizen_id,
                    "ambition_score": round(c.ambition_score, 4),
                    "perceived_support": round(support[c.citizen_id], 4),
                    "platform_distance": round(math.dist(c.issue_positions, parties_by_id[party_id].platform), 4),
                }
                for i, c in enumerate(sorted_candidates(members), start=1)
            ],
        }
        for party_id, members in contested.items()
    ]
    return json.dumps({"parties": party_blocks}, sort_keys=True, separators=(",", ":"))


def resolve_party_nomination_cid(decision: PartyNominationDecision, members: Sequence[Citizen]) -> int:
    """Translates decision.winner_position (1-indexed position into
    `members`, sorted by citizen_id) back to a real cid -- same purpose as
    resolve_ranking_cids, scoped to one contested party's own candidate
    sub-list instead of the full candidate list."""
    ordered = sorted_candidates(members)
    return ordered[decision.winner_position - 1].citizen_id


def decide_party_nominations(
    citizens: Sequence[Citizen],
    parties: Sequence[Party],
    declared_cids: set[int],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> PartyNominationBatchOutcome:
    """v2 increment 3's replacement for select_party_nominee_from_declared's
    deterministic tiebreak, contested parties only (design doc §2.3, dt=4).
    Pure aside from the injected client -- no journal writes here, matching
    cast_votes/decide_candidacies's convention.

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE: those guard
    *citizen* batches (tens to hundreds per call); this batches *contested
    parties* (a handful at most, `parties.initial_count` in the shipped
    config is 5, and most ticks have zero). One call for the whole tick,
    skipped entirely if no party is contested -- calling the client with an
    empty batch would violate PartyNominationBatch's own min_length=1 and is
    wasted work regardless.

    Calls the client with think=False, same as decide_candidacies. A live
    run initially tried think=True (the hypothesis was that this call's
    small batches -- a handful of parties, not tens of citizens -- would
    dodge candidacy_considered's reasoning-budget bug even without the
    flag). That hypothesis was wrong: think=True reliably hit the identical
    failure (finish_reason='length', zero visible content) regardless of
    batch size -- the bug tracks the *subjective, comparative-judgment*
    prompt shape ("which of these is best"), not batch size. See
    ollama_structured_output_results.md's Finding E."""
    _check_supported(config)

    parties_by_id = {party.party_id: party for party in parties}
    contested: dict[int, list[Citizen]] = {}
    for party in sorted(parties, key=lambda p: p.party_id):
        members = [c for c in citizens if c.party_affiliation == party.party_id and c.citizen_id in declared_cids]
        if len(members) >= 2:
            contested[party.party_id] = members

    if not contested:
        return PartyNominationBatchOutcome(decisions=[], winners={})

    all_contenders = [c for members in contested.values() for c in members]
    support = {c.citizen_id: sympathizer_ratio(c, list(citizens)) for c in all_contenders}

    expected_party_ids = list(contested.keys())
    decisions = _complete_and_decode_with_replay(
        client,
        system_prompt=build_party_nomination_system_prompt(contested),
        user_prompt=build_party_nomination_user_prompt(contested, parties_by_id, support),
        json_schema=PARTY_NOMINATION_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(contested)),
        think=False,
        decode=lambda raw: decode_party_nomination_batch(raw, expected_party_ids),
        replays=config.llm.max_batch_replays,
        decision_type="party_nomination_choice",
    )
    winners = {decision.party_id: resolve_party_nomination_cid(decision, contested[decision.party_id])
               for decision in decisions}

    return PartyNominationBatchOutcome(decisions=decisions, winners=winners)


@dataclass(frozen=True)
class PositioningBatchOutcome:
    decisions: list[PositioningDecision]
    platforms: dict[int, tuple[float, ...]]
    """cid -> resolved new pledged_platform (sincere position with validated
    shifts applied), ready to assign directly -- only this function has the
    sincere-position context needed to resolve a decision's sparse shifts
    into a full position tuple, mirroring how cast_votes resolves positions
    into ballots internally rather than exposing raw wire values."""


def apply_shifts(sincere: tuple[float, ...], shifts: Sequence[PositionShift]) -> tuple[float, ...]:
    """Applies a sparse set of validated shifts to a sincere position,
    clamping each shifted dimension to [0, 1] (positions must stay valid);
    dimensions with no shift are untouched. Pure -- bounds are already
    enforced by validate_positioning_decision before this is called.

    KNOWN OBSERVABILITY GAP (found 2026-08-22, v6b Lot 4's acceptance
    investigation) -- RESOLVED one level up, not here: the clamp is still
    silent AT THIS FUNCTION (no return value, no log, no journal event when
    a shift's target falls outside [0,1]) -- that stays true by design, see
    clamped_dimensions immediately below. What changed: every caller of
    apply_shifts (dt=5 campaign_positioning, dt=6 representative_response,
    dt=11 chamber_deliberation, all in run_polity_simulation.py) now also
    calls clamped_dimensions(base, shifts, result) right after, and journals
    a clamped_at_bound event whenever it's non-empty -- so a caller
    downstream of many accumulated shifts can now tell "the model stopped
    pushing" from "the model kept pushing but the position had already
    saturated" directly from run data, without replaying the full shift
    history by hand the way v6b Lot 4 had to (that manual, unclamped
    reconstruction ran x2.8-x3.6 higher than the reported, clamped value at
    the same ticks -- THEORY.md §10.9-§10.10). apply_shifts itself is
    unchanged: it was never the right place to journal from (pure, no
    Journal import in this module) -- the signal lives in the sibling
    function below and its three callers, not in a changed return value
    here."""
    positions = list(sincere)
    for shift in shifts:
        positions[shift.dimension] = min(1.0, max(0.0, positions[shift.dimension] + shift.delta))
    return tuple(positions)


def clamped_dimensions(
    base: tuple[float, ...], shifts: Sequence[PositionShift], result: tuple[float, ...],
) -> frozenset[int]:
    """Which dimensions apply_shifts's own [0,1] clamp actually altered from
    a naive base+delta target -- the fix for apply_shifts's own KNOWN
    OBSERVABILITY GAP docstring note. Deliberately takes `result` as a
    parameter rather than calling apply_shifts(base, shifts) itself: every
    caller already has the exact resolved position apply_shifts produced
    (PositioningBatchOutcome.platforms / Response.../ChamberBatchOutcome.
    positions), so comparing against THAT value is the single source of
    truth -- recomputing independently would risk this function's own
    [0,1] bounds silently drifting from apply_shifts's real ones, and costs
    a second full pass for nothing this function needs. Never itself calls
    apply_shifts; apply_shifts itself is completely unchanged by this
    function's existence. A shift landing EXACTLY on a bound (raw target
    == 0.0 or == 1.0) is NOT clamped -- only a target that would have
    exceeded [0,1] counts, i.e. result != base + delta, never result == 0.0
    or result == 1.0 alone."""
    return frozenset(
        shift.dimension for shift in shifts
        if result[shift.dimension] != base[shift.dimension] + shift.delta
    )


def validate_positioning_decision(decision: PositioningDecision, config: PolityConfig) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's config: the real shift-count and per-shift
    delta-magnitude caps (campaign.max_positioning_shifts/max_positioning_delta
    -- tighter than PositioningDecision's own structural ceiling), and that
    a targeted dimension actually exists in this run's issue space."""
    if len(decision.shifts) > config.campaign.max_positioning_shifts:
        raise LlmResponseError(
            f"decision for cid={decision.cid} shifts {len(decision.shifts)} dimension(s), "
            f"exceeding campaign.max_positioning_shifts={config.campaign.max_positioning_shifts}"
        )
    issue_count = config.citizens.issue_count
    for shift in decision.shifts:
        if shift.dimension >= issue_count:
            raise LlmResponseError(
                f"decision for cid={decision.cid} targets dimension {shift.dimension}, "
                f"out of range for issue_count={issue_count}"
            )
        if abs(shift.delta) > config.campaign.max_positioning_delta:
            raise LlmResponseError(
                f"decision for cid={decision.cid} shifts dimension {shift.dimension} by "
                f"{shift.delta}, exceeding campaign.max_positioning_delta="
                f"{config.campaign.max_positioning_delta}"
            )


def build_positioning_system_prompt(nominees: Sequence[Citizen], config: PolityConfig) -> str:
    """Same "enumerate the full expected cid list verbatim + self-check"
    discipline as every prior decision type (Finding B precedent). Also
    states the ACTUAL numeric bounds (campaign.max_positioning_shifts/
    max_positioning_delta), not just the word "borne" -- the JSON schema
    itself only enforces a loose structural ceiling (max 5 shifts, delta in
    [-1,1]; see PositionShift/PositioningDecision), since the real,
    tighter, config-driven bound can't be baked into a schema defined at
    import time. Without stating the real numbers here, the model has no
    way to know what it's actually being validated against in
    validate_positioning_decision -- an omission that would make rejections
    common rather than a validated guardrail against rare cases."""
    cid_list = ",".join(str(n.citizen_id) for n in nominees)
    return (
        "Tu es un moteur de simulation. Pour chaque candidat nomme, decide "
        "s'il ajuste sa position affichee par rapport a sa position "
        "sincere (strategie de campagne), a partir de sa propre position, "
        "son ambition, la plateforme de son parti, les positions des "
        "autres candidats de ce scrutin, et la position moyenne de "
        "l'electorat.\nChaque ajustement (shifts) cible une dimension "
        "precise (0-indexee) avec un delta signe ; une liste vide signifie "
        "que le candidat reste sur sa position sincere.\nCONTRAINTES "
        f"STRICTES : au plus {config.campaign.max_positioning_shifts} "
        f"ajustements par decision, chaque delta strictement compris entre "
        f"-{config.campaign.max_positioning_delta} et "
        f"{config.campaign.max_positioning_delta} inclus. Toute decision "
        "hors de ces bornes sera rejetee.\n"
        f"Motifs valides (code court obligatoire) :\n{CAMPAIGN_MOTIF_PROMPT_TABLE}\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(nominees)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_positioning_user_prompt(
    nominees: Sequence[Citizen],
    parties_by_id: dict[int, Party],
    electorate_mean: tuple[float, ...],
) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as every prior prompt builder. `nominees` is
    expected to already be in the canonical order the caller (decide_
    campaign_positioning) enforces (sorted by citizen_id) -- this function
    doesn't re-sort, since the system prompt's verbatim expected-cid list
    must describe the exact same order shown here, not a second one. `rivals`
    is only the OTHER dominant nominees standing this tick -- rupture
    candidates (a separate, rare, deliberately unstrategized path) are not
    part of the rival-context signal, consistent with this function never
    being called for them. `electorate_mean` is computed once by the
    caller against the full population, not per-nominee."""
    nominee_blocks = []
    for nominee in nominees:
        party = parties_by_id.get(nominee.party_affiliation) if nominee.party_affiliation is not None else None
        rivals = [
            {"cid": other.citizen_id, "position": [round(x, 4) for x in other.issue_positions]}
            for other in nominees
            if other.citizen_id != nominee.citizen_id
        ]
        nominee_blocks.append(
            {
                "cid": nominee.citizen_id,
                "position": [round(x, 4) for x in nominee.issue_positions],
                "priorities": [round(x, 4) for x in nominee.issue_priorities],
                "ambition_score": round(nominee.ambition_score, 4),
                "party_platform": [round(x, 4) for x in party.platform] if party is not None else None,
                "rivals": rivals,
            }
        )
    return json.dumps(
        {"nominees": nominee_blocks, "electorate_mean": [round(x, 4) for x in electorate_mean]},
        sort_keys=True,
        separators=(",", ":"),
    )


def decide_campaign_positioning(
    nominees: Sequence[Citizen],
    citizens: Sequence[Citizen],
    parties_by_id: dict[int, Party],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> PositioningBatchOutcome:
    """v2 increment 4's replacement for declare_candidacy's sincere-platform
    pin, dominant nominees only (see this module's docstring for what stays
    out of scope). Pure aside from the injected client -- no journal writes
    here, matching every prior decide_* function's convention.

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE, same
    reasoning as decide_party_nominations: this batches this tick's
    *nominees* (a handful, `parties.initial_count` in the shipped config),
    not citizens.

    Calls the client with think=True -- corrected from the original think=False
    guess (v2 increment 4) during the v4 Lot 8 acceptance run's own live
    verification, once that guess turned out wrong: think=False produced a
    100% reproducible degenerate batch (one nominee duplicated, the rest
    dropped, byte-identical across 9 attempts at temperature=0, including a
    reworded system prompt) for a real acceptance-run electorate. think=True
    resolved it cleanly (5/5 correct batches once given enough token budget --
    see the +_POSITIONING_THINK_TOKEN_ALLOWANCE below). This is NOT the same
    bug decide_party_nominations's docstring warns about (finish_reason='length'
    regardless of batch size, a comparative-judgment shape that reasoning
    cannot rescue) -- here the reasoning budget was simply too tight, and once
    widened the reasoning content itself resolved the alignment failure. The
    two decision types share a superficial "comparative/strategic judgment"
    description but not the same failure mode; do not assume this result
    transfers back to decide_party_nominations without its own live check."""
    _check_supported(config)

    if not nominees:
        return PositioningBatchOutcome(decisions=[], platforms={})

    # Sorted once, here, so system prompt / user prompt / expected_cids all
    # agree on the same order regardless of the caller's (party-iteration)
    # order -- never rely on an incidental insertion order (D-5 precedent).
    nominees = sorted(nominees, key=lambda n: n.citizen_id)
    electorate_mean = tuple(float(x) for x in np.mean([c.issue_positions for c in citizens], axis=0))
    expected_cids = [n.citizen_id for n in nominees]
    decisions = _complete_and_decode_with_replay(
        client,
        system_prompt=build_positioning_system_prompt(nominees, config),
        user_prompt=build_positioning_user_prompt(nominees, parties_by_id, electorate_mean),
        json_schema=POSITIONING_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(nominees)) + _POSITIONING_THINK_TOKEN_ALLOWANCE,
        think=True,
        decode=lambda raw: decode_positioning_batch(raw, expected_cids),
        replays=config.llm.max_batch_replays,
        decision_type="campaign_positioning",
    )

    nominees_by_id = {n.citizen_id: n for n in nominees}
    platforms: dict[int, tuple[float, ...]] = {}
    for decision in decisions:
        validate_positioning_decision(decision, config)
        platforms[decision.cid] = apply_shifts(nominees_by_id[decision.cid].issue_positions, decision.shifts)

    return PositioningBatchOutcome(decisions=decisions, platforms=platforms)


@dataclass(frozen=True)
class ResponseContext:
    """§3.6.5's `ctx` block, frozen at the moment the caller reads it -- the
    structural half of §7bis.7's one-tick lag (v4 Lot 6). `street` is
    street_pressure as of the END of the previous tick; the caller
    (run_polity_simulation._run_accountability_phase, via
    _run_representative_responses) captures it before this tick's step-2/3
    mutations, and this module never touches the live field -- it only ever
    reads what it's handed here. A None field means "this polity does not
    track that quantity" (legitimacy disabled, street pressure disabled or
    invisible, no term end) -- never 0.0, which would be a false claim
    about the polity's state (§3.6.6's own neighbors_acting=null
    precedent)."""

    cid: int
    legitimacy: float | None
    mandate_dev: float
    street: float | None
    lame_duck: bool
    ticks_left: int | None

    def to_payload(self) -> dict[str, float | int | None]:
        """§3.6.5's exact key names, rounded like every other prompt
        builder. Used by BOTH build_response_user_prompt and the journal
        write (run_polity_simulation.py), so the ctx an analyst reads is
        provably the ctx the model saw -- not a reconstruction that can
        drift from it."""
        return {
            "L": round(self.legitimacy, 4) if self.legitimacy is not None else None,
            "mandate_dev": round(self.mandate_dev, 4),
            "street": round(self.street, 4) if self.street is not None else None,
            "lame_duck": int(self.lame_duck),
            "ticks_left": self.ticks_left,
        }


@dataclass(frozen=True)
class ResponseBatchOutcome:
    decisions: list[ResponseDecision]
    positions: dict[int, tuple[float, ...]]
    """cid -> resolved new revealed_position (the holder's CURRENT
    revealed_position with validated shifts applied, so drift accumulates
    across ticks -- see validate_response_decision/apply_shifts). Unlike
    PositioningBatchOutcome's `platforms`, pledged_platform is never
    resolved here: the promise is immutable for the term, which is the
    only reason mandate_deviation means anything (§7bis.5)."""


def validate_response_decision(decision: ResponseDecision, config: PolityConfig) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's config: the real shift-count and per-shift
    delta-magnitude caps -- mandate.max_response_shifts/max_response_delta
    (v4 Lot 1), deliberately NOT campaign.max_positioning_shifts/
    max_positioning_delta -- mid-term mandate drift and campaign-time
    strategy must stay analytically separable (MandateConfig's own
    docstring) -- and that a targeted dimension actually exists in this
    run's issue space. Structurally identical to
    validate_positioning_decision, reading a different config section."""
    if len(decision.shifts) > config.mandate.max_response_shifts:
        raise LlmResponseError(
            f"decision for cid={decision.cid} shifts {len(decision.shifts)} dimension(s), "
            f"exceeding mandate.max_response_shifts={config.mandate.max_response_shifts}"
        )
    issue_count = config.citizens.issue_count
    for shift in decision.shifts:
        if shift.dimension >= issue_count:
            raise LlmResponseError(
                f"decision for cid={decision.cid} targets dimension {shift.dimension}, "
                f"out of range for issue_count={issue_count}"
            )
        if abs(shift.delta) > config.mandate.max_response_delta:
            raise LlmResponseError(
                f"decision for cid={decision.cid} shifts dimension {shift.dimension} by "
                f"{shift.delta}, exceeding mandate.max_response_delta="
                f"{config.mandate.max_response_delta}"
            )


def build_response_system_prompt(holders: Sequence[Citizen], config: PolityConfig) -> str:
    """Same "enumerate the full expected cid list verbatim + self-check"
    discipline as every prior decision type (Finding B precedent). States
    the ACTUAL numeric bounds (mandate.max_response_shifts/
    max_response_delta), not just the schema's loose structural ceiling --
    same reasoning as build_positioning_system_prompt. Also states the
    stance<->shifts and stance<->motif pairing rules explicitly: these are
    cross-field rules constrained decoding cannot enforce on its own (the
    prompt is the only prevention; llm_schemas.py's model validators are
    the guardrail behind it), and explains ctx's scale for each field --
    L in [0,1], mandate_dev a weighted distance from the pledge, street an
    UNBOUNDED mobilization accumulator (0=none, >=1=sustained, deliberately
    not normalized -- écart(t) consumes the same unnormalized number),
    lame_duck 0/1, ticks_left ticks to the next presidential election, and
    that a null ctx field means "not tracked in this polity", never
    zero."""
    cid_list = ",".join(str(h.citizen_id) for h in holders)
    return (
        "Tu es un moteur de simulation. Pour chaque elu recu "
        "(representative_response), decide sa reaction a la pression "
        "citoyenne et institutionnelle percue, a partir de sa promesse "
        "electorale, de sa position actuelle, et du contexte ctx.\n"
        "ctx.L : legitimite actuelle dans [0,1], null si non suivie.\n"
        "ctx.mandate_dev : ecart pondere entre la promesse et la position "
        "actuelle, deja accumule.\n"
        "ctx.street : pression de rue, un accumulateur NON BORNE (0 = "
        "aucune mobilisation, >=1 = mobilisation soutenue), null si non "
        "suivie ou non visible.\n"
        "ctx.lame_duck : 1 si l'elu a atteint la limite de mandats, "
        "sinon 0.\nctx.ticks_left : nombre de ticks avant la prochaine "
        "election presidentielle, null si aucune election prevue.\n"
        "Un champ ctx a null signifie que cette grandeur n'est pas suivie "
        "dans cette simulation, jamais qu'elle vaut zero.\n"
        f"stance : {STANCE_PROMPT_TABLE}\n"
        "shifts : au plus "
        f"{config.mandate.max_response_shifts} ajustements de position, "
        f"chaque delta strictement compris entre "
        f"-{config.mandate.max_response_delta} et "
        f"{config.mandate.max_response_delta} inclus. stance=1 "
        "(concession) exige au moins un ajustement ; stance=3 (silence) "
        "exige une liste vide.\n"
        f"Motifs valides (code court obligatoire) :\n{RESPONSE_MOTIF_PROMPT_TABLE}\n"
        "REGLE DE COHERENCE stance/motif obligatoire : stance=1 (concession) "
        "exige motif 301, 302 ou 303 ; stance=2 (defiance) exige motif "
        "307 ; stance=3 (silence) exige motif 308 ; stance=4 "
        "(counter_mobilization) exige motif 309. Toute decision hors de "
        "ces regles sera rejetee.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(holders)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_response_user_prompt(holders: Sequence[Citizen], contexts: Mapping[int, ResponseContext]) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as every prior prompt builder. `holders` is
    expected to already be in the canonical order the caller (decide_
    representative_response) enforces (sorted by citizen_id) -- this
    function doesn't re-sort, since the system prompt's verbatim
    expected-cid list must describe the exact same order shown here.
    Top-level key "holders" -- a sixth decision type needs a sixth
    unambiguous key so a fake/stub client can dispatch on it unambiguously
    (see _FakeLlmClient, test_polity_run_simulation.py)."""
    holder_blocks = []
    for holder in holders:
        assert holder.pledged_platform is not None and holder.revealed_position is not None
        holder_blocks.append(
            {
                "cid": holder.citizen_id,
                "office": 1,  # Office.PRESIDENT, §3.7.1
                "pledged_platform": [round(x, 4) for x in holder.pledged_platform],
                "revealed_position": [round(x, 4) for x in holder.revealed_position],
                "priorities": [round(x, 4) for x in holder.issue_priorities],
                "ctx": contexts[holder.citizen_id].to_payload(),
            }
        )
    return json.dumps({"holders": holder_blocks}, sort_keys=True, separators=(",", ":"))


def decide_representative_response(
    holders: Sequence[Citizen],
    contexts: Mapping[int, ResponseContext],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> ResponseBatchOutcome:
    """v4 Lot 6's dt=6 replacement for the status-quo deterministic fallback
    (see run_polity_simulation._run_representative_responses's own
    docstring for why there is no simple_rules.py baseline function to
    replace -- "no delta, stance=silence" is already true by construction
    without this module ever running).

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE, same
    reasoning as decide_party_nominations/decide_campaign_positioning:
    this batches this tick's sitting OFFICEHOLDERS (0-or-1 today, president
    only -- Office.DEPUTY is never assigned), not citizens.

    Calls the client with think=False -- no longer a guess for this
    decision type: scripts/lot6_batch_reliability_results.md measured
    16/16 clean responses for this exact schema at batch sizes 1/3/5/10
    through Ollama's native /api/chat think=false path (with its own
    documented caveat: not a guarantee, see that file)."""
    _check_supported(config)

    if not holders:
        return ResponseBatchOutcome(decisions=[], positions={})

    # Sorted once, here, so system prompt / user prompt / expected_cids all
    # agree on the same order regardless of the caller's order -- never
    # rely on an incidental insertion order (D-5 precedent).
    holders = sorted(holders, key=lambda h: h.citizen_id)
    expected_cids = [h.citizen_id for h in holders]
    decisions = _complete_and_decode_with_replay(
        client,
        system_prompt=build_response_system_prompt(holders, config),
        user_prompt=build_response_user_prompt(holders, contexts),
        json_schema=RESPONSE_JSON_SCHEMA,
        max_tokens=compute_max_tokens(len(holders)),
        think=False,
        decode=lambda raw: decode_response_batch(raw, expected_cids),
        replays=config.llm.max_batch_replays,
        decision_type="representative_response",
    )

    holders_by_id = {h.citizen_id: h for h in holders}
    positions: dict[int, tuple[float, ...]] = {}
    for decision in decisions:
        validate_response_decision(decision, config)
        holder = holders_by_id[decision.cid]
        assert holder.revealed_position is not None  # guaranteed by the caller's own filter
        positions[decision.cid] = apply_shifts(holder.revealed_position, decision.shifts)

    return ResponseBatchOutcome(decisions=decisions, positions=positions)


@dataclass(frozen=True)
class PressureContext:
    """§3.6.6's `ctx` block plus the institutional facts §7bis.3 point 2/3
    require, frozen before any of this tick's step-2 mutations run (v4
    Lot 7).

    `neighbors_acting` is `None` whenever `social_graph.enabled` is false
    (v4/v5's own atomized regime, §7bis.9e/f, still the shipped default) --
    the same "null means not tracked, never zero" rule every other optional
    ctx field in this project follows. From v6 Lot 3, when the graph is on,
    it carries a real `[0,1]` fraction (accountability.neighbors_acting,
    computed once per holder and threaded straight through by the caller)
    regardless of whether `awakening.context_modulation.neighbors_acting`
    additionally gates the awakening threshold itself -- v6 Lot 1's own
    cross-field rule keeps that a real, separate arm (the graph can feed
    this ctx without also modulating who gets consulted). `street_pressure`
    is absent BY CONSTRUCTION and not by omission -- §7bis.9f's atomized
    regime requires each citizen to decide alone; dt=6's ResponseContext.
    street exists for the exact opposite reason (§7bis.4b's "double rôle":
    the representative is meant to see the aggregate, the citizen is not).
    `signed_ratio`/signature counts are excluded on the same principle: an
    institutional object's existence is public record (Lot 5), its level of
    support is an aggregate of what the crowd just did."""

    cid: int
    target: int
    self_gap: float
    mandate_dev: float
    ticks_to_election: int | None
    available: tuple[int, ...]
    petition_open: bool
    petition_expires_at_tick: int | None
    already_signed: bool
    neighbors_acting: float | None = None

    def to_payload(self) -> dict[str, float | int | None]:
        """§3.6.6's exact four ctx keys, rounded like every other prompt
        builder. Used by BOTH build_pressure_user_prompt and the journal
        write, so the ctx an analyst reads is provably the ctx the model
        saw."""
        return {
            "self_gap": round(self.self_gap, 4),
            "mandate_dev": round(self.mandate_dev, 4),
            "neighbors_acting": round(self.neighbors_acting, 4) if self.neighbors_acting is not None else None,
            "ticks_to_election": self.ticks_to_election,
        }


@dataclass(frozen=True)
class PressureBatchOutcome:
    decisions: list[PressureDecision]
    """Decisions only -- unlike PositioningBatchOutcome/ResponseBatchOutcome
    there is nothing to resolve here (no shifts to apply to a position);
    the CALLER resolves each act against LIVE petition state via
    accountability.applicable_pressure_act, because only the caller owns
    mutation. Same one-field shape as CandidacyBatchOutcome."""


def menu_acts(menu: PressureMenuConfig) -> tuple[int, ...]:
    """§3.6.6: {0,4} always legal regardless of menu; +{1,2} iff
    petition_enabled; +{3} iff mobilization_enabled. The single source of
    truth for both build_pressure_system_prompt and
    validate_pressure_decision, so the stated menu and the enforced one can
    never drift apart."""
    acts = [0, 4]
    if menu.petition_enabled:
        acts += [1, 2]
    if menu.mobilization_enabled:
        acts.append(3)
    return tuple(sorted(acts))


def validate_pressure_decision(decision: PressureDecision, context: PressureContext, config: PolityConfig) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's config: that the decision targets the
    officeholder it was asked about, and §3.6.6's hard constraint --
    `act` must be a member of the ACTIVE pressure_menu (menu_acts), the
    ONLY batch-rejecting legality check this lot has. Deliberately does
    NOT check `decision.act in context.available`: live petition state
    (can this citizen actually sign/launch right now) is resolved by
    accountability.applicable_pressure_act at application time, never
    validated here -- see this lot's own judgment call on why a
    state-stale act must not abort the whole batch."""
    if decision.target != context.target:
        raise LlmResponseError(
            f"decision for cid={decision.cid} targets {decision.target}, expected {context.target}"
        )
    legal = menu_acts(config.pressure_menu)
    if decision.act not in legal:
        raise LlmResponseError(
            f"decision for cid={decision.cid} chose act={decision.act}, outside the active "
            f"pressure_menu {legal}"
        )


def build_pressure_system_prompt(consulted: Sequence[Citizen], config: PolityConfig) -> str:
    """Same "enumerate the full expected cid list verbatim + self-check"
    discipline as every prior decision type (Finding B precedent). States
    the ACTIVE MENU as a hard constraint, twice (before and after the
    reference table) and restricted to only the LEGAL entries -- an
    earlier version of this prompt showed the full 5-member
    PRESSURE_ACT_PROMPT_TABLE unconditionally next to the legal subset and
    a live check found the model chose an out-of-menu act even for a
    single-citizen batch under electoral_only (act=2 with only {0,4}
    legal) -- see scripts/lot6_batch_reliability_results.md's "Lot 7
    confirmatory pass". Filtering the table to only the legal rows and
    restating the constraint removed the ambiguity of "here is the full
    catalogue, but only some of it applies right now". Explains ctx:
    self_gap is the citizen's own weighted distance to what the
    officeholder currently delivers; mandate_dev is that officeholder's
    OWN distance from their promise (information, not the citizen's own
    state); ticks_to_election is ticks to the next presidential election.
    States explicitly that 0 (inaction) and 4 (deferred to the ballot) are
    legitimate, journaled outcomes, not failures (§7bis.3).

    ctx.neighbors_acting's own explanation branches on
    config.social_graph.enabled (v6 Lot 3): when the graph is off (v4/v5's
    own atomized regime, still the shipped default), the sentence stays
    exactly what it always was -- "toujours null... jamais zero" -- so this
    is a REGRESSION PIN, not just documentation. When the graph is on, a
    second sentence explains the real [0,1] fraction and appends one line
    of act<->motif pairing guidance for 306 FOLLOWING_NEIGHBORS
    (unenforced -- see PressureDecision's own docstring for why)."""
    cid_list = ",".join(str(c.citizen_id) for c in consulted)
    legal = menu_acts(config.pressure_menu)
    legal_table = "\n".join(
        line for line in PRESSURE_ACT_PROMPT_TABLE.splitlines() if int(line.split(" = ")[0]) in legal
    )
    if config.social_graph.enabled:
        neighbors_acting_line = (
            "ctx.neighbors_acting : proportion (0 a 1) de mon voisinage "
            "social qui a deja mobilise contre cette meme cible, au tick "
            "precedent. Le motif 306 (FOLLOWING_NEIGHBORS) est approprie "
            "pour un act 1, 2 ou 3 motive par ce signal -- jamais pour "
            "act 0 ou 4.\n"
        )
    else:
        neighbors_acting_line = (
            "ctx.neighbors_acting : toujours null dans cette simulation (aucun "
            "graphe social suivi), jamais zero.\n"
        )
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
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(consulted)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois, et chaque "
        f"act doit appartenir a {list(legal)}.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_pressure_user_prompt(consulted: Sequence[Citizen], contexts: Mapping[int, PressureContext]) -> str:
    """Canonical JSON (sort_keys, compact separators, floats rounded to 4),
    same reproducibility discipline as every prior prompt builder.
    Top-level key "consulted" -- the seventh dispatch key
    (citizens/parties/nominees/responders/holders/voters are taken; note
    _FakeLlmClient tests `"citizens" in payload` FIRST, so reusing that key
    would silently answer the candidacy schema instead). Per citizen: cid,
    target, ctx=contexts[cid].to_payload(), the frozen `available` act
    list, and the petition's institutional (never aggregate) state --
    open/expires_at_tick/already_signed, but no signatures/signed_ratio
    (§7bis.9f, see PressureContext). Deliberately NO 20-dim position
    vectors per citizen -- at up to 25 citizens per chunk that would
    multiply the prompt far beyond what self_gap/mandate_dev already
    encode. Does not re-sort -- the caller owns the canonical order the
    system prompt enumerates."""
    citizen_blocks = []
    for citizen in consulted:
        context = contexts[citizen.citizen_id]
        citizen_blocks.append(
            {
                "cid": citizen.citizen_id,
                "target": context.target,
                "ctx": context.to_payload(),
                "available": list(context.available),
                "petition": {
                    "open": context.petition_open,
                    "expires_at_tick": context.petition_expires_at_tick,
                    "already_signed": context.already_signed,
                },
            }
        )
    return json.dumps({"consulted": citizen_blocks}, sort_keys=True, separators=(",", ":"))


def decide_pressure_actions(
    consulted: Sequence[Citizen],
    contexts: Mapping[int, PressureContext],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> PressureBatchOutcome:
    """v4 Lot 7's dt=10 replacement for deterministic_pressure_action
    (simple_rules.py), which stays exactly as it is as the permanent
    §11.4 baseline.

    Unlike every other decide_* function, this one CHUNKS: it is the first
    decision type since vote_cast to batch CITIZENS rather than a handful
    of officeholders/nominees/parties, and the consulted cohort can be
    dozens of citizens. Chunking is NOT a consultation cap (§15bis.1,
    TRANCHÉ) -- every consulted citizen is still asked, every tick, without
    exception; chunking only changes the number of HTTP requests. Every
    chunk is decided here, in full, before the caller (run_polity_
    simulation._run_accountability_phase) applies any effect -- so a chunk
    boundary can never become a "wave" boundary that lets petition state
    go stale mid-decision.

    `min_batch_size=1` (not the MIN_SAFE_BATCH_SIZE default): justified by
    scripts/lot6_batch_reliability_results.md's measured 1/3/5/10 clean
    pass on this schema shape through the native think=False path --
    direct evidence in the region MIN_SAFE_BATCH_SIZE (measured on
    vote_cast's /v1 think=True shape) forbids.

    Calls the client with think=False -- proven for this exact schema
    shape twice now (the Lot 6 pre-flight spike and this lot's own
    confirmatory pass against the real schema, scripts/
    lot6_batch_reliability_results.md)."""
    _check_supported(config)

    if not consulted:
        return PressureBatchOutcome(decisions=[])

    # Sorted once, here, so system prompt / user prompt / expected_cids all
    # agree on the same order regardless of the caller's order -- never
    # rely on an incidental insertion order (D-5 precedent).
    consulted = sorted(consulted, key=lambda c: c.citizen_id)
    decisions: list[PressureDecision] = []
    for chunk in chunk_voters(consulted, config.llm.max_batch_size, min_batch_size=1):
        expected_cids = [c.citizen_id for c in chunk]
        chunk_decisions = _complete_and_decode_with_replay(
            client,
            system_prompt=build_pressure_system_prompt(chunk, config),
            user_prompt=build_pressure_user_prompt(chunk, contexts),
            json_schema=PRESSURE_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)),
            think=False,
            decode=lambda raw: decode_pressure_batch(raw, expected_cids),
            replays=config.llm.max_batch_replays,
            decision_type="pressure_action",
        )
        for decision in chunk_decisions:
            validate_pressure_decision(decision, contexts[decision.cid], config)
        decisions.extend(chunk_decisions)

    return PressureBatchOutcome(decisions=decisions)


@dataclass(frozen=True)
class ReactionContext:
    """dt=8's per-citizen ctx (v5 Lot 4, §8) -- deliberately ONE field, not
    an earlier roadmap-level sketch's {magnitude, self_gap, mandate_dev}
    shape (see ReactionDecision's own docstring for why that shape doesn't
    survive contact with vacancy and with ECONOMIC_SHOCK's always-null
    target). `event_salience` is the citizen's own CURRENT, PRE-UPDATE
    residual awareness -- the exact quantity this decision revises --
    frozen at the moment the caller reads it, before decide_reaction_to_event
    runs and before the caller's own per-citizen loop starts mutating it.
    Never None: every citizen carries event_salience unconditionally since
    v5 Lot 3 (default 0.0), so unlike ResponseContext/PressureContext's
    optional fields there is no "not tracked" case to represent here."""

    cid: int
    event_salience: float

    def to_payload(self) -> dict[str, float]:
        """Used by BOTH build_reaction_user_prompt and the journal write,
        so the ctx an analyst reads is provably the ctx the model saw."""
        return {"event_salience": round(self.event_salience, 4)}


@dataclass(frozen=True)
class ReactionBatchOutcome:
    decisions: list[ReactionDecision]
    """Decisions only -- same one-field shape as CandidacyBatchOutcome/
    PressureBatchOutcome. The CALLER applies each salience_delta via
    accountability.update_event_salience, exactly as it already applies
    deterministic_reaction_to_event's own flat delta (v5 Lot 3) -- this
    lot only changes WHO computes the delta, never how it's applied."""


_EVENT_TYPE_GROUNDING_MOTIF: dict[EventType, ReactionMotif] = {
    EventType.SCANDAL: ReactionMotif.SCANDAL_TRUST_EROSION,
    EventType.ECONOMIC_SHOCK: ReactionMotif.ECONOMIC_SHOCK_REACTION,
}


def validate_reaction_decision(decision: ReactionDecision, event_type: EventType, config: PolityConfig) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without knowing which event_type this call was for: the real
    events.max_reaction_delta bound (the schema only enforces the loose
    [0,1] structural ceiling), and that `motif` is either THIS call's own
    grounding motif or 403 (EVENT_PERSONALLY_IRRELEVANT) -- never the
    OTHER event_type's grounding code, which Literal[401,402,403] alone
    can't rule out since one schema serves both calls."""
    if decision.salience_delta > config.events.max_reaction_delta:
        raise LlmResponseError(
            f"decision for cid={decision.cid} salience_delta={decision.salience_delta} exceeds "
            f"events.max_reaction_delta={config.events.max_reaction_delta}"
        )
    grounding_motif = _EVENT_TYPE_GROUNDING_MOTIF[event_type]
    if decision.motif not in (int(grounding_motif), int(ReactionMotif.EVENT_PERSONALLY_IRRELEVANT)):
        raise LlmResponseError(
            f"decision for cid={decision.cid} motif={decision.motif} is not valid for "
            f"event_type={event_type.name} (expected {int(grounding_motif)} or "
            f"{int(ReactionMotif.EVENT_PERSONALLY_IRRELEVANT)})"
        )


def build_reaction_system_prompt(citizens: Sequence[Citizen], event_type: EventType, config: PolityConfig) -> str:
    """Same "enumerate the full expected cid list verbatim + self-check"
    discipline as every prior decision type (Finding B precedent). Filters
    REACTION_MOTIF_PROMPT_TABLE to exactly {this call's grounding motif,
    403} -- dt=10's own live-finding fix (build_pressure_system_prompt's
    docstring), applied proactively rather than waiting for a live failure
    to force it: showing the model a motif table containing the OTHER
    event_type's own grounding code would invite exactly the kind of
    out-of-menu-but-schema-legal confusion Lot 7 found live. States the
    real events.max_reaction_delta bound explicitly (the schema's own
    [0,1] ceiling is only structural) and the salience_delta==0<=>motif==403
    rule. Explains ctx.event_salience: the citizen's own already-accumulated
    awareness of past events, 0.0 if untouched so far."""
    cid_list = ",".join(str(c.citizen_id) for c in citizens)
    grounding_motif = _EVENT_TYPE_GROUNDING_MOTIF[event_type]
    legal_motifs = (int(grounding_motif), int(ReactionMotif.EVENT_PERSONALLY_IRRELEVANT))
    legal_table = "\n".join(
        line for line in REACTION_MOTIF_PROMPT_TABLE.splitlines() if int(line.split(" = ")[0]) in legal_motifs
    )
    event_label = "un scandale" if event_type is EventType.SCANDAL else "un choc economique"
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu (reaction_to_event), "
        f"decide sa reaction a {event_label} qui vient de se produire, en te basant sur "
        "son propre niveau d'attention deja accumule (ctx.event_salience).\n"
        "CONTRAINTE ABSOLUE : salience_delta doit etre >= 0.0 et <= "
        f"{config.events.max_reaction_delta} (events.max_reaction_delta). Tout depassement "
        "invalide le batch entier.\n"
        f"Motifs valides pour cet evenement (code court obligatoire) :\n{legal_table}\n"
        "REGLE DE COHERENCE : salience_delta == 0 si et seulement si motif == "
        f"{int(ReactionMotif.EVENT_PERSONALLY_IRRELEVANT)} "
        "(EVENT_PERSONALLY_IRRELEVANT) -- un citoyen indifferent a l'evenement choisit "
        "ce motif et une variation nulle ; toute autre reaction utilise "
        f"{int(grounding_motif)} avec une variation strictement positive.\n"
        "ctx.event_salience : le niveau d'attention DEJA accumule par ce citoyen envers "
        "les evenements recents, avant sa reaction actuelle -- 0.0 s'il n'a encore ete "
        "touche par rien.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces {len(citizens)} cid, "
        f"chacun une seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse avant de "
        "la finaliser : chaque cid de cette liste doit apparaitre exactement une fois.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_reaction_user_prompt(
    citizens: Sequence[Citizen],
    contexts: Mapping[int, ReactionContext],
    *,
    event_type: EventType,
    target: int | None,
    magnitude: float,
) -> str:
    """Canonical JSON (sort_keys, compact separators, floats rounded to 4).
    Top-level keys {"event": {...}, "reactors": [...]} -- "reactors" is the
    eighth dispatch key (citizens/parties/nominees/responders/holders/
    consulted/voters are taken). "event" is stated ONCE, shared across the
    whole batch -- never duplicated into each of up to 100 citizens' own
    blocks -- and is deliberately asymmetric per event_type, mirroring
    _run_exogenous_events's own scandal_occurred/economic_shock_tick
    payloads (v5 Lot 2) and Lot 3's own deterministic reaction_to_event
    payload: `magnitude` is present only for ECONOMIC_SHOCK (it is
    meaningless for a SCANDAL, whose deterministic reaction uses a flat
    config constant, not a magnitude). Does not re-sort -- the caller owns
    the canonical order the system prompt enumerates."""
    event: dict[str, object] = {"event_type": int(event_type), "target": target}
    if event_type is EventType.ECONOMIC_SHOCK:
        event["magnitude"] = round(magnitude, 4)
    reactor_blocks = [
        {"cid": citizen.citizen_id, "ctx": contexts[citizen.citizen_id].to_payload()} for citizen in citizens
    ]
    return json.dumps({"event": event, "reactors": reactor_blocks}, sort_keys=True, separators=(",", ":"))


def decide_reaction_to_event(
    citizens: Sequence[Citizen],
    contexts: Mapping[int, ReactionContext],
    event_type: EventType,
    config: PolityConfig,
    client: LlmClientProtocol,
    *,
    target: int | None,
    magnitude: float = 0.0,
) -> ReactionBatchOutcome:
    """v5 Lot 4's dt=8 replacement for deterministic_reaction_to_event
    (simple_rules.py), which stays exactly as it is as the permanent
    §11.4 baseline. Mirrors that function's own signature -- ONE event_type
    per call, never a combined scandal+shock request -- extended only by
    what the LLM path additionally needs (citizens/contexts/config/client).

    Population-wide, like decide_pressure_actions -- CHUNKS via
    chunk_voters, but at the DEFAULT MIN_SAFE_BATCH_SIZE floor, not dt=10's
    own min_batch_size=1 override: dt=8's cohort is the entire population
    (a static, run-level quantity), not a variable, sometimes-shrinking
    consulted cohort, so there is no production scenario this lot has
    identified where the floor would legitimately block a real run. At
    shipped population_size=100/llm.max_batch_size=25, chunk_voters
    produces exactly 4 chunks of 25 -- comfortably clear of the floor with
    no remainder.

    Calls the client with think=False -- confirmed for this exact schema
    shape by this lot's own pre-flight spike against the REAL ReactionMotif/
    EventType enums (scripts/check_lot4_reaction_reliability.py,
    scripts/lot4_reaction_reliability_results.md), unlike v4 Lot 6's own
    spike which had to use toy schemas because the real ones didn't exist
    yet."""
    _check_supported(config)

    if not citizens:
        return ReactionBatchOutcome(decisions=[])

    # Sorted once, here, so system prompt / user prompt / expected_cids all
    # agree on the same order regardless of the caller's order -- never
    # rely on an incidental insertion order (D-5 precedent).
    citizens = sorted(citizens, key=lambda c: c.citizen_id)
    decisions: list[ReactionDecision] = []
    for chunk in chunk_voters(citizens, config.llm.max_batch_size):
        expected_cids = [c.citizen_id for c in chunk]
        chunk_decisions = _complete_and_decode_with_replay(
            client,
            system_prompt=build_reaction_system_prompt(chunk, event_type, config),
            user_prompt=build_reaction_user_prompt(chunk, contexts, event_type=event_type, target=target, magnitude=magnitude),
            json_schema=REACTION_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)),
            think=False,
            decode=lambda raw: decode_reaction_batch(raw, expected_cids),
            replays=config.llm.max_batch_replays,
            decision_type="reaction_to_event",
        )
        for decision in chunk_decisions:
            validate_reaction_decision(decision, event_type, config)
        decisions.extend(chunk_decisions)

    return ReactionBatchOutcome(decisions=decisions)


@dataclass(frozen=True)
class ChamberContext:
    """dt=11's ctx (v6b Lot 3, §6bis.3) -- deliberately ONE field.
    Every other candidate ctx signal (legitimacy, mandate_dev, street
    pressure, neighbors_acting) is one of the three §7bis pressure
    channels or their downstream effects, explicitly excluded by §6bis.3's
    own insulation requirement -- a seated member sees none of them.
    ticks_left = member.sortition_seat_until_tick - tick, computed by the
    caller (run_polity_simulation._run_chamber_deliberation); always a
    plain int, never None, since a citizen only ever appears in this
    cohort while seated (sortition_seat_until_tick is guaranteed set)."""

    cid: int
    ticks_left: int

    def to_payload(self) -> dict[str, int]:
        """Used by BOTH build_chamber_user_prompt and the journal write, so
        the ctx an analyst reads is provably the ctx the model saw -- same
        "one serialization, two consumers" precedent every other Context in
        this module already follows."""
        return {"ticks_left": self.ticks_left}


@dataclass(frozen=True)
class ChamberBatchOutcome:
    decisions: list[ChamberDecision]
    positions: dict[int, tuple[float, ...]]
    """cid -> resolved new chamber_position (the member's CURRENT
    chamber_position with validated shifts applied, so drift accumulates
    across ticks -- never re-based on issue_positions each tick, same
    reasoning as dt=6's own `positions` dict). issue_positions itself is
    never resolved here -- it is the member's own sincere anchor, never
    mutated by any decision."""


def validate_chamber_decision(decision: ChamberDecision, config: PolityConfig) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's config: the real shift-count and per-shift
    delta-magnitude caps -- sortition_chamber.max_deliberation_shifts/
    max_deliberation_delta (v6b Lot 3), deliberately NOT mandate.*/
    campaign.*: a sortition member's own deliberation is a distinct effect
    from an elected officeholder's mandate drift or a candidate's campaign
    strategy, and must stay analytically separable, even though the
    shipped magnitudes happen to match mandate.*'s own (see
    SortitionChamberConfig's own docstring). Structurally identical to
    validate_response_decision, reading a different config section."""
    if len(decision.shifts) > config.sortition_chamber.max_deliberation_shifts:
        raise LlmResponseError(
            f"decision for cid={decision.cid} shifts {len(decision.shifts)} dimension(s), "
            f"exceeding sortition_chamber.max_deliberation_shifts={config.sortition_chamber.max_deliberation_shifts}"
        )
    issue_count = config.citizens.issue_count
    for shift in decision.shifts:
        if shift.dimension >= issue_count:
            raise LlmResponseError(
                f"decision for cid={decision.cid} targets dimension {shift.dimension}, "
                f"out of range for issue_count={issue_count}"
            )
        if abs(shift.delta) > config.sortition_chamber.max_deliberation_delta:
            raise LlmResponseError(
                f"decision for cid={decision.cid} shifts dimension {shift.dimension} by "
                f"{shift.delta}, exceeding sortition_chamber.max_deliberation_delta="
                f"{config.sortition_chamber.max_deliberation_delta}"
            )


def build_chamber_system_prompt(members: Sequence[Citizen], config: PolityConfig) -> str:
    """Finding B discipline: verbatim expected-cid list + self-check. States
    the ACTUAL numeric bounds (sortition_chamber.max_deliberation_shifts/
    max_deliberation_delta), not just the schema's loose structural ceiling.
    States the intended shifts<->motif pairing as GUIDANCE only, not a hard
    rule -- llm_schemas.ChamberDecision deliberately dropped its own
    enforcing model_validator after this lot's own pre-flight spike measured
    it failing at a high rate (9/10, 6/6 decisions rejected at real cohort
    sizes) against the real model's tendency to label a small shift
    "sincere" anyway; see that model's own docstring. Explains that this
    body is INSULATED: no election, no citizen pressure, no legitimacy
    floor reaches it -- purely a personal reflection on one's own stated
    position over time. Explains ctx.ticks_left's meaning.

    Names the chamber_position==sincere_position case explicitly (v6b Lot 5
    correction): a live 270-call sweep against the real model found this
    EXACT state -- true at seating time (chamber_position is pinned to
    issue_positions there, run_polity_simulation._run_sortition_rotation)
    and for as long as a member never picks motif=702 -- reliably triggers
    the model's own Mode A (unbounded, non-convergent reasoning: the same
    "wait, maybe they differ -- let me check again" paragraph repeated
    ~70-140x, landing exactly on the token ceiling every time, 7/270 =
    2.6% of this state specifically). Left ambiguous, the model treats
    "the two arrays are literally equal" as something to keep re-verifying
    rather than a self-evidently trivial case. See
    scripts/lot3_chamber_reliability_results.md's own "Lot 5 correction"
    for the full diagnostic; this sentence is the fix, not a budget change
    -- chunk_size is already at its floor (_CHAMBER_MAX_CHUNK_SIZE=1)."""
    cid_list = ",".join(str(m.citizen_id) for m in members)
    return (
        "Tu es un moteur de simulation. Pour chaque membre tire au sort de "
        "la chambre de sortition recu (chamber_deliberation), decide s'il "
        "maintient sa position sincere ou s'il l'ajuste, a partir de sa "
        "position sincere, de sa position actuellement exprimee, et du "
        "contexte ctx. Ce membre n'a ete elu par personne, n'a fait aucune "
        "promesse, et n'est expose a AUCUNE pression citoyenne, aucune "
        "mobilisation, aucune petition, aucun seuil de legitimite -- sa "
        "seule matiere est sa propre reflexion au fil du temps.\n"
        "ctx.ticks_left : nombre de ticks avant la fin de son propre "
        "mandat (non renouvelable).\n"
        "shifts : au plus "
        f"{config.sortition_chamber.max_deliberation_shifts} ajustements de "
        f"position, chaque delta strictement compris entre "
        f"-{config.sortition_chamber.max_deliberation_delta} et "
        f"{config.sortition_chamber.max_deliberation_delta} inclus.\n"
        f"Motifs valides (code court obligatoire) :\n{CHAMBER_MOTIF_PROMPT_TABLE}\n"
        "En principe, motif=701 (SINCERE_POSITION) correspond a une liste "
        "shifts vide, et motif=702 (DELIBERATIVE_SHIFT) a au moins un "
        "ajustement -- choisis le motif qui decrit le mieux ta decision.\n"
        "Si chamber_position est identique a sincere_position, c'est l'etat "
        "normal d'un membre qui vient d'etre tire au sort ou qui n'a jamais "
        "devie -- tranche motif=701, shifts vide, sans verification repetee "
        "ni hesitation.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces "
        f"{len(members)} cid, chacun une seule fois, dans cet ordre : "
        f"[{cid_list}]. Verifie ta reponse avant de la finaliser : chaque "
        "cid de cette liste doit apparaitre exactement une fois.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_chamber_user_prompt(members: Sequence[Citizen], contexts: Mapping[int, ChamberContext]) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as every prior prompt builder. `members` is
    expected to already be in the canonical order the caller (decide_
    chamber_deliberation) enforces (sorted by citizen_id) -- this function
    doesn't re-sort. Top-level key "members" -- the ninth unambiguous
    dispatch key (citizens/parties/nominees/responders/holders/consulted/
    reactors already taken; see _FakeLlmClient, test_polity_run_simulation.py).
    Shows BOTH sincere_position (= issue_positions, immutable) and
    chamber_position (mutable, accumulates shifts) -- mirrors dt=6 showing
    both pledged_platform and revealed_position, so the model can see
    exactly how far it has already drifted from its own stated
    convictions."""
    member_blocks = []
    for member in members:
        assert member.chamber_position is not None
        member_blocks.append(
            {
                "cid": member.citizen_id,
                "sincere_position": [round(x, 4) for x in member.issue_positions],
                "chamber_position": [round(x, 4) for x in member.chamber_position],
                "priorities": [round(x, 4) for x in member.issue_priorities],
                "ctx": contexts[member.citizen_id].to_payload(),
            }
        )
    return json.dumps({"members": member_blocks}, sort_keys=True, separators=(",", ":"))


def decide_chamber_deliberation(
    members: Sequence[Citizen],
    contexts: Mapping[int, ChamberContext],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> ChamberBatchOutcome:
    """v6b Lot 3's dt=11 replacement for the status-quo deterministic
    fallback (see run_polity_simulation._run_chamber_deliberation's own
    docstring for why there is no simple_rules.py baseline function to
    replace -- chamber_position is pinned to issue_positions at seating
    time and nothing else ever touches it, so "no delta" is already true by
    construction without this module ever running).

    Chunks via chunk_voters, but at _CHAMBER_MAX_CHUNK_SIZE (1), NOT
    config.llm.max_batch_size (25) -- a real, measured correction to this
    lot's own original design, which assumed a small, un-chunked cohort
    (sortition_chamber.seats capped at 30, "a handful", the same category
    as dt=5/dt=6). This lot's own pre-flight spike found that assumption
    wrong: at the real 30-member cohort, in ONE call, the model silently
    dropped 24 of 30 decisions (only the last 6 came back); re-chunking at
    15 (config.llm.max_batch_size-shaped) reproduced the exact same
    failure on EACH chunk. Shipped at 10 first (confirmed 3/3 on the real
    30-member cohort at the time); a later v6b Lot 4 acceptance run hit a
    genuine token-budget overflow at chunk_size=10 (3/3 attempts, exact
    ceiling); halving to 5 was tried and validated-then-DISPROVEN against
    the real failing chunk (a different 5-member sub-chunk overflowed too,
    zero margin); cut to 1 -- vote_cast's own endpoint, same reasoning --
    and that held, with real margin, against the same failing citizens.
    See _CHAMBER_MAX_CHUNK_SIZE's own docstring for the full diagnostic.
    `min_batch_size=1` is now a no-op (chunk_voters always produces chunks
    of exactly 1 at this chunk size) but is left in place -- harmless, and
    it was the right override even when the ceiling was higher, since
    sortition_chamber.seats can be configured below whatever
    _CHAMBER_MAX_CHUNK_SIZE happens to be, and chunk_voters's own default
    floor (MIN_SAFE_BATCH_SIZE=20) was calibrated on a lighter prompt shape
    (vote_cast) that doesn't apply here either way -- see
    scripts/lot3_chamber_reliability_results.md for the measured evidence
    behind both the original batch ceiling and this floor override.

    Calls the client with think=True (corrected from think=False, which
    this lot's own pre-flight spike originally chose): a real v6b
    acceptance run found a specific 10-cid chunk that think=False
    reproducibly (8/8) dropped to 4/10, well-formed JSON, not a
    truncation -- switching to think=True fixed that exact chunk 6/6, and
    costs the same _CHAMBER_THINK_TOKEN_ALLOWANCE budget
    decide_campaign_positioning already pays for the identical reason. See
    _CHAMBER_THINK_TOKEN_ALLOWANCE's own comment and
    scripts/lot3_chamber_reliability_results.md for the measured
    evidence."""
    _check_supported(config)

    if not members:
        return ChamberBatchOutcome(decisions=[], positions={})

    # Sorted once, here, so system prompt / user prompt / expected_cids all
    # agree on the same order regardless of the caller's order -- never
    # rely on an incidental insertion order (D-5 precedent).
    members = sorted(members, key=lambda m: m.citizen_id)
    members_by_id = {m.citizen_id: m for m in members}
    decisions: list[ChamberDecision] = []
    for chunk in chunk_voters(members, _CHAMBER_MAX_CHUNK_SIZE, min_batch_size=1):
        expected_cids = [m.citizen_id for m in chunk]
        chunk_decisions = _complete_and_decode_with_replay(
            client,
            system_prompt=build_chamber_system_prompt(chunk, config),
            user_prompt=build_chamber_user_prompt(chunk, contexts),
            json_schema=CHAMBER_JSON_SCHEMA,
            max_tokens=compute_max_tokens(len(chunk)) + _CHAMBER_THINK_TOKEN_ALLOWANCE,
            think=True,
            decode=lambda raw: decode_chamber_batch(raw, expected_cids),
            replays=config.llm.max_batch_replays,
            decision_type="chamber_deliberation",
        )
        decisions.extend(chunk_decisions)

    positions: dict[int, tuple[float, ...]] = {}
    for decision in decisions:
        validate_chamber_decision(decision, config)
        member = members_by_id[decision.cid]
        assert member.chamber_position is not None  # guaranteed by the caller's own filter
        positions[decision.cid] = apply_shifts(member.chamber_position, decision.shifts)

    return ChamberBatchOutcome(decisions=decisions, positions=positions)


@dataclass(frozen=True)
class CoalitionBatchOutcome:
    decisions: list[CoalitionDecision]
    initiator: int | None
    coalition: list[int] | None
    rounds: list[list[CoalitionDecision]] = field(default_factory=list)
    aborted_at_round: int | None = None
    """Already assembled into form_coalition's exact return shape
    (list[int] | None) -- only this module has the platform/seat context the
    assembly needs, mirroring how cast_votes resolves positions into ballots
    internally rather than exposing raw wire values. metrics.py consumes
    this unchanged.

    v7 Lot 2: `decisions` keeps its pre-v7 meaning -- the FINAL round's
    resolved decisions, so every caller that only ever looked at `decisions`/
    `coalition`/`initiator` needs no change. `rounds` is additive: `rounds[i]`
    is round i+1's own decisions, in order, so a caller that wants the full
    negotiation transcript (the journal writer, see plan-coalition-
    negotiation-v7.md §4) can journal one coalition_decision event per
    (round, party) instead of collapsing straight to the final answer.
    `decisions == rounds[-1]` always holds except when `aborted_at_round` is
    set, in which case `decisions` is the last round that DID complete (for
    diagnostic visibility) but `coalition` is always None -- an aborted
    negotiation is never treated as equivalent to a concluded one, since the
    model might have been about to change its mind (that is the entire
    reason to run more rounds); see decide_coalition's own docstring for why
    only round >= 2 failures reach this path."""


def build_coalition_system_prompt(
    responder_party_ids: Sequence[int],
    initiator: int,
    initiator_seats: int,
    total_seats: int,
    majority_seats_threshold: float,
    round_number: int = 1,
) -> str:
    """Mirrors build_party_nomination_system_prompt's "enumerate the full
    expected id list verbatim + self-check" discipline (Finding B), keyed on
    party_id -- the decision unit here is a seated party, not a citizen.
    States the ACTUAL institutional numbers (total_seats,
    majority_seats_threshold, the initiator's own party_id/seats), not just
    the word "majorite" -- the increment 4 lesson (a prompt/validator bound
    mismatch shipped as a real bug) applies here too: every number the code
    later compares against is stated explicitly. States the action<->motif
    coherence rule explicitly, since CoalitionDecision's model_validator
    enforces it strictly. No coalition-theory framing anywhere in this
    prompt (§3.3 -- no "prefer a minimal winning coalition", no strategy
    hint of any kind): only the rules of the game and the closed code
    tables.

    v7 Lot 2: `round_number` is additive, defaults to 1, and produces
    byte-identical output to the pre-v7 prompt when omitted -- round 1's own
    parity requirement (plan-coalition-negotiation-v7.md §3). round_number
    > 1 adds exactly one sentence naming this a revision round; everything
    else (rules, self-check discipline) is unchanged, since what a revision
    actually SEES is carried entirely by build_coalition_user_prompt's own
    prior_decisions/provisional_coalition_seats, not by this prompt."""
    party_id_list = ",".join(str(pid) for pid in responder_party_ids)
    round_sentence = (
        ""
        if round_number == 1
        else (
            f"Ceci est le tour {round_number} d'une negociation multi-tours : ta reponse au "
            "tour precedent et l'etat provisoire de la coalition te sont rappeles ci-dessous. "
            "Tu peux maintenir ta decision precedente ou en changer, a la lumiere de cet etat.\n"
        )
    )
    return (
        f"Tu es un moteur de simulation. Le parti {initiator} (avec "
        f"{initiator_seats} sieges) vient d'etre designe formateur et "
        "cherche a former une coalition gouvernementale. Pour chaque parti "
        "recu, decide s'il rejoint cette coalition (action=1) ou refuse "
        "(action=2), a partir de sa propre position, de sa proximite avec "
        "le formateur, de son nombre de sieges, et de ce qu'il manque au "
        f"formateur pour la majorite.\n{round_sentence}L'assemblee compte {total_seats} "
        "sieges au total ; la coalition doit depasser strictement "
        f"{majority_seats_threshold} sieges pour atteindre la majorite.\n"
        f"Actions valides :\n{COALITION_ACTION_PROMPT_TABLE}\nMotifs "
        f"valides (code court obligatoire) :\n{COALITION_MOTIF_PROMPT_TABLE}\n"
        "CONTRAINTE STRICTE : le motif doit correspondre a l'action -- 501 "
        "ou 502 si action=1, 504 ou 505 si action=2. Toute autre "
        "combinaison sera rejetee.\nIMPORTANT : la liste decisions doit "
        f"contenir EXACTEMENT ces {len(responder_party_ids)} party_id, "
        f"chacun une seule fois, dans cet ordre : [{party_id_list}]. "
        "Verifie ta reponse avant de la finaliser : chaque party_id de "
        "cette liste doit apparaitre exactement une fois.\nReponds "
        "UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def build_coalition_user_prompt(
    responder_party_ids: Sequence[int],
    initiator: int,
    party_platforms: dict[int, tuple[float, ...]],
    seats: dict[int, int],
    votes: dict[int, float],
    total_seats: int,
    majority_seats_threshold: float,
    prior_decisions: Mapping[int, CoalitionDecision] | None = None,
    provisional_coalition_seats: int | None = None,
) -> str:
    """Canonical JSON (sort_keys, compact separators, rounded floats), same
    reproducibility discipline as every prior prompt builder.
    `responder_party_ids` is expected already sorted by the caller (D-5
    precedent) -- this function does not re-sort, so the system prompt's
    verbatim id list and this user prompt describe one order, not two.
    `distance_to_initiator` reuses form_coalition's own unweighted
    math.dist convention, not the voter-tolerance-specific
    weighted_distance.

    v7 Lot 2: `prior_decisions`/`provisional_coalition_seats` are additive,
    both default to None, and produce byte-identical JSON to the pre-v7
    single-shot prompt when omitted -- round 1's own parity requirement
    (plan-coalition-negotiation-v7.md §3). When provided (round >= 2), each
    responder block gains its own prior round's `{"action", "motif"}`, and
    the "assembly" block gains the coalition's current provisional seat
    total -- the state that makes "I join iff party X joins" conditional
    reasoning possible, the single-shot gap this whole palier exists to
    close (see the pre-v7 docstring this replaces, kept in git history).
    Deliberately NOT a verbatim transcript of every prior round: a mutable
    snapshot, like chamber_position, not a growing log (plan doc §4) --
    keeps prompt size bounded regardless of how many rounds have run."""
    initiator_shortfall = max(0.0, majority_seats_threshold - seats[initiator])
    responder_blocks = [
        {
            "party_id": pid,
            "seats": seats[pid],
            "votes": round(votes.get(pid, 0.0), 4),
            "distance_to_initiator": round(math.dist(party_platforms[pid], party_platforms[initiator]), 4),
            **(
                {
                    "prior_decision": {
                        "action": prior_decisions[pid].action,
                        "motif": prior_decisions[pid].motif,
                    }
                }
                if prior_decisions is not None
                else {}
            ),
        }
        for pid in responder_party_ids
    ]
    assembly_block: dict[str, Any] = {
        "total_seats": total_seats,
        "majority_seats_threshold": round(majority_seats_threshold, 4),
        "initiator_shortfall": round(initiator_shortfall, 4),
    }
    if provisional_coalition_seats is not None:
        assembly_block["provisional_coalition_seats"] = provisional_coalition_seats
    return json.dumps(
        {
            "assembly": assembly_block,
            "initiator": {
                "party_id": initiator,
                "platform": [round(x, 4) for x in party_platforms[initiator]],
                "seats": seats[initiator],
                "votes": round(votes.get(initiator, 0.0), 4),
            },
            "responders": responder_blocks,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_coalition_decision(decision: CoalitionDecision, seats: dict[int, int], initiator: int) -> None:
    """Context-dependent checks llm_schemas.py's Pydantic validators can't
    do without the caller's seats/initiator state. coalition_decision emits
    a closed enum, so unlike validate_positioning_decision there is no
    config-driven numeric bound to enforce here -- what remains are the two
    preconditions assemble_coalition relies on that the wire cannot know on
    its own: the deciding party actually holds a seat, and it isn't the
    initiator (whose own action is never asked -- see decide_coalition)."""
    if decision.party_id == initiator:
        raise LlmResponseError(
            f"decision for party_id={decision.party_id} is the initiator -- its own action is never asked"
        )
    if seats.get(decision.party_id, 0) <= 0:
        raise LlmResponseError(f"decision for party_id={decision.party_id} does not hold a seat in this assembly")


def assemble_coalition(
    decisions: Sequence[CoalitionDecision],
    initiator: int,
    party_platforms: dict[int, tuple[float, ...]],
    seats: dict[int, int],
    majority_ratio: float,
) -> list[int] | None:
    """Turns a validated batch of join/leave decisions into the exact
    `list[int] | None` shape simple_rules.form_coalition already returns,
    so metrics.py needs zero changes. Deliberately reuses form_coalition's
    OWN ordering (ascending distance from the initiator, tie-broken by seats
    descending then party_id) over just the `join`-voting subset -- this
    isolates the LLM's causal contribution to willingness only, and buys a
    directly testable invariant: unanimous join produces byte-identical
    output to what form_coalition would return on the same inputs (see
    test_polity_llm_behavior_engine.py's parity test)."""
    total_seats = sum(seats.values())
    threshold = majority_ratio * total_seats

    coalition = [initiator]
    coalition_seats = seats[initiator]
    if coalition_seats > threshold:
        return coalition

    joiners = [d.party_id for d in decisions if d.action == CoalitionAction.JOIN.value]
    joiners.sort(
        key=lambda pid: (
            math.dist(party_platforms[pid], party_platforms[initiator]),
            -seats[pid],
            pid,
        )
    )
    for pid in joiners:
        coalition.append(pid)
        coalition_seats += seats[pid]
        if coalition_seats > threshold:
            return coalition

    return None


def decide_coalition(
    parties: Sequence[Party],
    seats: dict[int, int],
    votes: dict[int, float],
    config: PolityConfig,
    client: LlmClientProtocol,
) -> CoalitionBatchOutcome:
    """v2 increment 5's replacement for form_coalition's nearest-neighbour
    greedy aggregation -- the initiator designation, the majority rule, and
    the ordering in which willing partners are added all stay deterministic
    (see assemble_coalition); the LLM contributes only each seated,
    non-initiator party's willingness to join. Pure aside from the injected
    client -- no journal writes here, matching every prior decide_*
    function's convention; run_polity_simulation.py owns every journal
    write.

    Formation only: design doc §3.1's "maintien et rupture" of a coalition
    across subsequent ticks is out of scope for this increment. Reasons: no
    tick hook exists for it today (this module only touches coalitions
    inside `election in (LEGISLATIVE, BOTH)`); it would need new cross-tick
    state (a standing `current_coalition`) this increment deliberately
    doesn't introduce; the design doc gives it no consequence model (what
    happens when a coalition ruptures mid-term has no mechanic anywhere);
    and a mid-term rupture would break metrics.coalition_lifespans' "until
    the next legislative election" assumption -- exactly the metrics
    compatibility this increment promises to preserve.

    Deliberately does NOT use chunk_voters/MIN_SAFE_BATCH_SIZE, same
    reasoning as decide_party_nominations/decide_campaign_positioning: this
    batches seated parties (a handful at most, parties.initial_count in the
    shipped config), not citizens.

    Skips the client entirely (no network call) when no party holds a seat,
    when the initiator alone already clears the majority, or when there are
    no non-initiator seated parties to ask -- mirrors form_coalition's own
    short-circuits and avoids violating CoalitionBatch's min_length=1.

    Calls the client with think=False, the same guess as increments 3/4's
    comparative-judgment prompt shape ("do you join THIS coalition"),
    flagged for live verification rather than assumed -- see
    test_polity_llm_live.py.

    v7 Lot 2 (§3.4 Cas 2): what was a single batched call is now a bounded
    loop of up to config.parties.coalition_max_negotiation_rounds rounds,
    each an ordinary batched call over the SAME full responder set (never
    narrowed -- a party that already answered can still revise in a later
    round, which is the entire point: round 1 alone cannot express "I join
    iff party X joins"). Stops on whichever comes first: the hard round cap,
    or every responder's action matching the previous round's (a fixed
    point -- a motif-only change does not count, since it doesn't change
    assemble_coalition's result). Round 1's own prompts are byte-identical
    to the pre-v7 single-shot call (build_coalition_*_prompt's own
    parity-by-construction, tested directly) -- round 1 always runs even at
    the shipped default (3), so results a caller obtained before v7 do not
    silently change shape, only the number of calls does.

    Round >= 2 failure handling is deliberately asymmetric with round 1:
    round 1's LlmResponseError propagates exactly as the pre-v7 single call
    did (no behaviour change for that path). A round >= 2 failure is instead
    caught and converted into an outcome with `coalition=None` and
    `aborted_at_round` set -- unlike every other decide_* function, a failed
    coalition negotiation already has a legitimate, non-crashing domain
    outcome to degrade to (coalition_failed already exists for "no majority
    reachable"; there is no equivalent soft outcome for e.g. a citizen who
    fails to vote). Round 1 keeps the old propagate-and-abort-the-run
    behaviour specifically because nothing about it changed -- there is no
    new resilience to claim there that wasn't already a design choice this
    lot could make. See plan-coalition-negotiation-v7.md §4 for the
    reasoning and its own explicit limit: this protects only an
    intra-process retry (rounds already computed, never regenerated); a full
    run restart is not protected, exactly like every other decide_* call
    already is not (§4.3's accepted non-determinism limit)."""
    _check_supported(config)

    party_platforms = {party.party_id: party.platform for party in parties}
    seated = sorted(pid for pid, s in seats.items() if s > 0)
    if not seated:
        return CoalitionBatchOutcome(decisions=[], initiator=None, coalition=None)

    total_seats = sum(seats.values())
    majority_ratio = config.parties.coalition_majority_ratio
    threshold = majority_ratio * total_seats

    initiator = min(seated, key=lambda pid: tiebreak_key(pid, seats, votes, config.parties.coalition_tiebreak))
    if seats[initiator] > threshold:
        return CoalitionBatchOutcome(decisions=[], initiator=initiator, coalition=[initiator])

    responders = [pid for pid in seated if pid != initiator]
    if not responders:
        return CoalitionBatchOutcome(decisions=[], initiator=initiator, coalition=None)

    all_rounds: list[list[CoalitionDecision]] = []
    prior_by_party: dict[int, CoalitionDecision] | None = None
    provisional_seats: int | None = None
    round_number = 1
    while True:
        try:
            round_decisions = _complete_and_decode_with_replay(
                client,
                system_prompt=build_coalition_system_prompt(
                    responders, initiator, seats[initiator], total_seats, threshold,
                    round_number=round_number,
                ),
                user_prompt=build_coalition_user_prompt(
                    responders, initiator, party_platforms, seats, votes, total_seats, threshold,
                    prior_decisions=prior_by_party,
                    provisional_coalition_seats=provisional_seats,
                ),
                json_schema=COALITION_JSON_SCHEMA,
                max_tokens=compute_max_tokens(len(responders)),
                think=False,
                decode=lambda raw: decode_coalition_batch(raw, responders),
                replays=config.llm.max_batch_replays,
                decision_type="coalition_decision",
            )
        except LlmResponseError:
            if round_number == 1:
                raise
            return CoalitionBatchOutcome(
                decisions=all_rounds[-1],
                initiator=initiator,
                coalition=None,
                rounds=all_rounds,
                aborted_at_round=round_number,
            )

        for decision in round_decisions:
            validate_coalition_decision(decision, seats, initiator)
        all_rounds.append(round_decisions)

        current_by_party = {d.party_id: d for d in round_decisions}
        converged = prior_by_party is not None and all(
            prior_by_party[pid].action == current_by_party[pid].action for pid in responders
        )
        if converged or round_number >= config.parties.coalition_max_negotiation_rounds:
            break

        prior_by_party = current_by_party
        joiners = [pid for pid, d in current_by_party.items() if d.action == CoalitionAction.JOIN.value]
        provisional_seats = seats[initiator] + sum(seats[pid] for pid in joiners)
        round_number += 1

    final_decisions = all_rounds[-1]
    coalition = assemble_coalition(final_decisions, initiator, party_platforms, seats, majority_ratio)
    return CoalitionBatchOutcome(
        decisions=final_decisions, initiator=initiator, coalition=coalition, rounds=all_rounds
    )
