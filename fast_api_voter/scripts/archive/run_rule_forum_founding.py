"""EXP-031: the model arm's party system with the forum answered by a rule instead of the model. CPU only.

Finished experiment script (see archive/README.md): not imported, not type-checked, not collected by CI. From fast_api_voter/:

    python scripts/archive/run_rule_forum_founding.py <out-dir> [seeds, default 1..10] [rate, default 0.8]

The scenario profile as the model arm of EXP-028 ran it (`flagship_config(engine="llm", profile="scenario")`, so every setting
that follows `llm.enabled` is on: party births and deaths, stance step, regime, campaign salience), with the agent turns that
EXP-028's leaders took switched off (nominees, coalition, amendments: the engine's own rules decide them) and the
forum on with `party_moves`. The only client is a rule that answers each forum turn:
  - `found` with probability RATE when the prompt says founding is allowed (N citizens stand nearer to the citizen's positions than
    to their own party's platform is at least the need, and the citizen's party is not locked), else `none`;
  - no post, no stance shift, no join or leave.
The president must stay an agent (`llm.crowd` is false and the mandate needs one, `validate_config`), so its turn is answered by a
turn that does nothing (no position, no bill, no speech).
The chance is drawn from a hash of the seed and the prompt, so a run repeats exactly. RATE 0.8 is EXP-030's rate where allowed.
Any other kind of request raises: the run is meant to ask the client nothing else.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS.parent)]

from api.domain.polity.config import validate_config  # noqa: E402
from api.domain.polity.profiles import flagship_config  # noqa: E402
from api.domain.polity.run_digest import build_digest  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402

STAND = re.compile(
    r"(\d+) of the (\d+) citizens stand nearer to your positions than to their own party's platform, you included; founding a party needs (\d+)"
)
LOCK = "can neither found a party"


class RuleForumClient:
    def __init__(self, seed: int, rate: float) -> None:
        self.seed, self.rate = seed, rate
        self.turns = self.found = self.president_turns = 0

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
        max_tokens: int,
        think: bool = True,
        temperature: float | None = None,
        seed: int | None = None,
        extra_body: dict | None = None,
    ) -> str:
        title = json_schema.get("title")
        if (
            title == "LeaderTurn"
        ):  # the president must stay an agent (the mandate needs one): a turn that does nothing
            self.president_turns += 1
            return json.dumps(
                {
                    "rationale": "rule",
                    "positions": [],
                    "bill": [],
                    "speech": "",
                    "note_to_self": "",
                    "other_initiative": "",
                }
            )
        if title != "ForumTurn":
            raise RuntimeError(
                f"the rule client answers forum and president turns only, got {title!r}"
            )
        m = STAND.search(user_prompt)
        if (
            m is None
        ):  # the stand line is absent only if its wording changed: an arm that never founds would look valid
            raise RuntimeError(
                "no stand line in a forum prompt: the rule cannot read the founding condition"
            )
        allowed = int(m[1]) >= int(m[3]) and LOCK not in user_prompt
        draw = random.Random(
            hashlib.sha256(f"{self.seed}|{user_prompt}".encode()).hexdigest()
        ).random()
        move = "found" if allowed and draw < self.rate else "none"
        self.turns += 1
        self.found += move == "found"
        return json.dumps(
            {
                "rationale": "rule",
                "post": "",
                "note_to_self": "",
                "shift_issue": -1,
                "shift_direction": "none",
                "party_move": move,
                "party_id": -1,
            }
        )

    def count_prompt_tokens(
        self, *, system_prompt: str, user_prompt: str, think: bool = True
    ) -> int:
        return (len(system_prompt) + len(user_prompt)) // 4


def run(out: Path, seed: int, rate: float) -> Path:
    config = flagship_config(
        engine="llm",
        years=8,
        population=100,
        seats=15,
        seed=seed,
        output_dir=out / f"rule-forum-seed{seed}",
        max_batch_replays=0,
        provider="vllm",
        workers=1,
        profile="scenario",
    )
    config = dataclasses.replace(
        config,
        agents=dataclasses.replace(
            config.agents,
            president=True,
            nominees=False,
            amendments=False,
            amendment_stakes=False,
            coalition=False,
        ),
    )
    # what the agents the leaders took out of the run were the only users of (validate_config says which): off, as in the twin
    config = dataclasses.replace(
        config,
        campaign=dataclasses.replace(config.campaign, salience_step=0.0, max_reached=0),
        regime=dataclasses.replace(config.regime, enabled=False),
    )
    validate_config(config)
    client = RuleForumClient(seed, rate)
    journal = run_simulation(config, run_id=f"rule-forum-seed{seed}", llm_client=client)
    digest = build_digest(
        journal,
        config,
        run_id=f"rule-forum-seed{seed}",
        outcome="completed",
        resume=False,
    )
    (journal.parent / "digest.json").write_text(json.dumps(digest))
    print(
        f"seed {seed}: {client.turns} forum turns, {client.found} found; journal {journal}",
        flush=True,
    )
    return journal


if __name__ == "__main__":
    out = Path(sys.argv[1]).expanduser()
    seeds = (
        [int(s) for s in sys.argv[2].split(",")]
        if len(sys.argv) > 2
        else list(range(1, 11))
    )
    rate = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8
    for seed in seeds:
        run(out, seed, rate)
