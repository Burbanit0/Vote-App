"""run_polity_flagship.py's --base-url: a server that is not on localhost (a tunnelled rented GPU)."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from api.domain.polity import profiles


def _llm_base_url(tmp_path: Path, **overrides: Any) -> str:
    kwargs: dict[str, Any] = {
        "engine": "llm", "years": 2, "population": 50, "seats": 8, "seed": 1, "output_dir": tmp_path,
        "max_batch_replays": 0, "provider": None, "workers": 1, **overrides,
    }
    return str(profiles.flagship_config(**kwargs).llm.base_url)


def test_an_explicit_base_url_overrides_the_shipped_and_the_providers_default(tmp_path: Path) -> None:
    shipped = _llm_base_url(tmp_path)
    assert _llm_base_url(tmp_path, base_url="http://localhost:9000/v1") == "http://localhost:9000/v1"
    assert _llm_base_url(tmp_path, provider="ollama") == "http://localhost:11434/v1" != shipped
    assert _llm_base_url(tmp_path, provider="ollama", base_url="http://gpu:8000/v1") == "http://gpu:8000/v1"


def test_a_model_override_names_the_weights_the_server_serves(tmp_path: Path) -> None:
    kwargs: dict[str, Any] = {
        "engine": "llm", "years": 2, "population": 50, "seats": 8, "seed": 1, "output_dir": tmp_path,
        "max_batch_replays": 0, "provider": None, "workers": 1,
    }
    shipped = profiles.flagship_config(**kwargs).llm.model
    assert profiles.flagship_config(**kwargs, model="some-other-model").llm.model == "some-other-model" != shipped
