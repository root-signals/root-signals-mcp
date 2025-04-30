"""StdIO transport for the RootSignals MCP Server.

This module provides a dedicated implementation of the MCP server using
Standard I/O (stdio) transport for CLI environments.
"""

import asyncio
import logging
import sys
from typing import Any

from mcp import Tool
from mcp.types import TextContent

from root_signals_mcp.core import RootMCPServerCore
from root_signals_mcp.settings import settings

from root_signals_mcp.fastmcp_adapter import RootSignalsFastMCP  # noqa: E501  # isort: skip

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("root_signals_mcp.stdio")


class StdioMCPServer:
    """MCP server implementation with stdio transport for CLI environments."""

    def __init__(self) -> None:
        """Initialize the stdio-based MCP server."""
        self.core = RootMCPServerCore()

        self.mcp = RootSignalsFastMCP(self.core, name="RootSignals Evaluators")

    async def list_tools(self) -> list[Tool]:
        return await self.core.list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        return await self.core.call_tool(name, arguments)

    async def run(self) -> None:
        """Run the stdio server."""
        await self.mcp.run_stdio_async()


def main() -> None:
    """Entry point for the stdio server."""
    try:
        logger.info("Starting RootSignals MCP Server with stdio transport")
        logger.info(f"Targeting API: {settings.root_signals_api_url}")
        logger.info(f"Environment: {settings.env}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"API Key set: {bool(settings.root_signals_api_key)}")
        asyncio.run(StdioMCPServer().run())
        logger.info("RootSignals MCP Server (stdio) ready")

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
