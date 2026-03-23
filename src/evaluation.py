"""Deterministic evaluation framework for the Multi-Agent Research Assistant.

All scoring is pure Python — no LLM calls, no network, no external dependencies.

Scoring overview
----------------
plan_quality     : 0-100  (task count 60pts + uniqueness 20pts + non-empty 20pts)
research_quality : 0-100  (success rate 50pts + result depth 30pts + tool use 20pts)
report_quality   : 0-100  (structure 40pts + conclusion 30pts + word count 30pts)
overall          : weighted average (plan 20%, research 40%, report 40%)
"""

import re
from typing import Any


# ── Helpers ────────────────────────────────────────────────────────────────────

# Common English stop-words excluded from Jaccard similarity calculation
_STOPWORDS = {
    "the", "a", "an", "in", "of", "and", "to", "for", "is", "are",
    "that", "this", "it", "with", "on", "by", "as", "at", "be", "or",
    "how", "what", "which", "its", "their", "from", "was", "has",
}

# Patterns that signal real tool output appeared in a research result
_TOOL_EVIDENCE = re.compile(
    r"(https?://|URL:\s*http|\[\d+\]|Wikipedia|web_search|wiki_search)",
    re.IGNORECASE,
)

# Markdown heading anywhere in the text
_HEADING_RE = re.compile(r"^#{1,4}\s+\w", re.MULTILINE)

# Any word that suggests a conclusion section
_CONCLUSION_RE = re.compile(
    r"\b(conclusion|summary|in summary|to summarize|in conclusion|overall)\b",
    re.IGNORECASE,
)


def _word_set(text: str) -> frozenset[str]:
    """Lower-cased, stop-word-filtered content words in *text*."""
    tokens = re.findall(r"[a-zA-Z]\w*", text.lower())
    return frozenset(w for w in tokens if w not in _STOPWORDS and len(w) > 2)


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ── Evaluator ──────────────────────────────────────────────────────────────────

class Evaluator:
    """Compute quality scores for each phase of the research pipeline."""

    # ── Plan quality ──────────────────────────────────────────────────────────

    def plan_quality(self, plan: list[str], query: str) -> dict[str, Any]:
        """Evaluate the research plan produced by the Planner agent.

        Returns
        -------
        task_count      : number of sub-tasks
        has_duplicates  : True if any pair of tasks has Jaccard similarity > 0.5
        query_coverage  : True if plan appears related to the query
        score           : 0-100
        """
        if not plan:
            return {
                "task_count": 0,
                "has_duplicates": False,
                "query_coverage": False,
                "score": 0,
            }

        task_count = len(plan)
        has_duplicates = self._detect_duplicates(plan)
        query_coverage = self._plan_covers_query(plan, query)

        # Sub-scores (max total = 100)
        # Count score: 60 pts — ideal band is 3-5 tasks
        if task_count == 0:
            count_score = 0
        elif task_count == 1:
            count_score = 20
        elif task_count == 2:
            count_score = 35
        elif task_count <= 5:
            count_score = 60
        elif task_count <= 7:
            count_score = 45
        else:
            count_score = 25

        # Uniqueness: 20 pts
        uniqueness_score = 0 if has_duplicates else 20

        # Query coverage: 20 pts
        coverage_score = 20 if query_coverage else 0

        score = min(count_score + uniqueness_score + coverage_score, 100)

        return {
            "task_count": task_count,
            "has_duplicates": has_duplicates,
            "query_coverage": query_coverage,
            "score": score,
        }

    @staticmethod
    def _detect_duplicates(plan: list[str], threshold: float = 0.5) -> bool:
        """Return True if any two tasks in *plan* have Jaccard similarity > threshold."""
        sets = [_word_set(t) for t in plan]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                if _jaccard(sets[i], sets[j]) > threshold:
                    return True
        return False

    @staticmethod
    def _plan_covers_query(plan: list[str], query: str) -> bool:
        """Return True if the plan shares meaningful words with the query."""
        if not query:
            return bool(plan)
        q_words = _word_set(query)
        plan_words = frozenset().union(*[_word_set(t) for t in plan])
        if not q_words:
            return True
        return len(q_words & plan_words) / len(q_words) >= 0.2

    # ── Research quality ──────────────────────────────────────────────────────

    def research_quality(self, research_results: list[dict]) -> dict[str, Any]:
        """Evaluate the Researcher agent's output.

        Returns
        -------
        success_rate        : fraction of sub-tasks with status "success"
        avg_result_length   : average character count per result
        tool_usage          : fraction of results containing tool-output evidence
        score               : 0-100
        """
        if not research_results:
            return {
                "success_rate": 0.0,
                "avg_result_length": 0,
                "tool_usage": 0.0,
                "score": 0,
            }

        total = len(research_results)
        successes = sum(
            1 for r in research_results if r.get("status") == "success"
        )
        success_rate = successes / total

        texts = [r.get("result", "") for r in research_results]
        avg_len = sum(len(t) for t in texts) / total

        with_tools = sum(1 for t in texts if _TOOL_EVIDENCE.search(t))
        tool_usage = with_tools / total

        # Weighted sub-scores
        success_score  = success_rate * 50                      # 50 pts
        depth_score    = min(avg_len / 500, 1.0) * 30          # 30 pts (ideal ≥ 500 chars)
        tool_score     = tool_usage * 20                        # 20 pts

        score = round(min(success_score + depth_score + tool_score, 100))

        return {
            "success_rate": round(success_rate, 2),
            "avg_result_length": round(avg_len),
            "tool_usage": round(tool_usage, 2),
            "score": score,
        }

    # ── Report quality ────────────────────────────────────────────────────────

    def report_quality(self, report: str) -> dict[str, Any]:
        """Evaluate the Writer agent's Markdown report.

        Returns
        -------
        word_count      : total words in the report
        has_structure   : True if the report contains at least one Markdown heading
        has_conclusion  : True if the report contains a conclusion section
        score           : 0-100
        """
        if not report or not report.strip():
            return {
                "word_count": 0,
                "has_structure": False,
                "has_conclusion": False,
                "score": 0,
            }

        word_count    = len(report.split())
        has_structure = bool(_HEADING_RE.search(report))
        has_conclusion = bool(_CONCLUSION_RE.search(report))

        # Sub-scores
        structure_score   = 40 if has_structure  else 0         # 40 pts
        conclusion_score  = 30 if has_conclusion else 0         # 30 pts
        length_score      = min(word_count / 400, 1.0) * 30    # 30 pts (ideal ≥ 400 words)

        score = round(min(structure_score + conclusion_score + length_score, 100))

        return {
            "word_count": word_count,
            "has_structure": has_structure,
            "has_conclusion": has_conclusion,
            "score": score,
        }

    # ── Overall score ─────────────────────────────────────────────────────────

    def overall_score(
        self,
        plan: list[str],
        research_results: list[dict],
        report: str,
        query: str,
    ) -> dict[str, Any]:
        """Compute a weighted overall quality score.

        Weights: plan 20%, research 40%, report 40%.

        Returns the overall score plus the three dimension breakdowns.
        """
        plan_eval     = self.plan_quality(plan, query)
        research_eval = self.research_quality(research_results)
        report_eval   = self.report_quality(report)

        total = round(
            plan_eval["score"]     * 0.20
            + research_eval["score"] * 0.40
            + report_eval["score"]   * 0.40
        )

        return {
            "overall_score": total,
            "plan":     plan_eval,
            "research": research_eval,
            "report":   report_eval,
        }
