"""Planner Agent: decomposes a trade research query into structured sub-tasks."""

import json
import re
from typing import Any

from src.config import get_llm
from src.state import AgentState

_SYSTEM_PROMPT = """You are an APEC trade research planner. Given a user's trade research question
(typically about target markets, industries, or trade opportunities related to APEC 2026 Shenzhen),
break it down into 3 to 5 specific, structured sub-tasks covering key research dimensions.

Consider these dimensions when relevant:
- Market size and growth trends for the target industry
- Import/export tariffs, trade barriers, and regulatory policies
- Competitive landscape (local and international competitors)
- APEC-related trade agreements, policy benefits, or upcoming events
- Logistics, supply chain, and market entry considerations

IMPORTANT: You MUST respond with ONLY a valid JSON array of strings.
No markdown code fences, no explanation, no extra text — just the raw JSON array.

Example output:
["Research Vietnam consumer electronics market size and growth trends in 2024-2026",
 "Analyze Vietnam import tariffs and trade barriers for electronic products",
 "Identify key competitors in Vietnam consumer electronics market",
 "Review APEC 2026 trade facilitation policies relevant to electronics export"]
"""


def _parse_plan(text: str) -> list[str]:
    """Parse the LLM output into a list of sub-task strings.

    Tries JSON first; falls back to line-by-line extraction.
    """
    text = text.strip()

    # Remove markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()

    # Attempt 1: direct JSON parse
    try:
        result = json.loads(text)
        if isinstance(result, list) and result:
            return [str(item) for item in result]
    except json.JSONDecodeError:
        pass

    # Attempt 2: find first [...] block
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list) and result:
                return [str(item) for item in result]
        except json.JSONDecodeError:
            pass

    # Attempt 3: numbered / bulleted lines fallback
    lines = [
        re.sub(r"^[\d\-\*\.\)]+\s*", "", line).strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("]")
    ]
    tasks = [l for l in lines if len(l) > 5]
    if tasks:
        return tasks[:5]

    # Last resort: wrap the whole text as a single task
    return [text]


def planner_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: break the user query into research sub-tasks.

    Reads  : state["query"]
    Writes : state["plan"], state["current_task_index"], state["research_results"]
    """
    print("\n[Planner] Decomposing query into sub-tasks...")
    llm = get_llm()

    lang_instruction = (
        "\n请用中文输出子任务描述。"
        if state.get("language") == "zh"
        else ""
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT + lang_instruction},
        {"role": "user", "content": f"Research question: {state['query']}"},
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content
        print(f"[Planner] Raw LLM output: {raw[:200]}...")
        plan = _parse_plan(raw)
    except Exception as exc:
        print(f"[Planner] ERROR: {exc}")
        return {"error": str(exc), "plan": [], "current_task_index": 0, "research_results": []}

    print(f"[Planner] Generated {len(plan)} sub-tasks:")
    for i, task in enumerate(plan, 1):
        print(f"  {i}. {task}")

    return {
        "plan": plan,
        "current_task_index": 0,
        "research_results": [],
        "error": None,
    }
