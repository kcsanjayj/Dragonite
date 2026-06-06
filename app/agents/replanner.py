"""
Replanner agent for the autonomous agent system.
Performs dynamic plan repair after failures.
"""

from typing import Dict, Any
import uuid
from ..core.types import Plan, Node, Edge, ToolCall, ReplanRequest
from ..core.graph import GraphValidator
from ..llm.client import llm_client
from ..llm.prompts import ReplannerPrompts
from ..utils.observability import log_agent_decision, tracer
from ..tools.registry import TOOL_REGISTRY

class ReplannerAgent:
    """
    Replanner agent that dynamically repairs failed execution plans.
    Core component of the autonomy system - enables self-healing.
    """
    
    def __init__(self):
        """Initialize the replanner agent."""
        self.prompts = ReplannerPrompts()
        self.graph_validator = GraphValidator()
    
    async def replan(self, request: ReplanRequest, original_plan: Plan) -> Dict[str, Any]:
        """
        Generate a repaired plan after failure.
        Uses failure history and patterns for adaptive replanning.

        Args:
            request: Replan request with failure details
            original_plan: The original plan that failed

        Returns:
            Repair strategy with modified nodes and re-execution instructions
        """
        # Generate prompt with failure-aware context and partial results
        prompt = self.prompts.repair_plan(
            failed_node_id=request.failed_node_id,
            error_message=request.error_message,
            original_plan=original_plan.model_dump(),
            execution_context=request.context,
            failure_history=request.failure_history,
            failure_patterns=request.failure_patterns,
            attempt_count=request.attempt_count,
            completed_results=request.completed_results,
            problematic_tools=request.problematic_tools
        )
        
        # Log replanning start with pattern awareness
        tracer.add_step("Replanner", f"Replanning for failed node: {request.failed_node_id}",
                       {"error": request.error_message,
                        "attempt": request.attempt_count,
                        "patterns": request.failure_patterns})

        # Get response from LLM
        try:
            response = await llm_client.generate_json(prompt)
            
            # Validate repair strategy
            if not response.get("repair_strategy"):
                raise ValueError("Repair strategy missing")

            # Log decision
            log_agent_decision(
                "Replanner",
                f"Repair strategy: {response.get('repair_strategy')}",
                response.get("reasoning", "")
            )
            tracer.add_step("Replanner", f"Repair strategy: {response.get('repair_strategy')}")

            return response
            
        except Exception as e:
            tracer.add_step("Replanner", f"Replanning failed: {str(e)}")
            raise RuntimeError(f"Replanning failed: {str(e)}")
    
    async def apply_repair(self, original_plan: Plan, repair: Dict[str, Any]) -> Plan:
        """
        Apply a repair strategy to create a new plan.
        
        Args:
            original_plan: The original plan
            repair: Repair strategy from replanner
            
        Returns:
            Repaired plan
        """
        # Create new plan as a copy
        new_plan = Plan(
            id=str(uuid.uuid4()),
            nodes=original_plan.nodes.copy(),
            edges=original_plan.edges.copy(),
            goal=original_plan.goal,
            context=original_plan.context.copy()
        )
        
        # Track added nodes to create edges
        added_node_ids = []
        
        # Get valid tool names for validation
        valid_tools = set(TOOL_REGISTRY.list_tools())
        
        # Add or modify nodes based on repair
        for node_data in repair.get("modified_nodes", []):
            node_id = node_data.get("id", str(uuid.uuid4()))
            node_type = node_data.get("type", "tool_call")
            description = node_data.get("description", "")
            
            # Build tool call if present
            tool_call = None
            if "tool_call" in node_data:
                tc_data = node_data["tool_call"]
                tool_name = tc_data.get("tool_name", "")
                
                # Validate tool exists - skip invalid tools
                if tool_name and tool_name not in valid_tools:
                    print(f"[WARNING] Replanner generated invalid tool '{tool_name}', skipping node {node_id}")
                    continue
                
                tool_call = ToolCall(
                    tool_name=tool_name,
                    parameters=tc_data.get("parameters", {}),
                    timeout=tc_data.get("timeout", 30)
                )
            
            # Build dependencies set
            dependencies = set(node_data.get("dependencies", []))
            
            # Create or update node
            node = Node(
                id=node_id,
                type=node_type,
                description=description,
                tool_call=tool_call,
                dependencies=dependencies,
                status="pending"  # Reset to pending for re-execution
            )
            new_plan.nodes[node_id] = node
            added_node_ids.append(node_id)
        
        # Create edges for new nodes based on dependencies
        for node_id in added_node_ids:
            node = new_plan.nodes[node_id]
            for dep_id in node.dependencies:
                if dep_id in new_plan.nodes:
                    # Create edge from dependency to this node
                    edge = Edge(from_node=dep_id, to_node=node_id)
                    new_plan.edges.append(edge)
        
        # Skip auto-connecting nodes without dependencies to avoid cycles
        # Let the graph validator handle disconnected nodes as warnings
        
        # Reset status of nodes to re-execute
        nodes_to_reexecute = repair.get("nodes_to_reexecute", [])
        for node_id in nodes_to_reexecute:
            if node_id in new_plan.nodes:
                new_plan.nodes[node_id].status = "pending"
                new_plan.nodes[node_id].result = None
                new_plan.nodes[node_id].error = None
        
        # Validate the repaired plan - be lenient during replanning
        is_valid, errors = self.graph_validator.validate(new_plan)
        if not is_valid:
            # If validation fails, return the original plan instead of failing
            # This prevents cascading errors from replanning
            print(f"Warning: Replan validation failed with errors: {errors}. Using original plan.")
            return original_plan
        
        return new_plan