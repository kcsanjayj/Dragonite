"""
Critic agent for the autonomous agent system.
Performs rule and semantic validation.
"""

from typing import Dict, Any
from ..core.types import ValidationResult, Plan, Node
from ..llm.client import llm_client
from ..llm.prompts import CriticPrompts
from ..utils.observability import log_agent_decision, tracer


class CriticAgent:
    """
    Critic agent that validates execution results and plans.
    Performs rule-based and semantic validation.
    """
    
    def __init__(self):
        """Initialize the critic agent."""
        self.prompts = CriticPrompts()
        self.validation_rules = self._init_validation_rules()
    
    def _init_validation_rules(self) -> Dict[str, Any]:
        """Initialize validation rules."""
        return {
            "result_not_null": {
                "check": lambda r: r is not None,
                "description": "Result should not be null"
            },
            "result_not_empty": {
                "check": lambda r: r not in [None, "", [], {}],
                "description": "Result should not be empty"
            },
            "error_is_none": {
                "check": lambda r: r.get("error") is None if isinstance(r, dict) else True,
                "description": "Result should not have errors"
            }
        }
    
    async def validate_result(self, node: Node, result: Any, execution_context: Dict[str, Any]) -> ValidationResult:
        """
        Validate an execution result.
        
        Args:
            node: The executed node
            result: The execution result
            execution_context: Current execution context
            
        Returns:
            Validation result
        """
        # Log validation start
        tracer.add_step("Critic", f"Validating result for node: {node.id}")

        # First, run rule-based validation
        rule_validation = self._validate_rules(result)
        if not rule_validation.passed:
            log_agent_decision("Critic", f"Rule validation failed for {node.id}", rule_validation.message)
            tracer.add_step("Critic", f"Rule validation failed: {rule_validation.message}")
            return rule_validation

        # Then, run semantic validation using LLM
        try:
            prompt = self.prompts.validate_result(
                node_id=node.id,
                node_description=node.description,
                result=result,
                execution_context=execution_context
            )

            response = await llm_client.generate_json(prompt)

            validation_result = ValidationResult(
                rule_name="semantic_validation",
                passed=response.get("passed", True),
                message=response.get("message", ""),
                severity=response.get("severity", "info")
            )

            # Log validation result
            status = "passed" if validation_result.passed else "failed"
            log_agent_decision("Critic", f"Validation {status} for {node.id}", validation_result.message)
            tracer.add_step("Critic", f"Validation {status}: {node.id}")

            return validation_result

        except Exception as e:
            tracer.add_step("Critic", f"Validation error for {node.id}: {str(e)}")
            # On LLM error, fall back to rule-based validation result
            return ValidationResult(
                rule_name="rule_based_validation",
                passed=True,
                message=f"Semantic validation skipped: {str(e)}",
                severity="warning"
            )
    
    async def validate_plan(self, plan: Plan) -> ValidationResult:
        """
        Validate an execution plan.
        
        Args:
            plan: The plan to validate
            
        Returns:
            Validation result
        """
        tracer.add_step("Critic", f"Validating plan with {len(plan.nodes)} nodes")

        try:
            prompt = self.prompts.validate_plan(plan.model_dump())

            response = await llm_client.generate_json(prompt)

            validation_result = ValidationResult(
                rule_name="plan_validation",
                passed=response.get("passed", True),
                message=response.get("message", ""),
                severity=response.get("severity", "info")
            )

            # Log validation result
            status = "passed" if validation_result.passed else "failed"
            log_agent_decision("Critic", f"Plan validation {status}", validation_result.message)
            tracer.add_step("Critic", f"Plan validation {status}")

            return validation_result

        except Exception as e:
            tracer.add_step("Critic", f"Plan validation error: {str(e)}")
            return ValidationResult(
                rule_name="plan_validation",
                passed=False,
                message=f"Plan validation failed: {str(e)}",
                severity="error"
            )
    
    def _validate_rules(self, result: Any) -> ValidationResult:
        """
        Validate result against rule-based checks.
        
        Args:
            result: The result to validate
            
        Returns:
            Validation result
        """
        for rule_name, rule in self.validation_rules.items():
            try:
                if not rule["check"](result):
                    return ValidationResult(
                        rule_name=rule_name,
                        passed=False,
                        message=rule["description"],
                        severity="error"
                    )
            except Exception:
                # Rule check failed to execute, skip it
                continue
        
        return ValidationResult(
            rule_name="rule_based_validation",
            passed=True,
            message="All rule-based checks passed",
            severity="info"
        )

    async def evaluate_final_output(self, user_input: str, response: str, execution_results: list) -> ValidationResult:
        """
        Self-evaluation: Validate the final synthesized response.

        Args:
            user_input: The original user input
            response: The synthesized response
            execution_results: List of execution results

        Returns:
            Validation result indicating if response is acceptable
        """
        tracer.add_step("Critic", "Evaluating final output")

        try:
            prompt = self.prompts.evaluate_response(
                user_input=user_input,
                response=response,
                execution_results=[
                    {"node_id": r.node_id, "success": r.success, "error": r.error}
                    for r in execution_results
                ]
            )

            evaluation = await llm_client.generate_json(prompt)

            validation_result = ValidationResult(
                rule_name="final_evaluation",
                passed=evaluation.get("passed", True),
                message=evaluation.get("feedback", ""),
                severity="error" if not evaluation.get("passed", True) else "info"
            )

            status = "passed" if validation_result.passed else "failed"
            log_agent_decision("Critic", f"Final evaluation {status}", validation_result.message)
            tracer.add_step("Critic", f"Final evaluation {status}")

            return validation_result

        except Exception as e:
            tracer.add_step("Critic", f"Final evaluation error: {str(e)}")
            # On error, assume it's acceptable to avoid infinite loops
            return ValidationResult(
                rule_name="final_evaluation",
                passed=True,
                message=f"Evaluation skipped due to error: {str(e)}",
                severity="warning"
            )