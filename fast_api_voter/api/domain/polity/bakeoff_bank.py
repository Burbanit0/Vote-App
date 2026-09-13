"""The bake-off case bank's model and file format (S2.2): a case is one request with what
scoring needs; a bank is a content-hashed set of cases, frozen in a JSON Lines file.
Generation lives in bakeoff_cases, the S2.5 controls in bakeoff_controls."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api.domain.polity import llm_schemas

BANK_VERSION = 1
LOGPROB_GATE_FAMILY = "logprob_gate"
BASE_CONTROL = "base"

SCHEMAS: dict[str, dict[str, Any]] = {
    "vote_cast": llm_schemas.VOTE_CAST_JSON_SCHEMA,
    "candidacy_considered": llm_schemas.CANDIDACY_JSON_SCHEMA,
    "party_nomination_choice": llm_schemas.PARTY_NOMINATION_JSON_SCHEMA,
    "campaign_positioning": llm_schemas.POSITIONING_JSON_SCHEMA,
    "representative_response": llm_schemas.RESPONSE_JSON_SCHEMA,
    "pressure_action": llm_schemas.PRESSURE_JSON_SCHEMA,
    "reaction_to_event": llm_schemas.REACTION_JSON_SCHEMA,
    "chamber_deliberation": llm_schemas.CHAMBER_JSON_SCHEMA,
    "coalition_decision": llm_schemas.COALITION_JSON_SCHEMA,
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Case:
    case_id: str
    family: str
    decision_type: str
    system_prompt: str
    user_prompt: str
    think: bool
    budget: dict[str, Any]
    """{"rule": "fixed", "max_tokens": n}, or {"rule": "probe" | "allowance", "chunk_size": n,
    "allowance": <ModelProfile field>} -- see resolve_max_tokens."""
    unit_ids: tuple[int, ...]
    """The citizens (or parties) the request decides for, in the order it lists them."""
    labels: dict[str, Any]
    """What scoring needs; `labels["kind"]` is "truth", "contrast" or "permutation"."""

    def to_json(self) -> dict[str, Any]:
        return {**dataclasses.asdict(self), "unit_ids": list(self.unit_ids)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Case:
        return cls(**{**data, "unit_ids": tuple(data["unit_ids"])})


def make_case(
    *, family: str, decision_type: str, system_prompt: str, user_prompt: str, think: bool,
    budget: dict[str, Any], unit_ids: Sequence[int], labels: dict[str, Any],
) -> Case:
    body = {
        "family": family, "decision_type": decision_type, "system_prompt": system_prompt, "user_prompt": user_prompt,
        "think": think, "budget": budget, "unit_ids": list(unit_ids), "labels": labels,
    }
    return Case(
        case_id=_sha256(_canonical(body))[:16], family=family, decision_type=decision_type, system_prompt=system_prompt,
        user_prompt=user_prompt, think=think, budget=budget, unit_ids=tuple(unit_ids), labels=labels,
    )


@dataclass(frozen=True)
class CaseBank:
    reference: dict[str, Any]
    """The model and config the requests were rendered for."""
    cases: tuple[Case, ...]
    schemas: dict[str, dict[str, Any]] = field(default_factory=lambda: dict(SCHEMAS))
    version: int = BANK_VERSION

    @property
    def content_sha256(self) -> str:
        return _sha256(_canonical({
            "version": self.version, "reference": self.reference, "schemas": self.schemas,
            "cases": [case.to_json() for case in self.cases],
        }))

    def families(self) -> list[str]:
        return sorted({case.family for case in self.cases})


class BankIntegrityError(ValueError):
    """A case bank file whose content no longer matches the hash it was frozen with."""


def write_bank(bank: CaseBank, path: Path) -> None:
    """JSON Lines: a header line (version, reference, schemas, hash), then one case per line."""
    header = {"version": bank.version, "reference": bank.reference, "schemas": bank.schemas, "content_sha256": bank.content_sha256}
    lines = [_canonical(header)] + [_canonical(case.to_json()) for case in bank.cases]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_bank(path: Path) -> CaseBank:
    header_line, *case_lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    header = json.loads(header_line)
    bank = CaseBank(
        reference=header["reference"], schemas=header["schemas"], version=header["version"],
        cases=tuple(Case.from_json(json.loads(line)) for line in case_lines),
    )
    if bank.content_sha256 != header["content_sha256"]:
        raise BankIntegrityError(
            f"{path}: content hash {bank.content_sha256[:16]} does not match the frozen {header['content_sha256'][:16]}"
        )
    return bank
