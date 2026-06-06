"""
Planner agent for the autonomous agent system.
Generates strict JSON plans for execution.
"""

from typing import Dict, Any
import uuid
import json
from datetime import datetime
from ..core.types import Plan, Node, Edge, ToolCall, UserIntent
from ..core.graph import GraphValidator
from ..tools.registry import TOOL_REGISTRY
from ..llm.client import llm_client
from ..llm.prompts import PlannerPrompts
from ..utils.observability import log_agent_decision, tracer
from ..utils.memory import memory


class PlannerAgent:
    """
    Planner agent that generates strict JSON plans.
    Creates DAG-based execution plans from user input and intent.
    """
    
    def __init__(self):
        """Initialize the planner agent."""
        self.prompts = PlannerPrompts()
        self.graph_validator = GraphValidator()
    
    async def plan(self, user_input: str, intent: UserIntent) -> Plan:
        """
        Generate an execution plan from user input and intent.
        Uses memory context for continuity.

        Args:
            user_input: The user's input
            intent: Detected user intent

        Returns:
            Generated execution plan
        """
        # Get available tools
        available_tools = TOOL_REGISTRY.list_tools()

        # Get memory context for continuity
        memory_context = memory.get_context_summary(k=5)

        # Get active learning guidance that influences behavior
        active_guidance = memory.get_active_guidance()

        # Generate prompt with memory context and active guidance
        prompt = self.prompts.generate_plan(
            user_input,
            intent.model_dump(),
            available_tools,
            memory_context=memory_context,
            active_guidance=active_guidance
        )
        
        # Get response from LLM
        try:
            response = await llm_client.generate_json(prompt)
            
            # Build plan from response
            plan = self._build_plan_from_response(response, user_input)
            
            # Validate plan
            is_valid, errors = self.graph_validator.validate(plan)
            if not is_valid:
                raise ValueError(f"Plan validation failed: {errors}")
            
            # Log decision
            log_agent_decision(
                "Planner",
                f"Generated plan with {len(plan.nodes)} nodes and {len(plan.edges)} edges",
                f"Goal: {plan.goal}"
            )
            tracer.add_step("Planner", f"Plan created: {len(plan.nodes)} nodes")
            
            return plan
            
        except Exception as e:
            raise RuntimeError(f"Plan generation failed: {str(e)}")
    
    def _build_plan_from_response(self, response: Dict[str, Any], user_input: str) -> Plan:
        """
        Build a Plan object from LLM response.
        
        Args:
            response: LLM response
            user_input: Original user input
            
        Returns:
            Plan object
        """
        plan_id = str(uuid.uuid4())
        goal = response.get("goal", "Accomplish user request")
        
        nodes = {}
        # Get valid tool names for validation
        valid_tools = set(TOOL_REGISTRY.list_tools())
        
        for node_data in response.get("nodes", []):
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
                    print(f"[WARNING] Planner generated invalid tool '{tool_name}', skipping node {node_id}")
                    continue
                
                tool_call = ToolCall(
                    tool_name=tool_name,
                    parameters=tc_data.get("parameters", {}),
                    timeout=tc_data.get("timeout", 30)
                )
            
            # Build dependencies set
            dependencies = set(node_data.get("dependencies", []))
            
            node = Node(
                id=node_id,
                type=node_type,
                description=description,
                tool_call=tool_call,
                dependencies=dependencies
            )
            nodes[node_id] = node
        
        # Build edges
        edges = []
        for edge_data in response.get("edges", []):
            edge = Edge(
                from_node=edge_data.get("from_node", ""),
                to_node=edge_data.get("to_node", ""),
                condition=edge_data.get("condition")
            )
            edges.append(edge)
        
        # Create plan
        plan = Plan(
            id=plan_id,
            nodes=nodes,
            edges=edges,
            goal=goal,
            context={"user_input": user_input}
        )
        
        return plan