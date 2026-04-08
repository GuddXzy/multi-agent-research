"""Writer Agent: synthesises trade research results into a structured market brief."""

from typing import Any

from src.config import get_llm
from src.state import AgentState

_SYSTEM_PROMPT = """You are a professional trade analyst. Given a market research question and
research findings, produce a structured Market Research Brief in Markdown with these sections:

# 市场调研简报：<Target Market + Industry>

## 摘要
2-3 sentences summarizing key findings and actionable insights.

## 市场概况
Market size, growth trends, and key players.

## 贸易政策与壁垒
Tariffs, import regulations, trade agreements (especially APEC/FTA related).

## 竞争格局
Major competitors, market share, pricing landscape.

## 机遇与风险
Opportunities (APEC policy benefits, market gaps) and risks (regulatory, competition).

## 行动建议
3-5 specific, actionable recommendations for the business.

RULES:
- Write in Chinese (中文).
- Include specific numbers and data points wherever available.
- Be practical and business-oriented, not academic.
- Note data sources when citing statistics.
- Some sub-tasks may be marked as [FAILED] — skip those."""


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

    lang_instruction = (
        "\n请用中文撰写完整报告，包括标题、摘要、研究发现、结论等所有部分。"
        if state.get("language") == "zh"
        else ""
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT + lang_instruction},
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
