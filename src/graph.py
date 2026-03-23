"""LangGraph state graph definition and compilation."""

from langgraph.graph import END, START, StateGraph

from src.agents.planner import planner_node
from src.agents.human_review import human_review_node
from src.agents.replan import replan_node
from src.agents.researcher import researcher_node
from src.agents.writer import writer_node
from src.state import AgentState


# ── Routing functions ──────────────────────────────────────────────────────────

def route_after_review(state: AgentState) -> str:
    """After human_review: go to research (approved) or replan (needs revision)."""
    if state.get("human_approved"):
        return "researcher"
    return "replan"


def should_continue(state: AgentState) -> str:
    """After researcher: loop back if tasks remain, otherwise go to writer."""
    if state["current_task_index"] < len(state["plan"]):
        return "researcher"
    return "writer"


# ── Graph construction ─────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Construct and compile the research assistant state graph.

    Flow
    ----
    START
      -> planner          (decompose query into sub-tasks)
      -> human_review     (show plan; wait for approval or feedback)
           |
           +--[approved]--> researcher --(loop)--> writer --> END
           |
           +--[feedback]--> replan --> human_review  (repeat until approved)
    """
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("replan", replan_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)

    # Linear: start -> plan -> review
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "human_review")

    # Conditional: review -> research OR replan
    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {"researcher": "researcher", "replan": "replan"},
    )

    # Replan loops back to review
    workflow.add_edge("replan", "human_review")

    # Researcher loops until all sub-tasks done, then goes to writer
    workflow.add_conditional_edges(
        "researcher",
        should_continue,
        {"researcher": "researcher", "writer": "writer"},
    )

    workflow.add_edge("writer", END)

    return workflow.compile()


# Module-level compiled app — importable by main.py and tests
app = build_graph()
