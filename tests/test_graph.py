"""End-to-end smoke tests for the research graph.

Tests are skipped automatically when:
- Ollama is not reachable / configured model is absent  -> requires_ollama
- Network is not available                              -> requires_network

human_review_node calls input() which would block in CI.
All graph invocations in this file patch builtins.input to return "y"
(auto-approve) so the tests run non-interactively.
"""

import json
import socket
import urllib.request
from unittest.mock import patch

import pytest

SMOKE_QUERY = "What are the key differences between React and Vue.js?"

# Shared initial state factory — includes the new HITL fields
def _make_initial(query: str = SMOKE_QUERY) -> dict:
    return {
        "query": query,
        "plan": [],
        "research_results": [],
        "current_task_index": 0,
        "report": "",
        "error": None,
        "human_approved": False,
        "human_feedback": None,
    }


# ── Availability helpers ───────────────────────────────────────────────────────

def _ollama_available() -> bool:
    """Return True if Ollama is reachable and the configured model is present."""
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as resp:
            data = json.loads(resp.read())
        from src.config import LLM_MODEL
        available = [m["name"] for m in data.get("models", [])]
        return LLM_MODEL in available
    except Exception:
        return False


def _network_available() -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama not reachable or configured model not available",
)

requires_network = pytest.mark.skipif(
    not _network_available(),
    reason="Network not available",
)


# ── Static tests (no LLM / network needed) ────────────────────────────────────

def test_state_schema() -> None:
    """AgentState TypedDict must contain all required keys including HITL fields."""
    from src.state import AgentState

    keys = AgentState.__annotations__.keys()
    expected = {
        "query", "plan", "research_results", "current_task_index",
        "report", "error", "human_approved", "human_feedback",
    }
    assert expected.issubset(keys), f"Missing keys: {expected - set(keys)}"


def test_graph_compiles() -> None:
    """The LangGraph app must compile without errors."""
    from src.graph import app

    assert app is not None


def test_tool_registry() -> None:
    """Tool registry must return at least 3 tools with correct names."""
    from src.tools import get_all_tools

    tools = get_all_tools()
    names = {t.name for t in tools}
    assert {"web_search", "wiki_search", "save_note"}.issubset(names)


def test_human_review_approve(monkeypatch) -> None:
    """human_review_node returns approved=True when user enters 'y'."""
    monkeypatch.setattr("builtins.input", lambda _: "y")
    from src.agents.human_review import human_review_node

    result = human_review_node({"plan": ["task 1", "task 2"]})
    assert result["human_approved"] is True
    assert result["human_feedback"] is None


def test_human_review_feedback(monkeypatch) -> None:
    """human_review_node captures feedback when user enters free text."""
    monkeypatch.setattr("builtins.input", lambda _: "focus on performance only")
    from src.agents.human_review import human_review_node

    result = human_review_node({"plan": ["task 1"]})
    assert result["human_approved"] is False
    assert result["human_feedback"] == "focus on performance only"


# ── Integration smoke tests ───────────────────────────────────────────────────

@requires_ollama
@requires_network
@pytest.mark.timeout(300)
def test_smoke_full_graph() -> None:
    """Full pipeline with auto-approved plan: planner->review->researcher->writer."""
    from src.graph import app

    with patch("builtins.input", return_value="y"):
        result = app.invoke(_make_initial(SMOKE_QUERY))

    assert result["plan"], "plan should not be empty"
    assert result["human_approved"] is True
    assert len(result["research_results"]) == len(result["plan"]), (
        f"Expected {len(result['plan'])} results, got {len(result['research_results'])}"
    )
    for item in result["research_results"]:
        assert item["task"] and item["result"]
    assert result["report"], "report should not be empty"
    assert result["error"] is None


@requires_ollama
@pytest.mark.timeout(300)
def test_smoke_full_graph_offline() -> None:
    """Full pipeline without network: auto-approve, researcher uses LLM knowledge."""
    from src.graph import app

    with patch("builtins.input", return_value="y"):
        result = app.invoke(
            _make_initial("Explain the difference between TCP and UDP protocols")
        )

    assert result["plan"]
    assert len(result["research_results"]) == len(result["plan"])
    assert result["report"]
