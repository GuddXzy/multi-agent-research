"""Shared LangGraph state definition for the research assistant."""

from typing import Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State shared across all agents in the research graph.

    Fields
    ------
    query : str
        The user's original research question.
    plan : list[str]
        Ordered list of sub-tasks produced by the Planner agent.
    research_results : list[dict]
        Results collected by the Researcher agent.
        Each entry has keys:
          ``task``   (str)  — the sub-task description
          ``result`` (str)  — findings text, or "[FAILED] <reason>" on error
          ``status`` (str)  — "success" | "failed"
    current_task_index : int
        Zero-based index of the next sub-task to research.
    report : str
        Final Markdown report produced by the Writer agent.
    error : Optional[str]
        Error message if any agent failed; None otherwise.
    human_approved : bool
        Set to True by human_review_node when the user approves the plan.
    human_feedback : Optional[str]
        Revision instructions entered by the user; cleared after each replan.
    """

    query: str
    plan: list[str]
    research_results: list[dict]
    current_task_index: int
    report: str
    error: Optional[str]
    human_approved: bool          # True once the user signs off on the plan
    human_feedback: Optional[str] # Non-None when the user requests a revision
    language: str                 # Output language for LLM agents: "en" | "zh"
