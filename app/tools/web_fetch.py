"""
Web fetch tool for the autonomous agent system.
Provides web page fetching capabilities with browser automation support.
"""

from typing import Dict, Any, Optional
import aiohttp
from .registry import Tool


class WebFetchTool(Tool):
    """Web page fetch tool implementation with browser automation."""
    
    def __init__(self):
        """Initialize the web fetch tool."""
        super().__init__(
            name="web_fetch",
            description="Fetch and parse web page content using HTTP or browser automation"
        )
    
    async def execute(self, url: str, timeout: int = 30, browser: Optional[str] = None, headless: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Fetch a web page.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            browser: Browser to use (chrome, firefox, webkit, or None for HTTP only)
            headless: Whether to run browser in headless mode
            **kwargs: Additional parameters
            
        Returns:
            Fetched page content
        """
        # Use browser automation if browser is specified
        if browser:
            return await self._fetch_with_browser(url, browser, headless, timeout)
        
        # Otherwise use simple HTTP fetch
        return await self._fetch_http(url, timeout)
    
    async def _fetch_http(self, url: str, timeout: int) -> Dict[str, Any]:
        """Fetch using simple HTTP request."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise RuntimeError(f"HTTP {response.status}: {response.reason}")
                    
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'text/html' in content_type:
                        text = await response.text()
                        # Basic HTML to text conversion
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(text, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text
                        text = soup.get_text()
                        
                        # Clean up whitespace
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        
                        return {
                            "url": url,
                            "status": response.status,
                            "content_type": content_type,
                            "title": soup.title.string if soup.title else "",
                            "text": text,
                            "method": "http",
                            "success": True
                        }
                    else:
                        # Return raw content for non-HTML
                        content = await response.read()
                        return {
                            "url": url,
                            "status": response.status,
                            "content_type": content_type,
                            "content": str(content),
                            "method": "http",
                            "success": True
                        }
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Failed to fetch URL: {e}")
        except ImportError:
            raise RuntimeError("beautifulsoup4 package not installed. Install with: pip install beautifulsoup4")
    
    async def _fetch_with_browser(self, url: str, browser: str, headless: bool, timeout: int) -> Dict[str, Any]:
        """Fetch using browser automation with Playwright."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("playwright package not installed. Install with: pip install playwright")
        
        # Map browser names to Playwright browser types
        browser_map = {
            "chrome": "chromium",
            "brave": "chromium",  # Brave uses Chromium
            "firefox": "firefox",
            "webkit": "webkit",
            "safari": "webkit"
        }
        
        playwright_browser = browser_map.get(browser.lower(), "chromium")
        
        async with async_playwright() as p:
            # Launch browser
            browser_instance = await getattr(p, playwright_browser).launch(headless=headless)
            
            try:
                # Create new page
                page = await browser_instance.new_page()
                
                # Navigate to URL
                await page.goto(url, timeout=timeout * 1000)
                
                # Get page content
                content = await page.content()
                
                # Get title
                title = await page.title()
                
                # Get text content
                text = await page.inner_text("body")
                
                # Take screenshot if not headless
                screenshot = None
                if not headless:
                    screenshot_bytes = await page.screenshot()
                    screenshot = f"data:image/png;base64,{screenshot_bytes.hex()}"
                
                return {
                    "url": url,
                    "status": 200,
                    "content_type": "text/html",
                    "title": title,
                    "text": text,
                    "method": f"browser_{browser}",
                    "screenshot": screenshot,
                    "success": True
                }
                
            finally:
                await browser_instance.close()
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": 30
                },
                "browser": {
                    "type": "string",
                    "description": "Browser to use (chrome, firefox, webkit, brave, safari, or None for HTTP only)",
                    "enum": ["chrome", "firefox", "webkit", "brave", "safari", None]
                },
                "headless": {
                    "type": "boolean",
                    "description": "Whether to run browser in headless mode",
                    "default": True
                }
            },
            "required": ["url"]
        }