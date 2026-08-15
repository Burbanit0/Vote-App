"""
api.domain.polity.compaction — post-run analytical store (§16.6, v4 storage
lot).

§16.1 defines two strictly separated flow regimes: a "hot" one during the
run (append-only journal, never read, never indexed, never queried -- see
journal.py's own docstring), and a "cold" one after it, where "une étape de
compaction/indexation transforme le journal brut en base analytique, avec
index sur citizen_id, tick, event_type, et décodage du codebook par
jointure (§3.7.4)". This module IS that cold-regime step.

§16.6's own open question ("DuckDB par run confirmé, ou Postgres par
cohérence avec la stack existante ?") is resolved here: DuckDB. There is no
existing SQL stack in fast_api_voter to be "cohérent avec" -- Redis is the
only server dependency, and it is a cache, not a source of truth. The one
Postgres instance anywhere in the repo (analytics/docker-compose.yml) runs
Umami web analytics in a wholly separate project. DuckDB costs one pinned
dependency and zero new infrastructure, and "un fichier .duckdb par run"
composes directly with journal.py's existing one-directory-per-run layout.

The design doc's own file tree (§1) assigns "compaction/indexation post-run
(§16.6)" to a file named indexer.py -- but the actual, already-shipped
indexer.py (v4 Lot 8) explicitly declined that scope in its own docstring
("It is NOT §16.6's DuckDB compaction or codebook decoding -- both remain
unbuilt; this is a metrics reducer over a JSONL file, nothing more"). This
module is the deliberate resolution of that tension: a new module, built on
top of indexer.read_journal rather than by expanding indexer.py's
already-shipped, already-tested scope.

Decode scope: `motif` ONLY. §3.7.2's motif codes are globally unique by
design (the "préfixe de catégorie × 100" convention), which is what makes a
single flat codebook_motifs table safe -- see codebook.motif_labels()'s own
docstring for the verified collision audit. The OTHER §3.7.1 enumerated
fields (act, stance, bf, action, outcome, dt, role, office, path) live
inside `payload`, each in its own small, non-globally-unique code space,
meaningful only for specific event_types -- decoding them needs an
(event_type, field) -> enum routing table whose only real consumer would be
a future §16.7 "biographie citoyenne" lot, which is out of scope here.
DuckDB already makes them one-liners at query time without that machinery,
e.g. `payload ->> '$.act'`; the four boolean fields (blank, confidence,
lame_duck, party_change) are self-describing and need no codebook at all.
A future lot extending this is a pure addition (a second codebook table +
routing map in codebook.py, a wider view) -- it never needs to touch
citizen_events, because decoding is a JOIN, never a rewrite (see below).

§3.7.4: "le décodage se fait uniquement à l'indexation post-run (§16.6),
par jointure contre le codebook figé -- jamais par réécriture du journal
brut." This is enforced structurally: `citizen_events` is byte-faithful to
the JSONL journal and carries no decoded column; `citizen_events_decoded`
is a VIEW joining it against `codebook_motifs`, so it cannot drift from the
raw table and materializes nothing.

RunMetrics (indexer.py) is deliberately NOT persisted here -- see §16.2:
"les métriques du §10 deviennent des vues dérivées, pas une seconde source
de vérité à maintenir." Writing RunMetrics into tables would create exactly
that second source of truth; run_acceptance_comparison.py's existing
metrics.json-per-run already serves cross-run comparison.

The module's own acceptance criterion is §16.6's two worked examples,
answerable directly against a compacted store:

    -- "tous les événements du citoyen #4172"
    SELECT tick, event_type, motif_label, payload
    FROM citizen_events_decoded WHERE citizen_id = 4172 ORDER BY event_id;

    -- "distribution des motifs de vote blanc par année"
    -- NB: parenthesize a `->>` JSON extraction combined with AND/=  -- an
    -- unparenthesized `x = 'a' AND payload ->> '$.k' = 'b'` is a real
    -- DuckDB 1.5.5 operator-precedence trap (confirmed live, not assumed):
    -- it silently reparses the boolean expression and tries to CAST the
    -- whole payload to a number instead of extracting '$.k' first.
    SELECT tick / 4 AS year, motif_label, count(*)
    FROM citizen_events_decoded
    WHERE event_type = 'vote_cast' AND (payload ->> '$.blank') = '1'
    GROUP BY 1, 2 ORDER BY 1, 2;
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import duckdb

from api.domain.polity.codebook import CODEBOOK_VERSION, motif_labels
from api.domain.polity.config import PolityConfig
from api.domain.polity.indexer import read_journal

DEFAULT_DB_FILENAME = "events.duckdb"

# §16.3's table order, exactly. `payload` is DuckDB's native JSON type (not
# VARCHAR): it stores the text as-is, so a value bound via CAST(? AS JSON)
# from json.dumps(payload, sort_keys=True) is byte-faithful to what
# Journal.write wrote, while also unlocking `->>`/json_extract at query
# time with no per-query cast.
_CREATE_CITIZEN_EVENTS = """
CREATE TABLE citizen_events (
    run_id           VARCHAR NOT NULL,
    event_id         BIGINT  NOT NULL,
    codebook_version VARCHAR NOT NULL,
    tick             INTEGER NOT NULL,
    citizen_id       INTEGER,
    event_type       VARCHAR NOT NULL,
    payload          JSON    NOT NULL,
    motif            VARCHAR,
    rationale        VARCHAR
)
"""

# §16.1: "avec index sur citizen_id, tick, event_type" -- verbatim.
_CREATE_INDEXES = (
    "CREATE INDEX idx_citizen_events_citizen_id ON citizen_events (citizen_id)",
    "CREATE INDEX idx_citizen_events_tick ON citizen_events (tick)",
    "CREATE INDEX idx_citizen_events_event_type ON citizen_events (event_type)",
)

_INSERT_EVENT = """
INSERT INTO citizen_events VALUES (?, ?, ?, ?, ?, ?, CAST(? AS JSON), ?, ?)
"""

# One row per distinct code, deliberately -- NOT one row per (enum, code).
# Code 301 exists in both ResponseMotif and PressureMotif with the same
# label (see motif_labels()'s own docstring); an `enum_name` column would
# produce two rows for it, and the decoded view's LEFT JOIN would then fan
# out and duplicate every representative_response/pressure_action row
# carrying that motif. Keyed on `code` alone, this is structurally
# impossible.
_CREATE_CODEBOOK_MOTIFS = """
CREATE TABLE codebook_motifs (
    code             INTEGER NOT NULL,
    label            VARCHAR NOT NULL,
    codebook_version VARCHAR NOT NULL
)
"""

_INSERT_MOTIF = "INSERT INTO codebook_motifs VALUES (?, ?, ?)"

# TRY_CAST + LEFT JOIN, deliberately: a non-numeric motif (never written
# today, but not forbidden by the schema) or a code with no entry in
# codebook_motifs (e.g. an older/newer codebook_version -- see below) keeps
# its row with motif_label = NULL, rather than erroring the whole view
# (plain CAST) or silently dropping the row (INNER JOIN).
#
# No codebook_version predicate on the join: codebook.py's own hard rule is
# that a code is never reassigned (code 7 permanently retired) -- a code's
# meaning is therefore stable across versions, so a journal written under
# an older codebook_version still decodes correctly against the current
# table, and archiving an old run stays possible. Both facts remain
# queryable as plain data: citizen_events.codebook_version is the journal's
# own per-row value; codebook_motifs.codebook_version is the version this
# code was compacted with.
_CREATE_DECODED_VIEW = """
CREATE VIEW citizen_events_decoded AS
SELECT e.*, m.label AS motif_label
FROM citizen_events AS e
LEFT JOIN codebook_motifs AS m ON TRY_CAST(e.motif AS INTEGER) = m.code
"""


class PolityCompactionError(RuntimeError):
    """Raised when a journal cannot be compacted -- mirrors PolityConfigError
    / PolityCodebookError's loud-failure idiom."""


def compact_events(
    events: Iterable[Mapping[str, Any]],
    connection: duckdb.DuckDBPyConnection,
    *,
    decode_codebook: bool = True,
) -> int:
    """The real function: creates §16.3's schema on `connection`, inserts
    one row per event in the given order, creates §16.1's three indexes,
    and -- when `decode_codebook` -- the frozen codebook table plus the
    decoded view (§3.7.4). Returns the row count.

    Takes an Iterable of already-parsed event dicts and an open connection,
    so every unit test can hand-build a small event list against
    duckdb.connect(':memory:') -- no tmp_path, no Journal, no run. Same
    Iterable-core / Path-wrapper split, and the same testing reason, as
    indexer.index_events / index_run."""
    connection.execute(_CREATE_CITIZEN_EVENTS)

    rows = [
        (
            event["run_id"],
            event["event_id"],
            event["codebook_version"],
            event["tick"],
            event.get("citizen_id"),
            event["event_type"],
            json.dumps(event["payload"], sort_keys=True),
            event.get("motif"),
            event.get("rationale"),
        )
        for event in events
    ]
    if rows:
        connection.executemany(_INSERT_EVENT, rows)

    for statement in _CREATE_INDEXES:
        connection.execute(statement)

    if decode_codebook:
        connection.execute(_CREATE_CODEBOOK_MOTIFS)
        motif_rows = [(code, label, CODEBOOK_VERSION) for code, label in motif_labels().items()]
        if motif_rows:
            connection.executemany(_INSERT_MOTIF, motif_rows)
        connection.execute(_CREATE_DECODED_VIEW)

    return len(rows)


def compact_run(journal_path: Path, config: PolityConfig, *, db_path: Path | None = None) -> Path:
    """Thin wrapper: streams `journal_path` through indexer.read_journal
    into compact_events, into a .duckdb file beside the journal. Returns
    that path.

    db_path defaults to journal_path.with_name(DEFAULT_DB_FILENAME) --
    output_dir/<run_id>/events.duckdb, mirroring events.jsonl, matching
    §16.6's "un fichier .duckdb par run" and journal.py's own existing
    one-directory-per-run layout.

    Any existing file at db_path is deleted first: the .duckdb store is a
    DERIVED artifact, never a source of truth, so compaction must be a
    pure function of the journal -- a half-written database from an
    interrupted compaction must never survive into the next one."""
    if config.journal.format != "jsonl":
        raise PolityCompactionError(
            f"journal.format {config.journal.format!r} has no compaction reader -- "
            "only 'jsonl' is supported"
        )

    db_path = db_path or journal_path.with_name(DEFAULT_DB_FILENAME)
    db_path.unlink(missing_ok=True)

    with contextlib.closing(duckdb.connect(str(db_path))) as connection:
        compact_events(read_journal(journal_path), connection, decode_codebook=config.journal.decode_codebook_on_index)

    return db_path
