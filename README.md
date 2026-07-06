# Dragonite

**A graph-based AI agent system for chaining LLM reasoning, tool execution, and recovery.**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Repo](https://img.shields.io/badge/github-kcsanjayj/Dragonite-blue.svg)](https://github.com/kcsanjayj/Dragonite)

---

## What this is

Dragonite is a clean AI agent prototype. It turns a user request into a small execution graph, runs tools in parallel where possible, and retries failed steps with a fallback plan.

This is useful for building smart workflows that mix language model reasoning with simple tools like web search, Python execution, and scraping.

---

## Why it matters

- Built as a pipeline, not a monolith
- Clear separation between planning, execution, and response synthesis
- Supports multiple LLM providers and provider-specific keys
- Saves your UI settings locally so you can reuse the same provider/model setup

---

## Core architecture

```
Input → Router → Planner → DAG → Executor → Critic → (Replanner) → Synthesizer → Output
```

### Key parts

- **Router:** decides what kind of request this is
- **Planner:** creates a directed graph of tasks
- **Executor:** runs ready tasks in parallel
- **Critic:** checks results and triggers repairs
- **Replanner:** fixes failed or stuck plans
- **Synthesizer:** turns node outputs into the final response

---

## Quick start

```bash
git clone https://github.com/kcsanjayj/Dragonite.git
cd Dragonite
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install
python run.py --api
```

Open `http://localhost:8000/ui/terminal.html` and enter a prompt.

---

## UI workflow

1. Select provider
2. Enter provider API key
3. Save settings
4. Type a question and press Enter

The terminal-style page streams the agent response and shows simple metrics.

---

## Development notes

- `app/core/engine.py` is the main pipeline
- `app/api/routes.py` handles the frontend API
- `app/llm/client.py` abstracts provider calls
- `app/ui/` contains the new terminal UI
- `tests/` holds end-to-end and integration checks


## Run tests

```bash
pytest tests/
```

---

## License

MIT
