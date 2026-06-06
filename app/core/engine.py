"""
State machine core for the autonomous agent system.
Main brain that orchestrates the entire execution pipeline.
"""

from typing import Optional
import asyncio
from .state import state
from .types import SystemState, Plan, UserIntent, ReplanRequest, NodeStatus, ExecutionResult
from .config import config
from ..agents.router import RouterAgent
from ..agents.planner import PlannerAgent
from ..agents.replanner import ReplannerAgent
from ..agents.executor import ExecutorAgent
from ..agents.critic import CriticAgent
from ..agents.synthesizer import SynthesizerAgent
from ..llm.provider_factory import provider_factory
from ..utils.observability import tracer, log_agent_decision
from ..utils.persistence import persistence
import uuid


class Engine:
    """
    State machine core - the main brain of the autonomous agent system.
    Orchestrates the entire execution pipeline with state transitions.
    """
    
    def __init__(self):
        """Initialize the engine."""
        self.router = RouterAgent()
        self.planner = PlannerAgent()
        self.replanner = ReplannerAgent()
        self.executor = ExecutorAgent()
        self.critic = CriticAgent()
        self.synthesizer = SynthesizerAgent()
        
        self._running = False
        self._max_replan_attempts = config.get_setting("max_replan_attempts", 3)

        # EXECUTION GOVERNOR - Safety limits
        self._max_nodes = config.get_setting("max_nodes", 20)
        self._max_parallel = config.get_setting("max_parallel", 5)
        self._max_execution_time = config.get_setting("max_execution_time", 30)  # seconds
        self._execution_semaphore = asyncio.Semaphore(self._max_parallel)
    
    async def initialize(self) -> None:
        """Initialize the engine and all its components."""
        # Initialize LLM providers
        provider_factory.initialize()
        
        # Register tools
        from ..tools.search import SearchTool
        from ..tools.python_exec import PythonExecTool
        from ..tools.web_fetch import WebFetchTool
        from ..tools.web_scrape import WebScrapeTool
        from ..tools.code_search import CodeSearchTool
        from ..tools.registry import TOOL_REGISTRY
        
        TOOL_REGISTRY.register(SearchTool())
        TOOL_REGISTRY.register(PythonExecTool())
        TOOL_REGISTRY.register(WebFetchTool())
        TOOL_REGISTRY.register(WebScrapeTool())
        TOOL_REGISTRY.register(CodeSearchTool())
        
        self._running = True
    
    async def shutdown(self) -> None:
        """Shutdown the engine."""
        self._running = False
        state.reset()
    
    async def execute(self, user_input: str) -> str:
        """
        Execute a user request through the complete pipeline.
        
        Args:
            user_input: The user's input
            
        Returns:
            Final response to the user
        """
        if not self._running:
            await self.initialize()
        
        # Reset state for new execution
        state.reset()
        state.set_user_input(user_input)
        state.start_execution()

        # Generate execution ID for tracking and recovery
        execution_id = str(uuid.uuid4())[:8]
        state.update_execution_context("execution_id", execution_id)

        # Start trace for this execution
        tracer.start_trace("execute", user_input=user_input)

        try:
            # Save initial snapshot
            persistence.save_state(state, execution_id, user_input, {"stage": "init"})
            # State: ROUTING
            tracer.add_step("Engine", "Starting routing")
            state.set_system_state(SystemState.PLANNING)
            intent = await self.router.route(user_input)
            state.set_user_intent(intent)
            log_agent_decision("Engine", f"Intent detected: {intent.type.value}", intent.reasoning)

            # State: PLANNING
            tracer.add_step("Engine", "Starting planning")
            state.set_system_state(SystemState.PLANNING)
            plan = await self.planner.plan(user_input, intent)

            # EXECUTION GOVERNOR: Check plan size limit
            if len(plan.nodes) > self._max_nodes:
                raise ValueError(f"Plan too large: {len(plan.nodes)} nodes exceeds maximum of {self._max_nodes}")

            state.set_plan(plan)
            log_agent_decision("Engine", f"Generated plan: {len(plan.nodes)} nodes", plan.goal)

            # Validate plan
            tracer.add_step("Engine", "Validating plan")
            validation = await self.critic.validate_plan(plan)
            if not validation.passed:
                raise RuntimeError(f"Plan validation failed: {validation.message}")

            # State: EXECUTING
            tracer.add_step("Engine", f"Executing plan with {len(plan.nodes)} nodes")
            state.set_system_state(SystemState.EXECUTING)
            execution_results = await self._execute_plan(plan)

            # State: SYNTHESIZING
            tracer.add_step("Engine", "Synthesizing response")
            state.set_system_state(SystemState.SYNTHESIZING)

            # Self-evaluation loop with retry
            max_synthesis_attempts = 2
            response = None

            for attempt in range(max_synthesis_attempts):
                response = await self.synthesizer.synthesize(
                    user_input=user_input,
                    execution_results=execution_results,
                    execution_context=state.get_execution_context()
                )

                # Self-evaluate the response
                evaluation = await self.critic.evaluate_final_output(
                    user_input=user_input,
                    response=response,
                    execution_results=execution_results
                )

                if evaluation.passed:
                    tracer.add_step("Engine", f"Final output passed evaluation (attempt {attempt + 1})")
                    break
                else:
                    tracer.add_step("Engine", f"Final output failed evaluation (attempt {attempt + 1})",
                                   {"feedback": evaluation.message})
                    if attempt < max_synthesis_attempts - 1:
                        # Add feedback to execution context for retry
                        state.update_execution_context("synthesis_feedback", evaluation.message)

            # State: COMPLETED
            state.set_system_state(SystemState.COMPLETED)
            state.end_execution()
            tracer.end_trace("success", result=response[:100] if response else None)

            return response

        except Exception as e:
            # State: ERROR
            state.set_system_state(SystemState.ERROR)
            state.add_error({"error": str(e), "stage": state.get_system_state()})
            state.end_execution()
            tracer.end_trace("error", result=str(e))

            return f"Error during execution: {str(e)}"
    
    async def _execute_plan(self, plan: Plan) -> list:
        """
        Execute a plan with the replan loop (autonomy core).
        Supports TRUE PARALLEL execution of ready nodes.

        Args:
            plan: The execution plan

        Returns:
            List of execution results
        """
        results = []
        replan_attempts = 0

        tracer.add_step("Engine", "Starting plan execution", {"total_nodes": len(plan.nodes)})

        while not plan.is_complete() and replan_attempts < self._max_replan_attempts:
            # Get ready nodes
            ready_nodes = plan.get_ready_nodes()
            
            if not ready_nodes:
                # No ready nodes - check if we're stuck
                if plan.get_failed_nodes():
                    # Trigger replan
                    tracer.add_step("Engine", f"Triggering replan (attempt {replan_attempts + 1})")
                    state.set_system_state(SystemState.REPLANNING)
                    state.increment_replan_attempts()

                    failed_node = plan.get_failed_nodes()[0]
                    # Get recent failure history (last 5 errors)
                    failure_history = state.get_errors()[-5:]
                    failure_patterns = state.metrics["failure_patterns"]

                    # Gather partial results from completed nodes
                    completed_results = {
                        node_id: node.result
                        for node_id, node in plan.nodes.items()
                        if node.status == NodeStatus.COMPLETED and node.result is not None
                    }

                    # Get problematic tools to avoid
                    problematic_tools = state.get_problematic_tools(threshold=2)

                    replan_request = ReplanRequest(
                        failed_node_id=failed_node.id,
                        error_message=failed_node.error or "Unknown error",
                        context=state.get_execution_context(),
                        attempt_count=replan_attempts + 1,
                        failure_history=failure_history,
                        failure_patterns=failure_patterns,
                        completed_results=completed_results,
                        problematic_tools=problematic_tools
                    )

                    # Get repair strategy
                    repair = await self.replanner.replan(replan_request, plan)

                    # Apply repair
                    plan = await self.replanner.apply_repair(plan, repair)
                    state.set_plan(plan)
                    log_agent_decision("Engine", f"Applied repair: {repair.get('repair_strategy', 'unknown')}")

                    replan_attempts += 1
                    continue
                else:
                    # No ready nodes and no failures - plan complete
                    break
            
            # TRUE PARALLEL EXECUTION of ready nodes
            tracer.add_step("Engine", f"Executing {len(ready_nodes)} nodes in parallel")

            # Mark all as running
            for node in ready_nodes:
                state.update_node_status(node.id, NodeStatus.RUNNING)

            # Create parallel tasks
            tasks = []
            node_map = {}

            async def limited_execute(node):
                """Execute with semaphore for concurrency limiting."""
                async with self._execution_semaphore:
                    return await self.executor.execute(node)

            for node in ready_nodes:
                task = asyncio.create_task(limited_execute(node))
                tasks.append(task)
                node_map[task] = node

            # Execute all in parallel
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for task, result in zip(tasks, parallel_results):
                node = node_map[task]

                if isinstance(result, Exception):
                    # Execution raised an exception
                    error_msg = str(result)
                    state.update_node_status(node.id, NodeStatus.FAILED, error=error_msg)
                    state.add_error({"node_id": node.id, "error": error_msg, "type": "execution"})
                    state.metrics["failure_patterns"]["execution_failures"] += 1
                    tracer.add_step("Engine", f"Node {node.id} failed with exception", {"error": error_msg})
                else:
                    # Execution succeeded - validate result
                    results.append(result)
                    state.add_execution_result(result)

                    validation = await self.critic.validate_result(
                        node=node,
                        result=result.result,
                        execution_context=state.get_execution_context()
                    )

                    if result.success and validation.passed:
                        # Success!
                        state.update_node_status(node.id, NodeStatus.COMPLETED, result=result.result)
                        state.update_execution_context(f"node_{node.id}_result", result.result)
                        tracer.add_step("Engine", f"Node {node.id} completed", {"duration_ms": result.duration_ms})
                    else:
                        # Failed validation or execution error
                        error_msg = result.error or validation.message
                        state.update_node_status(node.id, NodeStatus.FAILED, error=error_msg)
                        error_type = "validation" if not validation.passed else "execution"
                        state.add_error({"node_id": node.id, "error": error_msg, "type": error_type})
                        # Track failure pattern
                        if not validation.passed:
                            state.metrics["failure_patterns"]["validation_failures"] += 1
                        else:
                            state.metrics["failure_patterns"]["tool_failures"] += 1
        
        return results
    
    def get_system_state(self) -> SystemState:
        """Get the current system state."""
        return state.get_system_state()
    
    def get_metrics(self) -> dict:
        """Get execution metrics."""
        return state.get_metrics()


# Global engine instance
engine = Engine()