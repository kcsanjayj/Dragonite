"""
Web scrape tool for the autonomous agent system.
Extracts specific content from web pages using CSS selectors.
"""

from typing import Dict, Any, Optional
import aiohttp
from .registry import Tool


class WebScrapeTool(Tool):
    """Web scrape tool implementation with CSS selector support."""
    
    def __init__(self):
        """Initialize the web scrape tool."""
        super().__init__(
            name="web_scrape",
            description="Extract specific content from web pages using CSS selectors (e.g., code blocks, articles, specific sections)"
        )
    
    async def execute(
        self, 
        url: str, 
        selector: str,
        extract_type: str = "text",
        timeout: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Scrape content from a web page using CSS selector.
        
        Args:
            url: URL to scrape
            selector: CSS selector to target specific elements (e.g., "pre", "code", ".content", "article", "#code-block")
            extract_type: What to extract - "text", "html", "all_links", "code_blocks"
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
            
        Returns:
            Extracted content based on selector
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise RuntimeError(f"HTTP {response.status}: {response.reason}")
                    
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'text/html' not in content_type:
                        raise RuntimeError(f"Not HTML content: {content_type}")
                    
                    text = await response.text()
                    
                    # Parse HTML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # Extract based on selector and type
                    if extract_type == "code_blocks":
                        return self._extract_code_blocks(soup)
                    elif extract_type == "all_links":
                        return self._extract_links(soup)
                    else:
                        return self._extract_by_selector(soup, selector, extract_type)
                    
        except Exception as e:
            raise RuntimeError(f"Failed to scrape {url}: {str(e)}")
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
                "selector": {"type": "string", "description": "CSS selector (e.g., 'pre', 'code', '.content')"},
                "extract_type": {"type": "string", "enum": ["text", "html", "all_links", "code_blocks"], "default": "text"},
                "timeout": {"type": "integer", "default": 30}
            },
            "required": ["url", "selector"]
        }
    
    def _extract_by_selector(self, soup, selector: str, extract_type: str) -> Dict[str, Any]:
        """Extract content by CSS selector."""
        elements = soup.select(selector)
        
        if not elements:
            return {
                "content": None,
                "count": 0,
                "selector": selector,
                "warning": f"No elements found matching selector: {selector}"
            }
        
        results = []
        for elem in elements:
            if extract_type == "html":
                results.append(str(elem))
            else:
                results.append(elem.get_text(strip=True))
        
        return {
            "content": results[0] if len(results) == 1 else results,
            "count": len(results),
            "selector": selector,
            "url_found": True
        }
    
    def _extract_code_blocks(self, soup) -> Dict[str, Any]:
        """Extract code blocks from the page."""
        code_blocks = []
        
        # Look for code in pre/code tags
        for pre in soup.find_all('pre'):
            code = pre.get_text(strip=True)
            if code and len(code) > 10:  # Filter out tiny snippets
                code_blocks.append(code)
        
        # Also check code tags
        for code_tag in soup.find_all('code'):
            code = code_tag.get_text(strip=True)
            if code and len(code) > 10 and code not in code_blocks:
                code_blocks.append(code)
        
        # Look for common code container classes
        for elem in soup.find_all(class_=lambda x: x and any(c in str(x).lower() for c in ['code', 'syntax', 'highlight'])):
            code = elem.get_text(strip=True)
            if code and len(code) > 10 and code not in code_blocks:
                code_blocks.append(code)
        
        return {
            "content": code_blocks[0] if len(code_blocks) == 1 else code_blocks[:5],  # Limit to top 5
            "count": len(code_blocks),
            "selector": "code_blocks",
            "type": "code"
        }
    
    def _extract_links(self, soup) -> Dict[str, Any]:
        """Extract all links from the page."""
        links = []
        for a in soup.find_all('a', href=True):
            links.append({
                "text": a.get_text(strip=True),
                "url": a['href']
            })
        
        return {
            "content": links[:20],  # Limit to top 20
            "count": len(links),
            "selector": "links",
            "type": "links"
        }
