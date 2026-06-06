"""
Structured agent prompts for the autonomous agent system.
Provides consistent, structured prompts for each agent type.
"""

from typing import Dict, Any


class RouterPrompts:
    """Prompts for the Router agent (intent detection)."""
    
    @staticmethod
    def detect_intent(user_input: str, available_workflows: Dict[str, str]) -> str:
        """
        Generate prompt for intent detection.
        
        Args:
            user_input: The user's input
            available_workflows: Dictionary of workflow names and descriptions
            
        Returns:
            Prompt string
        """
        workflows_desc = "\n".join([f"- {name}: {desc}" for name, desc in available_workflows.items()])
        
        return f"""You are an intent detection agent. Your task is to analyze the user's input and determine their intent.

Available workflows:
{workflows_desc}

User input:
{user_input}

Analyze the user input and determine:
1. The type of intent (query, task, analysis, code, research, unknown)
2. Confidence score (0.0 to 1.0)
3. The most appropriate workflow
4. Brief reasoning for your classification

Respond in JSON format with the following structure:
{{
  "type": "intent_type",
  "confidence": 0.0-1.0,
  "workflow": "workflow_name",
  "reasoning": "brief explanation"
}}"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for router agent."""
        return "You are an intent detection agent. Analyze user input and classify the intent with high accuracy."


class PlannerPrompts:
    """Prompts for the Planner agent (JSON plan generation)."""
    
    @staticmethod
    def generate_plan(user_input: str, intent: Dict[str, Any], available_tools: Dict[str, str],
                      memory_context: str = "", active_guidance: str = "") -> str:
        """
        Generate prompt for plan creation.

        Args:
            user_input: The user's input
            intent: Detected intent information
            available_tools: Dictionary of tool names and descriptions
            memory_context: Recent execution context from memory
            active_guidance: Active learning guidance to influence behavior

        Returns:
            Prompt string
        """
        tools_desc = "\n".join([f"- {name}: {desc}" for name, desc in available_tools.items()])

        memory_section = f"\n\nPrior execution context:\n{memory_context}" if memory_context else ""
        guidance_section = f"\n{active_guidance}" if active_guidance else ""

        return f"""You are an INTELLIGENT planning agent. Create OPTIMAL execution plans as DAGs with MAXIMUM EFFICIENCY.

User input:
{user_input}

Detected intent:
- Type: {intent.get('type')}
- Workflow: {intent.get('workflow')}
- Reasoning: {intent.get('reasoning')}

Available tools:
{tools_desc}{memory_section}{guidance_section}

## CORE RULES (VIOLATION = FAILURE):
1. **USE ONLY LISTED TOOLS**: search, python_exec, web_fetch, web_scrape, code_search. NO bing_search, google_search, etc.
2. **NEVER INVENT TOOLS**: Only tools in Available tools list above are valid.
3. **SEARCH-FIRST STRATEGY**: All information queries MUST start with search tool.
4. **NO WEB SCRAPING FOR INFO**: web_scrape/web_fetch ONLY for code extraction, NEVER for general info queries.
5. **USE SEARCH RESULTS DIRECTLY**: Search returns titles, URLs, AND body content. Synthesize from body content - DO NOT re-fetch URLs.

## ADAPTIVE PLANNING STRATEGY:

**Query Type: Information/Knowledge (query, research)**
- Nodes: 2 MAXIMUM
- Pattern: search → synthesize_answer
- No web scraping, no URL fetching
- Synthesize directly from search result body content

**Query Type: Code/Programming (code, analysis)**
- Nodes: 2-3
- Pattern: code_search → [optional: web_fetch for docs] → synthesize
- Use code_search for examples, web_fetch only if official docs needed

**Query Type: Data/Computation (analysis, task)**
- Nodes: 2-3
- Pattern: search → python_exec → synthesize
- Use python_exec for calculations, data processing

**Query Type: Complex Research (research, comparison)**
- Nodes: 3-4 MAXIMUM
- Pattern: parallel_search_1 + parallel_search_2 → [optional: web_fetch] → synthesize
- Multiple search angles in parallel, then synthesize

## OPTIMIZATION RULES:
1. **PARALLEL EXECUTION**: Independent searches can run in parallel (no dependencies)
2. **MINIMAL STEPS**: Fewer nodes = faster execution. Combine where possible.
3. **NO REDUNDANCY**: Never search same thing twice
4. **SMART DEPENDENCIES**: Only add edges when data flow is required
5. **QUALITY OVER QUANTITY**: 2-3 high-quality results beat 10 low-quality

## ANTI-PATTERNS (NEVER DO):
- ❌ search → web_fetch → web_fetch → synthesize (excessive, slow)
- ❌ node IDs as URLs
- ❌ Multiple sequential searches on same topic
- ❌ web_scrape for general information
- ❌ Plans with 5+ nodes for simple queries

Respond in JSON format with the following structure:
{{
  "goal": "brief description of the overall goal",
  "nodes": [
    {{
      "id": "unique_node_id",
      "type": "tool_call",
      "description": "human-readable description",
      "tool_call": {{
        "tool_name": "tool_name",
        "parameters": {{
          "param1": "value1"
        }}
      }},
      "dependencies": ["node_id_1", "node_id_2"]
    }}
  ],
  "edges": [
    {{
      "from_node": "node_id_1",
      "to_node": "node_id_2"
    }}
  ]
}}"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for planner agent."""
        return "You are a planning agent. Create detailed, executable plans as DAGs. Be precise and ensure plans are valid and efficient."


class ReplannerPrompts:
    """Prompts for the Replanner agent (dynamic plan repair)."""
    
    @staticmethod
    def repair_plan(failed_node_id: str, error_message: str, original_plan: Dict[str, Any],
                     execution_context: Dict[str, Any], failure_history: list = None,
                     failure_patterns: Dict[str, int] = None, attempt_count: int = 1,
                     completed_results: Dict[str, Any] = None) -> str:
        """
        Generate prompt for plan repair with failure-aware context and partial results.

        Args:
            failed_node_id: ID of the failed node
            error_message: Error that caused failure
            original_plan: The original plan
            execution_context: Current execution context
            failure_history: Recent failure history
            failure_patterns: Aggregated failure pattern counts
            attempt_count: Current replan attempt number
            completed_results: Results from successfully completed nodes
            problematic_tools: Tools with high failure rates

        Returns:
            Prompt string
        """
        failure_history_str = "\n".join([f"- {e.get('node_id')}: {e.get('error')} ({e.get('type')})"
                                          for e in (failure_history or [])])
        failure_patterns_str = "\n".join([f"- {k}: {v}"
                                         for k, v in (failure_patterns or {}).items()])
        
        # Build problematic tools info
        problematic_tools_str = "\n".join([f"- {tool}: {count} failures (AVOID THIS TOOL)"
                                            for tool, count in (problematic_tools or {}).items()])

        completed_str = "\n".join([f"- {k}: {str(v)[:200]}..."  # Truncate long results
                                    for k, v in (completed_results or {}).items()])

        return f"""You are a replanning agent. Your task is to repair a failed execution plan.

Failed node ID:
{failed_node_id}

Error message:
{error_message}

Replan attempt: {attempt_count}

Original plan:
{original_plan}

Execution context:
{execution_context}

Recent failure history:
{failure_history_str or "No prior failures"}

Failure patterns detected:
{failure_patterns_str or "No patterns detected"}

Problematic tools to AVOID:
{problematic_tools_str or "No problematic tools detected"}

Successfully completed node results (USE these in your repair strategy):
{completed_str or "No completed nodes yet"}

Analyze the failure and create a repaired plan. Consider:
1. Why the node failed - look at failure patterns for systemic issues
2. How to fix the issue (retry with different parameters, skip failed node, simplify plan, etc.)
3. How to integrate the fix into the existing plan
4. Which nodes need to be re-executed
5. If multiple replan attempts failed, REMOVE the problematic node and use search results directly
6. LEVERAGE completed results - use data from successful nodes to inform your repair

REPAIR STRATEGIES:
- If web_scrape or web_fetch fails: REMOVE those nodes and use search results directly for synthesis
- If search succeeds but scraping fails: Skip scraping, proceed to synthesis with search results
- NEVER suggest retrying web scraping multiple times - it almost always fails due to site blocking
- Prefer SIMPLER plans over complex multi-step approaches

## 🚨 CRITICAL: TOOL FAILURE THRESHOLD RULE 🚨
IF a tool has failed 2 or more times in this execution:
1. DO NOT use that tool again - it will fail again
2. SWITCH to an alternative tool immediately
3. web_scrape/web_fetch failing → use search tool instead
4. Any tool failing → use search or python_exec as fallback

VIOLATION = wasted tokens, delayed response, poor user experience

Respond in JSON format with the following structure:
{{
  "repair_strategy": "description of repair strategy",
  "modified_nodes": [
    {{
      "id": "unique_node_id",
      "type": "tool_call",
      "description": "human-readable description",
      "tool_call": {{
        "tool_name": "tool_name",
        "parameters": {{
          "param1": "value1"
        }}
      }},
      "dependencies": ["node_id_1", "node_id_2"]
    }}
  ],
  "nodes_to_reexecute": ["node_id_1", "node_id_2"],
  "reasoning": "explanation of why this repair will work, referencing failure patterns and completed results"
}}"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for replanner agent."""
        return "You are a replanning agent. Analyze failures and create effective repair strategies. Be resilient and creative in finding solutions."


class CriticPrompts:
    """Prompts for the Critic agent (validation)."""
    
    @staticmethod
    def validate_result(node_id: str, node_description: str, result: Any, execution_context: Dict[str, Any]) -> str:
        """
        Generate prompt for result validation.
        
        Args:
            node_id: ID of the executed node
            node_description: Description of the node
            result: Execution result
            execution_context: Current execution context
            
        Returns:
            Prompt string
        """
        return f"""You are a critic agent. Your task is to validate execution results.

Node ID:
{node_id}

Node description:
{node_description}

Execution result:
{result}

Execution context:
{execution_context}

Validate the result based on:
1. Semantic correctness (does the result make sense?)
2. Data quality (is the data complete and accurate?)
3. Relevance (does the result address the node's purpose?)
4. Consistency (is the result consistent with context?)

Respond in JSON format with the following structure:
{{
  "passed": true/false,
  "message": "validation message",
  "severity": "error/warning/info",
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}"""
    
    @staticmethod
    def validate_plan(plan: Dict[str, Any]) -> str:
        """
        Generate prompt for plan validation.
        
        Args:
            plan: The plan to validate
            
        Returns:
            Prompt string
        """
        return f"""You are a critic agent. Your task is to validate execution plans.

Plan:
{plan}

Validate the plan based on:
1. Completeness (does it cover all necessary steps?)
2. Correctness (are the steps logically sound?)
3. Efficiency (is the plan optimized?)
4. Feasibility (can the plan be executed?)
5. Safety (are there any potential issues?)

IMPORTANT: Be lenient in your validation. Only mark a plan as FAILED (passed: false) if there are CRITICAL errors that would prevent execution. Minor issues, suggestions, or potential concerns should be marked as warnings but still pass the plan.

Respond in JSON format with the following structure:
{{
  "passed": true/false,
  "message": "validation message",
  "severity": "error/warning/info",
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}"""
    
    @staticmethod
    def evaluate_response(user_input: str, response: str, execution_results: list) -> str:
        """
        Generate prompt for final response evaluation.

        Args:
            user_input: The user's original input
            response: The synthesized response
            execution_results: Summary of execution results

        Returns:
            Prompt string
        """
        # Check if this is a code/programming query
        code_keywords = ["code", "function", "class", "program", "script", "java", "python", "javascript", "js", "c++", "cpp", "html", "css", "sql", "api"]
        is_code_query = any(keyword in user_input.lower() for keyword in code_keywords)
        
        code_note = """
IMPORTANT: This appears to be a CODE/PROGRAMMING query. Code examples should be evaluated as PASS if:
- They contain valid, runnable code snippets (even partial examples)
- The code demonstrates the requested concept/functionality
- The explanation is clear and helpful
DO NOT fail code responses just because they are simplified or partial examples.
""" if is_code_query else ""

        return f"""You are a critic agent performing final quality evaluation.

User request:
{user_input}

Generated response:
{response}

Execution summary:
{execution_results}

Evaluate the response based on:
1. Does it directly address the user's request?
2. Is it coherent and well-structured?
3. Are there any obvious errors or contradictions?
4. Given the execution results, is the response accurate?
5. Would this be helpful to the user?
{code_note}
IMPORTANT: Be FAIR, not overly critical. If the response is helpful and addresses the core request, mark it as PASSED. 
Only mark as FAILED if the response is fundamentally wrong, missing critical information, or completely unhelpful.

Respond in JSON format:
{{
  "passed": true/false,
  "feedback": "explanation of why it passed or failed",
  "suggestions": ["improvement1", "improvement2"]  // Only if failed
}}"""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for critic agent."""
        return "You are a critic agent. Validate results and plans with rigor. Be thorough but fair in your assessments."


class SynthesizerPrompts:
    """Prompts for the Synthesizer agent (final response building)."""
    
    @staticmethod
    def synthesize_response(user_input: str, execution_results: Dict[str, Any], execution_context: Dict[str, Any]) -> str:
        """
        Generate prompt for response synthesis.
        
        Args:
            user_input: The user's original input
            execution_results: All execution results
            execution_context: Final execution context
            
        Returns:
            Prompt string
        """
        return f"""You are a PREMIUM synthesizer agent. Create EXCEPTIONAL, publication-quality responses.

User input:
{user_input}

Execution results:
{execution_results}

Execution context:
{execution_context}

## RESPONSE QUALITY STANDARDS:
1. **COMPREHENSIVE COVERAGE**: Address all aspects of the user's request thoroughly
2. **STRUCTURED FORMAT**: Use markdown formatting - headers, bullet points, numbered lists
3. **CLEAR ORGANIZATION**: Logical flow with introduction, body sections, and conclusion
4. **EVIDENCE-BASED**: Cite sources and data from execution results
5. **ACTIONABLE INSIGHTS**: Practical recommendations and next steps
6. **PROFESSIONAL TONE**: Authoritative yet accessible language
7. **CONCISENESS**: Every sentence adds value - no filler content

## FORMATTING REQUIREMENTS:
- Start with a brief executive summary (2-3 sentences)
- Use ## headers for main sections
- Use bullet points for lists and key points
- Include numbered steps for procedures
- Bold key terms and important concepts
- End with a conclusion and actionable takeaways

## EXAMPLE STRUCTURE:
**Executive Summary**: Brief overview of findings

## Key Findings
- Point 1 with explanation
- Point 2 with supporting evidence

## Detailed Analysis
Comprehensive explanation organized by topic...

## Recommendations
1. First actionable step
2. Second actionable step

**Conclusion**: Final thoughts and next steps

Create a response worthy of professional publication."""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for synthesizer agent."""
        return "You are a synthesizer agent. Create clear, helpful, and comprehensive responses from execution results. Be conversational and user-focused."


class ExecutorPrompts:
    """Prompts for the Executor agent (tool execution only - no reasoning)."""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for executor agent."""
        return "You are an executor agent. Execute tool calls exactly as specified. Do not add reasoning or interpretation. Return only the raw results."


# Prompt registry
PROMPTS = {
    "router": RouterPrompts,
    "planner": PlannerPrompts,
    "replanner": ReplannerPrompts,
    "critic": CriticPrompts,
    "synthesizer": SynthesizerPrompts,
    "executor": ExecutorPrompts,
}


def get_prompt(agent_type: str) -> Any:
    """
    Get prompt class for an agent type.
    
    Args:
        agent_type: Type of agent
        
    Returns:
        Prompt class
    """
    return PROMPTS.get(agent_type)