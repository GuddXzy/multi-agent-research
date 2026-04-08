[English Version](README_EN.md)

# APEC 外贸商机研究助手

面向 2026 深圳 APEC 峰会，帮助外贸企业快速调研目标市场——多 Agent 协作拆解调研维度、多源采集信息、生成结构化市场简报，支持趋势追踪。

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-green)
![DeepSeek](https://img.shields.io/badge/DeepSeek-V3-purple)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)
![SQLite](https://img.shields.io/badge/SQLite-memory-lightgrey?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 为什么做这个

2026 年 11 月 APEC 峰会在深圳举办，21 个成员经济体参与。深圳作为中国外贸第一城，大量中小出口企业需要快速了解目标市场的贸易政策、竞争格局和 APEC 政策利好。

**痛点**：信息源分散（各国新闻、政策文件、经济数据）、更新频繁、人工调研耗时且容易遗漏关键维度。

**解决方案**：多 Agent 系统自动拆解调研维度 → 多源信息采集 → 结构化市场简报 → 历史趋势追踪。

**为什么不直接问 ChatGPT**：
- 需要系统化拆解调研维度（市场规模、关税壁垒、竞争格局、APEC 政策），一个问题问不完
- 需要标准化输出格式，不是聊天文字
- 需要历史记录和趋势对比，ChatGPT 没有记忆
- 敏感议题需要人工审核调研维度

---

## Demo

典型使用流程：

1. 输入调研需求：「我是深圳做消费电子出口的企业，想了解越南市场机会」
2. **Planner** 自动拆解为 5 个调研维度（市场规模、关税壁垒、竞争格局、APEC 政策、物流策略）
3. **Human Review**：确认维度划分，或要求增删修改
4. **Researcher** 逐维度搜索，DuckDuckGo（实时数据）+ Wikipedia（背景知识）
5. **Writer** 汇总为标准化《市场调研简报》（中文，含数据和来源）
6. **趋势对比**：自动与历史调研结果对比，标注市场规模↑↓、政策变化、竞争格局变动

---

## 架构

```
用户调研需求
   │
   ▼
┌─────────────┐
│   Planner   │  按调研维度拆解（市场/关税/竞争/政策/物流）
└──────┬──────┘
       │
       ▼
┌─────────────┐   修改意见？   ┌──────────────┐
│ Human Review│ ◀────────────▶ │   Replan     │
└──────┬──────┘                └──────────────┘
       │ 确认
       ▼
┌─────────────────────────────────────────────┐
│              Researcher Agent               │
│                                             │
│  维度 1 → [ReAct 循环] → 搜索结果          │
│  维度 2 → [ReAct 循环] → 搜索结果          │  ← 失败自动重试（最多 3 次）
│  维度 N → [ReAct 循环] → 搜索结果          │
│                                             │
│  Tools: DuckDuckGo（实时） | Wikipedia      │
│  策略: 英文搜索 → 中文总结                  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
           ┌──────────────┐
           │    Writer    │  → 标准化《市场调研简报》
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │   Memory     │  → SQLite 持久化 + 趋势对比
           └──────────────┘
```

---

## 核心功能

| 功能 | 说明 |
|------|------|
| **Multi-Agent 编排** | LangGraph 状态图管理完整工作流，5 个 Agent 节点协作 |
| **外贸调研 Prompt** | 针对市场规模、关税壁垒、竞争格局、APEC 政策等维度优化 |
| **Human-in-the-Loop** | 调研前人工审阅维度划分，支持多轮修改直到满意 |
| **手写 ReAct 循环** | 正则解析 Thought/Action/Observation，不依赖框架 function calling |
| **英文搜索 + 中文输出** | 搜索用英文（国际贸易数据覆盖更广），报告用中文 |
| **错误恢复** | 单任务 3 次重试，失败不中断流程，报告标注失败原因 |
| **趋势追踪** | 同一话题多次调研后，LLM 自动对比新旧报告，标注 ↑↓→ 变化 |
| **结构化简报** | 固定模板：摘要/市场概况/贸易政策/竞争格局/机遇与风险/行动建议 |
| **质量评估** | 计划质量、研究深度、报告完整性三维度自动评分，零 LLM 依赖 |
| **双入口** | Streamlit Web UI + CLI，支持中英双语 |

---

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| Agent 编排 | LangGraph 0.2+ | 状态图、节点路由、循环控制 |
| LLM 调用 | LangChain + langchain-openai | 统一 LLM 接口 |
| LLM 模型 | DeepSeek-V3（API）/ Ollama（本地） | 可配置切换 |
| 网络搜索 | DuckDuckGo (ddgs) | 实时搜索工具 |
| 百科搜索 | Wikipedia | 结构化知识来源 |
| 数据持久化 | SQLite | 会话记忆 + 趋势对比 |
| 前端 | Streamlit 1.35+ | Web 交互界面 |
| 容器化 | Docker + Compose | 一键部署（GPU 透传） |
| 测试 | pytest | 76 个单元/集成测试 |

---

## 快速开始

### 前置条件

- Python 3.11+
- DeepSeek API Key（[申请地址](https://platform.deepseek.com)，免费额度足够测试）

### 安装运行

```bash
git clone https://github.com/GuddXzy/multi-agent-research.git
cd multi-agent-research

pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key

# 启动 Web 界面
streamlit run app.py

# 或使用 CLI
python main.py "我是深圳做消费电子出口的企业，想了解越南市场机会"
```

### Docker 部署

```bash
docker compose up -d
```

> 使用本地 Ollama 模型：修改 `.env` 中的 `LLM_BASE_URL` 和 `LLM_MODEL`

---

## 项目结构

```
multi-agent-research/
├── app.py                  # Streamlit 前端入口
├── main.py                 # CLI 入口
├── eval_runner.py          # 评估脚本
├── Dockerfile
├── docker-compose.yml
├── src/
│   ├── config.py           # 全局配置（LLM、重试参数、环境变量）
│   ├── state.py            # AgentState 类型定义
│   ├── graph.py            # LangGraph 状态图编排
│   ├── memory.py           # SQLite 会话记忆 + 趋势对比
│   ├── evaluation.py       # 三维度评估框架
│   ├── i18n.py             # 中英双语国际化
│   ├── agents/
│   │   ├── planner.py      # 调研维度拆解
│   │   ├── researcher.py   # ReAct 循环搜索
│   │   ├── writer.py       # 市场简报生成
│   │   ├── human_review.py # 人工审阅
│   │   └── replan.py       # 计划修改
│   └── tools/
│       ├── web_search.py   # DuckDuckGo 搜索
│       ├── wikipedia.py    # Wikipedia 搜索
│       └── text_tools.py   # 笔记保存
├── tests/                  # 76 个测试
└── data/                   # SQLite 数据库
```

---

## 趋势对比示例

同一话题调研两次后，系统自动生成对比：

```
📊 趋势对比摘要（2026-03-15 vs 2026-04-08）

1. 市场规模：从约 80 亿美元增至 91.2 亿美元（↑），但增速从 6% 放缓至 3-5%（↓）
2. 增长品类：从智能手机转向可穿戴设备（→），消费热点向新兴品类转移
3. 贸易政策：ACFTA 优惠税率从 0-5% 明确降至 0%（↓），新增 APEC 无纸化通关
4. 竞争格局：三星份额稳定超 40%（→），中国品牌份额整体上升（↑）
5. 战略建议：从瞄准中端市场转向聚焦可穿戴增量市场，强调 RCEP+ACFTA 双重优惠
```

---

## License

[MIT](LICENSE)
