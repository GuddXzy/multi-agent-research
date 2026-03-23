"""Tests for the deterministic evaluation framework.

Fully offline — no LLM, no network, no Ollama required.
All inputs are hand-crafted fixtures that produce predictable scores.
"""

import pytest
from src.evaluation import Evaluator

# Module-level evaluator instance shared across all tests
ev = Evaluator()


# ── Fixtures ───────────────────────────────────────────────────────────────────

GOOD_PLAN = [
    "Define the fundamental concepts of React",
    "Identify the core features of Vue.js",
    "Compare component lifecycle management in both frameworks",
    "Analyze state management strategies in React and Vue",
    "Evaluate ecosystem and community support for each framework",
]

DUPLICATE_PLAN = [
    "Compare React and Vue differences",
    "Compare Vue and React differences",   # near-duplicate
    "Analyze performance in React and Vue",
]

GOOD_RESULTS = [
    {
        "task": "Define React",
        "result": (
            "React is a JavaScript library. URL: https://react.dev\n"
            "It uses virtual DOM for efficient rendering. " * 20
        ),
        "status": "success",
    },
    {
        "task": "Define Vue.js",
        "result": (
            "[1] Vue.js - Wikipedia. Vue is a progressive framework. " * 25
        ),
        "status": "success",
    },
]

MIXED_RESULTS = [
    {
        "task": "Task A",
        "result": "Some findings URL: https://example.com " * 15,
        "status": "success",
    },
    {
        "task": "Task B",
        "result": "[FAILED] Network timeout after 3 attempts",
        "status": "failed",
    },
]

ALL_FAILED_RESULTS = [
    {"task": "Task A", "result": "[FAILED] Error A", "status": "failed"},
    {"task": "Task B", "result": "[FAILED] Error B", "status": "failed"},
]

GOOD_REPORT = """# React vs Vue.js: A Comprehensive Comparison

## Abstract

React and Vue.js are two of the most popular JavaScript frameworks today.
This report examines their key differences across multiple dimensions.

## Research Findings

### Component Architecture

React uses JSX and a unidirectional data flow. Components are pure functions
returning markup. The virtual DOM enables efficient reconciliation.

### State Management

Vue.js has a built-in reactivity system. React relies on useState and external
libraries such as Redux or Zustand for complex state.

### Performance

Both frameworks perform comparably for most applications. React's Fiber
architecture enables concurrent rendering. Vue 3's Proxy-based reactivity
is more granular.

## Conclusion

React and Vue.js each have distinct strengths. React suits large teams
familiar with JavaScript, while Vue.js offers a gentler learning curve and
excellent official documentation.
"""

POOR_REPORT = "React and Vue are different."


# ── plan_quality ───────────────────────────────────────────────────────────────

class TestPlanQuality:
    def test_good_plan_high_score(self) -> None:
        result = ev.plan_quality(GOOD_PLAN, "React vs Vue")
        assert result["score"] >= 80
        assert result["task_count"] == 5
        assert result["has_duplicates"] is False

    def test_empty_plan_zero_score(self) -> None:
        result = ev.plan_quality([], "React vs Vue")
        assert result["score"] == 0
        assert result["task_count"] == 0

    def test_single_task_low_score(self) -> None:
        result = ev.plan_quality(["Compare React and Vue"], "React vs Vue")
        assert result["score"] < 70

    def test_too_many_tasks_penalty(self) -> None:
        many = [f"Sub-task {i}: research topic {i}" for i in range(10)]
        result = ev.plan_quality(many, "broad question")
        good  = ev.plan_quality(GOOD_PLAN, "broad question")
        assert result["score"] < good["score"]

    def test_duplicates_detected(self) -> None:
        result = ev.plan_quality(DUPLICATE_PLAN, "React vs Vue")
        assert result["has_duplicates"] is True

    def test_duplicate_penalty_applied(self) -> None:
        with_dup    = ev.plan_quality(DUPLICATE_PLAN, "React vs Vue")
        without_dup = ev.plan_quality(GOOD_PLAN[:3],  "React vs Vue")
        # Duplicate plan should score lower even if count is similar
        assert with_dup["score"] < without_dup["score"]

    def test_query_coverage(self) -> None:
        result = ev.plan_quality(GOOD_PLAN, "React and Vue frameworks")
        assert result["query_coverage"] is True

    def test_unrelated_plan_coverage_false(self) -> None:
        unrelated = ["history of ancient Rome", "Roman architecture", "Julius Caesar"]
        result = ev.plan_quality(unrelated, "quantum computing breakthroughs")
        assert result["query_coverage"] is False


# ── research_quality ───────────────────────────────────────────────────────────

class TestResearchQuality:
    def test_all_success_high_score(self) -> None:
        result = ev.research_quality(GOOD_RESULTS)
        assert result["score"] >= 60
        assert result["success_rate"] == 1.0

    def test_with_failures_lower_score(self) -> None:
        good  = ev.research_quality(GOOD_RESULTS)
        mixed = ev.research_quality(MIXED_RESULTS)
        assert mixed["score"] < good["score"]

    def test_all_failed_low_score(self) -> None:
        result = ev.research_quality(ALL_FAILED_RESULTS)
        assert result["success_rate"] == 0.0
        assert result["score"] < 30

    def test_failure_rate_calculated(self) -> None:
        result = ev.research_quality(MIXED_RESULTS)
        assert result["success_rate"] == pytest.approx(0.5)

    def test_empty_results_zero(self) -> None:
        result = ev.research_quality([])
        assert result["score"] == 0
        assert result["success_rate"] == 0.0

    def test_tool_usage_detected(self) -> None:
        """Results containing URLs or [n] citations increase tool_usage."""
        result = ev.research_quality(GOOD_RESULTS)
        assert result["tool_usage"] > 0.0

    def test_no_tool_usage(self) -> None:
        plain = [{"task": "T", "result": "Some plain text answer.", "status": "success"}]
        result = ev.research_quality(plain)
        assert result["tool_usage"] == 0.0

    def test_avg_length_reported(self) -> None:
        result = ev.research_quality(GOOD_RESULTS)
        assert result["avg_result_length"] > 0

    def test_short_results_lower_score(self) -> None:
        short = [{"task": "T", "result": "Short.", "status": "success"}]
        long  = GOOD_RESULTS
        assert ev.research_quality(short)["score"] < ev.research_quality(long)["score"]


# ── report_quality ─────────────────────────────────────────────────────────────

class TestReportQuality:
    def test_structured_report_high_score(self) -> None:
        result = ev.report_quality(GOOD_REPORT)
        assert result["score"] >= 80
        assert result["has_structure"] is True
        assert result["has_conclusion"] is True

    def test_poor_report_low_score(self) -> None:
        result = ev.report_quality(POOR_REPORT)
        assert result["score"] < 40

    def test_empty_report_zero(self) -> None:
        assert ev.report_quality("")["score"] == 0
        assert ev.report_quality("   ")["score"] == 0

    def test_structure_detected(self) -> None:
        with_heading    = ev.report_quality("# Title\nContent here.")
        without_heading = ev.report_quality("Content here without any heading.")
        assert with_heading["has_structure"] is True
        assert without_heading["has_structure"] is False

    def test_conclusion_variants(self) -> None:
        for phrase in ("In conclusion", "In summary", "To summarize", "Overall"):
            result = ev.report_quality(f"# Report\n\n{phrase}, the answer is yes.")
            assert result["has_conclusion"] is True, f"Missed phrase: {phrase!r}"

    def test_word_count(self) -> None:
        result = ev.report_quality(GOOD_REPORT)
        assert result["word_count"] > 100

    def test_length_contributes_to_score(self) -> None:
        short  = ev.report_quality("# Title\n\nIn conclusion, short.")
        long   = ev.report_quality(GOOD_REPORT)
        assert long["score"] >= short["score"]


# ── overall_score & weights ────────────────────────────────────────────────────

class TestOverallScore:
    def test_full_pipeline_score(self) -> None:
        result = ev.overall_score(GOOD_PLAN, GOOD_RESULTS, GOOD_REPORT, "React vs Vue")
        assert 0 <= result["overall_score"] <= 100
        assert "plan" in result
        assert "research" in result
        assert "report" in result

    def test_weights_plan_20pct(self) -> None:
        """Only plan is perfect; research and report are zero."""
        # Manufacture a plan that scores 100
        perfect_plan = [f"Sub-task {i}: distinct topic number {i}" for i in range(4)]
        empty_results: list[dict] = []
        empty_report = ""

        result = ev.overall_score(perfect_plan, empty_results, empty_report, "topic")
        plan_score = result["plan"]["score"]
        expected   = round(plan_score * 0.20)
        assert result["overall_score"] == expected

    def test_weights_research_40pct(self) -> None:
        """Only research is non-zero (empty plan, empty report)."""
        empty_plan: list[str] = []
        empty_report = ""

        result    = ev.overall_score(empty_plan, GOOD_RESULTS, empty_report, "")
        r_score   = result["research"]["score"]
        expected  = round(r_score * 0.40)
        assert result["overall_score"] == expected

    def test_weights_report_40pct(self) -> None:
        """Only report is non-zero (empty plan, empty research)."""
        result   = ev.overall_score([], [], GOOD_REPORT, "")
        rep_score = result["report"]["score"]
        expected  = round(rep_score * 0.40)
        assert result["overall_score"] == expected

    def test_all_perfect_near_100(self) -> None:
        """When all components score high, overall should be high too."""
        result = ev.overall_score(GOOD_PLAN, GOOD_RESULTS, GOOD_REPORT, "React vs Vue")
        assert result["overall_score"] >= 70

    def test_all_empty_zero(self) -> None:
        result = ev.overall_score([], [], "", "")
        assert result["overall_score"] == 0

    def test_weights_sum_correctly(self) -> None:
        """overall = plan*0.2 + research*0.4 + report*0.4 (rounded)."""
        result = ev.overall_score(GOOD_PLAN, MIXED_RESULTS, GOOD_REPORT, "React vs Vue")
        manual = round(
            result["plan"]["score"]     * 0.20
            + result["research"]["score"] * 0.40
            + result["report"]["score"]   * 0.40
        )
        assert result["overall_score"] == manual
