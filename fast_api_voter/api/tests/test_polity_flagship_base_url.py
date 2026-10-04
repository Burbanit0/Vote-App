"""run_polity_flagship.py's --base-url: a server that is not on localhost (a tunnelled rented GPU)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_polity_flagship.py"


@pytest.fixture(scope="module")
def flagship() -> Any:
    spec = importlib.util.spec_from_file_location("run_polity_flagship", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_polity_flagship"] = module
    spec.loader.exec_module(module)
    return module


def _llm_base_url(flagship: Any, tmp_path: Path, **overrides: Any) -> str:
    kwargs: dict[str, Any] = {
        "engine": "llm", "years": 2, "population": 50, "seats": 8, "seed": 1, "output_dir": tmp_path,
        "max_batch_replays": 0, "provider": None, "workers": 1, **overrides,
    }
    return str(flagship._flagship_config(**kwargs).llm.base_url)


def test_an_explicit_base_url_overrides_the_shipped_and_the_providers_default(flagship: Any, tmp_path: Path) -> None:
    shipped = _llm_base_url(flagship, tmp_path)
    assert _llm_base_url(flagship, tmp_path, base_url="http://localhost:9000/v1") == "http://localhost:9000/v1"
    assert _llm_base_url(flagship, tmp_path, provider="ollama") == "http://localhost:11434/v1" != shipped
    assert _llm_base_url(flagship, tmp_path, provider="ollama", base_url="http://gpu:8000/v1") == "http://gpu:8000/v1"
