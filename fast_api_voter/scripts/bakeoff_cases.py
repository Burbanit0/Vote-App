"""Generate or check the model bake-off's case bank (S2.2).

The bank is rendered for the reference model -- the flagship runner's config (the one the
p500 batch runs) on vLLM / qwen3:8b, seed 42 -- by running the production decide_*
functions against a capturing client. See api/domain/polity/bakeoff_cases.py.

Usage (from fast_api_voter/):
    python scripts/bakeoff_cases.py generate    # writes scripts/bakeoff/case_bank.jsonl
    python scripts/bakeoff_cases.py check       # the frozen hash holds, and what production renders differently today
    python scripts/bakeoff_cases.py generate --set emotions   # ADR-012's prerequisite bank, case_bank_emotions.jsonl

A bank is frozen once sessions have answered it: regenerate only on purpose, and say why
in the commit, since sessions on different banks do not compare.
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.bakeoff_bank import BankIntegrityError, read_bank, write_bank  # noqa: E402
from api.domain.polity.bakeoff_cases import drift, generate_bank, generate_emotions_bank  # noqa: E402
from api.domain.polity.config import PolityConfig  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

DEFAULT_BANK = Path(__file__).resolve().parent / "bakeoff" / "case_bank.jsonl"
EMOTIONS_BANK = Path(__file__).resolve().parent / "bakeoff" / "case_bank_emotions.jsonl"
"""ADR-012's prerequisite: a bank of its own, so the frozen bank earlier sessions answered is unchanged."""
REFERENCE_SEED = 42


def reference_config(*, provider: str = "vllm", model: str | None = None, seed: int = REFERENCE_SEED) -> PolityConfig:
    """The p500 batch's config: the flagship runner's full-mechanism overrides."""
    return _flagship_config(
        engine="llm", years=8, population=500, seats=75, seed=seed, output_dir=Path("bakeoff-unused"),
        max_batch_replays=2, provider=provider, workers=1, model=model,
    )


def _summary(bank_path: Path) -> str:
    bank = read_bank(bank_path)
    families = collections.Counter(case.family for case in bank.cases)
    return f"{bank_path}: {len(bank.cases)} cases, sha256 {bank.content_sha256[:16]}, " + ", ".join(
        f"{family} {count}" for family, count in sorted(families.items())
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--bank", type=Path, default=None)
    parser.add_argument("--set", choices=("reference", "emotions"), default="reference",
                        help="reference: the frozen bank; emotions: ADR-012's prerequisite bank")
    args = parser.parse_args(argv)
    generate = generate_emotions_bank if args.set == "emotions" else generate_bank
    args.bank = args.bank or (EMOTIONS_BANK if args.set == "emotions" else DEFAULT_BANK)

    if args.command == "generate":
        write_bank(generate(reference_config()), args.bank)
        print(_summary(args.bank))
        return 0
    try:
        bank = read_bank(args.bank)
    except BankIntegrityError as exc:
        print(f"FROZEN HASH BROKEN: {exc}")
        return 1
    print(_summary(args.bank))
    changes = drift(bank, generate(reference_config()))
    if not any(changes.values()):
        print("production renders every case identically today")
        return 0
    print(f"production renders differently today: {len(changes['no_longer_rendered'])} case(s) no longer rendered, "
          f"{len(changes['newly_rendered'])} new -- sessions on this bank still compare with each other, "
          "but no longer measure today's prompts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
