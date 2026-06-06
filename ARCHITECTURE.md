# Dragon Architecture

## System Overview

Dragon is a semi-autonomous multi-agent executor (8.8/10 autonomy score) that uses a graph-based execution model with self-replanning and smart tool-switching capabilities.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                        │
│                    (Terminal UI / API)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                          Engine                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              State Machine Core                        │  │
│  │  • Idle → Planning → Executing → Replanning → Done   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Pipeline                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Router  │→ │ Planner  │→ │ Executor │→ │  Critic  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                     │                      │
│                                     ▼                      │
│                              ┌──────────┐                 │
│                              │Replanner │                 │
│                              └──────────┘                 │
│                                     │                      │
│                                     ▼                      │
│                              ┌──────────┐                 │
│                              │Synthesizer│                 │
│                              └──────────┘                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tool Registry                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Search  │  │Web Fetch │  │Python Exec│  │  Custom  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM Client Gateway                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  OpenAI  │  │Anthropic │  │  NVIDIA  │  │  Gemini  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐                               │
│  │   Grok   │  │HuggingFace│                               │
│  └──────────┘  └──────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## Agent Details

### Router Agent
- **Purpose**: Classify user intent and determine workflow
- **Input**: User query
- **Output**: Intent classification (type, workflow, confidence)
- **LLM Used**: For intent classification

### Planner Agent
- **Purpose**: Generate execution plan as a DAG
- **Input**: User query, intent, available tools
- **Output**: Plan with nodes, edges, dependencies
- **LLM Used**: For plan generation
- **Key Feature**: Always includes at least one tool call

### Executor Agent
- **Purpose**: Execute tool calls from the plan
- **Input**: Plan nodes with tool calls
- **Output**: Tool execution results
- **Tools Used**: Search, Web Fetch, Python Exec, Custom tools

### Critic Agent
- **Purpose**: Validate execution results and plans
- **Input**: Execution results or plans
- **Output**: Validation result (passed/failed, severity, message)
- **LLM Used**: For semantic validation
- **Rule-Based**: Basic validation rules

### Replanner Agent
- **Purpose**: Repair failed plans dynamically
- **Input**: Failed node, error, original plan, problematic tools
- **Output**: Repaired plan with modified nodes
- **LLM Used**: For repair strategy generation
- **Key Feature**: Self-healing without manual intervention, avoids tools that failed 2+ times

### Synthesizer Agent
- **Purpose**: Create final response from execution results
- **Input**: All execution results, context
- **Output**: Comprehensive user response
- **LLM Used**: For response synthesis

## Graph-Based Execution

### DAG Structure
- **Nodes**: Individual execution steps (tool calls, synthesis)
- **Edges**: Dependencies between nodes
- **Validation**: Ensures acyclic graph (no circular dependencies)
- **Execution**: Topological sort for parallel execution

### Example DAG
```
Node 1: Search for information
    ↓
Node 2: Fetch web page (depends on Node 1)
    ↓
Node 3: Extract data (depends on Node 2)
    ↓
Node 4: Analyze data (depends on Node 3)
    ↓
Node 5: Synthesize response (depends on Node 4)
```

## State Machine

### States
1. **Idle**: Waiting for user input
2. **Planning**: Generating execution plan
3. **Executing**: Running tool execution
4. **Replanning**: Repairing failed plan
5. **Done**: Execution complete

### Transitions
- Idle → Planning: User input received
- Planning → Executing: Plan generated successfully
- Executing → Replanning: Tool execution failed
- Replanning → Executing: Plan repaired
- Executing → Done: All nodes executed successfully
- Replanning → Done: Cannot repair (fallback)

## Tool Execution

### Search Tool
- **Provider**: DuckDuckGo
- **Purpose**: Web search for information
- **Output**: Search results with titles, URLs, snippets

### Web Fetch Tool
- **Provider**: HTTP + Playwright
- **Purpose**: Fetch web page content
- **Browsers**: Chrome, Firefox, Brave, Safari
- **Modes**: HTTP (fast) or Browser (JavaScript rendering)

### Python Exec Tool
- **Purpose**: Execute Python code safely
- **Sandbox**: Restricted execution environment
- **Output**: Code execution results

## LLM Integration

### Provider Architecture
- **Unified Interface**: Single client for all providers
- **Async Support**: All providers use async/await
- **Error Handling**: Unified error handling and retries
- **Model Selection**: Dynamic model selection per provider

### Supported Providers
- OpenAI (GPT-4, GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5 Sonnet, Claude 3.5 Haiku)
- NVIDIA (Llama 3.1 405B, Llama 3.1 8B)
- Gemini (Gemini 1.5 Pro, Gemini 1.5 Flash)
- Grok (Grok Beta, Grok 1)
- HuggingFace (Mistral 7B, Llama 2)

## Data Flow

1. **User Input** → Router Agent
2. **Intent Classification** → Planner Agent
3. **Plan Generation** → Graph Builder
4. **DAG Validation** → State Machine
5. **Tool Execution** → Executor Agent
6. **Result Validation** → Critic Agent
7. **Plan Repair** (if needed) → Replanner Agent
8. **Response Synthesis** → Synthesizer Agent
9. **Final Response** → User

## Error Handling

### Tool Execution Errors
- Per-tool failure tracking
- Smart tool switching after 2 failures
- Automatic retry with exponential backoff
- Replanner creates alternative strategies
- Fallback to simpler tools if available

### LLM Errors
- Provider fallback (if multiple configured)
- Retry with different parameters
- Graceful degradation

### Plan Validation Errors
- Replanner attempts to fix
- Returns original plan if repair fails
- Logs warnings for debugging

## Performance Considerations

### Concurrency
- Parallel tool execution when dependencies allow
- Async I/O for all network operations
- Connection pooling for HTTP requests

### Caching (Future)
- LLM response caching
- Tool result caching
- Plan template caching

### Scalability (Future)
- Distributed execution support
- Task queue for long-running operations
- Load balancing for multiple users
