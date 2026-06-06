"""
Router agent for the autonomous agent system.
Performs intent detection and workflow selection.
"""

from typing import Dict, Any
from ..core.types import UserIntent, IntentType
from ..core.config import config
from ..llm.client import llm_client
from ..llm.prompts import RouterPrompts
from ..utils.observability import log_agent_decision, tracer


class RouterAgent:
    """
    Router agent that detects user intent and selects appropriate workflow.
    First step in the execution pipeline.
    """
    
    def __init__(self):
        """Initialize the router agent."""
        self.prompts = RouterPrompts()
    
    async def route(self, user_input: str) -> UserIntent:
        """
        Analyze user input and detect intent.
        
        Args:
            user_input: The user's input
            
        Returns:
            Detected user intent
        """
        # Get available workflows from config
        workflows = config.get_all_workflows()
        
        # Generate prompt
        prompt = self.prompts.detect_intent(user_input, workflows)
        
        # Get response from LLM
        try:
            response = await llm_client.generate_json(prompt)
            
            # Parse response
            intent_type_str = response.get("type", "unknown")
            confidence = float(response.get("confidence", 0.5))
            workflow = response.get("workflow", "general")
            reasoning = response.get("reasoning", "")
            
            # Map string to enum
            intent_type = IntentType(intent_type_str.lower())
            
            # Log decision
            log_agent_decision(
                "Router",
                f"Detected intent: {intent_type.value} (confidence: {confidence:.2f})",
                reasoning
            )
            tracer.add_step("Router", f"Intent: {intent_type.value}", {"confidence": confidence})
            
            return UserIntent(
                type=intent_type,
                confidence=confidence,
                workflow=workflow,
                reasoning=reasoning
            )
            
        except Exception as e:
            # Fallback to unknown intent on error
            return UserIntent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                workflow="general",
                reasoning=f"Intent detection failed: {str(e)}"
            )
    
    async def get_workflow(self, user_input: str) -> str:
        """
        Get the workflow name for a user input.
        
        Args:
            user_input: The user's input
            
        Returns:
            Workflow name
        """
        intent = await self.route(user_input)
        return intent.workflow