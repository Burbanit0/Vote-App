"""Shared fixtures for the bake-off tests (S2.2): the reference config, a generated bank,
and fake clients that answer every case -- with token logprobs, when asked."""
from __future__ import annotations

import dataclasses
import json
import math
from functools import lru_cache
from typing import Any

from api.domain.polity.bakeoff_bank import CaseBank
from api.domain.polity.bakeoff_cases import generate_bank
from api.domain.polity.bakeoff_controls import parse_paths
from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.llm_client import TokenLogprob
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient


def reference_config() -> PolityConfig:
    """What scripts/bakeoff_cases.py renders the bank for, as far as requests depend on it:
    the LLM engine on vLLM / qwen3:8b, the flagship's full pressure menu, one worker."""
    config = load_config()
    return dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True, provider="vllm", base_url="http://localhost:8000/v1"),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True),
        parallel=dataclasses.replace(config.parallel, intra_run_workers=1),
    )


@lru_cache(maxsize=1)
def reference_bank() -> CaseBank:
    return generate_bank(reference_config())


CHOSEN_DIGIT_PROBABILITY = 0.9


def char_tokens(content: str) -> list[TokenLogprob]:
    """One token per character. At a digit, every digit is an alternative and the one
    written has probability 0.9 -- so a reading at any digit field is 0.9 for the answer."""
    tokens = []
    for char in content:
        if char.isdigit():
            alternatives = {d: math.log(CHOSEN_DIGIT_PROBABILITY if d == char else (1 - CHOSEN_DIGIT_PROBABILITY) / 9) for d in "0123456789"}
            tokens.append(TokenLogprob(token=char, logprob=alternatives[char], alternatives=alternatives))
        else:
            tokens.append(TokenLogprob(token=char, logprob=0.0, alternatives={char: 0.0}))
    return tokens


class BankFakeClient(_ElectingFakeLlmClient):  # type: ignore[misc]
    """The run-simulation fake, able to read every rendering in the bank (S2.5): a user
    prompt that is not JSON or TOON is a path rendering, turned back into JSON first.
    Counts decision calls."""

    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, **kwargs: Any) -> str:
        self.calls += 1
        user_prompt = kwargs["user_prompt"]
        if not user_prompt.startswith(("{", "citizens[")):
            kwargs = {**kwargs, "user_prompt": json.dumps(parse_paths(user_prompt))}
        return str(super().complete_json(**kwargs))


class LogprobFakeClient(BankFakeClient):
    """BankFakeClient plus complete_json_with_logprobs."""

    def complete_json_with_logprobs(self, **kwargs: Any) -> tuple[str, list[TokenLogprob]]:
        content = self.complete_json(**kwargs)
        return content, char_tokens(content)
