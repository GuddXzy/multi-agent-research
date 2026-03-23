"""Human-in-the-loop review node.

Pauses the graph after planning, shows the proposed plan, and waits for
the user to approve it, request revisions, or quit.
"""

import sys
from typing import Any

from src.state import AgentState

_DIVIDER = "-" * 60


def human_review_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: present the plan to the user and collect a decision.

    Reads  : state["plan"]
    Writes : state["human_approved"], state["human_feedback"]

    User options
    ------------
    Enter / y   Approve — research starts immediately.
    <any text>  Revision note — triggers a replan with this feedback.
    q           Quit the program.
    """
    plan = state.get("plan", [])

    print(f"\n[REVIEW] {_DIVIDER}")
    print("[REVIEW] Proposed research plan:")
    for i, task in enumerate(plan, 1):
        print(f"[REVIEW]   {i}. {task}")
    print(f"[REVIEW] {_DIVIDER}")
    print("[REVIEW] Options:")
    print("[REVIEW]   Enter / y  -> approve and start research")
    print("[REVIEW]   <text>     -> request revisions (describe changes)")
    print("[REVIEW]   q          -> quit")
    print(f"[REVIEW] {_DIVIDER}")

    try:
        user_input = input("[REVIEW] Your decision: ").strip()
    except (EOFError, KeyboardInterrupt):
        # Non-interactive environment (e.g. piped input) — auto-approve
        print("\n[REVIEW] Non-interactive mode detected — auto-approving plan.")
        return {"human_approved": True, "human_feedback": None}

    if user_input.lower() == "q":
        print("[REVIEW] Quitting.")
        sys.exit(0)

    if user_input == "" or user_input.lower() == "y":
        print("[REVIEW] Plan approved. Starting research...")
        return {"human_approved": True, "human_feedback": None}

    # Any other text → revision request
    print(f"[REVIEW] Feedback recorded: \"{user_input}\"")
    print("[REVIEW] Sending to Replan Agent...")
    return {"human_approved": False, "human_feedback": user_input}
