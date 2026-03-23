"""Writer Agent: synthesises all research results into a structured Markdown report."""

from typing import Any

from src.config import get_llm
from src.state import AgentState

_SYSTEM_PROMPT = """You are a professional technical writer. Given a research question and a set
of research findings, produce a well-structured Markdown report with the following sections:

# <Title>

## Abstract
A short (2-3 sentence) summary of the whole report.

## Research Findings
One ### subsection per sub-task with its findings.

## Conclusion
Key takeaways and synthesis.

Use clear headings, bullet points where appropriate, and maintain an objective, informative tone.
Note: some sub-tasks may be marked as [FAILED] — skip those in Research Findings."""


def _build_limitations(failed_items: list[dict]) -> str:
    """Build a Markdown 'Research Limitations' section for failed sub-tasks."""
    lines = ["\n\n## Research Limitations\n"]
    lines.append(
        "The following sub-tasks could not be completed due to errors "
        "and are absent from the findings above:\n"
    )
    for item in failed_items:
        reason = item["result"].removeprefix("[FAILED]").strip()
        lines.append(f"- **{item['task']}**: {reason}")
    return "\n".join(lines)


def writer_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: compile all research results into a Markdown report.

    Successful sub-tasks are synthesised by the LLM.
    Failed sub-tasks are listed in an appended 'Research Limitations' section.

    Reads  : state["query"], state["research_results"]
    Writes : state["report"]
    """
    print("\n[Writer] Compiling final report...")
    llm = get_llm()

    results = state.get("research_results", [])
    success_items = [r for r in results if r.get("status") != "failed"]
    failed_items  = [r for r in results if r.get("status") == "failed"]

    if failed_items:
        print(f"[Writer] {len(failed_items)} sub-task(s) failed — will note in limitations.")

    findings_text = "\n\n".join(
        f"Sub-task: {item['task']}\nFindings: {item['result']}"
        for item in success_items
    ) or "No successful findings available."

    user_message = (
        f"Research Question: {state['query']}\n\n"
        f"Research Findings:\n{findings_text}"
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    try:
        response = llm.invoke(messages)
        report = response.content
    except Exception as exc:
        print(f"[Writer] ERROR: {exc}")
        report = f"# Report\n\n*Error generating report: {exc}*"

    # Always append limitations section when any sub-task failed
    if failed_items:
        report += _build_limitations(failed_items)

    print(f"[Writer] Report generated ({len(report)} chars).")
    return {"report": report}
