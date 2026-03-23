"""Unit tests for individual tools.

Network-dependent tests are skipped automatically when the internet
is not reachable, so the suite stays green in offline CI environments.
"""

import socket
import tempfile
from pathlib import Path

import pytest


# ── Network availability check ─────────────────────────────────────────────────

def _network_available() -> bool:
    """Return True if a basic TCP connection to 8.8.8.8:53 succeeds."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


requires_network = pytest.mark.skipif(
    not _network_available(),
    reason="Network not available",
)


# ── web_search ─────────────────────────────────────────────────────────────────

@requires_network
def test_web_search_returns_string() -> None:
    """web_search should return a non-empty string."""
    from src.tools.web_search import web_search

    result = web_search.invoke("Python programming language")
    assert isinstance(result, str)
    assert len(result) > 0


@requires_network
def test_web_search_contains_url() -> None:
    """web_search results should include at least one URL."""
    from src.tools.web_search import web_search

    result = web_search.invoke("Python programming language")
    assert "URL:" in result or "http" in result


@requires_network
def test_web_search_graceful_on_bad_query() -> None:
    """web_search should not raise; it returns an error string on failure."""
    from src.tools.web_search import web_search

    result = web_search.invoke("")
    assert isinstance(result, str)  # either results or an error message


# ── wiki_search ────────────────────────────────────────────────────────────────

@requires_network
def test_wiki_search_returns_python_article() -> None:
    """wiki_search should return text mentioning 'Python'."""
    from src.tools.wikipedia import wiki_search

    result = wiki_search.invoke("Python (programming language)")
    assert isinstance(result, str)
    assert len(result) > 50
    assert "Python" in result


@requires_network
def test_wiki_search_disambiguation() -> None:
    """wiki_search should handle disambiguation pages without raising."""
    from src.tools.wikipedia import wiki_search

    result = wiki_search.invoke("Mercury")
    assert isinstance(result, str)
    assert len(result) > 0


@requires_network
def test_wiki_search_unknown_topic() -> None:
    """wiki_search should return a friendly message for unknown topics."""
    from src.tools.wikipedia import wiki_search

    result = wiki_search.invoke("xyzzy_nonexistent_topic_12345")
    assert isinstance(result, str)


# ── save_note ──────────────────────────────────────────────────────────────────

def test_save_note_creates_file(tmp_path, monkeypatch) -> None:
    """save_note should write a file to OUTPUTS_DIR and confirm the path."""
    import src.config as cfg
    import src.tools.text_tools as tt
    from importlib import reload

    # Redirect OUTPUTS_DIR to a temp directory for isolation
    monkeypatch.setattr(cfg, "OUTPUTS_DIR", tmp_path)
    reload(tt)  # re-import so the tool picks up the patched path

    from src.tools.text_tools import save_note

    result = save_note.invoke("test-note|Hello from pytest")
    assert "saved" in result.lower() or "note" in result.lower()

    saved_files = list(tmp_path.glob("*.txt"))
    assert len(saved_files) == 1
    assert saved_files[0].read_text(encoding="utf-8") == "Hello from pytest"


def test_save_note_auto_filename(tmp_path, monkeypatch) -> None:
    """save_note should work without an explicit filename separator."""
    import src.config as cfg
    import src.tools.text_tools as tt
    from importlib import reload

    monkeypatch.setattr(cfg, "OUTPUTS_DIR", tmp_path)
    reload(tt)

    from src.tools.text_tools import save_note

    result = save_note.invoke("Just some plain content without a pipe char")
    assert isinstance(result, str)
    saved_files = list(tmp_path.glob("*.txt"))
    assert len(saved_files) == 1


# ── get_all_tools ──────────────────────────────────────────────────────────────

def test_get_all_tools_returns_list() -> None:
    """get_all_tools should return a list of at least 3 tools."""
    from src.tools import get_all_tools

    tools = get_all_tools()
    assert isinstance(tools, list)
    assert len(tools) >= 3


def test_tool_names() -> None:
    """All tools should have the expected names."""
    from src.tools import get_all_tools

    names = {t.name for t in get_all_tools()}
    assert "web_search" in names
    assert "wiki_search" in names
    assert "save_note" in names
