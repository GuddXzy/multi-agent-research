"""Streamlit web UI for the Multi-Agent Research Assistant.

Stage machine:
    idle -> planning -> reviewing -> researching -> writing -> done

Run with:
    streamlit run app.py
"""

import io
import sys
import contextlib

# Import config first — sets HTTP_PROXY / HTTPS_PROXY / NO_PROXY env vars
# before any network library (httpx / requests / ddgs) is imported.
import src.config  # noqa: F401

import streamlit as st

from src.agents.planner import planner_node
from src.agents.replan import replan_node
from src.agents.researcher import researcher_node
from src.agents.writer import writer_node
from src.evaluation import Evaluator
from src.memory import MemoryStore
from src.config import MEMORY_DB_PATH
from src.state import AgentState
from src.i18n import get_text


# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    page_icon=":books:",
    layout="wide",
)


# ── Session-state initialisation ───────────────────────────────────────────────

def _init_state() -> None:
    defaults: dict = {
        "stage": "idle",        # idle|planning|reviewing|researching|writing|done
        "query": "",
        "plan": [],
        "research_results": [],
        "current_task_index": 0,
        "report": "",
        "task_logs": {},        # {task_text: captured_stdout_str}
        "eval_scores": None,
        "lang": "zh",           # "zh" | "en"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ── i18n helper ────────────────────────────────────────────────────────────────

def _t(key: str) -> str:
    """Shorthand: get UI text in the current language."""
    return get_text(st.session_state.lang, key)


# ── Helpers ────────────────────────────────────────────────────────────────────

@contextlib.contextmanager
def _capture_stdout():
    """Redirect stdout into a StringIO buffer; yield the buffer."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def _make_state() -> AgentState:
    """Build an AgentState dict from current session state."""
    return {
        "query":               st.session_state.query,
        "plan":                list(st.session_state.plan),
        "research_results":    list(st.session_state.research_results),
        "current_task_index":  st.session_state.current_task_index,
        "report":              st.session_state.report,
        "error":               None,
        "human_approved":      True,
        "human_feedback":      None,
        "language":            st.session_state.lang,  # "zh" | "en"
    }


def _reset() -> None:
    """Return to idle stage and clear all research state."""
    st.session_state.stage = "idle"
    st.session_state.query = ""
    st.session_state.plan = []
    st.session_state.research_results = []
    st.session_state.current_task_index = 0
    st.session_state.report = ""
    st.session_state.task_logs = {}
    st.session_state.eval_scores = None


# ── Sidebar ────────────────────────────────────────────────────────────────────

def _render_sidebar() -> None:
    with st.sidebar:
        # ── Language selector (top of sidebar) ───────────────────────────────
        lang_options = ["中文", "English"]
        current_index = 0 if st.session_state.lang == "zh" else 1
        chosen = st.selectbox(
            _t("lang_label"),
            options=lang_options,
            index=current_index,
            key="lang_select",
        )
        new_lang = "zh" if chosen == "中文" else "en"
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang
            st.rerun()

        st.divider()

        # ── History ───────────────────────────────────────────────────────────
        with st.expander(_t("history_title"), expanded=False):
            mem = MemoryStore(MEMORY_DB_PATH)
            stats = mem.get_stats()
            st.caption(f"{_t('total_sessions')}: {stats['total']}")

            search_kw = st.text_input(
                _t("search_history_label"),
                placeholder=_t("search_placeholder"),
                key="hist_search",
            )

            sessions = (
                mem.search_sessions(search_kw)
                if search_kw.strip()
                else mem.get_recent_sessions(limit=8)
            )

            if not sessions:
                st.info(_t("no_sessions_found") if search_kw else _t("no_history"))
            else:
                for i, s in enumerate(sessions):
                    label = s["query"]
                    if len(label) > 52:
                        label = label[:49] + "..."
                    with st.expander(label, expanded=False):
                        ts = (s["created_at"] or "")[:19].replace("T", " ")
                        st.caption(ts)
                        plan_list = s["plan_json"] if isinstance(s["plan_json"], list) else []
                        res_list = s["results_json"] if isinstance(s["results_json"], list) else []
                        succeeded = sum(
                            1 for r in res_list if r.get("status") == "success"
                        )
                        st.write(_t("session_tasks").format(
                            n_plan=len(plan_list),
                            n_ok=succeeded,
                            n_res=len(res_list),
                        ))
                        if st.button(_t("load_report"), key=f"load_{s['id']}_{i}"):
                            st.session_state.report = s["report"]
                            st.session_state.plan = plan_list
                            st.session_state.research_results = res_list
                            st.session_state.query = s["query"]
                            st.session_state.eval_scores = None
                            st.session_state.stage = "done"
                            st.rerun()

        st.divider()
        if st.button(_t("new_research"), use_container_width=True, type="primary"):
            _reset()
            st.rerun()


# ── Stage: idle ────────────────────────────────────────────────────────────────

def _stage_idle() -> None:
    st.title(_t("title"))
    st.write(_t("idle_description"))

    query = st.text_area(
        _t("research_question_label"),
        placeholder=_t("input_placeholder"),
        height=110,
        key="query_input",
    )

    if st.button(
        _t("start_btn"),
        type="primary",
        disabled=not query.strip(),
    ):
        st.session_state.query = query.strip()
        st.session_state.stage = "planning"
        st.rerun()


# ── Stage: planning ────────────────────────────────────────────────────────────

def _stage_planning() -> None:
    st.title(_t("planning_title"))
    st.write(f"**{_t('query_label')}:** {st.session_state.query}")

    with st.spinner(_t("planning_spinner")):
        state = _make_state()
        with _capture_stdout():
            result = planner_node(state)
        plan = result.get("plan", [])

    if not plan:
        st.error(_t("plan_empty_error"))
        if st.button(_t("back")):
            _reset()
            st.rerun()
        return

    st.session_state.plan = plan
    st.session_state.stage = "reviewing"
    st.rerun()


# ── Stage: reviewing ───────────────────────────────────────────────────────────

def _stage_reviewing() -> None:
    st.title(_t("review_title"))
    st.write(f"**{_t('query_label')}:** {st.session_state.query}")
    st.write(_t("plan_subtasks").format(n=len(st.session_state.plan)))

    for i, task in enumerate(st.session_state.plan, 1):
        st.write(f"{i}. {task}")

    st.divider()

    col_approve, col_feedback, col_cancel = st.columns([1, 2, 1])

    with col_approve:
        if st.button(_t("approve_btn"), type="primary", use_container_width=True):
            st.session_state.current_task_index = 0
            st.session_state.research_results = []
            st.session_state.task_logs = {}
            st.session_state.stage = "researching"
            st.rerun()

    with col_feedback:
        feedback = st.text_input(
            _t("request_changes"),
            placeholder=_t("request_changes_placeholder"),
            key="review_feedback",
        )
        if st.button(
            _t("replan_btn"),
            use_container_width=True,
            disabled=not feedback.strip(),
        ):
            with st.spinner(_t("replanning_spinner")):
                state = _make_state()
                state["human_approved"] = False
                state["human_feedback"] = feedback.strip()
                with _capture_stdout():
                    result = replan_node(state)
                new_plan = result.get("plan", st.session_state.plan)
            st.session_state.plan = new_plan
            st.rerun()

    with col_cancel:
        if st.button(_t("cancel_btn"), use_container_width=True):
            _reset()
            st.rerun()


# ── Stage: researching ────────────────────────────────────────────────────────

def _stage_researching() -> None:
    idx = st.session_state.current_task_index
    plan = st.session_state.plan
    total = len(plan)

    st.title(_t("research_header"))
    st.write(f"**{_t('query_label')}:** {st.session_state.query}")
    st.progress(
        idx / total if total else 1.0,
        text=_t("progress_text").format(idx=idx, total=total),
    )

    # ── Render already-finished tasks ────────────────────────────────────────
    for past_idx, task in enumerate(plan[:idx]):
        past_result = next(
            (r for r in st.session_state.research_results if r.get("task") == task),
            None,
        )
        ok = past_result and past_result.get("status") == "success"
        icon = _t("task_ok") if ok else _t("task_fail")
        with st.expander(f"{icon} Task {past_idx + 1}: {task}", expanded=False):
            logs = st.session_state.task_logs.get(task, "")
            if logs.strip():
                st.code(logs, language=None)
            if past_result:
                st.markdown(past_result.get("result", ""))

    # ── Process current task ──────────────────────────────────────────────────
    if idx < total:
        current_task = plan[idx]
        label = _t("researching_task").format(idx=idx + 1, total=total, task=current_task)

        with st.status(label, expanded=True) as status_widget:
            state = _make_state()
            with _capture_stdout() as buf:
                result = researcher_node(state)
            logs = buf.getvalue()

            new_results: list = result.get("research_results", [])
            new_idx: int = result.get("current_task_index", idx + 1)

            # The node appended exactly one entry; grab the latest
            latest = new_results[-1] if new_results else None

            if latest:
                ok = latest.get("status") == "success"
                icon = _t("task_ok") if ok else _t("task_fail")
                done_label = f"{icon} Task {idx + 1}: {current_task}"
                status_widget.update(
                    label=done_label,
                    state="complete" if ok else "error",
                )
                if logs.strip():
                    st.code(logs, language=None)
                st.markdown(latest.get("result", ""))
            else:
                status_widget.update(
                    label=f"{_t('task_skip')} Task {idx + 1}: no result",
                    state="error",
                )

        # Persist and advance
        st.session_state.task_logs[current_task] = logs
        st.session_state.research_results = new_results
        st.session_state.current_task_index = new_idx
        st.rerun()

    else:
        # All tasks complete — move to writing stage
        st.session_state.stage = "writing"
        st.rerun()


# ── Stage: writing ────────────────────────────────────────────────────────────

def _stage_writing() -> None:
    st.title(_t("writing_title"))
    st.write(f"**{_t('query_label')}:** {st.session_state.query}")

    with st.spinner(_t("generating_report")):
        state = _make_state()
        with _capture_stdout():
            result = writer_node(state)
        report = result.get("report", "")

    if not report.strip():
        st.error(_t("report_empty_error"))
        if st.button(_t("back_to_research")):
            st.session_state.stage = "reviewing"
            st.rerun()
        return

    st.session_state.report = report

    # Evaluate quality
    evaluator = Evaluator()
    st.session_state.eval_scores = evaluator.overall_score(
        plan=st.session_state.plan,
        research_results=st.session_state.research_results,
        report=report,
        query=st.session_state.query,
    )

    # Persist session to memory
    mem = MemoryStore(MEMORY_DB_PATH)
    mem.save_session(
        query=st.session_state.query,
        plan=st.session_state.plan,
        research_results=st.session_state.research_results,
        report=report,
    )

    st.session_state.stage = "done"
    st.rerun()


# ── Stage: done ───────────────────────────────────────────────────────────────

def _stage_done() -> None:
    st.title(_t("complete_header"))
    st.write(f"**{_t('query_label')}:** {st.session_state.query}")

    # ── Quality metrics ───────────────────────────────────────────────────────
    scores = st.session_state.eval_scores
    if scores:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(_t("overall"), f"{scores['overall_score']}/100")
        c2.metric(_t("plan_quality"), f"{scores['plan']['score']}/100")
        c3.metric(_t("research_quality"), f"{scores['research']['score']}/100")
        c4.metric(_t("report_quality"), f"{scores['report']['score']}/100")
        st.divider()

    # ── Research summary ──────────────────────────────────────────────────────
    with st.expander(_t("research_details"), expanded=False):
        for r in st.session_state.research_results:
            ok = r.get("status") == "success"
            icon = _t("task_ok") if ok else _t("task_fail")
            st.write(f"**{icon} {r.get('task', '')}**")
            snippet = r.get("result", "")
            if len(snippet) > 400:
                snippet = snippet[:397] + "..."
            st.write(snippet)
            st.divider()

    # ── Full report ───────────────────────────────────────────────────────────
    st.subheader(_t("report_header"))
    st.markdown(st.session_state.report)

    # ── Actions ───────────────────────────────────────────────────────────────
    col_dl, col_new = st.columns([1, 3])
    with col_dl:
        st.download_button(
            label=_t("download_label"),
            data=st.session_state.report.encode("utf-8"),
            file_name="research_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_new:
        if st.button(_t("start_new_research"), type="primary"):
            _reset()
            st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────

_render_sidebar()

_STAGES = {
    "idle":        _stage_idle,
    "planning":    _stage_planning,
    "reviewing":   _stage_reviewing,
    "researching": _stage_researching,
    "writing":     _stage_writing,
    "done":        _stage_done,
}

stage = st.session_state.stage
handler = _STAGES.get(stage)
if handler:
    handler()
else:
    st.error(f"Unknown stage: {stage!r}")
    _reset()
    st.rerun()
