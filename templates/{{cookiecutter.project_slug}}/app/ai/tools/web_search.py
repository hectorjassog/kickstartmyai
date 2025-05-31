"""Web search tool for AI agents."""

import asyncio
import aiohttp
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import logging
from pydantic import BaseModel, Field

from .base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class WebSearchInput(ToolInput):
    """Input schema for web search tool."""
    
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    search_engine: str = Field(default="duckduckgo", description="Search engine to use")
    safe_search: bool = Field(default=True, description="Enable safe search")
    region: Optional[str] = Field(default=None, description="Search region (e.g., 'us-en')")


class WebSearchResult(BaseModel):
    """Single web search result."""
    
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")
    snippet: str = Field(..., description="Page snippet/description")
    domain: str = Field(..., description="Domain name")
    timestamp: Optional[str] = Field(default=None, description="When the page was indexed")


class WebSearchOutput(ToolOutput):
    """Output schema for web search tool."""
    
    results: List[WebSearchResult] = Field(default_factory=list, description="Search results")
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results found")
    search_time: float = Field(..., description="Time taken for search in seconds")


class WebContentInput(ToolInput):
    """Input schema for web content extraction."""
    
    url: str = Field(..., description="URL to extract content from")
    max_length: int = Field(default=5000, ge=100, le=50000, description="Maximum content length")
    include_links: bool = Field(default=False, description="Include links in content")
    clean_html: bool = Field(default=True, description="Clean HTML tags from content")


class WebContentOutput(ToolOutput):
    """Output schema for web content extraction."""
    
    content: str = Field(..., description="Extracted content")
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")
    meta_description: Optional[str] = Field(default=None, description="Meta description")
    word_count: int = Field(..., description="Word count of extracted content")
    links: List[str] = Field(default_factory=list, description="Links found on the page")


class WebSearchTool(BaseTool):
    """Tool for performing web searches and extracting content."""
    
    name: str = "web_search"
    description: str = "Search the web and extract content from web pages"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize web search tool."""
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = self.config.get("timeout", 30)
        self.user_agent = self.config.get(
            "user_agent",
            "Mozilla/5.0 (compatible; AI-Agent/1.0; +https://example.com/bot)"
        )
        self.max_concurrent_requests = self.config.get("max_concurrent_requests", 5)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {"User-Agent": self.user_agent}
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=aiohttp.TCPConnector(limit=self.max_concurrent_requests)
            )
        return self.session
    
    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        safe_search: bool = True,
        region: Optional[str] = None
    ) -> List[WebSearchResult]:
        """Perform search using DuckDuckGo."""
        session = await self._get_session()
        
        # DuckDuckGo instant answer API
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        
        if safe_search:
            params["safe_search"] = "strict"
        
        if region:
            params["kl"] = region
        
        try:
            async with session.get(
                "https://api.duckduckgo.com/",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    # Parse related topics and results
                    for topic in data.get("RelatedTopics", [])[:max_results]:
                        if isinstance(topic, dict) and "Text" in topic:
                            result = WebSearchResult(
                                title=topic.get("Text", "").split(" - ")[0][:100],
                                url=topic.get("FirstURL", ""),
                                snippet=topic.get("Text", "")[:300],
                                domain=self._extract_domain(topic.get("FirstURL", ""))
                            )
                            results.append(result)
                    
                    return results
                else:
                    logger.error(f"DuckDuckGo search failed with status {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {e}")
            return []
    
    async def _search_serper(
        self,
        query: str,
        max_results: int,
        safe_search: bool = True,
        region: Optional[str] = None
    ) -> List[WebSearchResult]:
        """Perform search using Serper API (requires API key)."""
        api_key = self.config.get("serper_api_key")
        if not api_key:
            logger.error("Serper API key not configured")
            return []
        
        session = await self._get_session()
        
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": min(max_results, 100)
        }
        
        if region:
            payload["gl"] = region
        
        try:
            async with session.post(
                "https://google.serper.dev/search",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    for item in data.get("organic", []):
                        result = WebSearchResult(
                            title=item.get("title", ""),
                            url=item.get("link", ""),
                            snippet=item.get("snippet", ""),
                            domain=self._extract_domain(item.get("link", ""))
                        )
                        results.append(result)
                    
                    return results
                else:
                    logger.error(f"Serper search failed with status {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error searching Serper: {e}")
            return []
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return ""
    
    async def _extract_content(
        self,
        url: str,
        max_length: int,
        include_links: bool = False,
        clean_html: bool = True
    ) -> WebContentOutput:
        """Extract content from a web page."""
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('title')
                    title = title_tag.get_text().strip() if title_tag else ""
                    
                    # Extract meta description
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    meta_description = None
                    if meta_desc and meta_desc.get('content'):
                        meta_description = meta_desc['content'].strip()
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                    
                    # Extract main content
                    main_content = soup.find('main') or soup.find('article') or soup.find('body')
                    if main_content:
                        content = main_content.get_text()
                    else:
                        content = soup.get_text()
                    
                    # Clean content
                    if clean_html:
                        lines = (line.strip() for line in content.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        content = ' '.join(chunk for chunk in chunks if chunk)
                    
                    # Truncate content
                    if len(content) > max_length:
                        content = content[:max_length] + "..."
                    
                    # Extract links if requested
                    links = []
                    if include_links:
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if href.startswith('http'):
                                links.append(href)
                            elif href.startswith('/'):
                                links.append(urljoin(url, href))
                    
                    return WebContentOutput(
                        content=content,
                        title=title,
                        url=url,
                        meta_description=meta_description,
                        word_count=len(content.split()),
                        links=links[:50]  # Limit links
                    )
                else:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
        
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            raise Exception(f"Failed to extract content: {str(e)}")
    
    async def search(self, tool_input: WebSearchInput) -> WebSearchOutput:
        """Perform web search."""
        import time
        start_time = time.time()
        
        # Choose search method based on configuration
        search_engine = tool_input.search_engine.lower()
        
        if search_engine == "duckduckgo":
            results = await self._search_duckduckgo(
                tool_input.query,
                tool_input.max_results,
                tool_input.safe_search,
                tool_input.region
            )
        elif search_engine == "serper":
            results = await self._search_serper(
                tool_input.query,
                tool_input.max_results,
                tool_input.safe_search,
                tool_input.region
            )
        else:
            raise ValueError(f"Unsupported search engine: {search_engine}")
        
        search_time = time.time() - start_time
        
        return WebSearchOutput(
            results=results,
            query=tool_input.query,
            total_results=len(results),
            search_time=search_time
        )
    
    async def extract_content(self, tool_input: WebContentInput) -> WebContentOutput:
        """Extract content from a web page."""
        return await self._extract_content(
            tool_input.url,
            tool_input.max_length,
            tool_input.include_links,
            tool_input.clean_html
        )
    
    async def execute(self, tool_input: Union[WebSearchInput, WebContentInput]) -> Union[WebSearchOutput, WebContentOutput]:
        """Execute the web search or content extraction tool."""
        try:
            if isinstance(tool_input, WebSearchInput):
                return await self.search(tool_input)
            elif isinstance(tool_input, WebContentInput):
                return await self.extract_content(tool_input)
            else:
                raise ValueError(f"Unsupported input type: {type(tool_input)}")
        
        except Exception as e:
            logger.error(f"Web tool execution failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search", "extract_content"],
                        "description": "Action to perform"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search action)"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to extract content from (for extract_content action)"
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Maximum number of search results"
                    },
                    "max_length": {
                        "type": "integer",
                        "minimum": 100,
                        "maximum": 50000,
                        "default": 5000,
                        "description": "Maximum content length for extraction"
                    }
                },
                "required": ["action"],
                "anyOf": [
                    {"required": ["query"]},
                    {"required": ["url"]}
                ]
            }
        }
