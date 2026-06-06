"""
Observability utilities for the autonomous agent system.
Provides logging, metrics, and tracing for agent operations.
"""

import time
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime
from .logger import logger


class AgentTracer:
    """Traces agent execution and decisions."""
    
    def __init__(self):
        """Initialize tracer."""
        self.traces: list = []
        self.current_trace: Optional[Dict[str, Any]] = None
    
    def start_trace(self, operation: str, **context):
        """Start a new trace."""
        self.current_trace = {
            "operation": operation,
            "start_time": time.time(),
            "context": context,
            "steps": []
        }
        logger.info(f"[TRACE] Starting: {operation}")
        return self.current_trace
    
    def add_step(self, agent: str, action: str, details: Dict[str, Any] = None):
        """Add a step to current trace."""
        if self.current_trace:
            step = {
                "agent": agent,
                "action": action,
                "timestamp": time.time(),
                "details": details or {}
            }
            self.current_trace["steps"].append(step)
            logger.info(f"[{agent}] {action}")
    
    def end_trace(self, status: str = "success", result: Any = None):
        """End current trace."""
        if self.current_trace:
            duration = time.time() - self.current_trace["start_time"]
            self.current_trace.update({
                "end_time": time.time(),
                "duration_ms": duration * 1000,
                "status": status,
                "result": result
            })
            self.traces.append(self.current_trace)
            logger.info(f"[TRACE] Completed: {self.current_trace['operation']} in {duration:.2f}s")
            self.current_trace = None
    
    def get_traces(self) -> list:
        """Get all traces."""
        return self.traces


class TokenTracker:
    """Tracks token usage and costs across LLM calls."""
    
    # Approximate costs per 1K tokens (adjust based on provider)
    COSTS_PER_1K = {
        "openai": {"input": 0.0015, "output": 0.002},
        "anthropic": {"input": 0.003, "output": 0.015},
        "nvidia": {"input": 0.0005, "output": 0.0015},
        "gemini": {"input": 0.0005, "output": 0.0015},
        "grok": {"input": 0.005, "output": 0.015},
    }
    
    def __init__(self):
        """Initialize token tracker."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.calls_by_provider: Dict[str, int] = {}
        self.tokens_by_agent: Dict[str, Dict[str, int]] = {}
    
    def record_usage(self, provider: str, agent: str, 
                     input_tokens: int, output_tokens: int):
        """Record token usage from a call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        # Track by provider
        self.calls_by_provider[provider] = self.calls_by_provider.get(provider, 0) + 1
        
        # Track by agent
        if agent not in self.tokens_by_agent:
            self.tokens_by_agent[agent] = {"input": 0, "output": 0}
        self.tokens_by_agent[agent]["input"] += input_tokens
        self.tokens_by_agent[agent]["output"] += output_tokens
        
        # Calculate cost
        cost = self._calculate_cost(provider, input_tokens, output_tokens)
        self.total_cost += cost
        
        logger.info(f"[TOKENS] {agent}: {input_tokens} in / {output_tokens} out (${cost:.4f})")
    
    def _calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage."""
        costs = self.COSTS_PER_1K.get(provider, {"input": 0.001, "output": 0.002})
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        return input_cost + output_cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": round(self.total_cost, 4),
            "calls_by_provider": self.calls_by_provider,
            "tokens_by_agent": self.tokens_by_agent
        }
    
    def check_limits(self, max_tokens: int = 100000, max_cost: float = 1.0) -> bool:
        """Check if within token/cost limits."""
        total = self.total_input_tokens + self.total_output_tokens
        if total > max_tokens:
            logger.warning(f"[LIMIT] Token limit exceeded: {total}/{max_tokens}")
            return False
        if self.total_cost > max_cost:
            logger.warning(f"[LIMIT] Cost limit exceeded: ${self.total_cost:.4f}/${max_cost}")
            return False
        return True


# Global instances
tracer = AgentTracer()
token_tracker = TokenTracker()


@contextmanager
def trace_step(agent: str, action: str, **context):
    """Context manager for tracing agent steps."""
    tracer.add_step(agent, action, context)
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        logger.debug(f"[{agent}] {action} completed in {duration:.3f}s")


def log_agent_decision(agent: str, decision: str, reasoning: str = ""):
    """Log an agent decision."""
    logger.info(f"[DECISION] {agent}: {decision}")
    if reasoning:
        logger.debug(f"[REASONING] {agent}: {reasoning}")


def log_tool_call(tool_name: str, parameters: Dict[str, Any], success: bool = True):
    """Log a tool call."""
    status = "✓" if success else "✗"
    logger.info(f"[TOOL] {status} {tool_name}: {parameters}")


def get_execution_report() -> Dict[str, Any]:
    """Get complete execution report."""
    return {
        "traces": tracer.get_traces(),
        "token_usage": token_tracker.get_summary(),
        "within_limits": token_tracker.check_limits()
    }


def export_metrics() -> Dict[str, Any]:
    """
    Export structured metrics for monitoring (Prometheus/JSON).

    Returns:
        Dictionary with production-ready metrics
    """
    from ..core.state import state
    metrics = state.get_metrics()

    return {
        "execution": {
            "total_time_ms": metrics.get("total_duration_ms", 0),
            "total_nodes": metrics.get("total_nodes", 0),
            "completed_nodes": metrics.get("completed_nodes", 0),
            "failed_nodes": metrics.get("failed_nodes", 0),
            "success_rate": (
                metrics.get("completed_nodes", 0) / max(metrics.get("total_nodes", 1), 1)
            ),
            "replan_attempts": metrics.get("replan_attempts", 0),
        },
        "tokens": token_tracker.get_summary(),
        "failures": metrics.get("failure_patterns", {}),
        "errors_count": len(state.get_errors()),
        "timestamp": datetime.utcnow().isoformat()
    }


def export_prometheus_format() -> str:
    """
    Export metrics in Prometheus text format.

    Returns:
        Prometheus-formatted metrics string
    """
    metrics = export_metrics()
    lines = []

    # Execution metrics
    lines.append(f"# TYPE dragon_execution_time_ms gauge")
    lines.append(f"dragon_execution_time_ms {metrics['execution']['total_time_ms']}")

    lines.append(f"# TYPE dragon_nodes_total gauge")
    lines.append(f"dragon_nodes_total {metrics['execution']['total_nodes']}")

    lines.append(f"# TYPE dragon_nodes_completed gauge")
    lines.append(f"dragon_nodes_completed {metrics['execution']['completed_nodes']}")

    lines.append(f"# TYPE dragon_nodes_failed gauge")
    lines.append(f"dragon_nodes_failed {metrics['execution']['failed_nodes']}")

    lines.append(f"# TYPE dragon_success_rate gauge")
    lines.append(f"dragon_success_rate {metrics['execution']['success_rate']:.4f}")

    lines.append(f"# TYPE dragon_replan_attempts counter")
    lines.append(f"dragon_replan_attempts {metrics['execution']['replan_attempts']}")

    # Token metrics
    tokens = metrics['tokens']
    lines.append(f"# TYPE dragon_tokens_total gauge")
    lines.append(f"dragon_tokens_total {tokens.get('total_tokens', 0)}")

    lines.append(f"# TYPE dragon_cost_usd gauge")
    lines.append(f"dragon_cost_usd {tokens.get('estimated_cost_usd', 0)}")

    return "\n".join(lines)
