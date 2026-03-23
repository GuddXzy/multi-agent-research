"""Evaluation runner — executes the full research pipeline on a fixed set of
benchmark questions and reports quality scores.

Requires Ollama to be running locally.  Not part of the pytest suite.

Usage
-----
  py eval_runner.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.evaluation import Evaluator
from src.graph import app
from src.state import AgentState

# ── Benchmark questions ────────────────────────────────────────────────────────

TEST_QUESTIONS = [
    "What are the key differences between React and Vue.js?",
    "Explain how transformer models work in NLP",
    "What are the pros and cons of microservices architecture?",
]

EVAL_OUTPUT_PATH = Path("data/eval_results.json")


# ── Pipeline runner ────────────────────────────────────────────────────────────

def run_pipeline(question: str) -> AgentState:
    """Run the full research graph, auto-approving the human review step."""
    initial: AgentState = {
        "query": question,
        "plan": [],
        "research_results": [],
        "current_task_index": 0,
        "report": "",
        "error": None,
        "human_approved": False,
        "human_feedback": None,
    }
    with patch("builtins.input", return_value="y"):
        return app.invoke(initial)


# ── Display helpers ────────────────────────────────────────────────────────────

def _trunc(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def print_table(rows: list[dict]) -> None:
    """Print a formatted ASCII results table to stdout."""
    col_q   = 42
    col_num = 7

    header = (
        f"{'Question':<{col_q}} "
        f"{'Plan':>{col_num}} "
        f"{'Research':>{col_num}} "
        f"{'Report':>{col_num}} "
        f"{'Overall':>{col_num}}"
    )
    sep = "-" * len(header)

    print("\n" + sep)
    print(header)
    print(sep)

    overall_scores = []
    for row in rows:
        q_short = _trunc(row["question"], col_q)
        if row["status"] == "ok":
            s = row["scores"]
            plan_s     = s["plan"]["score"]
            research_s = s["research"]["score"]
            report_s   = s["report"]["score"]
            overall_s  = s["overall_score"]
            overall_scores.append(overall_s)
            print(
                f"{q_short:<{col_q}} "
                f"{plan_s:>{col_num}} "
                f"{research_s:>{col_num}} "
                f"{report_s:>{col_num}} "
                f"{overall_s:>{col_num}}"
            )
        else:
            print(f"{q_short:<{col_q}} {'ERROR':>{col_num * 4 + 3}}")

    print(sep)
    if overall_scores:
        avg = round(sum(overall_scores) / len(overall_scores))
        print(
            f"{'AVERAGE':<{col_q}} "
            f"{'':>{col_num}} "
            f"{'':>{col_num}} "
            f"{'':>{col_num}} "
            f"{avg:>{col_num}}"
        )
    print(sep + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    evaluator = Evaluator()
    results = []
    total = len(TEST_QUESTIONS)

    print(f"\n[EVAL] Starting evaluation run — {total} questions")
    print(f"[EVAL] Timestamp: {datetime.now(timezone.utc).isoformat()}\n")

    for idx, question in enumerate(TEST_QUESTIONS, 1):
        print(f"[EVAL] ({idx}/{total}) {question}")
        print("[EVAL] Running pipeline...", flush=True)

        try:
            state = run_pipeline(question)
            scores = evaluator.overall_score(
                plan=state["plan"],
                research_results=state["research_results"],
                report=state["report"],
                query=question,
            )
            results.append({
                "question": question,
                "status": "ok",
                "scores": scores,
                "plan_task_count": len(state["plan"]),
                "research_result_count": len(state["research_results"]),
            })
            print(
                f"[EVAL]   overall={scores['overall_score']} "
                f"plan={scores['plan']['score']} "
                f"research={scores['research']['score']} "
                f"report={scores['report']['score']}"
            )
        except Exception as exc:
            print(f"[EVAL]   FAILED: {exc}")
            results.append({
                "question": question,
                "status": "error",
                "scores": None,
                "error": str(exc),
            })

    # Print summary table
    print_table(results)

    # Persist results
    EVAL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "questions": results,
    }
    EVAL_OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[EVAL] Results saved to: {EVAL_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
