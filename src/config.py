"""Global configuration for the Multi-Agent Research Assistant."""

import os
from pathlib import Path
from langchain_openai import ChatOpenAI

# ── Proxy (Clash on port 7897) ─────────────────────────────────────────────────
# Set before any network library is imported so httpx / requests / ddgs pick it up.
# NO_PROXY keeps Ollama (localhost) direct so LLM calls are never proxied.
os.environ.setdefault("HTTP_PROXY",  "http://127.0.0.1:7897")
os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:7897")
os.environ.setdefault("NO_PROXY",    "localhost,127.0.0.1")


# LLM Configuration
LLM_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = "qwen2.5:7b"
LLM_TEMPERATURE = 0
LLM_API_KEY = "ollama"  # Ollama doesn't require a real key

# Task Configuration
MIN_SUBTASKS = 3
MAX_SUBTASKS = 5

# Tool Configuration
MAX_TOOL_ITERATIONS = 3          # max ReAct loop iterations per sub-task
SEARCH_DELAY = 1                 # seconds between web search calls (rate-limit)
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"  # saved notes directory

# Error-recovery Configuration
MAX_TASK_ATTEMPTS = 3            # 1 initial attempt + 2 retries per sub-task
RETRY_SLEEP = 2                  # seconds to wait between retry attempts

# Memory Configuration
MEMORY_DB_PATH = "data/memory.db"  # relative to project root


def get_llm() -> ChatOpenAI:
    """Return a configured ChatOpenAI instance pointing at local Ollama."""
    return ChatOpenAI(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=LLM_API_KEY,
    )
