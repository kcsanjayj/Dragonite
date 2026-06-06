"""
Code search tool for finding code examples online.
Combines web search with code extraction for efficient code retrieval.
"""

from typing import Dict, Any, Optional
from .registry import Tool


class CodeSearchTool(Tool):
    """Code search tool that finds and extracts code examples."""
    
    def __init__(self):
        """Initialize the code search tool."""
        super().__init__(
            name="code_search",
            description="Search for code examples online and extract actual code from results. Best for finding working code snippets."
        )
    
    async def execute(
        self, 
        query: str,
        language: Optional[str] = None,
        max_results: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for code examples and extract them.
        
        Args:
            query: The code search query (e.g., "java draw circle", "python list comprehension")
            language: Optional programming language filter
            max_results: Maximum number of code examples to return (default: 3)
            **kwargs: Additional parameters
            
        Returns:
            List of code examples with sources
        """
        try:
            # Enhance query for better code results
            enhanced_query = query
            if language:
                enhanced_query = f"{language} {query} example code"
            else:
                enhanced_query = f"{query} example code"
            
            # Use search tool
            from ..tools.search import SearchTool
            search_tool = SearchTool()
            
            search_results = await search_tool.execute(
                query=enhanced_query,
                max_results=max_results * 2  # Get more to filter
            )
            
            if not search_results or not search_results.get("results"):
                return {
                    "code_examples": [],
                    "count": 0,
                    "message": "No code examples found"
                }
            
            # Extract code from top results using web_scrape
            from ..tools.web_scrape import WebScrapeTool
            scrape_tool = WebScrapeTool()
            
            code_examples = []
            
            for result in search_results.get("results", [])[:max_results * 2]:
                url = result.get("href", "")
                if not url or not url.startswith("http"):
                    continue
                
                try:
                    # Extract code from the page
                    scrape_result = await scrape_tool.execute(
                        url=url,
                        selector="pre, code, .highlight, .codeblock",
                        extract_type="code_blocks"
                    )
                    
                    code_blocks = scrape_result.get("content", [])
                    if isinstance(code_blocks, str):
                        code_blocks = [code_blocks]
                    
                    # Filter for substantial code
                    for code in code_blocks:
                        if code and len(code) > 20:  # Skip tiny snippets
                            # Validate it's actually code (contains common patterns)
                            if self._looks_like_code(code, language):
                                code_examples.append({
                                    "code": code,
                                    "source": url,
                                    "title": result.get("title", "Code Example")
                                })
                                
                                if len(code_examples) >= max_results:
                                    break
                    
                    if len(code_examples) >= max_results:
                        break
                        
                except Exception:
                    continue
            
            return {
                "code_examples": code_examples,
                "count": len(code_examples),
                "query": query,
                "language": language
            }
            
        except Exception as e:
            raise RuntimeError(f"Code search failed: {str(e)}")
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Code search query (e.g., 'java draw circle', 'python list comprehension')"},
                "language": {"type": "string", "description": "Programming language filter (optional)"},
                "max_results": {"type": "integer", "default": 3, "description": "Maximum code examples to return"}
            },
            "required": ["query"]
        }
    
    def _looks_like_code(self, text: str, language: Optional[str] = None) -> bool:
        """Check if text looks like actual code."""
        text = text.strip()
        
        # General code indicators
        code_patterns = [
            ";", "{", "}", "def ", "class ", "function", "var ", "let ", "const ",
            "import ", "#", "//", "/*", "*/", "print(", "return ", "if ", "for ",
            "while ", "public ", "private ", "static ", "void ", "int ", "String "
        ]
        
        code_indicators = sum(1 for pattern in code_patterns if pattern in text)
        
        # If we have at least 2 code patterns, likely code
        return code_indicators >= 2
