"""Permutation and rendering controls for the collapse probes (S2.5).

A collapse reading -- the same answer whatever the input -- could be the model reading
the content and not caring, or the model latching onto the surface of the request: the
first code in a table, the first unit in a batch, a JSON layout. The controls change the
surface and keep the content, so a sensitivity that survives them is about the content:

- `renumbered`: the scenario re-captured through production with every citizen or party
  id reversed, which also reverses the order units are listed in (bakeoff_cases).
- `codes`: the answer field's codes cyclically relabelled throughout the system prompt --
  every table line and every rule that names them -- with the table re-sorted by the new
  codes, so both the numbers and the order of the options move. The JSON schema lists
  the set of legal codes, which a bijection keeps, so it is unchanged; answers are mapped
  back to the canonical codes before production decodes them.
- `rendering:indented` and `rendering:paths`: the same user-prompt content as indented
  JSON with keys in reverse order, and as one `path = value` line per field.

With the production rendering that is at least three renderings of every contrast case.
Every transformation here is checked to be exactly invertible before a case is made.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from api.domain.polity.bakeoff_bank import BASE_CONTROL, Case, make_case
from api.domain.polity.codebook import CampaignMotif, ChamberMotif, CoalitionAction, ReactionMotif, Stance


@dataclass(frozen=True)
class CodeField:
    field: str
    codes: type[IntEnum]
    bare: bool
    """Whether the codes are distinctive enough (three digits) to relabel wherever they
    appear; single-digit codes are relabelled only in table lines and `field=code` rules."""


CODE_FIELDS: dict[str, CodeField] = {
    "representative_response": CodeField("stance", Stance, bare=False),
    "coalition_decision": CodeField("action", CoalitionAction, bare=False),
    "chamber_deliberation": CodeField("motif", ChamberMotif, bare=True),
    "reaction_to_event": CodeField("motif", ReactionMotif, bare=True),
    "campaign_positioning": CodeField("motif", CampaignMotif, bare=True),
}


def _table_line(spec: CodeField) -> re.Pattern[str]:
    names = "|".join(member.name for member in spec.codes)
    return re.compile(rf"^(?P<prefix>.*?)(?P<code>\d+) = (?P<name>{names})$")


def present_codes(system_prompt: str, spec: CodeField) -> list[int]:
    """The codes the prompt's option table lists for this field, in ascending order."""
    pattern = _table_line(spec)
    found = {int(m["code"]) for line in system_prompt.splitlines() if (m := pattern.match(line)) and spec.codes[m["name"]].value == int(m["code"])}
    return sorted(found)


def cyclic_mapping(codes: list[int]) -> dict[int, int]:
    """Each code to the next one up, the highest to the lowest: no code keeps its number."""
    return {code: codes[(i + 1) % len(codes)] for i, code in enumerate(codes)}


def _relabel_text(text: str, mapping: dict[int, int], spec: CodeField) -> str:
    """Every mention of a mapped code, replaced at once (never one code after another,
    which would relabel a code twice)."""
    codes = "|".join(str(code) for code in sorted(mapping, reverse=True))
    if spec.bare:
        pattern = re.compile(rf"(?<![\w.])(?P<code>{codes})(?![\w.])")
    else:
        names = "|".join(member.name for member in spec.codes)
        pattern = re.compile(rf"(?<![\w.])(?P<code>{codes})(?= = (?:{names})\b)|(?<=\b{spec.field}=)(?P<rule>{codes})\b")
    return pattern.sub(lambda m: str(mapping[int(m.group(m.lastgroup or "code"))]), text)


def _sort_tables(text: str, spec: CodeField) -> str:
    """Each run of consecutive option-table lines, re-sorted by code; a label written
    before the first entry ("stance : 1 = ...") stays on the first line."""
    pattern = _table_line(spec)
    lines = text.split("\n")
    out: list[str] = []
    run: list[re.Match[str]] = []

    def flush() -> None:
        if run:
            prefix = run[0]["prefix"]
            entries = sorted((int(m["code"]), m["name"]) for m in run)
            out.extend(f"{prefix if i == 0 else ''}{code} = {name}" for i, (code, name) in enumerate(entries))
            run.clear()

    for line in lines:
        match = pattern.match(line)
        if match and (not run or not match["prefix"]):
            run.append(match)
            continue
        flush()
        if match:
            run.append(match)
        else:
            out.append(line)
    flush()
    return "\n".join(out)


def relabel_codes(system_prompt: str, mapping: dict[int, int], spec: CodeField) -> str:
    return _sort_tables(_relabel_text(system_prompt, mapping, spec), spec)


class UnsafeControlError(ValueError):
    """A transformation that does not invert exactly -- the control would change content."""


def permute_codes(case: Case) -> Case:
    spec = CODE_FIELDS[case.decision_type]
    mapping = cyclic_mapping(present_codes(case.system_prompt, spec))
    if len(mapping) < 2:
        raise UnsafeControlError(f"{case.family}: fewer than two {spec.field} codes in the option table")
    permuted = relabel_codes(case.system_prompt, mapping, spec)
    inverse = {new: old for old, new in mapping.items()}
    if permuted == case.system_prompt or relabel_codes(permuted, inverse, spec) != case.system_prompt:
        raise UnsafeControlError(f"{case.family}: relabelling {spec.field} codes does not invert exactly")
    labels = {**case.labels, "control": "codes", "codes": {"field": spec.field, "to_canonical": {str(new): old for new, old in inverse.items()}}}
    if case.labels.get("value") is not None and case.labels["field"] == spec.field:
        offset = int(case.labels.get("value_char_offset", 0))
        canonical = _code_with_digit(mapping, offset, case.labels["value"])
        labels["value"] = str(mapping[canonical])[offset]
    return _variant(case, labels, system_prompt=permuted)


def _code_with_digit(mapping: dict[int, int], offset: int, digit: str) -> int:
    """The canonical code whose digit at `offset` is the one a reading asks for."""
    (code,) = [code for code in mapping if str(code)[offset] == digit]
    return code


def canonical_content(case: Case, content: str) -> str:
    """An answer to a code-permuted case, with its codes mapped back to the canonical ones
    production decodes and validates. Content that is not a decision batch is returned
    unchanged, for production's decoder to reject."""
    codes = case.labels.get("codes")
    if codes is None:
        return content
    try:
        batch = json.loads(content)
        decisions = batch["decisions"]
    except (ValueError, TypeError, KeyError):
        return content
    field, to_canonical = codes["field"], codes["to_canonical"]
    for decision in decisions if isinstance(decisions, list) else []:
        if isinstance(decision, dict) and str(decision.get(field)) in to_canonical:
            decision[field] = to_canonical[str(decision[field])]
    return json.dumps(batch)


# ── renderings ────────────────────────────────────────────────────────────

def _reverse_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _reverse_keys(value[key]) for key in sorted(value, reverse=True)}
    if isinstance(value, list):
        return [_reverse_keys(item) for item in value]
    return value


def render_indented(user_prompt: str) -> str:
    return json.dumps(_reverse_keys(json.loads(user_prompt)), indent=2, ensure_ascii=False)


def _children(value: Any, path: str) -> list[tuple[Any, str]] | None:
    """A branch's (child, path) pairs; None for a leaf -- a scalar, an empty container, or a
    list of scalars, which stays one JSON value on its line."""
    if isinstance(value, dict) and value:
        return [(item, f"{path}.{key}" if path else key) for key, item in value.items()]
    if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        return [(item, f"{path}[{i}]") for i, item in enumerate(value)]
    return None


def _path_lines(value: Any, path: str) -> list[str]:
    children = _children(value, path)
    if children is None:
        return [f"{path} = {json.dumps(value, ensure_ascii=False)}"]
    return [line for item, child_path in children for line in _path_lines(item, child_path)]


def render_paths(user_prompt: str) -> str:
    return "\n".join(_path_lines(json.loads(user_prompt), ""))


def parse_paths(text: str) -> Any:
    """render_paths' inverse, used to prove a rendering keeps every value."""
    root: dict[str, Any] = {}
    for line in text.splitlines():
        path, _, raw = line.partition(" = ")
        _assign(root, re.findall(r"[^.\[\]]+|\[\d+\]", path), json.loads(raw))
    return root


def _assign(node: Any, steps: list[str], value: Any) -> None:
    for step, following in zip(steps, steps[1:]):
        key: Any = int(step[1:-1]) if step.startswith("[") else step
        default: Any = [] if following.startswith("[") else {}
        if isinstance(node, list):
            while len(node) <= key:
                node.append(None)
            node[key] = node[key] if node[key] is not None else default
        else:
            node.setdefault(key, default)
        node = node[key]
    last: Any = int(steps[-1][1:-1]) if steps[-1].startswith("[") else steps[-1]
    if isinstance(node, list):
        while len(node) <= last:
            node.append(None)
    node[last] = value


RENDERINGS: dict[str, tuple[Callable[[str], str], Callable[[str], Any]]] = {
    "rendering:indented": (render_indented, json.loads),
    "rendering:paths": (render_paths, parse_paths),
}


def render(case: Case, name: str) -> Case:
    renderer, parser = RENDERINGS[name]
    rendered = renderer(case.user_prompt)
    if parser(rendered) != json.loads(case.user_prompt):
        raise UnsafeControlError(f"{case.family}: the {name} rendering does not keep every value")
    return _variant(case, {**case.labels, "control": name}, user_prompt=rendered)


def _variant(case: Case, labels: dict[str, Any], *, system_prompt: str | None = None, user_prompt: str | None = None) -> Case:
    return make_case(
        family=case.family, decision_type=case.decision_type,
        system_prompt=case.system_prompt if system_prompt is None else system_prompt,
        user_prompt=case.user_prompt if user_prompt is None else user_prompt,
        think=case.think, budget=case.budget, unit_ids=case.unit_ids, labels=labels,
    )


def controls_for(cases: Iterable[Case]) -> list[Case]:
    """The code-permuted and re-rendered variants of every base contrast case."""
    variants: list[Case] = []
    for case in cases:
        if case.labels["kind"] == "contrast" and case.labels.get("control", BASE_CONTROL) == BASE_CONTROL:
            variants.append(permute_codes(case))
            variants += [render(case, name) for name in RENDERINGS]
    return variants
