"""
Integration tests for the full agent pipeline.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.core.engine import Engine
from app.llm.client import NVIDIAProvider, llm_client
from app.core.types import Plan, Node, Edge


@pytest.mark.integration
class TestEngineIntegration:
    """Integration tests for the Engine."""
    
    @pytest.fixture
    async def engine(self):
        """Create and initialize an engine for testing."""
        engine = Engine()
        # Skip actual initialization for testing
        engine._running = True
        yield engine
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_full_pipeline_simple(self, engine):
        """Test full pipeline with a simple query."""
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            # Mock router response
            mock_llm.side_effect = [
                # Router
                {
                    "type": "information",
                    "workflow": "research",
                    "confidence": 0.9,
                    "reasoning": "Information query"
                },
                # Planner
                {
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
                },
                # Critic (plan validation)
                {
                    "passed": True,
                    "message": "Plan is valid",
                    "severity": "info"
                },
                # Critic (result validation)
                {
                    "passed": True,
                    "message": "Result is valid",
                    "severity": "info"
                },
                # Synthesizer
                "Here is the synthesized response"
            ]
            
            # Mock tool execution
            with patch('app.tools.registry.TOOL_REGISTRY.get') as mock_registry:
                mock_tool = Mock()
                mock_tool.execute = AsyncMock(return_value={"result": "search results"})
                mock_registry.return_value = mock_tool
                
                response = await engine.execute("What is AI?")
                
                assert response is not None
                assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_pipeline_with_replanning(self, engine):
        """Test pipeline with replanning on failure."""
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm:
            call_count = 0
            
            def mock_llm_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count == 1:  # Router
                    return {
                        "type": "information",
                        "workflow": "research",
                        "confidence": 0.9,
                        "reasoning": "Information query"
                    }
                elif call_count == 2:  # Planner
                    return {
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
                elif call_count == 3:  # Critic (plan validation)
                    return {
                        "passed": True,
                        "message": "Plan is valid",
                        "severity": "info"
                    }
                elif call_count == 4:  # Replanner
                    return {
                        "repair_strategy": "Retry",
                        "modified_nodes": [],
                        "nodes_to_reexecute": ["node1"],
                        "reasoning": "Fix the issue"
                    }
                elif call_count == 5:  # Critic (result validation after replan)
                    return {
                        "passed": True,
                        "message": "Result is valid",
                        "severity": "info"
                    }
                else:  # Synthesizer
                    return "Here is the synthesized response"
            
            mock_llm.side_effect = mock_llm_side_effect
            
            # Mock tool execution (fails first time, succeeds second)
            with patch('app.tools.registry.TOOL_REGISTRY.get') as mock_registry:
                mock_tool = Mock()
                execution_count = 0
                
                async def mock_execute(*args, **kwargs):
                    nonlocal execution_count
                    execution_count += 1
                    if execution_count == 1:
                        raise RuntimeError("Tool failed")
                    return {"result": "search results"}
                
                mock_tool.execute = mock_execute
                mock_registry.return_value = mock_tool
                
                response = await engine.execute("What is AI?")
                
                assert response is not None
                assert execution_count == 2  # Tool executed twice (failed then succeeded)


@pytest.mark.integration
class TestLLMClientIntegration:
    """Integration tests for LLM client."""
    
    @pytest.mark.asyncio
    async def test_provider_registration(self):
        """Test provider registration and retrieval."""
        provider = NVIDIAProvider(
            api_key="test_key",
            model="meta/llama-3.1-8b-instruct"
        )
        
        llm_client.register_provider("nvidia", provider, set_default=True)
        
        retrieved = llm_client.get_provider("nvidia")
        
        assert retrieved is provider
        assert llm_client.default_provider == "nvidia"
    
    @pytest.mark.asyncio
    async def test_generate_call(self):
        """Test generate call through client."""
        provider = NVIDIAProvider(
            api_key="test_key",
            model="meta/llama-3.1-8b-instruct"
        )
        
        with patch.object(provider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Test response"
            
            llm_client.register_provider("nvidia", provider, set_default=True)
            
            response = await llm_client.generate("Test prompt")
            
            assert response == "Test response"
            mock_generate.assert_called_once()


@pytest.mark.integration
class TestToolIntegration:
    """Integration tests for tool execution."""
    
    @pytest.mark.asyncio
    async def test_search_tool_integration(self):
        """Test search tool in real execution."""
        from app.tools.search import SearchTool
        
        tool = SearchTool()
        
        with patch('duckduckgo_search.DDGS') as mock_ddgs:
            mock_results = [
                {"title": "Test", "body": "Test result", "href": "http://test.com"}
            ]
            mock_ddgs.return_value.__enter__.return_value.text.return_value = mock_results
            
            result = await tool.execute(query="test")
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_python_exec_tool_integration(self):
        """Test Python exec tool in real execution."""
        from app.tools.python_exec import PythonExecTool
        
        tool = PythonExecTool()
        
        result = await tool.execute(code="print(2)")
        
        assert result["success"] is True


@pytest.mark.chaos
class TestChaosScenarios:
    """Chaos testing - failure scenarios and recovery."""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_tool_failure_and_replan(self):
        """
        Test full pipeline when tool fails mid-execution.
        Verifies replanner kicks in and final output succeeds.
        """
        from app.core.engine import Engine
        from app.core.types import SystemState
        
        engine = Engine()
        engine._running = True
        
        call_count = 0
        
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm, \
             patch('app.llm.client.llm_client.generate', new_callable=AsyncMock) as mock_generate:
            
            def mock_llm_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count == 1:  # Router
                    return {"type": "query", "workflow": "research", "confidence": 0.9, "reasoning": "Test"}
                elif call_count == 2:  # Planner
                    return {
                        "goal": "Test goal",
                        "nodes": [
                            {"id": "node1", "type": "tool_call", "description": "Test", 
                             "tool_call": {"tool_name": "search", "parameters": {}}, "dependencies": []}
                        ],
                        "edges": []
                    }
                elif call_count == 3:  # Critic (plan validation)
                    return {"passed": True, "message": "Valid", "severity": "info"}
                elif call_count == 4:  # Replanner (after failure)
                    return {
                        "repair_strategy": "Retry with fix",
                        "modified_nodes": [],
                        "nodes_to_reexecute": ["node1"],
                        "reasoning": "Fixed"
                    }
                elif call_count == 5:  # Critic (result validation after replan)
                    return {"passed": True, "message": "Valid", "severity": "info"}
                return {}
            
            mock_llm.side_effect = mock_llm_side_effect
            mock_generate.return_value = "Final synthesized response after recovery"
            
            # Mock tool to fail first time, succeed second
            with patch('app.tools.registry.TOOL_REGISTRY.get') as mock_registry:
                execution_attempts = 0
                
                async def mock_execute(*args, **kwargs):
                    nonlocal execution_attempts
                    execution_attempts += 1
                    if execution_attempts == 1:
                        from app.core.types import ExecutionResult
                        return ExecutionResult(
                            node_id="node1",
                            success=False,
                            result=None,
                            error="Tool failed",
                            duration_ms=100.0
                        )
                    return ExecutionResult(
                        node_id="node1",
                        success=True,
                        result="Success after retry",
                        error=None,
                        duration_ms=100.0
                    )
                
                mock_tool = Mock()
                mock_tool.execute = mock_execute
                mock_registry.return_value = mock_tool
                
                result = await engine.execute("Test query")
                
                # Verify recovery happened
                assert execution_attempts == 2, "Tool should be called twice (failure + retry)"
                assert "after recovery" in result or "Error" not in result
        
        await engine.shutdown()


@pytest.mark.e2e
class TestEndToEndAutonomousFlow:
    """End-to-end autonomous flow tests."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_autonomous_flow(self):
        """
        Full end-to-end test: user input → autonomous execution → final answer.
        Simulates complete flow without external API calls.
        """
        from app.core.engine import Engine
        
        engine = Engine()
        engine._running = True
        
        with patch('app.llm.client.llm_client.generate_json', new_callable=AsyncMock) as mock_llm, \
             patch('app.llm.client.llm_client.generate', new_callable=AsyncMock) as mock_generate:
            
            # Setup complete mock responses for full pipeline
            mock_llm.side_effect = [
                # Router
                {"type": "query", "workflow": "research", "confidence": 0.95, "reasoning": "AI research query"},
                # Planner
                {
                    "goal": "Research latest AI news",
                    "nodes": [
                        {"id": "search", "type": "tool_call", "description": "Search AI news",
                         "tool_call": {"tool_name": "search", "parameters": {"query": "AI news"}},
                         "dependencies": []}
                    ],
                    "edges": []
                },
                # Critic (plan validation)
                {"passed": True, "message": "Plan valid", "severity": "info"},
                # Critic (result validation)
                {"passed": True, "message": "Result valid", "severity": "info"}
            ]
            
            mock_generate.return_value = "Latest AI news shows significant advances in large language models..."
            
            # Mock search tool
            with patch('app.tools.registry.TOOL_REGISTRY.get') as mock_registry:
                from app.core.types import ExecutionResult
                
                mock_tool = Mock()
                mock_tool.execute = AsyncMock(return_value=ExecutionResult(
                    node_id="search",
                    success=True,
                    result="AI breakthrough in 2026...",
                    error=None,
                    duration_ms=150.0
                ))
                mock_registry.return_value = mock_tool
                
                # Execute full autonomous flow
                result = await engine.execute("Find latest AI news and summarize")
                
                # Assertions
                assert result is not None, "Result should not be None"
                assert isinstance(result, str), "Result should be a string"
                assert len(result) > 0, "Result should not be empty"
                assert "AI" in result, "Result should contain 'AI'"
        
        await engine.shutdown()
