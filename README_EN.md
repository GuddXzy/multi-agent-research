[中文版本](README.md)

# APEC Trade Research Assistant

Targeting the 2026 Shenzhen APEC Summit — helps export businesses rapidly research target markets. Multi-agent collaboration breaks down research dimensions, gathers multi-source information, generates structured market briefs, and supports trend tracking.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-green)
![DeepSeek](https://img.shields.io/badge/DeepSeek-V3-purple)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)
![SQLite](https://img.shields.io/badge/SQLite-memory-lightgrey?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Why This Project

The 2026 APEC Summit will be held in Shenzhen in November, with 21 member economies participating. As China's top export city, Shenzhen is home to numerous SMEs that need to quickly understand target markets — trade policies, competitive landscapes, and APEC policy benefits.

**Pain point**: Information sources are scattered (news, policy documents, economic data from various countries), updates are frequent, and manual research is time-consuming and prone to missing key dimensions.

**Solution**: Multi-agent system automatically decomposes research dimensions → multi-source information gathering → structured market brief → historical trend tracking.

**Why not just ask ChatGPT?**
- Requires systematic decomposition of research dimensions (market size, tariff barriers, competitive landscape, APEC policies) — one question isn't enough
- Needs standardised output format, not chat-style text
- Needs historical records and trend comparison — ChatGPT has no memory
- Sensitive topics require human review of research dimensions

---

## Demo

![Home](docs/demo_home.png)
![Plan Review](docs/demo_plan.png)
![Research Complete](docs/demo_report.png)

Typical workflow:

1. Enter a research query — e.g. *"I'm a Shenzhen consumer electronics exporter, looking into the Vietnam market opportunity"*
2. **Planner** decomposes the query into 5 research dimensions (market size, tariff barriers, competitive landscape, APEC policies, logistics strategy)
3. **Human Review**: confirm the dimensions, or request additions/modifications
4. **Researcher** searches each dimension via DuckDuckGo (real-time data) + Wikipedia (background knowledge)
5. **Writer** synthesises a standardised *Market Research Brief* (with data and sources)
6. **Trend comparison**: automatically compares with historical research, marking changes with ↑↓→

---

## Architecture

```
User Research Query
   │
   ▼
┌─────────────┐
│   Planner   │  Decomposes by research dimension (market/tariff/competition/policy/logistics)
└──────┬──────┘
       │
       ▼
┌─────────────┐   needs changes?   ┌──────────────┐
│ Human Review│ ◀─────────────────▶ │   Replan     │
└──────┬──────┘                    └──────────────┘
       │ approved
       ▼
┌─────────────────────────────────────────────────┐
│               Researcher Agent                  │
│                                                 │
│  Dimension 1 → [ReAct loop] → findings          │
│  Dimension 2 → [ReAct loop] → findings          │  ← auto-retry on failure (up to 3×)
│  Dimension N → [ReAct loop] → findings          │
│                                                 │
│  Tools: DuckDuckGo (real-time) | Wikipedia      │
│  Strategy: search in English → summarise in Chinese │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
           ┌──────────────┐
           │    Writer    │  → Standardised Market Research Brief
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │   Memory     │  → SQLite persistence + trend comparison
           └──────────────┘
```

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent Orchestration** | LangGraph state graph manages the full workflow with 5 agent nodes |
| **Trade Research Prompts** | Optimised for market size, tariff barriers, competitive landscape, APEC policies |
| **Human-in-the-Loop** | Review research dimensions before execution; supports multiple revision rounds |
| **Hand-written ReAct Loop** | Regex-based Thought/Action/Observation parsing; no framework function-calling dependency |
| **English Search + Chinese Output** | Searches in English (broader international trade coverage), reports in Chinese |
| **Error Recovery** | Per-task 3× retry; failures don't block the pipeline; report flags failure reasons |
| **Trend Tracking** | After multiple research runs on the same topic, LLM auto-compares old vs new reports with ↑↓→ |
| **Structured Brief** | Fixed template: Summary / Market Overview / Trade Policy / Competition / Opportunities & Risks / Action Items |
| **Quality Evaluation** | Plan quality, research depth, report completeness — three-dimensional auto-scoring, zero LLM dependency |
| **Dual Entry Points** | Streamlit Web UI + CLI, bilingual Chinese/English support |

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Agent orchestration | LangGraph 0.2+ | State graph, node routing, loop control |
| LLM interface | LangChain + langchain-openai | Unified LLM abstraction |
| LLM model | DeepSeek-V3 (API) / Ollama (local) | Configurable model switching |
| Web search | DuckDuckGo (ddgs) | Real-time search tool |
| Knowledge base | Wikipedia | Structured reference source |
| Persistence | SQLite | Session memory + trend comparison |
| Frontend | Streamlit 1.35+ | Interactive web UI |
| Containerisation | Docker + Compose | One-command deployment (GPU passthrough) |
| Testing | pytest | 76 unit / integration tests |

---

## Quick Start

### Prerequisites

- Python 3.11+
- DeepSeek API Key ([get one here](https://platform.deepseek.com) — free credits are enough for testing)

### Install & Run

```bash
git clone https://github.com/GuddXzy/multi-agent-research.git
cd multi-agent-research

pip install -r requirements.txt

# Configure API Key
cp .env.example .env
# Edit .env and fill in your DeepSeek API Key

# Launch Web UI
streamlit run app.py

# Or use the CLI
python main.py "I'm a Shenzhen consumer electronics exporter, looking into the Vietnam market"
```

### Docker Deployment

```bash
docker compose up -d
```

> To use a local Ollama model: edit `LLM_BASE_URL` and `LLM_MODEL` in `.env`

---

## Project Structure

```
multi-agent-research/
├── app.py                  # Streamlit frontend entry point
├── main.py                 # CLI entry point
├── eval_runner.py          # Evaluation script
├── Dockerfile
├── docker-compose.yml
├── src/
│   ├── config.py           # Global config (LLM, retry params, env vars)
│   ├── state.py            # AgentState type definition
│   ├── graph.py            # LangGraph state graph orchestration
│   ├── memory.py           # SQLite session memory + trend comparison
│   ├── evaluation.py       # Three-dimensional evaluation framework
│   ├── i18n.py             # Chinese/English internationalisation
│   ├── agents/
│   │   ├── planner.py      # Research dimension decomposition
│   │   ├── researcher.py   # ReAct loop search
│   │   ├── writer.py       # Market brief generation
│   │   ├── human_review.py # Human review gate
│   │   └── replan.py       # Plan revision
│   └── tools/
│       ├── web_search.py   # DuckDuckGo search
│       ├── wikipedia.py    # Wikipedia search
│       └── text_tools.py   # Note saving
├── tests/                  # 76 tests
└── data/                   # SQLite database
```

---

## Trend Comparison Example

After researching the same topic twice, the system auto-generates a comparison:

```
📊 Trend Comparison Summary (2026-03-15 vs 2026-04-08)

1. Market size: grew from ~$8B to $9.12B (↑), but growth slowed from 6% to 3–5% (↓)
2. Growth categories: shifted from smartphones to wearables (→), consumer hotspots moving to emerging categories
3. Trade policy: ACFTA preferential rate dropped from 0–5% to 0% (↓), new APEC paperless customs clearance added
4. Competition: Samsung share stable above 40% (→), Chinese brands overall share rising (↑)
5. Strategy: shifted from targeting mid-range market to focusing on wearable growth segment, emphasising RCEP+ACFTA dual benefits
```

---

## License

[MIT](LICENSE)
