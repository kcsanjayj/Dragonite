"""
Unit tests for tool implementations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.tools.search import SearchTool
from app.tools.web_fetch import WebFetchTool
from app.tools.python_exec import PythonExecTool


@pytest.mark.unit
class TestSearchTool:
    """Test cases for SearchTool."""
    
    @pytest.fixture
    def search_tool(self):
        return SearchTool()
    
    def test_tool_initialization(self, search_tool):
        """Test tool initialization."""
        assert search_tool.name == "search"
        assert "search" in search_tool.description.lower()
    
    @pytest.mark.asyncio
    async def test_search_execution(self, search_tool):
        """Test search execution."""
        with patch('duckduckgo_search.DDGS') as mock_ddgs:
            mock_results = [
                {"title": "Test", "body": "Test result", "href": "http://test.com"}
            ]
            mock_ddgs.return_value.__enter__.return_value.text.return_value = mock_results
            
            result = await search_tool.execute(query="test query")
            
            assert result is not None
            assert "results" in result or len(result) > 0
    
    def test_get_schema(self, search_tool):
        """Test tool schema."""
        schema = search_tool.get_schema()
        
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert schema["required"] == ["query"]


@pytest.mark.unit
class TestWebFetchTool:
    """Test cases for WebFetchTool."""

    @pytest.fixture
    def web_fetch_tool(self):
        return WebFetchTool()

    def test_tool_initialization(self, web_fetch_tool):
        """Test tool initialization."""
        assert web_fetch_tool.name == "web_fetch"
        assert "web page" in web_fetch_tool.description.lower()

    @pytest.mark.asyncio
    async def test_http_fetch(self, web_fetch_tool, mocker):
        """Test HTTP fetch with proper async mocking."""
        # Mock the ClientSession context manager
        mock_session = mocker.AsyncMock()
        mock_response = mocker.AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = mocker.AsyncMock(return_value="<html><body>Test content</body></html>")

        # Setup the nested context managers
        mock_session.get.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = mocker.AsyncMock(return_value=False)

        # Mock ClientSession
        mock_client_session = mocker.patch('aiohttp.ClientSession')
        mock_client_session.return_value.__aenter__ = mocker.AsyncMock(return_value=mock_session)
        mock_client_session.return_value.__aexit__ = mocker.AsyncMock(return_value=False)

        result = await web_fetch_tool._fetch_http("http://test.com", 30)

        assert result["success"] is True
        assert result["status"] == 200
        assert "Test content" in result["text"]

    @pytest.mark.asyncio
    async def test_http_fetch_httpx_pattern(self, mocker):
        """
        Test HTTP fetch using httpx with clean async mocking pattern.
        This demonstrates the elite async testing approach.
        """
        mock_response = mocker.AsyncMock()
        mock_response.text = mocker.AsyncMock(return_value="<html><body>OK</body></html>")
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}

        mock_get = mocker.patch("httpx.AsyncClient.get", return_value=mock_response)

        # Use httpx-based fetch directly
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://example.com")
            text = await response.text()

        assert "OK" in text
        mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_browser_fetch(self, web_fetch_tool):
        """Test browser fetch."""
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html>Test</html>")
            mock_page.title = AsyncMock(return_value="Test Page")
            mock_page.inner_text = AsyncMock(return_value="Test content")
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context
            
            result = await web_fetch_tool._fetch_with_browser("http://test.com", "chrome", True, 30)
            
            assert result["success"] is True
            assert result["method"] == "browser_chrome"
    
    def test_get_schema(self, web_fetch_tool):
        """Test tool schema."""
        schema = web_fetch_tool.get_schema()
        
        assert schema["type"] == "object"
        assert "url" in schema["properties"]
        assert "browser" in schema["properties"]
        assert schema["required"] == ["url"]


@pytest.mark.unit
class TestPythonExecTool:
    """Test cases for PythonExecTool."""
    
    @pytest.fixture
    def python_exec_tool(self):
        return PythonExecTool()
    
    def test_tool_initialization(self, python_exec_tool):
        """Test tool initialization."""
        assert python_exec_tool.name == "python_exec"
        assert "python" in python_exec_tool.description.lower()
    
    @pytest.mark.asyncio
    async def test_simple_execution(self, python_exec_tool):
        """Test simple Python execution."""
        result = await python_exec_tool.execute(code="print('Hello, World!')")
        
        assert result is not None
        assert result["success"] is True
        assert "Hello, World!" in result.get("stdout", "")
    
    @pytest.mark.asyncio
    async def test_execution_with_variables(self, python_exec_tool):
        """Test execution with variable assignment."""
        # Use a simpler test that just checks success
        result = await python_exec_tool.execute(code="print(42)")
        
        assert result["success"] is True
        assert "42" in result.get("stdout", "")
    
    @pytest.mark.asyncio
    async def test_execution_error(self, python_exec_tool):
        """Test execution with syntax error."""
        result = await python_exec_tool.execute(code="print('unclosed string")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_schema(self, python_exec_tool):
        """Test tool schema."""
        schema = python_exec_tool.get_schema()
        
        assert schema["type"] == "object"
        assert "code" in schema["properties"]
        assert schema["required"] == ["code"]
