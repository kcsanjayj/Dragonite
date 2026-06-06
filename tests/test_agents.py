"""
Unit tests for agent implementations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.agents.router import RouterAgent
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.agents.critic import CriticAgent
from app.agents.replanner import ReplannerAgent
from app.agents.synthesizer import SynthesizerAgent
from app.core.types import Plan, Node, Edge, ToolCall, ReplanRequest


@pytest.mark.unit
class TestRouterAgent:
    """Test cases for RouterAgent."""
    
    @pytest.fixture
    def router(self):
        return RouterAgent()
    
    @pytest.mark.asyncio
    async def test_route_basic_query(self, router):
        """Test routing a basic query."""
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "type": "query",
                "workflow": "research",
                "confidence": 0.9,
                "reasoning": "User is asking for information"
            }
            
            result = await router.route("What is AI?")
            
            assert result.type.value == "query"
            assert result.workflow == "research"
            assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_route_with_context(self, router):
        """Test routing with additional context."""
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "type": "analysis",
                "workflow": "data_analysis",
                "confidence": 0.85,
                "reasoning": "User wants data analysis"
            }
            
            result = await router.route("Analyze this data")
            
            assert result.type.value == "analysis"


@pytest.mark.unit
class TestPlannerAgent:
    """Test cases for PlannerAgent."""
    
    @pytest.fixture
    def planner(self):
        return PlannerAgent()
    
    @pytest.mark.asyncio
    async def test_generate_plan(self, planner):
        """Test plan generation."""
        from app.core.types import UserIntent, IntentType
        
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "goal": "Search for information",
                "nodes": [
                    {
                        "id": "node1",
                        "type": "tool_call",
                        "description": "Search",
                        "tool_call": {
                            "tool_name": "search",
                            "parameters": {"query": "test"}
                        },
                        "dependencies": []
                    }
                ],
                "edges": []
            }
            
            intent = UserIntent(
                type=IntentType.QUERY,
                confidence=0.9,
                workflow="research",
                reasoning="Test"
            )
            
            result = await planner.plan(
                user_input="Search for AI",
                intent=intent
            )
            
            assert result.goal == "Search for information"
            assert len(result.nodes) > 0


@pytest.mark.unit
class TestExecutorAgent:
    """Test cases for ExecutorAgent."""
    
    @pytest.fixture
    def executor(self):
        return ExecutorAgent()
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, executor):
        """Test tool execution."""
        with patch('app.tools.registry.TOOL_REGISTRY.get') as mock_registry:
            mock_tool = Mock()
            mock_tool.execute = AsyncMock(return_value={"result": "success"})
            mock_registry.return_value = mock_tool
            
            node = Node(
                id="node1",
                type="tool_call",
                description="Test node",
                tool_call=ToolCall(
                    tool_name="search",
                    parameters={"query": "test"}
                ),
                dependencies=set()
            )
            
            result = await executor.execute(node)
            
            assert result is not None
            mock_tool.execute.assert_called_once()


@pytest.mark.unit
class TestCriticAgent:
    """Test cases for CriticAgent."""
    
    @pytest.fixture
    def critic(self):
        return CriticAgent()
    
    @pytest.mark.asyncio
    async def test_validate_result_success(self, critic):
        """Test result validation with successful result."""
        node = Node(id="node1", type="tool_call", description="Test", dependencies=set())
        result = {"data": "test"}
        
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "passed": True,
                "message": "Validation passed",
                "severity": "info"
            }
            
            validation = await critic.validate_result(node, result, {})
            
            assert validation.passed is True
            assert validation.severity == "info"
    
    @pytest.mark.asyncio
    async def test_validate_plan(self, critic):
        """Test plan validation."""
        plan = Plan(
            id="plan1",
            goal="Test plan",
            nodes={},
            edges=[],
            context={}
        )
        
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "passed": True,
                "message": "Plan is valid",
                "severity": "info"
            }
            
            validation = await critic.validate_plan(plan)
            
            assert validation.passed is True


@pytest.mark.unit
class TestReplannerAgent:
    """Test cases for ReplannerAgent."""
    
    @pytest.fixture
    def replanner(self):
        return ReplannerAgent()
    
    @pytest.mark.asyncio
    async def test_replan(self, replanner):
        """Test replanning after failure."""
        request = ReplanRequest(
            failed_node_id="node1",
            error_message="Tool failed",
            context={}
        )
        original_plan = Plan(
            id="plan1",
            goal="Test",
            nodes={},
            edges=[],
            context={}
        )
        
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "repair_strategy": "Retry with different parameters",
                "modified_nodes": [],
                "nodes_to_reexecute": ["node1"],
                "reasoning": "Fix the issue"
            }
            
            result = await replanner.replan(request, original_plan)
            
            assert "repair_strategy" in result
            assert result["repair_strategy"] == "Retry with different parameters"
    
    @pytest.mark.asyncio
    async def test_apply_repair(self, replanner):
        """Test applying repair to plan."""
        original_plan = Plan(
            id="plan1",
            goal="Test",
            nodes={},
            edges=[],
            context={}
        )
        
        repair = {
            "repair_strategy": "Add new node",
            "modified_nodes": [
                {
                    "id": "node2",
                    "type": "tool_call",
                    "description": "New node",
                    "tool_call": {
                        "tool_name": "search",
                        "parameters": {"query": "test"}
                    },
                    "dependencies": []
                }
            ],
            "nodes_to_reexecute": []
        }
        
        new_plan = await replanner.apply_repair(original_plan, repair)
        
        assert "node2" in new_plan.nodes
        assert len(new_plan.nodes) == 1


@pytest.mark.unit
class TestSynthesizerAgent:
    """Test cases for SynthesizerAgent."""
    
    @pytest.fixture
    def synthesizer(self):
        return SynthesizerAgent()
    
    @pytest.mark.asyncio
    async def test_synthesize_response(self, synthesizer):
        """Test response synthesis."""
        from app.core.types import ExecutionResult
        
        execution_results = [
            ExecutionResult(
                node_id="node1",
                success=True,
                result="Search results",
                error=None,
                duration_ms=100.0
            )
        ]
        
        with patch('app.llm.client.llm_client.generate', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Here is the synthesized response"
            
            response = await synthesizer.synthesize(
                user_input="Search for AI",
                execution_results=execution_results,
                execution_context={}
            )
            
            assert response == "Here is the synthesized response"
