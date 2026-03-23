"""CLI entry point for the Multi-Agent Research Assistant.

Usage
-----
  py main.py "research question"   # run the full research pipeline
  py main.py --history             # show the 5 most recent sessions
  py main.py --search "keyword"    # search past sessions by keyword
"""

import sys

from src.config import MEMORY_DB_PATH
from src.graph import app
from src.memory import MemoryStore
from src.state import AgentState

# ── Output helpers ─────────────────────────────────────────────────────────────
# Use rich when available; fall back to plain print.
# Wrap stdout in UTF-8 so Windows GBK terminals don't crash on box-drawing chars.
try:
    import io
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.rule import Rule

    _utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console = Console(file=_utf8_stdout, highlight=False, safe_box=True)

    def print_header(text: str) -> None:
        console.print(Rule(f"[bold cyan]{text}[/bold cyan]"))

    def print_info(text: str) -> None:
        console.print(f"[dim]{text}[/dim]")

    def print_report(text: str) -> None:
        console.print(Markdown(text))

except (ImportError, AttributeError):
    def print_header(text: str) -> None:
        print(f"\n{'=' * 60}")
        print(f"  {text}")
        print("=" * 60)

    def print_info(text: str) -> None:
        print(text)

    def print_report(text: str) -> None:
        print(text)


# ── Research pipeline ──────────────────────────────────────────────────────────

def run(query: str) -> None:
    """Execute the research graph for the given query and save the session."""
    initial_state: AgentState = {
        "query": query,
        "plan": [],
        "research_results": [],
        "current_task_index": 0,
        "report": "",
        "error": None,
        "human_approved": False,
        "human_feedback": None,
    }

    print_header("Multi-Agent Research Assistant")
    print_info(f"[PLAN] Query: {query}\n")

    final_state = app.invoke(initial_state)

    # ── [PLAN] Final approved plan ─────────────────────────────────────────
    print_header("[PLAN] Approved Research Plan")
    for i, task in enumerate(final_state.get("plan", []), 1):
        print_info(f"  {i}. {task}")

    # ── [RESEARCH] Per-task results ────────────────────────────────────────
    print_header("[RESEARCH] Results by Sub-task")
    for item in final_state.get("research_results", []):
        print_info(f"\n>> {item['task']}")
        print_info(item["result"])

    # ── [REPORT] Final Markdown report ────────────────────────────────────
    print_header("[REPORT] Final Report")
    print_report(final_state.get("report", "*No report generated.*"))

    if final_state.get("error"):
        print(f"\n[ERROR] {final_state['error']}")

    # ── [MEMORY] Persist session ───────────────────────────────────────────
    print_header("[MEMORY] Saving Session")
    memory = MemoryStore(MEMORY_DB_PATH)
    memory.save_session(
        query=query,
        plan=final_state.get("plan", []),
        research_results=final_state.get("research_results", []),
        report=final_state.get("report", ""),
    )
    stats = memory.get_stats()
    print_info(f"[MEMORY] Total sessions stored: {stats['total']}")


# ── History / search commands ──────────────────────────────────────────────────

def cmd_history() -> None:
    """Print the 5 most recent research sessions."""
    memory = MemoryStore(MEMORY_DB_PATH)
    sessions = memory.get_recent_sessions(limit=5)
    if not sessions:
        print("No research history found.")
        return

    print_header("[MEMORY] Recent Research Sessions")
    for s in sessions:
        print_info(f"  [{s['id']}] {s['created_at']}  |  {s['query']}")


def cmd_search(keyword: str) -> None:
    """Search past sessions by keyword and print matching queries."""
    memory = MemoryStore(MEMORY_DB_PATH)
    sessions = memory.search_sessions(keyword)
    if not sessions:
        print(f"No sessions found matching: {keyword!r}")
        return

    print_header(f"[MEMORY] Sessions matching '{keyword}'")
    for s in sessions:
        print_info(f"  [{s['id']}] {s['created_at']}  |  {s['query']}")
        # Show a short excerpt from the report
        report_excerpt = s.get("report", "")[:120].replace("\n", " ")
        print_info(f"         Report: {report_excerpt}...")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        user_query = input("Enter your research question: ").strip()
        if not user_query:
            print("No query provided. Exiting.")
            sys.exit(1)
        run(user_query)

    elif args[0] == "--history":
        cmd_history()

    elif args[0] == "--search":
        if len(args) < 2:
            print("Usage: py main.py --search \"keyword\"")
            sys.exit(1)
        cmd_search(" ".join(args[1:]))

    else:
        run(" ".join(args))
