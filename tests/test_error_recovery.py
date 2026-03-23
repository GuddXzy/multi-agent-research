"""Tests for the Researcher error-recovery (retry) mechanism and Writer
failure-awareness.

All tests are fully offline — no Ollama, no network required.
LLM calls and _react_loop are mocked where needed.
"""

import time
from unittest.mock import MagicMock, call, patch

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_researcher_state(task: str = "Test sub-task") -> dict:
    return {
        "query": "Test query",
        "plan": [task],
        "research_results": [],
        "current_task_index": 0,
        "report": "",
        "error": None,
        "human_approved": True,
        "human_feedback": None,
    }


# ── test_researcher_retry ──────────────────────────────────────────────────────

def test_researcher_retry() -> None:
    """_react_loop fails twice then succeeds on the 3rd attempt.

    Verifies:
    - result status is "success"
    - result text is the value returned on the successful call
    - sleep was called twice (once per failed attempt before the last)
    - retry log messages were printed
    """
    from src.agents.researcher import researcher_node

    attempts = {"count": 0}

    def flaky_react_loop(task, llm, tool_map):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError(f"Simulated tool timeout (attempt {attempts['count']})")
        return "Research successful on attempt 3"

    state = _make_researcher_state()

    with (
        patch("src.agents.researcher._react_loop", side_effect=flaky_react_loop),
        patch("src.agents.researcher.get_llm", return_value=MagicMock()),
        patch("src.agents.researcher.get_all_tools", return_value=[]),
        patch("src.agents.researcher.time.sleep") as mock_sleep,
    ):
        result = researcher_node(state)

    assert attempts["count"] == 3, "Expected exactly 3 calls to _react_loop"

    records = result["research_results"]
    assert len(records) == 1
    assert records[0]["status"] == "success"
    assert records[0]["result"] == "Research successful on attempt 3"
    assert records[0]["task"] == state["plan"][0]

    # sleep called between attempt 1→2 and 2→3 (not after the successful one)
    assert mock_sleep.call_count == 2


# ── test_researcher_all_fail ───────────────────────────────────────────────────

def test_researcher_all_fail() -> None:
    """_react_loop always raises.

    Verifies:
    - result status is "failed"
    - result text starts with "[FAILED]"
    - current_task_index is still incremented (flow continues)
    - sleep was called MAX_TASK_ATTEMPTS-1 times
    """
    from src.agents.researcher import researcher_node
    from src.config import MAX_TASK_ATTEMPTS, RETRY_SLEEP

    state = _make_researcher_state("Impossible task")

    with (
        patch(
            "src.agents.researcher._react_loop",
            side_effect=RuntimeError("Persistent network error"),
        ),
        patch("src.agents.researcher.get_llm", return_value=MagicMock()),
        patch("src.agents.researcher.get_all_tools", return_value=[]),
        patch("src.agents.researcher.time.sleep") as mock_sleep,
    ):
        result = researcher_node(state)

    records = result["research_results"]
    assert len(records) == 1, "Should still record one result even on failure"

    entry = records[0]
    assert entry["status"] == "failed"
    assert entry["result"].startswith("[FAILED]")
    assert "Persistent network error" in entry["result"]
    assert entry["task"] == "Impossible task"

    # task index advances so the graph keeps moving
    assert result["current_task_index"] == 1

    # sleep called between each failed attempt except the last
    assert mock_sleep.call_count == MAX_TASK_ATTEMPTS - 1


# ── test_writer_handles_failures ──────────────────────────────────────────────

def test_writer_handles_failures() -> None:
    """Writer receives a mixed state (1 success + 1 failed).

    Verifies:
    - report contains the successful findings
    - report contains a 'Research Limitations' section
    - the failed task name/reason appears in that section
    """
    from src.agents.writer import writer_node

    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = (
        "# Test Report\n\n"
        "## Abstract\nThis is a test.\n\n"
        "## Research Findings\n### Task 1\nGood findings here.\n\n"
        "## Conclusion\nAll good."
    )

    state = {
        "query": "Test research question",
        "research_results": [
            {
                "task": "Successful task about Python",
                "result": "Python is great.",
                "status": "success",
            },
            {
                "task": "Failed task about network speeds",
                "result": "[FAILED] Connection refused after 3 attempts",
                "status": "failed",
            },
        ],
        "plan": [],
        "current_task_index": 2,
        "report": "",
        "error": None,
        "human_approved": True,
        "human_feedback": None,
    }

    with patch("src.agents.writer.get_llm", return_value=mock_llm):
        result = writer_node(state)

    report = result["report"]

    assert "Research Limitations" in report, (
        "'Research Limitations' section missing from report"
    )
    assert "Failed task about network speeds" in report, (
        "Failed task name not mentioned in limitations"
    )
    assert "Connection refused" in report, (
        "Failure reason not mentioned in limitations"
    )

    # LLM was called with only the successful findings
    call_args = mock_llm.invoke.call_args[0][0]  # list of messages
    user_msg = next(m["content"] for m in call_args if m["role"] == "user")
    assert "Successful task about Python" in user_msg
    assert "Failed task about network speeds" not in user_msg


# ── test_writer_no_failures ────────────────────────────────────────────────────

def test_writer_no_failures() -> None:
    """Writer with all-successful results must NOT add a limitations section."""
    from src.agents.writer import writer_node

    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "# Clean Report\n\n## Conclusion\nAll done."

    state = {
        "query": "Clean query",
        "research_results": [
            {"task": "Task A", "result": "Finding A", "status": "success"},
            {"task": "Task B", "result": "Finding B", "status": "success"},
        ],
        "plan": [],
        "current_task_index": 2,
        "report": "",
        "error": None,
        "human_approved": True,
        "human_feedback": None,
    }

    with patch("src.agents.writer.get_llm", return_value=mock_llm):
        result = writer_node(state)

    assert "Research Limitations" not in result["report"], (
        "Limitations section should NOT appear when all tasks succeeded"
    )


# ── test_status_field_present ─────────────────────────────────────────────────

def test_status_field_present_on_success() -> None:
    """researcher_node always writes a 'status' key even on the happy path."""
    from src.agents.researcher import researcher_node

    state = _make_researcher_state("Happy path task")

    with (
        patch("src.agents.researcher._react_loop", return_value="Great findings"),
        patch("src.agents.researcher.get_llm", return_value=MagicMock()),
        patch("src.agents.researcher.get_all_tools", return_value=[]),
        patch("src.agents.researcher.time.sleep"),
    ):
        result = researcher_node(state)

    entry = result["research_results"][0]
    assert "status" in entry
    assert entry["status"] == "success"
    assert entry["result"] == "Great findings"
