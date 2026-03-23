"""Replan Agent: revises the research plan based on human feedback."""

from typing import Any

from src.config import get_llm
from src.agents.planner import _parse_plan
from src.state import AgentState

_SYSTEM_PROMPT = """You are a research planner. You will be given an original research question,
a proposed research plan, and revision feedback from a human reviewer.

Your job: produce a revised plan that incorporates the feedback.

IMPORTANT: respond with ONLY a valid JSON array of strings (3-5 items).
No markdown fences, no explanation — just the raw JSON array.

Example output:
["Revised sub-task 1: ...", "Revised sub-task 2: ...", "Revised sub-task 3: ..."]
"""


def replan_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: revise the plan using LLM + human feedback.

    Reads  : state["query"], state["plan"], state["human_feedback"]
    Writes : state["plan"] (revised), state["human_feedback"] (cleared),
             state["current_task_index"] (reset), state["research_results"] (reset)
    """
    feedback = state.get("human_feedback") or ""
    original_plan = "\n".join(f"{i}. {t}" for i, t in enumerate(state["plan"], 1))

    print(f"\n[REPLAN] Revising plan with feedback: \"{feedback}\"")

    llm = get_llm()
    user_message = (
        f"Research question: {state['query']}\n\n"
        f"Current plan:\n{original_plan}\n\n"
        f"Human feedback: {feedback}\n\n"
        "Please produce a revised research plan as a JSON array."
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content
        print(f"[REPLAN] Raw LLM output: {raw[:200]}...")
        new_plan = _parse_plan(raw)
    except Exception as exc:
        print(f"[REPLAN] ERROR: {exc} — keeping original plan.")
        new_plan = state["plan"]

    print(f"[REPLAN] Revised plan ({len(new_plan)} tasks):")
    for i, task in enumerate(new_plan, 1):
        print(f"[REPLAN]   {i}. {task}")

    return {
        "plan": new_plan,
        "human_feedback": None,   # clear after use
        "human_approved": False,  # user must re-review
        "current_task_index": 0,
        "research_results": [],
    }
