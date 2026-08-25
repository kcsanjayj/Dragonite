# 🐉 Dragonite — Autonomous Multi-Agent System

> **A graph-based autonomous AI agent system that plans, executes, evaluates, repairs, and synthesizes complex tasks.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python\&logoColor=white)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.6.3-4285F4?logo=google)](https://google.github.io/adk-docs/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi\&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ⚡ 30-Second Overview

**Dragonite is not a single LLM call.**

It separates an autonomous workflow into explicit engineering components:

```text
User Request
     │
     ▼
  Planner
     │
     ▼
  Task DAG
     │
     ├──────────────┐
     ▼              ▼
 Task A           Task B
     └──────┬───────┘
            ▼
        Executor
            │
            ▼
          Critic
            │
       ┌────┴────┐
       │         │
     Good      Failed
       │         │
       │      Replanner
       │         │
       └────◄────┘
            │
            ▼
       Synthesizer
            │
            ▼
       Final Answer
```

### 🧠 What I built

* 🗺️ LLM-powered task planning
* 🕸️ Dependency-aware DAG execution
* ⚡ Parallel execution of independent tasks
* 🔧 Tool execution layer
* 🔄 Retry handling
* 🔍 Critic / quality-control stage
* ♻️ Replanning and repair flow
* 🧩 Shared LLM client architecture
* 💾 Memory layer
* 📊 Execution progress tracking
* 🔭 Logging and tracing
* 🔌 Google ADK integration

---

## 🎥 Live Terminal Demo

<p align="center">
  <video
    src="https://github.com/kcsanjayj/Dragonite/raw/refs/heads/main/docs/demo/dragonite.mp4"
    controls
    autoplay
    muted
    loop
    playsinline
    width="900">
  </video>
</p>

<p align="center">
  <strong>23-second live terminal demonstration of Dragonite</strong>
</p>

<p align="center">
  Request → Planning → Task Execution → Orchestration → Evaluation → Final Output
</p>

---

# 🏗️ Architecture

Dragonite uses a modular orchestration architecture:

```text
                    ┌──────────────┐
                    │ User Request │
                    └───────┬──────┘
                            ▼
                    ┌──────────────┐
                    │    Memory    │
                    └───────┬──────┘
                            ▼
                    ┌──────────────┐
                    │   Planner    │
                    └───────┬──────┘
                            ▼
                    ┌──────────────┐
                    │   Task DAG   │
                    └───────┬──────┘
                            ▼
                    ┌──────────────┐
                    │   Executor   │
                    └───────┬──────┘
                            ▼
                    ┌──────────────┐
                    │    Critic    │
                    └───────┬──────┘
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
              Accepted              Failed
                 │                     │
                 │               ┌─────▼─────┐
                 │               │ Replanner │
                 │               └─────┬─────┘
                 │                     │
                 └───────────◄─────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Synthesizer  │
                    └───────┬──────┘
                            ▼
                       Final Answer
```

### Key design decision

The system intentionally separates:

**planning ≠ execution ≠ evaluation ≠ recovery ≠ presentation**

This makes the workflow easier to reason about, extend, debug, and test than putting the entire process into one large agent prompt.

📐 **Detailed design:** [`architecture.md`](architecture.md)

---

# 🔥 Engineering Highlights

### 1. Dependency-aware execution

Tasks are represented as nodes with dependencies.

For example:

```text
research_A ──────┐
                 ├──► compare ──► evaluate ──► recommend
research_B ──────┘
```

Independent tasks can execute concurrently while dependent tasks wait for their prerequisites.

---

### 2. Parallel execution

The executor uses Python concurrency to execute ready independent tasks in parallel.

This provides a foundation for scaling workflows beyond strictly sequential execution.

---

### 3. Retry handling

Task failures do not necessarily terminate the entire workflow.

The executor supports configurable retry attempts with backoff.

```text
Attempt 1
   │
 Failure
   ▼
Attempt 2
   │
 Failure
   ▼
Attempt 3
   │
 Success / Final Failure
```

---

### 4. Critic → Repair loop

Dragonite does not blindly trust the first generated result.

The critic can identify quality problems and feed repair information into the replanning process.

```text
Execute
  │
  ▼
Critic
  │
  ├── Good ──────────────► Continue
  │
  └── Problem ─► Replan ─► Repair ─► Execute
```

---

### 5. Shared LLM infrastructure

Planner, executor, and synthesizer can use a shared configured LLM client.

```text
                 Shared LLM Client
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Planner      Executor    Synthesizer
```

This avoids unnecessary model-client duplication and keeps model configuration centralized.

---

# 🛠️ Tech Stack

| Technology             | Purpose                        |
| ---------------------- | ------------------------------ |
| **Python 3.11+**       | Core implementation            |
| **Google ADK**         | Agent/application ecosystem    |
| **LLM providers**      | Model execution                |
| **FastAPI**            | API/application infrastructure |
| **Pydantic**           | Validation and configuration   |
| **ThreadPoolExecutor** | Parallel execution             |
| **OpenTelemetry**      | Observability                  |
| **python-dotenv**      | Environment configuration      |

All pinned dependencies are documented in [`requirements.txt`](requirements.txt).

---

# 🚀 Run Locally

## 1. Clone

```bash
git clone https://github.com/kcsanjayj/Dragonite.git
cd Dragonite
```

## 2. Create environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment

Copy:

```text
.env_example
```

to:

```text
.env
```

Then configure your required model/provider credentials.

## 5. Start Dragonite

```bash
python run_agent.py
```

Alternative:

```bash
python -m multi_tool_agent.cli
```

---

# 🔐 Security

Secrets are intentionally excluded from Git.

Use:

```text
.env
```

for local credentials.

Use:

```text
.env_example
```

to document required variables.

**Never commit API keys, tokens, passwords, or private credentials.**

---

# 🎯 Honest Project Scope

Dragonite is a **hands-on autonomous-agent engineering project**, not a claim of AGI or a production-ready platform.

The project demonstrates practical understanding of:

* multi-agent orchestration
* DAG-based workflows
* dependency management
* concurrent execution
* LLM integration
* tool execution
* retries and failure handling
* quality control
* replanning
* memory
* observability

There are still important areas to improve before production deployment, including:

* broader automated tests
* stronger sandboxing
* persistent production-grade state
* systematic evaluation benchmarks
* security hardening
* CI/CD
* production monitoring
* stronger failure isolation

**Those limitations are intentionally documented rather than hidden.**

> 💡 The goal of Dragonite is not to claim that the system is perfect.
> The goal is to demonstrate that I can design, implement, debug, and explain a non-trivial AI-agent architecture.

---

# 📚 Documentation

* 📐 [`architecture.md`](architecture.md) — system architecture
* 📦 [`requirements.txt`](requirements.txt) — pinned dependencies
* ⚙️ [`.env_example`](.env_example) — configuration template
* 🎥 [`docs/demo/`](docs/demo/) — project demonstration
* 📜 [`LICENSE`](LICENSE) — MIT License

---

## ⭐ Why this project matters

Dragonite was built to explore what happens when an LLM application is treated as a **software system rather than just a prompt**.

The focus is on:

**architecture → execution → failure handling → evaluation → recovery → observability**

rather than simply generating a response from one model call.

---

## 📜 License

MIT License.

See [`LICENSE`](LICENSE).

---

**Built by [Sanjay](https://github.com/kcsanjayj) as a hands-on exploration of autonomous AI-agent systems and Python engineering.**

⭐ If you find Dragonite interesting, consider starring the repository.
