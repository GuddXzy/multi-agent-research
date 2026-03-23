"""Internationalisation strings for the Streamlit UI.

Usage:
    from src.i18n import get_text
    label = get_text("zh", "start_btn")   # -> "开始研究"
    label = get_text("en", "start_btn")   # -> "Start Research"
"""

TEXTS: dict[str, dict[str, str]] = {
    "zh": {
        # ── Language selector ────────────────────────────────────────────────
        "lang_label": "语言 / Language",
        # ── Titles / stage headers ───────────────────────────────────────────
        "title": "Multi-Agent 研究助手",
        "planning_title": "规划中",
        "review_title": "审阅研究计划",
        "plan_header": "研究计划",
        "research_header": "研究进行中",
        "writing_title": "生成报告",
        "report_header": "研究报告",
        "complete_header": "研究完成",
        # ── Sidebar ──────────────────────────────────────────────────────────
        "history_title": "研究历史",
        "total_sessions": "已保存会话数",
        "search_history_label": "搜索历史",
        "search_placeholder": "搜索关键词...",
        "no_history": "暂无历史记录",
        "no_sessions_found": "未找到相关记录。",
        "load_report": "加载报告",
        "new_research": "新研究",
        "session_tasks": "任务：{n_plan}  |  研究：{n_ok}/{n_res} 完成",
        # ── Idle stage ───────────────────────────────────────────────────────
        "idle_description": (
            "输入研究问题，助手将自动规划、调用搜索工具并生成结构化 Markdown 报告。"
        ),
        "research_question_label": "研究问题",
        "input_placeholder": "输入你的研究问题...",
        "start_btn": "开始研究",
        # ── Planning stage ───────────────────────────────────────────────────
        "query_label": "问题",
        "planning_spinner": "正在生成研究计划...",
        "plan_empty_error": "规划器返回了空计划，请重试。",
        "back": "返回",
        # ── Reviewing stage ──────────────────────────────────────────────────
        "plan_subtasks": "规划器生成了 **{n}** 个子任务：",
        "approve_btn": "确认并开始",
        "request_changes": "修改意见",
        "request_changes_placeholder": "例如：增加一个性能对比的章节...",
        "replan_btn": "提交修改意见",
        "replanning_spinner": "正在重新规划...",
        "cancel_btn": "取消",
        # ── Researching stage ────────────────────────────────────────────────
        "progress_text": "已完成 {idx}/{total} 个任务",
        "task_ok": "[完成]",
        "task_fail": "[失败]",
        "task_skip": "[跳过]",
        "researching_task": "正在研究任务 {idx}/{total}：{task}",
        # ── Writing stage ────────────────────────────────────────────────────
        "generating_report": "正在生成研究报告...",
        "report_empty_error": "Writer 返回了空报告。",
        "back_to_research": "返回研究",
        # ── Done stage ───────────────────────────────────────────────────────
        "overall": "综合评分",
        "plan_quality": "计划质量",
        "research_quality": "研究质量",
        "report_quality": "报告质量",
        "research_details": "研究详情",
        "download_label": "下载 (.md)",
        "start_new_research": "开始新研究",
    },
    "en": {
        # ── Language selector ────────────────────────────────────────────────
        "lang_label": "语言 / Language",
        # ── Titles / stage headers ───────────────────────────────────────────
        "title": "Multi-Agent Research Assistant",
        "planning_title": "Planning",
        "review_title": "Review Research Plan",
        "plan_header": "Research Plan",
        "research_header": "Researching",
        "writing_title": "Writing Report",
        "report_header": "Report",
        "complete_header": "Research Complete",
        # ── Sidebar ──────────────────────────────────────────────────────────
        "history_title": "Research History",
        "total_sessions": "Total sessions stored",
        "search_history_label": "Search history",
        "search_placeholder": "keyword...",
        "no_history": "No history yet.",
        "no_sessions_found": "No sessions found.",
        "load_report": "Load report",
        "new_research": "New Research",
        "session_tasks": "Tasks: {n_plan}  |  Research: {n_ok}/{n_res} OK",
        # ── Idle stage ───────────────────────────────────────────────────────
        "idle_description": (
            "Enter a research question. The assistant will plan, research using "
            "web/Wikipedia tools, and write a structured Markdown report."
        ),
        "research_question_label": "Research question",
        "input_placeholder": "Enter your research question...",
        "start_btn": "Start Research",
        # ── Planning stage ───────────────────────────────────────────────────
        "query_label": "Query",
        "planning_spinner": "Generating research plan...",
        "plan_empty_error": "The planner returned an empty plan. Please try again.",
        "back": "Back",
        # ── Reviewing stage ──────────────────────────────────────────────────
        "plan_subtasks": "The planner created **{n}** sub-tasks:",
        "approve_btn": "Approve & Start",
        "request_changes": "Request changes",
        "request_changes_placeholder": "e.g. Add a section on performance benchmarks...",
        "replan_btn": "Replan with Feedback",
        "replanning_spinner": "Replanning...",
        "cancel_btn": "Cancel",
        # ── Researching stage ────────────────────────────────────────────────
        "progress_text": "Completed {idx} of {total} tasks",
        "task_ok": "[OK]",
        "task_fail": "[FAIL]",
        "task_skip": "[SKIP]",
        "researching_task": "Researching task {idx}/{total}: {task}",
        # ── Writing stage ────────────────────────────────────────────────────
        "generating_report": "Generating research report...",
        "report_empty_error": "The writer returned an empty report.",
        "back_to_research": "Back to Research",
        # ── Done stage ───────────────────────────────────────────────────────
        "overall": "Overall",
        "plan_quality": "Plan quality",
        "research_quality": "Research quality",
        "report_quality": "Report quality",
        "research_details": "Research details",
        "download_label": "Download (.md)",
        "start_new_research": "Start New Research",
    },
}


def get_text(lang: str, key: str) -> str:
    """Return the UI string for *key* in *lang* (falls back to English)."""
    return TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))
