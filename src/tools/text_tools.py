"""Text processing tools for the research assistant."""

import re
from pathlib import Path
from langchain_core.tools import tool
from src.config import OUTPUTS_DIR


@tool
def save_note(content: str) -> str:
    """Save a research note to the outputs directory.

    The input should be: '<filename>|<content>' where filename is a short
    descriptive name (no extension needed) and content is the text to save.
    Example: 'llm-trends-2024|Key findings about LLM trends...'

    Returns the path where the note was saved.
    """
    # Parse "filename|content" format; fall back to auto-generated filename
    if "|" in content:
        filename, note_body = content.split("|", 1)
        filename = filename.strip()
        note_body = note_body.strip()
    else:
        filename = "note"
        note_body = content.strip()

    # Sanitise filename
    filename = re.sub(r"[^\w\-]", "_", filename)[:50] or "note"
    if not filename.endswith(".txt"):
        filename += ".txt"

    output_path = Path(OUTPUTS_DIR) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(note_body, encoding="utf-8")

    return f"Note saved to: {output_path}"
