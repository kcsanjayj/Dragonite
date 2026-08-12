# Autonomous AI Agent

A modular, task-oriented **Autonomous AI Agent** built in Python.

The project takes a user's natural-language request, creates a task plan, executes independent tasks in parallel, evaluates results, handles failures/retries, and produces a final response.

The goal of this project is not to claim "AGI", but to demonstrate practical understanding of **LLM orchestration, task graphs, retries, modular architecture, memory, tool execution, and autonomous workflows**.

---

## Why I Built This

Most beginner AI projects simply do:

```text
User → LLM → Answer
```

I wanted to explore a more structured architecture:

```text
User Request
     ↓
Memory
     ↓
Planner
     ↓
Task Graph / DAG
     ↓
Executor
     ↓
Critic
     ↓
Repair / Replanning
     ↓
Synthesis
     ↓
Final Answer
```

This project helped me understand how an LLM can be used as a component inside a larger software system rather than being the entire system.

---

## What It Does

The agent can:

* Accept natural-language requests.
* Create multi-step execution plans.
* Represent tasks as a dependency graph.
* Execute independent tasks concurrently.
* Execute LLM-based tasks.
* Execute tool-based tasks.
* Retry failed tasks.
* Track task status and progress.
* Critically evaluate completed tasks.
* Support repair/replanning workflows.
* Maintain a modular memory layer.
* Synthesize task outputs into a concise final response.
* Expose a simple CLI interface.

### Example

Input:

```text
BMW vs Audi which is best?
```

The planner may produce:

```text
research_bmw
research_audi
       ↓
    compare
       ↓
   recommend
```

The executor then runs the independent research tasks before executing dependent tasks.

---

# Architecture

```text
                         ┌──────────────────┐
                         │    User / CLI    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ AutonomousEngine │
                         └────────┬─────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
        ┌─────────┐          ┌──────────┐        ┌─────────┐
        │ Memory  │          │ Planner  │        │ Logger  │
        └─────────┘          └────┬─────┘        └─────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Task Graph    │
                         │      (DAG)      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    Executor     │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
              ┌──────────┐                ┌──────────┐
              │ LLM Task │                │ Tool Task│
              └──────────┘                └──────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  ▼
                            ┌──────────┐
                            │  Critic  │
                            └────┬─────┘
                                 │
                         ┌───────┴────────┐
                         │                │
                         ▼                ▼
                      Accept            Repair
                         │                │
                         │                ▼
                         │           Replanner
                         │                │
                         └───────┬────────┘
                                 ▼
                           ┌────────────┐
                           │Synthesizer │
                           └─────┬──────┘
                                 │
                                 ▼
                           Final Answer
```

---

# Project Structure

```text
adk-agent/
│
├── multi_tool_agent/
│   │
│   ├── agent.py
│   ├── cli.py
│   ├── config.py
│   ├── providers.py
│   │
│   ├── llm/
│   │   └── llm_client.py
│   │
│   ├── model/
│   │   └── model_router.py
│   │
│   ├── core/
│   │   ├── graph.py
│   │   ├── node.py
│   │   ├── state.py
│   │   │
│   │   └── plan/
│   │       ├── plan_converter.py
│   │       └── plan_schema.py
│   │
│   ├── orchestration/
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── critic.py
│   │   ├── replanner.py
│   │   ├── router.py
│   │   └── synthesizer.py
│   │
│   ├── runtime/
│   │   └── engine.py
│   │
│   ├── memory/
│   │   ├── context.py
│   │   ├── manager.py
│   │   ├── memory_store.py
│   │   ├── models.py
│   │   └── store.py
│   │
│   ├── tools/
│   │   ├── builtins.py
│   │   ├── executor.py
│   │   ├── manager.py
│   │   └── tool_registry.py
│   │
│   └── observability/
│       ├── logger.py
│       └── tracer.py
│
├── data/
├── .env
├── requirements.txt
├── architecture.md
├── run_agent.py
└── README.md
```

---

# Core Components

## 1. AutonomousEngine

`AutonomousEngine` is the main orchestration layer.

It coordinates:

* Planning
* Execution
* Criticism
* Replanning
* Synthesis
* Memory
* Observability

The engine also manages the shared LLM client used by different components.

---

## 2. Planner

The planner converts a natural-language request into executable tasks.

For example:

```text
User:
BMW vs Audi which is best?
```

Possible plan:

```text
research_bmw
research_audi
compare
recommend
```

Dependencies are represented explicitly:

```text
research_bmw ─────┐
                  ├──> compare ───> recommend
research_audi ────┘
```

This allows independent tasks to run concurrently.

---

## 3. Task Graph

Tasks are represented as nodes in a directed acyclic graph (DAG).

Each node can contain information such as:

* Task ID
* Task description
* Task type
* Dependencies
* Input data
* Output data
* Status
* Retry information
* Metadata

The graph allows the executor to determine which tasks are currently ready.

---

## 4. Executor

The executor is responsible for actually running tasks.

It supports:

### LLM tasks

```text
Task → Shared LLM Client → Result
```

### Tool tasks

```text
Task → ToolManager → Tool → Result
```

### Parallel execution

Independent tasks can execute concurrently using Python's thread pool.

For example:

```text
research_bmw   ──┐
                 ├── execute in parallel
research_audi  ──┘
```

while:

```text
compare
```

waits for both dependencies.

---

## 5. Retry Mechanism

Temporary failures should not immediately terminate the entire workflow.

The executor supports retry attempts with increasing delays.

Conceptually:

```text
Attempt 1
   ↓
Failure
   ↓
Attempt 2
   ↓
Failure
   ↓
Attempt 3
   ↓
Success / Failure
```

This is intentionally simple and transparent rather than pretending to provide sophisticated distributed fault tolerance.

---

## 6. Critic

The critic evaluates completed task outputs.

A task can be:

```text
PASS
```

or:

```text
PASS WITH WARNING
```

or require repair.

The purpose is to prevent every generated result from automatically being treated as correct.

---

## 7. Replanner

If a task requires improvement, the replanning layer can provide additional instructions or modify the workflow.

This creates a feedback loop:

```text
Execute
   ↓
Critic
   ↓
Needs improvement?
   ↓
Replan / Repair
   ↓
Execute again
```

---

## 8. Synthesizer

The synthesizer converts multiple task outputs into a single user-facing answer.

It is deliberately configured to:

* Hide internal execution details.
* Put the conclusion first when appropriate.
* Avoid exposing DAG/task/critic information.
* Keep responses concise.
* Prefer useful information over long generated explanations.

---

# LLM Integration

The project currently uses a shared LLM client architecture.

The LLM client is injected into components such as:

```text
Planner
Executor
Synthesizer
```

rather than creating unrelated clients throughout the application.

This makes provider/model changes easier and keeps the orchestration layer separated from the model layer.

---

# Example Execution

A simplified execution can look like:

```text
User Request
     │
     ▼
Planner
     │
     ▼
5 Tasks Created
     │
     ▼
2 Independent Tasks Ready
     │
     ├──────────────┐
     ▼              ▼
 Research A      Research B
     │              │
     └──────┬───────┘
            ▼
         Compare
            │
            ▼
         Evaluate
            │
            ▼
        Recommend
            │
            ▼
        Synthesis
            │
            ▼
       Final Answer
```

---

# Running the Project

Activate the virtual environment:

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the main CLI:

```powershell
python -m multi_tool_agent.cli
```

Or use the project launcher:

```powershell
python run_agent.py
```

---

# Example

```text
AUTONOMOUS AI AGENT

You: BMW vs Audi which is best?

Agent is working...
```

The internal system can create a dependency graph and execute the appropriate tasks before returning the final response.

---

# Configuration

Environment-specific configuration is kept outside the source code.

Example:

```text
.env
```

API keys and other secrets should **never be committed to Git**.

A typical setup may contain provider/model configuration such as:

```text
NVIDIA_API_KEY=your_key_here
```

Use the variable names expected by the project's configuration code.

---

# Design Principles

The project follows several principles.

### Separation of concerns

Planning, execution, criticism, memory, tools, and synthesis are separate components.

### Dependency-aware execution

Tasks should execute only when their dependencies are satisfied.

### Shared dependencies

The LLM client is shared instead of repeatedly constructing model clients.

### Failure awareness

Failures are represented explicitly rather than silently returning fake successful results.

### Observable execution

The system exposes progress and execution information through logging.

### Honest capability boundaries

This project is an **LLM orchestration system**, not AGI.

It does not independently possess human-level reasoning, guaranteed factual accuracy, or unrestricted autonomy.

---

# What I Learned

Building this project helped me understand several concepts beyond simply calling an LLM API:

* LLM application architecture
* Dependency injection
* DAG-based workflows
* Task scheduling
* Concurrent execution
* Retry mechanisms
* Error propagation
* Modular Python design
* Provider/model abstraction
* Tool execution
* State management
* Memory architecture
* Observability
* Prompt design
* LLM-based evaluation
* Autonomous workflow design

The biggest lesson was that an AI application is not just a prompt.

A reliable system requires software engineering around the model.

---

# Current Limitations

This project is intentionally presented honestly.

It currently has limitations including:

* LLM outputs are not guaranteed to be factually correct.
* Research quality depends on the available tools and model.
* The planner can generate imperfect task decompositions.
* Critic decisions are themselves LLM-dependent.
* Memory is not equivalent to human long-term memory.
* Parallel execution currently uses a relatively simple concurrency model.
* There is no guarantee of production-grade fault tolerance.
* Security hardening is not yet production-level.
* Evaluation is still an area for improvement.
* The system is better described as an **autonomous workflow/orchestration engine** than as a fully autonomous general-purpose intelligence.

These limitations are part of the reason this project is a learning/research project rather than a production platform.

---

# Future Improvements

Possible next steps include:

1. Better structured task schemas.
2. Stronger validation of planner-generated DAGs.
3. Persistent vector-based memory.
4. More reliable tool execution.
5. Better evaluation benchmarks.
6. Structured LLM outputs.
7. Improved observability and tracing.
8. Async execution for larger workflows.
9. Authentication and API-level security.
10. Web UI for interacting with the agent.
11. Human approval checkpoints for sensitive actions.
12. Automated regression tests.
13. Cost and latency tracking.
14. Better failure classification.
15. More robust model/provider fallback.

---

# Testing Philosophy

The project should not be evaluated only by whether:

```text
SUCCESS = True
```

A successful execution does not necessarily mean the generated answer is correct.

A stronger evaluation should measure:

* Task completion rate
* Planning accuracy
* Dependency correctness
* Retry effectiveness
* Final answer quality
* Latency
* Failure recovery
* LLM cost
* Factual accuracy

This distinction is important when building real AI systems.

---

# Project Status

**Status: Working prototype / learning project**

The core autonomous workflow is functional, including planning, dependency-based execution, retries, criticism, and final synthesis.

The project is still evolving toward stronger testing, evaluation, security, and production reliability.

---

# Why This Project Is Relevant to AI Engineering

A basic LLM application demonstrates:

```text
Prompt → Model → Response
```

This project explores a larger engineering problem:

```text
Request
   ↓
Planning
   ↓
Task decomposition
   ↓
Dependency management
   ↓
Execution
   ↓
Evaluation
   ↓
Recovery
   ↓
Synthesis
```

That difference is the main learning objective of this project.

---

# Author

Built as a learning project focused on understanding **AI agents, LLM orchestration, and autonomous task execution**.

The project is intentionally documented with its limitations so that its capabilities are easy to verify and defend during technical discussions.

---

## License

This project is licensed under the MIT License.
