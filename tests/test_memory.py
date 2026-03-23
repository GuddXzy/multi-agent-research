"""Tests for MemoryStore — fully offline, no LLM or network required.

Each test gets its own isolated temporary database that is deleted afterward.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.memory import MemoryStore


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path: Path) -> MemoryStore:
    """Yield a fresh MemoryStore backed by a temp file; cleaned up automatically."""
    db_file = tmp_path / "test_memory.db"
    store = MemoryStore(str(db_file))
    return store


# ── Sample data ────────────────────────────────────────────────────────────────

_PLAN_A = ["Research React", "Research Vue", "Compare both"]
_RESULTS_A = [
    {"task": "Research React", "result": "React is a JS library.", "status": "success"},
    {"task": "Research Vue",   "result": "Vue is a JS framework.", "status": "success"},
]
_REPORT_A = "# React vs Vue\n\nReact and Vue are both popular choices."

_PLAN_B = ["Intro to Python", "Python in science"]
_RESULTS_B = [
    {"task": "Intro to Python", "result": "Python is versatile.", "status": "success"},
]
_REPORT_B = "# Python Overview\n\nPython is widely used in data science."


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestSaveAndRetrieve:
    def test_save_returns_id(self, db: MemoryStore) -> None:
        row_id = db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_retrieve_query(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        sessions = db.get_recent_sessions(limit=1)
        assert len(sessions) == 1
        assert sessions[0]["query"] == "React vs Vue"

    def test_plan_deserialised(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        s = db.get_recent_sessions(limit=1)[0]
        assert s["plan_json"] == _PLAN_A

    def test_results_deserialised(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        s = db.get_recent_sessions(limit=1)[0]
        assert s["results_json"] == _RESULTS_A

    def test_report_stored(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        s = db.get_recent_sessions(limit=1)[0]
        assert "React" in s["report"]

    def test_created_at_present(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        s = db.get_recent_sessions(limit=1)[0]
        assert s["created_at"]  # non-empty timestamp string

    def test_custom_timestamp(self, db: MemoryStore) -> None:
        ts = "2025-01-01T00:00:00+00:00"
        db.save_session("Q", [], [], "", timestamp=ts)
        s = db.get_recent_sessions(limit=1)[0]
        assert s["created_at"] == ts


class TestRecentSessions:
    def test_multiple_sessions_order(self, db: MemoryStore) -> None:
        """Most recent session should appear first."""
        db.save_session("First query",  _PLAN_A, _RESULTS_A, _REPORT_A,
                        timestamp="2025-01-01T10:00:00+00:00")
        db.save_session("Second query", _PLAN_B, _RESULTS_B, _REPORT_B,
                        timestamp="2025-01-02T10:00:00+00:00")
        sessions = db.get_recent_sessions(limit=5)
        assert sessions[0]["query"] == "Second query"
        assert sessions[1]["query"] == "First query"

    def test_limit_respected(self, db: MemoryStore) -> None:
        for i in range(6):
            db.save_session(f"Query {i}", [], [], "")
        assert len(db.get_recent_sessions(limit=3)) == 3

    def test_limit_larger_than_total(self, db: MemoryStore) -> None:
        db.save_session("Only one", [], [], "")
        assert len(db.get_recent_sessions(limit=10)) == 1


class TestSearch:
    def test_find_by_query_keyword(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        db.save_session("Python overview", _PLAN_B, _RESULTS_B, _REPORT_B)

        results = db.search_sessions("React")
        assert len(results) == 1
        assert results[0]["query"] == "React vs Vue"

    def test_find_by_report_keyword(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        db.save_session("Python overview", _PLAN_B, _RESULTS_B, _REPORT_B)

        # "data science" only appears in _REPORT_B
        results = db.search_sessions("data science")
        assert len(results) == 1
        assert results[0]["query"] == "Python overview"

    def test_case_insensitive(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        assert len(db.search_sessions("react")) == 1
        assert len(db.search_sessions("REACT")) == 1

    def test_no_match_returns_empty(self, db: MemoryStore) -> None:
        db.save_session("React vs Vue", _PLAN_A, _RESULTS_A, _REPORT_A)
        assert db.search_sessions("quantum physics") == []

    def test_multiple_matches(self, db: MemoryStore) -> None:
        db.save_session("React intro", _PLAN_A, _RESULTS_A, "React report")
        db.save_session("React advanced", _PLAN_A, _RESULTS_A, "More React")
        db.save_session("Vue basics", _PLAN_B, _RESULTS_B, "Vue report")

        results = db.search_sessions("React")
        assert len(results) == 2


class TestStats:
    def test_empty_stats(self, db: MemoryStore) -> None:
        stats = db.get_stats()
        assert stats["total"] == 0
        assert stats["latest"] is None

    def test_total_count(self, db: MemoryStore) -> None:
        db.save_session("Q1", [], [], "")
        db.save_session("Q2", [], [], "")
        db.save_session("Q3", [], [], "")
        assert db.get_stats()["total"] == 3

    def test_latest_timestamp(self, db: MemoryStore) -> None:
        db.save_session("Q1", [], [], "", timestamp="2025-01-01T00:00:00+00:00")
        db.save_session("Q2", [], [], "", timestamp="2025-06-15T12:00:00+00:00")
        stats = db.get_stats()
        assert stats["latest"] == "2025-06-15T12:00:00+00:00"

    def test_stats_increment(self, db: MemoryStore) -> None:
        assert db.get_stats()["total"] == 0
        db.save_session("Q", [], [], "")
        assert db.get_stats()["total"] == 1


class TestEmptyDatabase:
    def test_get_recent_empty(self, db: MemoryStore) -> None:
        assert db.get_recent_sessions() == []

    def test_search_empty(self, db: MemoryStore) -> None:
        assert db.search_sessions("anything") == []

    def test_stats_empty(self, db: MemoryStore) -> None:
        stats = db.get_stats()
        assert stats == {"total": 0, "latest": None}


class TestResiliency:
    def test_bad_db_does_not_raise(self, tmp_path: Path) -> None:
        """MemoryStore whose sqlite3 connection fails must not crash the caller.

        We mock sqlite3.connect to simulate a DB that is always unavailable
        (platform-independent — avoids relying on unwritable path behaviour).
        """
        import sqlite3 as _sqlite3
        from unittest.mock import patch

        with patch(
            "src.memory.sqlite3.connect",
            side_effect=_sqlite3.OperationalError("simulated DB unavailable"),
        ):
            store = MemoryStore(str(tmp_path / "bad.db"))

        # _ok is False, so all methods return safe defaults without raising
        assert store.get_recent_sessions() == []
        assert store.search_sessions("x") == []
        assert store.get_stats()["total"] == 0
        assert store.save_session("q", [], [], "") is None
