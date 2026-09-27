"""
fast_api_voter/scripts/llm_test_harness/storage.py

SQLite storage for experiments and trials -- one file per project (not
per experiment), so trials from different experiments can be queried
against each other over time (the design brief's own stated goal: "tous
les essais ou le conteneur avait plus de N prompts en cache" across
experiments, not within one). Stdlib sqlite3 only, no ORM.

Immutability of a registered experiment is enforced by ABSENCE of an
update function, not by a database-level constraint -- there is no
update_experiment() anywhere in this module. Fixing a registration
mistake means registering a new experiment_id, which is itself the
correct behavior (see registration.py's own docstring), not a workaround.

Foreign-key enforcement is turned on explicitly (`PRAGMA foreign_keys =
ON`) -- SQLite defines the `REFERENCES` constraint in the schema but does
NOT enforce it by default, so a trial row naming a never-registered
experiment_id would otherwise insert silently.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "harness.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    hypothesis TEXT NOT NULL,
    decision_criterion TEXT NOT NULL,
    threshold REAL,
    comparison TEXT,
    metric TEXT,
    planned_n INTEGER NOT NULL,
    budget_description TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    git_commit TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
    trial_number INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    environment_before TEXT NOT NULL,
    environment_after TEXT NOT NULL,
    ok INTEGER NOT NULL,
    finish_reason TEXT,
    truncated INTEGER,
    latency_seconds REAL,
    decoded_tokens INTEGER,
    detail TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_trials_experiment_id ON trials (experiment_id);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Opens (creating if needed) the harness database and ensures the
    schema exists. `db_path` defaults to DEFAULT_DB_PATH -- overridable
    per-call so tests never touch the real, gitignored project database
    (see tests/test_storage.py's own tmp_path fixture)."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    return conn


def insert_experiment(conn: sqlite3.Connection, row: dict[str, object]) -> None:
    """Inserts one experiment row. Raises sqlite3.IntegrityError on a
    duplicate experiment_id (PRIMARY KEY) -- deliberately not an
    INSERT OR REPLACE, since silently overwriting a pre-registration
    would defeat the whole point of pre-registering it."""
    conn.execute(
        """INSERT INTO experiments
           (experiment_id, hypothesis, decision_criterion, threshold, comparison,
            metric, planned_n, budget_description, registered_at, git_commit)
           VALUES (:experiment_id, :hypothesis, :decision_criterion, :threshold,
                   :comparison, :metric, :planned_n, :budget_description,
                   :registered_at, :git_commit)""",
        row,
    )
    conn.commit()


def get_experiment(conn: sqlite3.Connection, experiment_id: str) -> sqlite3.Row | None:
    cursor = conn.execute("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,))
    # sqlite3's stubs type fetchone() as Any regardless of row_factory --
    # cast rather than # type: ignore, since the return type IS correct
    # (storage.connect always sets row_factory = sqlite3.Row), just not
    # statically inferred.
    return cast("sqlite3.Row | None", cursor.fetchone())


def insert_trial(conn: sqlite3.Connection, row: dict[str, object]) -> None:
    conn.execute(
        """INSERT INTO trials
           (experiment_id, trial_number, started_at, finished_at,
            environment_before, environment_after, ok, finish_reason,
            truncated, latency_seconds, decoded_tokens, detail)
           VALUES (:experiment_id, :trial_number, :started_at, :finished_at,
                   :environment_before, :environment_after, :ok, :finish_reason,
                   :truncated, :latency_seconds, :decoded_tokens, :detail)""",
        row,
    )
    conn.commit()


def get_trials(conn: sqlite3.Connection, experiment_id: str) -> list[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT * FROM trials WHERE experiment_id = ? ORDER BY trial_number", (experiment_id,)
    )
    return cursor.fetchall()
