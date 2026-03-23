"""Long-term memory backed by a local SQLite database.

Stores complete research sessions so the assistant can reference past work.
Uses only the Python standard library (sqlite3, json, pathlib, datetime).
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Schema ─────────────────────────────────────────────────────────────────────
_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query       TEXT    NOT NULL,
    plan_json   TEXT    NOT NULL,
    results_json TEXT   NOT NULL,
    report      TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
"""

_CREATE_IDX_QUERY = """
CREATE INDEX IF NOT EXISTS idx_sessions_query ON sessions (query);
"""

_CREATE_IDX_CREATED = """
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions (created_at);
"""


class MemoryStore:
    """Persist and retrieve research sessions in a local SQLite database."""

    def __init__(self, db_path: str = "data/memory.db") -> None:
        """Open (or create) the database at *db_path*.

        The parent directory is created automatically if it does not exist.
        Any initialisation error is logged but not re-raised so the rest of
        the application can still run without memory support.
        """
        self._db_path = db_path
        self._ok = False  # set to True only when the DB is ready

        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.execute(_CREATE_SESSIONS)
                conn.execute(_CREATE_IDX_QUERY)
                conn.execute(_CREATE_IDX_CREATED)
            self._ok = True
            print(f"[Memory] Database ready at: {db_path}")
        except Exception as exc:
            print(f"[Memory] WARNING: could not initialise database: {exc}")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Return a new database connection with row_factory set."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        """Convert a sqlite3.Row to a plain dict, deserialising JSON columns."""
        d = dict(row)
        for key in ("plan_json", "results_json"):
            if key in d and d[key]:
                try:
                    d[key] = json.loads(d[key])
                except json.JSONDecodeError:
                    pass  # leave as raw string on parse error
        return d

    # ── Public API ─────────────────────────────────────────────────────────────

    def save_session(
        self,
        query: str,
        plan: list[str],
        research_results: list[dict],
        report: str,
        timestamp: str | None = None,
    ) -> int | None:
        """Persist a complete research session.

        Returns the new row *id* on success, or None on failure.
        """
        if not self._ok:
            return None
        try:
            ts = timestamp or datetime.now(timezone.utc).isoformat()
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO sessions (query, plan_json, results_json, report, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        query,
                        json.dumps(plan, ensure_ascii=False),
                        json.dumps(research_results, ensure_ascii=False),
                        report,
                        ts,
                    ),
                )
                row_id: int = cur.lastrowid
            print(f"[Memory] Session saved (id={row_id}).")
            return row_id
        except Exception as exc:
            print(f"[Memory] WARNING: save_session failed: {exc}")
            return None

    def get_recent_sessions(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return the *limit* most recent sessions, newest first.

        Returns an empty list on error.
        """
        if not self._ok:
            return []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, query, plan_json, results_json, report, created_at
                    FROM sessions
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as exc:
            print(f"[Memory] WARNING: get_recent_sessions failed: {exc}")
            return []

    def search_sessions(self, keyword: str) -> list[dict[str, Any]]:
        """Return sessions whose query or report contains *keyword* (case-insensitive).

        Returns an empty list on error.
        """
        if not self._ok:
            return []
        try:
            pattern = f"%{keyword}%"
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, query, plan_json, results_json, report, created_at
                    FROM sessions
                    WHERE query  LIKE ? COLLATE NOCASE
                       OR report LIKE ? COLLATE NOCASE
                    ORDER BY created_at DESC
                    """,
                    (pattern, pattern),
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as exc:
            print(f"[Memory] WARNING: search_sessions failed: {exc}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics about the stored sessions.

        Returns a dict with keys ``total`` (int) and ``latest`` (str | None).
        Returns safe defaults on error.
        """
        if not self._ok:
            return {"total": 0, "latest": None}
        try:
            with self._connect() as conn:
                total: int = conn.execute(
                    "SELECT COUNT(*) FROM sessions"
                ).fetchone()[0]
                latest_row = conn.execute(
                    "SELECT created_at FROM sessions ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
            return {
                "total": total,
                "latest": latest_row[0] if latest_row else None,
            }
        except Exception as exc:
            print(f"[Memory] WARNING: get_stats failed: {exc}")
            return {"total": 0, "latest": None}
