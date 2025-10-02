"""MCP server configuration for web research capabilities.

Provides configuration for Model Context Protocol (MCP) servers including:
- Brave Search MCP for web search with rate limiting
- Configurable options for different API tiers
- Helper functions for creating SDK options
"""

import os
from typing import Any, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions
import structlog

from .rate_limiter import BraveSearchRateLimiter


logger = structlog.get_logger(__name__)


class MCPConfig:
    """Configuration for MCP servers."""

    def __init__(self, brave_tier: str = "free"):
        """Initialize MCP configuration.

        Args:
            brave_tier: Brave Search API tier ('free' or 'pro')
        """
        self.brave_tier = brave_tier
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.brave_rate_limiter = BraveSearchRateLimiter(tier=brave_tier)

        # Log configuration
        logger.info(
            "mcp.config.initialized",
            brave_tier=brave_tier,
            has_api_key=bool(self.brave_api_key),
        )

    def get_brave_mcp_config(self) -> Dict[str, Any]:
        """Get Brave Search MCP server configuration.

        Returns:
            MCP server configuration dict for stdio type

        Raises:
            ValueError: If BRAVE_API_KEY not set in environment
        """
        if not self.brave_api_key or self.brave_api_key == "your-brave-api-key-here":
            raise ValueError(
                "BRAVE_API_KEY not set in environment. "
                "Get your API key from https://brave.com/search/api/"
            )

        return {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@brave/brave-search-mcp-server"],
            "env": {
                "BRAVE_API_KEY": self.brave_api_key,
                "BRAVE_MCP_LOG_LEVEL": os.getenv("BRAVE_MCP_LOG_LEVEL", "info"),
            }
        }

    def get_allowed_brave_tools(
        self,
        web_search: bool = True,
        news_search: bool = True,
        local_search: bool = False,
        summarizer: bool = False,
    ) -> List[str]:
        """Get list of allowed Brave Search MCP tools.

        Args:
            web_search: Enable brave_web_search tool
            news_search: Enable brave_news_search tool
            local_search: Enable brave_local_search tool (Pro tier only)
            summarizer: Enable brave_summarizer tool (Pro tier only)

        Returns:
            List of MCP tool names with proper prefixes
        """
        tools = []

        if web_search:
            tools.append("mcp__brave__brave_web_search")

        if news_search:
            tools.append("mcp__brave__brave_news_search")

        # Pro-only features
        if self.brave_tier == "pro":
            if local_search:
                tools.append("mcp__brave__brave_local_search")
            if summarizer:
                tools.append("mcp__brave__brave_summarizer")
        elif local_search or summarizer:
            logger.warning(
                "mcp.brave.pro_features_requested",
                tier=self.brave_tier,
                msg="Pro features requested but using free tier"
            )

        return tools

    def create_research_options(
        self,
        max_turns: int = 20,
        include_file_tools: bool = True,
        permission_mode: str = 'acceptEdits',
        system_prompt: Optional[str] = None,
    ) -> ClaudeAgentOptions:
        """Create ClaudeAgentOptions configured for investment research.

        Args:
            max_turns: Maximum conversation turns
            include_file_tools: Include Read/Write/Bash tools
            permission_mode: Permission mode ('manual', 'acceptEdits', 'acceptAll')
            system_prompt: Optional system prompt override

        Returns:
            Configured ClaudeAgentOptions with Brave Search MCP
        """
        # Build MCP servers configuration
        mcp_servers = {
            "brave": self.get_brave_mcp_config()
        }

        # Build allowed tools list
        allowed_tools = self.get_allowed_brave_tools(
            web_search=True,
            news_search=True,
            local_search=False,  # Free tier doesn't support
            summarizer=False,    # Free tier doesn't support
        )

        # Add built-in file tools if requested
        if include_file_tools:
            allowed_tools.extend(["Read", "Write", "Bash"])

        # Default system prompt for research
        if system_prompt is None:
            system_prompt = """You are a financial research analyst with web search capabilities.

CRITICAL RULES:
1. ALWAYS execute brave_web_search for every research question asked
2. DO NOT just plan or describe searches - EXECUTE them using the tool
3. After each search, extract specific findings (numbers, dates, sources)
4. Include source URLs and publication dates in your summary
5. Wait 1 second between searches (free tier rate limit)

SEARCH BEST PRACTICES:
- Use specific queries: "NVIDIA Q2 2025 revenue" not "NVIDIA performance"
- Include time periods: "Q2 2025", "fiscal 2025", "2024-2025"
- Target quantitative data: revenue, growth %, margins, market share
- Look for official sources: investor relations, SEC filings, earnings releases

OUTPUT FORMAT:
For each question, provide:
- The search query you used
- Key findings with specific numbers
- Source titles and URLs
- Direct quotes when relevant"""

        options = ClaudeAgentOptions(
            mcp_servers=mcp_servers,
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            permission_mode=permission_mode,
            system_prompt=system_prompt,
        )

        logger.info(
            "mcp.research_options.created",
            max_turns=max_turns,
            tools_count=len(allowed_tools),
            permission_mode=permission_mode,
        )

        return options

    async def rate_limited_query(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        wait_for_rate_limit: bool = True,
    ):
        """Execute query with automatic rate limiting.

        Wraps Claude Agent SDK query() with Brave Search rate limiting.

        Args:
            prompt: Query prompt
            options: Claude Agent options
            wait_for_rate_limit: If True, wait for rate limit before query

        Yields:
            Messages from query() response stream
        """
        from claude_agent_sdk import query

        # Enforce rate limit before making request
        if wait_for_rate_limit:
            await self.brave_rate_limiter.acquire()
            logger.debug(
                "mcp.rate_limit.acquired",
                tokens_remaining=self.brave_rate_limiter.tokens,
            )

        # Execute query
        async for message in query(prompt=prompt, options=options):
            yield message


def get_brave_research_options(
    brave_tier: str = "free",
    max_turns: int = 20,
    system_prompt: Optional[str] = None,
) -> ClaudeAgentOptions:
    """Convenience function to get Brave Search research options.

    Args:
        brave_tier: Brave Search API tier ('free' or 'pro')
        max_turns: Maximum conversation turns
        system_prompt: Optional custom system prompt

    Returns:
        Configured ClaudeAgentOptions

    Example:
        ```python
        from investing_agents.core.mcp_config import get_brave_research_options
        from claude_agent_sdk import query

        options = get_brave_research_options(brave_tier="free")

        async for message in query(
            "Search for NVIDIA Q4 2024 earnings",
            options=options
        ):
            # Process messages
            pass
        ```
    """
    config = MCPConfig(brave_tier=brave_tier)
    return config.create_research_options(
        max_turns=max_turns,
        system_prompt=system_prompt,
    )


# Singleton instance for global use
_global_mcp_config: Optional[MCPConfig] = None


def get_mcp_config(brave_tier: str = "free") -> MCPConfig:
    """Get global MCP configuration instance.

    Returns singleton instance, creating it if necessary.

    Args:
        brave_tier: Brave Search API tier (only used on first call)

    Returns:
        Global MCPConfig instance
    """
    global _global_mcp_config

    if _global_mcp_config is None:
        _global_mcp_config = MCPConfig(brave_tier=brave_tier)

    return _global_mcp_config
