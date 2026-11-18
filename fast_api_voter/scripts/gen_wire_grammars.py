"""Generate api/domain/polity/wire_grammars.json: the EBNF grammar of every schema the vLLM client sends.

vLLM 0.31 with `disable_any_whitespace` constrains an answer to JSON spaced `", "` and `": "`; from 0.32 the
same flag gives compact JSON, and the model answers differently on it (EXP-025, EXP-026). So the client can
send the grammar itself (`VllmJsonClient.structured_output = "grammar"`), spacing included, and the server's
default stops mattering. The grammar is the one xgrammar builds from the schema, printed as EBNF: this script
runs xgrammar inside the server image on the CPU (no GPU, no model, no server), as
check_vote_grammar_xgrammar.py does. xgrammar is not a backend dependency (its wheel pulls torch).

Usage (from fast_api_voter/, Docker and the image needed):
    python scripts/gen_wire_grammars.py                 # rewrite the artifact from the pinned image
    python scripts/gen_wire_grammars.py --check         # exit 1 if the committed artifact is not what this gives
    python scripts/gen_wire_grammars.py --check --image vllm/vllm-openai:v0.34.0   # same, another xgrammar

The artifact is generated: never edit it by hand. Regenerate it when a schema, `WIRE_ORDER` or a bake-off arm
changes (`llm_client.wire_grammar` raises on a schema it has no grammar for).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SEPARATORS = (", ", ": ")
"""What xgrammar puts between items and after a key when `any_whitespace=False` and no separators are given:
the spacing every measurement on vLLM <= 0.31 was made on. Passed explicitly so a change of that default
cannot move it."""


def in_container(work: Path) -> int:
    import importlib.metadata

    import xgrammar as xgr

    schemas: dict[str, str] = json.loads((work / "schemas.json").read_text())
    grammars: dict[str, str] = {}
    differ_from_default = 0
    for key, schema in schemas.items():
        text = str(xgr.Grammar.from_json_schema(schema, any_whitespace=False, separators=SEPARATORS))
        xgr.Grammar.from_ebnf(text)  # what the server will do with it: it must parse
        # the call vLLM 0.31's backend makes for a schema request, to show the artifact is that grammar
        differ_from_default += text != str(xgr.Grammar.from_json_schema(schema, any_whitespace=False))
        grammars[key] = text
    (work / "grammars.json").write_text(json.dumps({
        "xgrammar": importlib.metadata.version("xgrammar"), "vllm": importlib.metadata.version("vllm"),
        "differ_from_default": differ_from_default, "grammars": grammars,
    }))
    return 0


def wire_schemas() -> dict[str, str]:
    """sha256 -> wire schema, for every (schema, field order) the vLLM client can be asked to send: each
    schema of llm_schemas, vote_cast's grammar for each ranking limit, the run's warm-up and the
    bake-off's renamed-`motif` schemas, each under production's `WIRE_ORDER` and under every bake-off arm's order."""
    from api.domain.polity import llm_schemas
    from api.domain.polity.bakeoff_bank import SCHEMAS
    from api.domain.polity.bakeoff_runner import _MOTIF_KEYS, ARMS, _rename_motif
    from api.domain.polity.llm_behavior_engine import _TRUNCATION_THRESHOLD
    from api.domain.polity.llm_client import WIRE_ORDER, wire_schema
    from api.domain.polity.run_polity_simulation import _WARM_UP_SCHEMA

    # every module-level schema, whatever its name: a constant named otherwise must not be left without a grammar
    schemas = [value for value in vars(llm_schemas).values() if isinstance(value, dict) and "properties" in value]
    schemas += [llm_schemas.vote_cast_json_schema(limit) for limit in range(1, _TRUNCATION_THRESHOLD + 1)]
    schemas.append(_WARM_UP_SCHEMA)  # the vLLM warm-up (the recycle warm-up is the Ollama client's)
    schemas += [_rename_motif(schema, key) for schema in SCHEMAS.values() for key in _MOTIF_KEYS.values()]
    orders = [WIRE_ORDER, *(arm.wire_order for arm in ARMS.values() if arm.wire_order is not None)]
    wires = {wire_schema(schema, order) for schema in schemas for order in orders}
    return {hashlib.sha256(wire.encode("utf-8")).hexdigest(): wire for wire in sorted(wires)}


def main(argv: list[str] | None = None) -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--in-container":
        return in_container(Path(sys.argv[2]))
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    from api.domain.polity.llm_client import _WIRE_GRAMMARS_PATH
    from check_vote_grammar_xgrammar import _image

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare with the committed artifact, write nothing")
    parser.add_argument("--image", default=_image(backend / "docker-compose.llm.yml"), help="default: the pinned image")
    args = parser.parse_args(argv)
    pinned = _image(backend / "docker-compose.llm.yml")
    if args.image != pinned and not args.check:
        parser.error(f"the artifact is written from the pinned image ({pinned}) only: use --check with --image")

    schemas = wire_schemas()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "schemas.json").write_text(json.dumps(schemas))
        shutil.copy(__file__, work / "gen.py")
        subprocess.run(["docker", "run", "--rm", "-v", f"{work}:/work", "--entrypoint", "python3", args.image,
                        "/work/gen.py", "--in-container", "/work"], check=True)
        made = json.loads((work / "grammars.json").read_text())
    grammars: dict[str, str] = made["grammars"]
    print(f"{len(grammars)} grammars from {args.image} (vllm {made['vllm']}, xgrammar {made['xgrammar']}); "
          f"{made['differ_from_default']} differ from xgrammar's own default spacing")
    if args.check:
        committed: dict[str, str] = json.loads(_WIRE_GRAMMARS_PATH.read_text(encoding="utf-8"))["grammars"]
        wrong = sorted(key for key in grammars.keys() | committed.keys() if grammars.get(key) != committed.get(key))
        for key in wrong:
            state = "missing from the artifact" if key not in committed else "stale in the artifact" if key not in grammars else "differs"
            title = json.loads(schemas[key]).get("title", "?") if key in schemas else "?"
            print(f"  {key[:12]} ({title}): {state}")
        print("artifact matches" if not wrong else f"{len(wrong)} entries do not match {_WIRE_GRAMMARS_PATH}")
        return 1 if wrong else 0
    _WIRE_GRAMMARS_PATH.write_text(json.dumps({
        "generated_by": "scripts/gen_wire_grammars.py", "image": args.image, "xgrammar": made["xgrammar"],
        "grammars": grammars,
    }, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_WIRE_GRAMMARS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
