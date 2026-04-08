"""Researcher Agent — ReAct-style tool-calling loop.

Uses a manual Thought/Action/Observation cycle for structured trade research.
Searches in English for broader coverage, synthesizes findings in the user's language.
"""

import re
import time
from typing import Any

from src.config import get_llm, MAX_TOOL_ITERATIONS, MAX_TASK_ATTEMPTS, RETRY_SLEEP
from src.state import AgentState
from src.tools import get_all_tools

# ── Regex parsers ──────────────────────────────────────────────────────────────
_ACTION_RE = re.compile(r"Action\s*:\s*(\w+)", re.IGNORECASE)
_ACTION_INPUT_RE = re.compile(
    r"Action\s*Input\s*:\s*(.+?)(?=\n(?:Thought|Action|Observation|Final)|$)",
    re.IGNORECASE | re.DOTALL,
)
_FINAL_RE = re.compile(r"Final\s*Answer\s*:\s*([\s\S]+)", re.IGNORECASE)

# ── ReAct system prompt ────────────────────────────────────────────────────────
_REACT_SYSTEM = """You are a trade research analyst specializing in APEC economies and international trade.
Research the given task using the tools below.

IMPORTANT SEARCH STRATEGY:
- Always search in ENGLISH for better coverage of international trade data.
- Use specific trade-related keywords (tariff, import policy, market size, trade agreement, APEC).
- Cross-reference web search (recent data) with Wikipedia (background context).

AVAILABLE TOOLS:
- web_search : Search the internet for recent trade data, policies, news, and statistics.
- wiki_search : Search Wikipedia for country/industry background and economic overviews.

STRICT RESPONSE FORMAT — follow EXACTLY:

Thought: <your reasoning about what to search and why>
Action: <web_search or wiki_search>
Action Input: <search query in English — plain text, no quotes>

After you see the Observation, either call another tool OR give your final answer:

Final Answer: <comprehensive research findings with specific data points, 3-5 paragraphs>

RULES:
- Use at least one tool before giving Final Answer.
- Final Answer must include specific numbers, dates, or facts from the search results.
- Cite sources where possible (e.g., "according to [source]").
- Do NOT use any tool name other than web_search or wiki_search.

EXAMPLE:
Task: Research Vietnam consumer electronics import tariffs.

Thought: I need to search for Vietnam's current tariff rates on electronics.
Action: web_search
Action Input: Vietnam import tariff consumer electronics 2025 2026

Observation: Vietnam's MFN tariff rate for electronic products...

Thought: Let me also check ASEAN/APEC trade agreements that may reduce tariffs.
Action: web_search
Action Input: Vietnam APEC trade agreement electronics tariff reduction

Observation: Under the ASEAN-China FTA...

Final Answer: Vietnam's import tariff structure for consumer electronics...
"""


# ── Internal ReAct loop ────────────────────────────────────────────────────────

def _react_loop(task: str, llm, tool_map: dict[str, Any]) -> str:
    """Run the ReAct Thought/Action/Observation loop for one sub-task.

    Returns the final answer string (from 'Final Answer:' or graceful fallback).
    """
    messages: list[dict] = [
        {"role": "system", "content": _REACT_SYSTEM},
        {"role": "user", "content": f"Task: {task}"},
    ]
    observations: list[str] = []

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = llm.invoke(messages)
        text = response.content.strip()

        # ── 1. Check for Final Answer ──────────────────────────────────────
        fa_match = _FINAL_RE.search(text)
        if fa_match:
            return fa_match.group(1).strip()

        # ── 2. Parse Action / Action Input ────────────────────────────────
        action_match = _ACTION_RE.search(text)
        input_match = _ACTION_INPUT_RE.search(text)

        if not (action_match and input_match):
            # Model didn't follow format — treat raw output as result
            print("[Researcher] [WARN] LLM did not follow ReAct format; using raw output.")
            return text

        action_name = action_match.group(1).strip().lower()
        action_input = input_match.group(1).strip().strip("\"'")

        # ── 3. Execute tool ───────────────────────────────────────────────
        print(f"[Researcher] [TOOL] Using tool: {action_name} with input: {action_input}")

        tool_fn = tool_map.get(action_name)
        if tool_fn:
            try:
                obs = str(tool_fn.invoke(action_input))
            except Exception as exc:
                obs = f"Tool error ({action_name}): {exc}"
        else:
            obs = f"Unknown tool '{action_name}'. Available: {list(tool_map)}"

        print(f"[Researcher] [OBS] Observation: {obs[:200]}...")
        observations.append(obs)

        # ── 4. Append exchange to conversation ────────────────────────────
        messages.append({"role": "assistant", "content": text})
        messages.append({
            "role": "user",
            "content": (
                f"Observation: {obs}\n\n"
                "Continue your research (use another tool) or write your Final Answer:"
            ),
        })

    # ── Exhausted iterations without Final Answer ─────────────────────────────
    print("[Researcher] [WARN] Max iterations reached; compiling observations as result.")
    if observations:
        return "Research findings:\n\n" + "\n\n---\n\n".join(observations)
    return "[No research results obtained]"


# ── LangGraph node ────────────────────────────────────────────────────────────

def researcher_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: research one sub-task using the ReAct tool-calling loop.

    Reads  : state["plan"], state["current_task_index"], state["research_results"]
    Writes : state["research_results"] (appended), state["current_task_index"] (incremented)
    """
    idx = state["current_task_index"]
    if not state.get("plan") or idx >= len(state["plan"]):
        print("[Researcher] No tasks to process (plan is empty or exhausted).")
        return {}

    task = state["plan"][idx]
    print(f"\n[Researcher] -- Sub-task {idx + 1}/{len(state['plan'])} --")
    print(f"[Researcher] Task: {task}")

    llm = get_llm()
    tools = get_all_tools()
    tool_map = {t.name: t for t in tools}

    # ── Retry loop ────────────────────────────────────────────────────────────
    result_text: str = ""
    status: str = "failed"
    short_task = task[:60]

    for attempt in range(MAX_TASK_ATTEMPTS):
        try:
            result_text = _react_loop(task, llm, tool_map)
            status = "success"
            break
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_TASK_ATTEMPTS - 1:
                next_num = attempt + 2
                print(
                    f'[RETRY] Task "{short_task}" failed, '
                    f"retrying ({next_num}/{MAX_TASK_ATTEMPTS})..."
                )
                time.sleep(RETRY_SLEEP)
            else:
                print(
                    f'[RETRY] Task "{short_task}" failed after '
                    f"{MAX_TASK_ATTEMPTS} attempts."
                )
                result_text = f"[FAILED] {last_error}"

    if status == "success":
        print(f"[Researcher] [OK] Result preview: {result_text[:150]}...")
    else:
        print(f"[Researcher] [FAIL] Sub-task recorded as failed: {result_text[:150]}")

    updated_results = list(state.get("research_results", []))
    updated_results.append({"task": task, "result": result_text, "status": status})

    return {
        "research_results": updated_results,
        "current_task_index": idx + 1,
    }
