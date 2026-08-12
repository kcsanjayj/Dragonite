# Autonomous AI Agent — Architecture

## 1. Overview

This project is a modular **autonomous AI agent system** built in Python.

The main goal is to take a natural-language request, create a plan, execute independent tasks, evaluate the results, optionally repair failed work, and finally produce a concise user-facing answer.

The project is intentionally designed as a learning and portfolio project rather than a production-grade autonomous system.

The architecture separates:

* Planning
* Task execution
* Quality control
* Replanning
* Final answer synthesis
* Memory
* Tool execution
* Model/provider management
* Observability
* CLI interaction

---

# 2. High-Level Architecture

```text
                         USER
                           |
                           v
                    +-------------+
                    |     CLI     |
                    |   cli.py    |
                    +-------------+
                           |
                           v
                 +-------------------+
                 | AutonomousEngine   |
                 |   runtime/engine   |
                 +-------------------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
     Memory           Planner          Observability
                         |
                         v
                  +-------------+
                  |    Task     |
                  |    Graph    |
                  +-------------+
                         |
                         v
                  +-------------+
                  |  Executor   |
                  +-------------+
                    /         \
                   /           \
                  v             v
             LLM Tasks       Tool Tasks
                |                |
                v                v
           LLM Client       ToolManager
                |
                v
        Model / Provider Layer
                |
                v
          External LLM API


                  Executor
                     |
                     v
                  Critic
                     |
             +-------+-------+
             |               |
           PASS            FAIL
             |               |
             v               v
          Continue        Replanner
                             |
                             v
                         Executor
                             |
                             v
                        Synthesizer
                             |
                             v
                           USER
```

---

# 3. Project Structure

```text
multi_tool_agent/
│
├── agent.py
├── cli.py
├── config.py
├── providers.py
│
├── llm/
│   └── llm_client.py
│
├── model/
│   └── model_router.py
│
├── core/
│   ├── graph.py
│   ├── node.py
│   ├── state.py
│   │
│   └── plan/
│       ├── plan_converter.py
│       └── plan_schema.py
│
├── orchestration/
│   ├── planner.py
│   ├── executor.py
│   ├── critic.py
│   ├── replanner.py
│   ├── router.py
│   └── synthesizer.py
│
├── runtime/
│   └── engine.py
│
├── memory/
│   ├── context.py
│   ├── manager.py
│   ├── memory_store.py
│   ├── models.py
│   └── store.py
│
├── observability/
│   ├── logger.py
│   └── tracer.py
│
└── tools/
    ├── builtins.py
    ├── executor.py
    ├── manager.py
    └── tool_registry.py
```

---

# 4. Main Runtime Flow

The runtime follows approximately this pipeline:

```text
User Request
     |
     v
Memory Retrieval
     |
     v
Planning
     |
     v
Task Graph / DAG
     |
     v
Execute Ready Tasks
     |
     v
Critic
     |
     +---- PASS ------+
     |                |
     |                v
     |          Next Ready Tasks
     |                |
     |                v
     |             Execute
     |
     +---- FAIL ----> Replanner
                         |
                         v
                    Updated Plan
                         |
                         v
                      Execute
                         |
                         v
                     Synthesis
                         |
                         v
                   Final Response
```

The engine controls this lifecycle.

---

# 5. AutonomousEngine

### Location

```text
multi_tool_agent/runtime/engine.py
```

`AutonomousEngine` is the main orchestration layer.

Its responsibility is to coordinate the other components rather than perform every operation itself.

Conceptually:

```python
request
   ↓
memory
   ↓
planner
   ↓
executor
   ↓
critic
   ↓
replanner if necessary
   ↓
synthesizer
   ↓
response
```

The engine also controls the maximum number of autonomous cycles.

For example:

```text
Cycle 1
  execute → criticize

Cycle 2
  execute repaired/new tasks → criticize

Cycle 3
  execute remaining tasks → criticize

...

Maximum cycles reached
```

This prevents an incorrectly designed plan from running indefinitely.

---

# 6. Planner

### Location

```text
multi_tool_agent/orchestration/planner.py
```

The planner converts a natural-language request into a structured task plan.

For example:

```text
User:
BMW vs Audi which is best?
```

The planner may create:

```text
research_bmw
research_audi
       ↓
    compare
       ↓
   recommend
```

This is represented as a directed acyclic graph (DAG).

The planner uses the shared LLM client to generate the plan.

The important design decision is that the planner does not directly execute the tasks.

It only determines:

* What tasks are required
* Which tasks depend on other tasks
* Which tasks can run independently
* What type of task should be executed

---

# 7. Task Graph

### Locations

```text
multi_tool_agent/core/graph.py
multi_tool_agent/core/node.py
```

The task graph represents the execution plan.

Each task is represented by a node.

A simplified node can be thought of as:

```text
TaskNode
│
├── id
├── task
├── task_type
├── dependencies
├── status
├── output_data
├── error
└── retry information
```

Typical states include:

```text
PENDING
   ↓
RUNNING
   ↓
COMPLETED
```

or:

```text
RUNNING
   ↓
FAILED
   ↓
REPAIRING
   ↓
RUNNING
```

Dependencies determine whether a task is ready for execution.

---

# 8. Executor

### Location

```text
multi_tool_agent/orchestration/executor.py
```

The executor is responsible for actually running tasks.

It supports two primary execution paths:

```text
                    Executor
                       |
              +--------+--------+
              |                 |
           LLM Task          Tool Task
              |                 |
              v                 v
         LLM Client        ToolManager
```

Independent ready tasks can be executed concurrently using Python's thread pool.

For example:

```text
research_bmw ──────┐
                   ├──> compare
research_audi ─────┘
```

Both research tasks can run at the same time because neither depends on the other.

This is one of the main reasons the project uses a DAG instead of simply executing tasks sequentially.

---

# 9. Retry Handling

The executor supports task retries.

A simplified execution sequence is:

```text
Attempt 1
   |
   +---- success → completed
   |
   +---- failure
           |
           v
       Attempt 2
           |
           +---- success
           |
           +---- failure
                   |
                   v
               Attempt 3
```

A retry delay can increase between attempts.

The retry system is useful for transient failures, but it should not be considered a complete reliability system.

For example, retrying an invalid LLM prompt three times will not necessarily fix the underlying problem.

---

# 10. Critic

### Location

```text
multi_tool_agent/orchestration/critic.py
```

The critic performs a quality-control step after task execution.

Its purpose is to determine whether a completed task is good enough to continue.

Conceptually:

```text
Task Output
    |
    v
  Critic
    |
    +---- PASS
    |
    +---- WARNING
    |
    +---- FAIL
```

The critic can evaluate factors such as:

* Relevance
* Completeness
* Accuracy
* Task satisfaction

The critic itself may use the LLM.

---

# 11. Replanner

### Location

```text
multi_tool_agent/orchestration/replanner.py
```

If a task fails quality control, the replanner can generate updated instructions or modify the execution strategy.

Conceptually:

```text
Task Failure
     |
     v
  Critic
     |
     v
 Replanner
     |
     v
Updated Task / Plan
     |
     v
 Executor
```

This gives the system a basic feedback loop.

However, this is not equivalent to human-level autonomous reasoning.

The quality of replanning is still heavily dependent on the underlying LLM.

---

# 12. Synthesizer

### Location

```text
multi_tool_agent/orchestration/synthesizer.py
```

The synthesizer converts the outputs of completed tasks into the final user-facing response.

Its responsibilities are:

* Collect useful task outputs
* Remove internal orchestration information
* Prioritize the conclusion
* Keep the answer concise
* Produce a coherent final response

For example, internal results may look like:

```text
research_bmw
research_audi
compare
recommend
```

The user should not normally see those internal details.

Instead, the synthesizer produces something like:

```text
For driving engagement, BMW is generally the stronger choice.
Audi may be preferable if technology, interior design and
all-weather traction are higher priorities.
```

The exact answer depends on the task outputs.

---

# 13. LLM Client

### Location

```text
multi_tool_agent/llm/llm_client.py
```

The LLM client provides a common interface to the language model.

The rest of the architecture should not need to know the low-level provider API.

Conceptually:

```text
Planner
   |
Executor
   |
Critic
   |
Synthesizer
   |
   v
LLM Client
   |
   v
Provider
   |
   v
Model API
```

A shared LLM client is important because multiple components may need the same model configuration.

---

# 14. Provider and Model Routing

### Locations

```text
multi_tool_agent/providers.py
multi_tool_agent/model/model_router.py
```

These components separate model/provider configuration from orchestration logic.

This allows the project to potentially support different providers or models without rewriting the planner and executor.

The current implementation should be understood as a provider abstraction rather than a fully production-grade model routing platform.

---

# 15. Tool System

### Locations

```text
multi_tool_agent/tools/
```

The tool layer provides a mechanism for executing non-LLM operations.

Important components include:

```text
tool_registry.py
      |
      v
tool manager
      |
      v
tool executor
      |
      v
specific tool
```

The architecture allows an LLM-generated plan to contain tool tasks in addition to pure LLM tasks.

This is important because a useful autonomous agent should eventually be able to combine reasoning with actions.

---

# 16. Memory

### Locations

```text
multi_tool_agent/memory/
```

The memory subsystem is separated from the orchestration system.

Its purpose is to provide context from previous interactions.

Conceptually:

```text
Previous Information
       |
       v
Memory Store
       |
       v
Memory Manager
       |
       v
Relevant Context
       |
       v
Planner / Agent
```

The current memory architecture should not be described as a sophisticated long-term human-memory system.

It is better understood as a modular foundation for adding persistent or semantic memory later.

---

# 17. Observability

### Locations

```text
multi_tool_agent/observability/logger.py
multi_tool_agent/observability/tracer.py
```

Logging and tracing are separated from the core orchestration logic.

This helps inspect:

* Task execution
* Errors
* Execution cycles
* Model calls
* Runtime behavior

The current console logs are primarily useful for development and debugging.

For production, this could be extended with structured logs, metrics, distributed tracing, and persistent monitoring.

---

# 18. CLI

### Location

```text
multi_tool_agent/cli.py
```

The CLI provides the current user interface.

Typical flow:

```text
You: BMW vs Audi which is best?

Agent is working...

[internal execution]

Final response
```

The CLI is intentionally kept separate from the autonomous engine.

This means another interface can be added later without rewriting the orchestration layer.

For example:

```text
CLI
 |
 +---- Web UI
 |
 +---- API
 |
 +---- ADK Web
 |
 +---- Other frontend
```

---

# 19. Single Shared LLM Client

A key architectural decision is to use one shared LLM client.

```text
                  Shared LLM Client
                         |
        +----------------+----------------+
        |                |                |
     Planner          Executor          Critic
        |                |                |
        +----------------+----------------+
                         |
                    Synthesizer
```

This avoids unnecessarily creating separate model clients for every component.

It also makes provider configuration easier to manage.

---

# 20. Why the DAG Architecture?

A simple sequential agent could do:

```text
Task 1
  ↓
Task 2
  ↓
Task 3
  ↓
Task 4
```

The current architecture instead supports:

```text
Task A ─────┐
            ├──> Task C
Task B ─────┘
```

A and B can execute concurrently.

For larger workflows:

```text
A ──┐
B ──┼──> D ──> F
C ──┘     |
          E
```

This can reduce unnecessary waiting when tasks are independent.

---

# 21. Error Handling Strategy

The system currently has several layers of failure handling:

```text
LLM / Tool Error
      |
      v
Executor Retry
      |
      +---- success
      |
      +---- failure
             |
             v
          Task Failed
             |
             v
           Critic
             |
             v
          Replanner
```

The engine also has a maximum cycle limit.

This protects the application from infinite autonomous loops.

---

# 22. Important Design Boundary

The system should NOT be described as:

> "A fully autonomous AGI."

That would be misleading.

A more accurate description is:

> "A modular autonomous-agent orchestration system that uses an LLM to plan, execute, evaluate and synthesize multi-step tasks."

This distinction is important.

The LLM remains the main reasoning component.

The surrounding Python system provides:

* Structure
* State management
* Task dependencies
* Execution
* Retries
* Quality control
* Tool integration
* Memory integration
* Runtime control

---

# 23. Current Strengths

The strongest parts of the architecture are:

1. **Clear separation of responsibilities**
2. **DAG-based task execution**
3. **Parallel execution of independent tasks**
4. **Shared LLM client**
5. **Retry handling**
6. **Quality-control stage**
7. **Replanning capability**
8. **Tool abstraction**
9. **Memory abstraction**
10. **Separate runtime and CLI layers**

These make the project significantly more structured than a single Python script that simply sends prompts to an LLM.

---

# 24. Current Limitations

This project is still a learning/portfolio implementation.

Important limitations include:

### LLM dependence

Planning, task execution, criticism and synthesis can depend heavily on the LLM.

If the model produces a poor plan, the system can still make poor decisions.

### No guaranteed factual correctness

The critic is not a ground-truth verifier.

A task can pass the critic while still containing incorrect information.

### Limited tool grounding

The agent can only perform actions for tools that have actually been implemented and registered.

### Limited persistent memory

The memory layer is modular, but it should not be presented as equivalent to a mature vector-memory or enterprise knowledge system unless those capabilities are actually implemented.

### No guaranteed optimal planning

The generated DAG is an LLM-generated plan.

There is no formal proof that it is optimal.

### Concurrency limitations

Thread-based execution is useful for independent I/O-heavy tasks, but it is not a replacement for a distributed task execution system.

### Security

The current architecture should not be assumed to be safe for arbitrary untrusted tool execution.

Production deployment would require authentication, authorization, sandboxing, rate limiting and stronger input/output controls.

---

# 25. Why This Architecture Is Defensible in an Interview

If asked:

### "Did you build an AI agent?"

A defensible answer is:

> "Yes. I built a modular LLM-based autonomous-agent orchestration system. It converts a request into a DAG of tasks, executes independent tasks concurrently, evaluates outputs, supports retries and replanning, and synthesizes the final response."

If asked:

### "Is it production-ready?"

A strong honest answer is:

> "No. I consider it a portfolio and learning implementation. The architecture is modular, but production deployment would require stronger observability, security, persistence, evaluation, distributed execution and reliability guarantees."

If asked:

### "Why didn't you just make one LLM call?"

A good answer is:

> "A single LLM call is simpler, but it doesn't explicitly manage multi-step dependencies, parallel execution, retries, quality control or task-level state. I wanted to explore those orchestration problems separately."

---

# 26. Future Architecture

A realistic next evolution would be:

```text
                    Web / API / ADK UI
                           |
                           v
                    API / Session Layer
                           |
                           v
                  AutonomousEngine
                           |
        +------------------+------------------+
        |                  |                  |
     Planner            Memory           Observability
        |
        v
      DAG
        |
        v
 Distributed Executor
        |
   +----+----+
   |         |
  LLM      Tools
   |         |
   +----+----+
        |
        v
     Critic
        |
   +----+----+
   |         |
 PASS      REPLAN
   |         |
   +----+----+
        |
        v
   Synthesizer
        |
        v
      User
```

Possible future improvements:

* Web/API interface
* ADK integration
* Persistent database
* Vector/semantic memory
* Structured model outputs
* Better task schemas
* Evaluation benchmarks
* Distributed task execution
* Authentication and authorization
* Sandboxed tools
* Cost tracking
* Token usage tracking
* Model fallback strategies
* Structured telemetry
* Automated regression tests

---

# 27. Engineering Philosophy

The project follows one important principle:

> **Prefer explicit orchestration over hiding everything inside one prompt.**

The LLM provides reasoning and language capabilities.

Python provides deterministic control over:

* State
* Dependencies
* Execution
* Retries
* Components
* Interfaces
* Runtime limits

This separation makes the system easier to inspect, test and extend.

---

# 28. Final Assessment

This project should be presented as:

**A modular autonomous-agent orchestration project built for learning and demonstrating agent architecture.**

It is not presented as a production-grade autonomous AI platform.

The most valuable engineering aspect is not the claim that the system is "fully autonomous."

The valuable part is the architecture:

```text
Natural Language
      ↓
LLM Planning
      ↓
Structured DAG
      ↓
Parallel Execution
      ↓
Quality Control
      ↓
Repair / Replanning
      ↓
Synthesis
      ↓
Final Answer
```

That is the core design demonstrated by the project.
