[中文版本](README.md)

# Multi-Agent Research Assistant

Multiple AI agents collaborate to tackle research questions — automatically breaking down problems, gathering information, and producing structured reports.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)
![SQLite](https://img.shields.io/badge/SQLite-memory-lightgrey?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Demo

![Home](docs/demo_home.png)
![Plan Review](docs/demo_plan.png)
![Research Complete](docs/demo_report.png)

Typical workflow in under 30 seconds:

1. Enter a research question in the Streamlit UI — e.g. *"How does quantum computing threaten modern cryptography?"*
2. The Planner breaks it into 3–5 focused sub-tasks and presents the plan for review
3. You approve or refine the plan; the Researcher then executes each sub-task using DuckDuckGo and Wikipedia
4. Once all sub-tasks finish, the Writer synthesises findings into a structured Markdown report with citations
5. The session is saved to SQLite — pick up where you left off in any future run

---

## Architecture

```
User Query
   │
   ▼
┌─────────────┐
│   Planner   │  Decomposes the query into 3–5 actionable sub-tasks
└──────┬──────┘
       │ plan
       ▼
┌─────────────┐   needs changes?   ┌──────────────┐
│ Human Review│ ◀─────────────────▶ │   Replan     │
└──────┬──────┘                    └──────────────┘
       │ approved
       ▼
┌─────────────────────────────────────────────────┐
│               Researcher Agent                  │
│                                                 │
│  Sub-task 1 → [ReAct loop] → findings           │
│  Sub-task 2 → [ReAct loop] → findings           │  ← auto-retry on failure (up to 3×)
│  Sub-task N → [ReAct loop] → findings           │
│                                                 │
│  Tools: DuckDuckGo Search | Wikipedia           │
└──────────────────┬──────────────────────────────┘
                   │ all tasks complete
                   ▼
           ┌──────────────┐
           │    Writer    │  Synthesises findings → Markdown report
           └──────────────┘
```

**Planner** — Calls the LLM to decompose the research question into concrete, independently answerable sub-tasks that collectively cover the topic.

**Human Review / Replan** — Execution pauses after planning so you can read, approve, or request changes. Supports multiple revision rounds before the pipeline proceeds.

**Researcher** — Runs a hand-written ReAct loop for each sub-task, calling search tools to gather evidence. Built-in retry logic handles transient failures gracefully.

**Writer** — Aggregates all sub-task results into a structured report with sections, cited sources, and a *Research Limitations* note generated deterministically (no extra LLM call).

---

## Features

- **Multi-Agent Orchestration** — LangGraph state graph wires agents together; shared state flows through every node
- **Human-in-the-Loop** — Review and edit the research plan before any searches run
- **Real Tool Calling** — Live DuckDuckGo web search + Wikipedia; ReAct loop hand-rolled for compatibility with small models
- **Error Recovery** — Per-task retry with configurable back-off; graceful degradation flags failed tasks in the final report
- **Long-term Memory** — SQLite persists session history; CLI offers `--history` and `--search` for recall
- **Evaluation Framework** — Three-dimensional automatic scoring (plan quality, research depth, report completeness); fully deterministic, no LLM judge needed

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Agent orchestration | LangGraph 0.2+ | State graph, node routing, loop control |
| LLM interface | LangChain + langchain-openai | Unified LLM abstraction |
| Local LLM | Ollama + qwen2.5:7b | Inference engine, runs fully offline |
| Web search | DuckDuckGo (ddgs) | Real-time search tool |
| Knowledge base | Wikipedia | Structured reference source |
| Persistence | SQLite | Session memory storage |
| Frontend | Streamlit 1.35+ | Interactive web UI |
| Containerisation | Docker + Compose | One-command deployment |
| Testing | pytest | 76 tests, all passing |

---

## Quick Start

### Prerequisites

- Git
- **Option A (Docker):** Docker Desktop
- **Option B (Local):** Python 3.11+, [Ollama](https://ollama.com)

---

### A. Docker (recommended)

```bash
git clone https://github.com/GuddXzy/multi-agent-research.git
cd multi-agent-research

# Start all services in the background
docker compose up -d

# Pull the model — ~2 GB on first run, skipped thereafter
bash scripts/init_ollama.sh
```

Open http://localhost:8501 in your browser.

> **No NVIDIA GPU?** Remove the `deploy` block from `docker-compose.yml` and it runs on CPU just fine.

---

### B. Local

```bash
git clone https://github.com/GuddXzy/multi-agent-research.git
cd multi-agent-research

pip install -r requirements.txt

# Pull and serve the model locally
ollama pull qwen2.5:7b
ollama serve

# Launch the web UI
streamlit run app.py

# Or use the CLI
python main.py "How does quantum computing threaten modern cryptography?"
```

---

## Project Structure

```
multi-agent-research/
├── app.py                  # Streamlit frontend entry point
├── main.py                 # CLI entry point
├── eval_runner.py          # Evaluation script
├── Dockerfile
├── docker-compose.yml
├── scripts/
│   └── init_ollama.sh      # Model initialisation helper
├── src/
│   ├── config.py           # Global config (LLM, paths, retry params)
│   ├── state.py            # AgentState type definition
│   ├── graph.py            # LangGraph state graph
│   ├── memory.py           # SQLite session memory
│   ├── evaluation.py       # Evaluation framework
│   ├── agents/
│   │   ├── planner.py
│   │   ├── researcher.py
│   │   ├── writer.py
│   │   ├── human_review.py
│   │   └── replan.py
│   └── tools/
│       ├── web_search.py
│       ├── wikipedia.py
│       └── text_tools.py
└── tests/                  # 74 unit / integration tests
```

---

## Evaluation

Run `python eval_runner.py` to score a research run across three dimensions:

| Dimension | What's measured |
|-----------|----------------|
| **Plan Quality** | Sub-task count, topic coverage, specificity of each task |
| **Research Depth** | Information yield per sub-task, tool call frequency, result completeness |
| **Report Completeness** | Section structure, cited sources, limitations section, word coverage |

Scoring is fully deterministic Python — no LLM judge, no flakiness.

---

## Roadmap

- [x] LangGraph multi-agent state graph
- [x] Human-in-the-loop plan review
- [x] ReAct tool calling (DuckDuckGo + Wikipedia)
- [x] Error recovery and retry logic
- [x] SQLite long-term memory
- [x] Evaluation framework
- [x] Streamlit web UI
- [x] Docker one-command deployment
- [ ] Parallel sub-task execution for faster research
- [ ] Additional tools (arXiv, GitHub, News API)
- [ ] RAG-enhanced retrieval over past reports
- [ ] Multi-model support (swap in GPT-4, Claude, or Gemini via config)

---

## License

[MIT](LICENSE)
