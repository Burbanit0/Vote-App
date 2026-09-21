"""Model profiles (S2.3): what the engine needs to know about a served model --
how to switch its thinking on and off, the context ceiling the server enforces,
and the chunk sizes and thinking budgets measured for it.

Until S2.3 these were module constants selected by `llm.provider == "vllm"`
checks in llm_behavior_engine, and the thinking switch was Qwen's
`chat_template_kwargs.enable_thinking` written into every vLLM request. Adding a
non-Qwen model meant editing the engine; now it means adding a profile.

A profile is keyed by (provider, model), not by model alone: this project serves
different weights under the same `llm.model` tag on purpose (`qwen3:8b` is the
Ollama library GGUF on Ollama and Qwen/Qwen3-8B-AWQ on vLLM, so prompt and
journal bytes stay identical across providers -- docker-compose.llm.yml), and
every value below was measured on one of them, not both.

Values are copied from measurements, never guessed: each profile names the
results docs behind it. A model with no profile is refused at config validation
rather than run on another model's numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal


@dataclass(frozen=True)
class ThinkingControl:
    """How a request turns a model's reasoning on or off.

    - `chat_template_kwargs`: `{"chat_template_kwargs": {key: on | off}}` -- Qwen3
      (`enable_thinking`), Granite (`thinking`).
    - `reasoning_effort`: a top-level `reasoning_effort` field set to `on` or `off`,
      e.g. "high" / "low", for models whose effort levels have no true "off".
    - `none`: the model has no switch; nothing is sent, and `think` changes nothing.
    """

    field: Literal["chat_template_kwargs", "reasoning_effort", "none"]
    key: str | None = None
    on: Any = True
    off: Any = False

    def request_fields(self, think: bool) -> dict[str, Any]:
        value = self.on if think else self.off
        if self.field == "chat_template_kwargs":
            return {"chat_template_kwargs": {self.key: value}}
        if self.field == "reasoning_effort":
            return {"reasoning_effort": value}
        return {}


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    """`llm.model`, the name the server serves the weights under."""
    weights: str
    family: str
    thinking: ThinkingControl
    context_limit: int | None
    """prompt + completion tokens the server accepts per request (vLLM's
    --max-model-len); None where the engine never sizes against it."""
    probe_token_budget: bool
    """Whether vote_cast and chamber_deliberation size max_tokens from a
    prompt-token probe against `context_limit` (llm_behavior_engine._dynamic_max_tokens)
    instead of a flat allowance."""
    vote_cast_chunk_size: int
    chamber_chunk_size: int
    vote_think_allowance: int
    chamber_think_allowance: int
    positioning_think_allowance: int


QWEN3_THINKING = ThinkingControl(field="chat_template_kwargs", key="enable_thinking")

QWEN3_8B_AWQ_VLLM = ModelProfile(
    provider="vllm",
    model="qwen3:8b",
    weights="Qwen/Qwen3-8B-AWQ",
    family="qwen3",
    thinking=QWEN3_THINKING,
    # docker-compose.llm.yml's --max-model-len, sized live 2026-09-05.
    context_limit=16384,
    probe_token_budget=True,
    # check_vllm_chunk_size_throughput_results.md (2026-09-08): vote_cast 23/24 correct
    # at chunk 3; chamber_deliberation clean at 5. See llm_behavior_engine's
    # _VOTE_CAST_MAX_CHUNK_SIZE_VLLM / _CHAMBER_MAX_CHUNK_SIZE_VLLM for the full record.
    vote_cast_chunk_size=3,
    chamber_chunk_size=5,
    # Measured on Ollama (2026-08-17/20) and kept for vLLM; see
    # _VOTE_THINK_TOKEN_ALLOWANCE, _CHAMBER_THINK_TOKEN_ALLOWANCE and
    # _POSITIONING_THINK_TOKEN_ALLOWANCE in llm_behavior_engine.
    vote_think_allowance=12000,
    chamber_think_allowance=8000,
    positioning_think_allowance=8000,
)

# The precision probe's checkpoint (docker-compose.llm-nvfp4.yml): the same weights lineage in NVFP4
# instead of AWQ. The probe changes ONE thing, the weight format, so it must send the same requests:
# every other value is the AWQ profile's on purpose. None of them was measured on this checkpoint --
# do not run a simulation on it on these numbers.
QWEN3_8B_NVFP4A16_VLLM = replace(
    QWEN3_8B_AWQ_VLLM,
    model="qwen3:8b-nvfp4a16",
    weights="ELVISIO/Qwen3-8B-NVFP4A16",
)

QWEN3_8B_OLLAMA = ModelProfile(
    provider="ollama",
    model="qwen3:8b",
    weights="qwen3:8b (Ollama library GGUF)",
    family="qwen3",
    # The Ollama client switches thinking by endpoint (/v1 vs native /api/chat) and
    # does not send this field; recorded for what the model family's template uses.
    thinking=QWEN3_THINKING,
    context_limit=None,
    probe_token_budget=False,
    # Ollama-era measurements (v6b acceptance, 2026-08-17): vote_cast collapses from
    # chunk 4; chamber_deliberation dropped decisions above 1.
    vote_cast_chunk_size=1,
    chamber_chunk_size=1,
    vote_think_allowance=12000,
    chamber_think_allowance=8000,
    positioning_think_allowance=8000,
)

PROFILES: dict[tuple[str, str], ModelProfile] = {
    (profile.provider, profile.model): profile
    for profile in (QWEN3_8B_AWQ_VLLM, QWEN3_8B_NVFP4A16_VLLM, QWEN3_8B_OLLAMA)
}

PROFILED_PROVIDERS = frozenset(provider for provider, _ in PROFILES)


class UnknownModelProfileError(LookupError):
    """No profile for this (provider, model): its chunk sizes and thinking switch are unmeasured."""


def model_profile(provider: str, model: str) -> ModelProfile:
    try:
        return PROFILES[(provider, model)]
    except KeyError:
        known = ", ".join(f"{p}/{m}" for p, m in sorted(PROFILES))
        raise UnknownModelProfileError(
            f"no model profile for {model!r} on {provider!r} (profiles: {known}) -- measure it and add "
            "one to api/domain/polity/model_profiles.py"
        ) from None
