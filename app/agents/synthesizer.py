"""
Synthesizer agent for the autonomous agent system.
Builds final responses from execution results.
"""

from typing import Dict, Any
from ..llm.client import llm_client
from ..llm.prompts import SynthesizerPrompts
from ..utils.observability import log_agent_decision, tracer

class SynthesizerAgent:
    """
    Synthesizer agent that creates final responses.
    Combines execution results into a comprehensive user-facing response.
    """
    
    def __init__(self):
        """Initialize the synthesizer agent."""
        self.prompts = SynthesizerPrompts()
    
    async def synthesize(self, user_input: str, execution_results: list, execution_context: Dict[str, Any]) -> str:
        """
        Synthesize a final response from execution results.
        
        Args:
            user_input: The user's original input
            execution_results: List of execution results
            execution_context: Final execution context
            
        Returns:
            Synthesized response
        """
        # Convert execution results to dict format
        results_dict = [
            {
                "node_id": result.node_id,
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "duration_ms": result.duration_ms
            }
            for result in execution_results
        ]
        
        # Generate prompt
        prompt = self.prompts.synthesize_response(
            user_input=user_input,
            execution_results=results_dict,
            execution_context=execution_context
        )
        
        # Log synthesis start
        tracer.add_step("Synthesizer", f"Synthesizing response from {len(execution_results)} results")

        # Get response from LLM
        try:
            response = await llm_client.generate(prompt)

            # Log completion
            log_agent_decision("Synthesizer", f"Generated response ({len(response)} chars)")
            tracer.add_step("Synthesizer", "Response generated")

            return response
        except Exception as e:
            tracer.add_step("Synthesizer", f"Synthesis failed: {str(e)}")
            # Fallback to simple summary on error
            return f"Execution completed with {len(execution_results)} steps. Error synthesizing response: {str(e)}"