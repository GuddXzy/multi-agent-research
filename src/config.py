"""Global configuration for the APEC Trade Research Assistant."""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ── Proxy (optional, set in .env if needed) ────────────────────────────────────
if os.environ.get("HTTP_PROXY"):
    os.environ.setdefault("HTTPS_PROXY", os.environ["HTTP_PROXY"])
    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")


# LLM Configuration — defaults to DeepSeek API, fallback to local Ollama
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")

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
    """Return a configured ChatOpenAI instance (DeepSeek API or local Ollama)."""
    return ChatOpenAI(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=LLM_API_KEY,
    )
