"""S1.2: does the pinned vLLM's own xgrammar compile vote_cast's grammar, and forbid what it should?

Runs vLLM's structured-output code inside the server image (docker-compose.llm.yml's pinned
`vllm/vllm-openai` tag) on the CPU -- no GPU, no model, no server. For today's schema and
S1.2's (`llm_schemas.vote_cast_json_schema`, as the client sends it: refs inlined), it asks
vLLM's own `has_xgrammar_unsupported_json_features` whether xgrammar would take the schema
(true would mean vLLM silently falls back to another backend), then compiles the grammar
with the server's settings (`disable_any_whitespace`, strict) and tests sample ballots.

Usage (from fast_api_voter/, Docker and the pulled image needed):
    python scripts/check_vote_grammar_xgrammar.py

Exits non-zero if S1.2's grammar accepts a ballot it should forbid or refuses one it should take.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SAMPLES = {
    "ranked ballot": ({"decisions": [{"cid": 3, "blank": 0, "ranking": [2, 1], "motif": 104}]}, True),
    "blank ballot": ({"decisions": [{"cid": 3, "blank": 1, "ranking": [], "motif": 101}]}, True),
    "blank WITH a ranking": ({"decisions": [{"cid": 3, "blank": 1, "ranking": [2], "motif": 101}]}, False),
    "not blank, EMPTY ranking": ({"decisions": [{"cid": 3, "blank": 0, "ranking": [], "motif": 104}]}, False),
    "six positions, limit five": ({"decisions": [{"cid": 3, "blank": 0, "ranking": [1, 2, 3, 4, 5, 6], "motif": 104}]}, False),
    "two voters, one of each": ({"decisions": [{"cid": 3, "blank": 1, "ranking": [], "motif": 101},
                                               {"cid": 4, "blank": 0, "ranking": [5], "motif": 104}]}, True),
}


def _image(compose: Path) -> str:
    match = re.search(r"image:\s*(vllm/vllm-openai:\S+)", compose.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"no vllm/vllm-openai image pinned in {compose}")
    return match.group(1)


def in_container(schemas_path: Path) -> int:
    import importlib.metadata

    import xgrammar as xgr
    from vllm.v1.structured_output.backend_xgrammar import has_xgrammar_unsupported_json_features
    from xgrammar.testing import _is_grammar_accept_string

    schemas = json.loads(schemas_path.read_text())
    print(f"vllm {importlib.metadata.version('vllm')}, xgrammar {importlib.metadata.version('xgrammar')}")
    print("| schema | sample | accepted | as S1.2 requires |\n|---|---|---|---|")
    wrong = 0
    for name, schema in schemas.items():
        print(f"| {name} | (xgrammar would refuse the schema) | {has_xgrammar_unsupported_json_features(schema)} | |")
        grammar = xgr.Grammar.from_json_schema(json.dumps(schema), any_whitespace=False, strict_mode=True)
        for label, (sample, allowed) in SAMPLES.items():
            accepted = _is_grammar_accept_string(grammar, json.dumps(sample))  # xgrammar's own no-whitespace separators
            verdict = "" if name != "S1.2" else ("yes" if accepted == allowed else "**NO**")
            wrong += name == "S1.2" and accepted != allowed
            print(f"| {name} | {label} | {accepted} | {verdict} |")
    return 1 if wrong else 0


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--in-container":
        return in_container(Path(sys.argv[2]))
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    from api.domain.polity.llm_client import _inline_refs
    from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA, vote_cast_json_schema

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "schemas.json").write_text(json.dumps({
            "today": _inline_refs(VOTE_CAST_JSON_SCHEMA), "S1.2": _inline_refs(vote_cast_json_schema(5)),
        }))
        shutil.copy(__file__, work / "check.py")
        command = ["docker", "run", "--rm", "-v", f"{work}:/work", "--entrypoint", "python3",
                   _image(backend / "docker-compose.llm.yml"), "/work/check.py", "--in-container", "/work/schemas.json"]
        return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
