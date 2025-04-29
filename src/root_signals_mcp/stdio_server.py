"""StdIO transport for the RootSignals MCP Server.

This module provides a dedicated implementation of the MCP server using
Standard I/O (stdio) transport for CLI environments.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from root_signals_mcp import tools as tool_catalogue
from root_signals_mcp.core import RootMCPServerCore
from root_signals_mcp.settings import settings

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
        self.mcp = FastMCP("RootSignals Evaluators")

        self._register_tools()

    def _register_tools(self) -> None:
        """Register tool handlers with the FastMCP instance."""
        tools = tool_catalogue.get_tools()

        for tool in tools:
            self._register_tool_handler(tool.name)

    def _register_tool_handler(self, tool_name: str) -> None:
        """Register a handler for a specific tool."""

        async def handler(**kwargs) -> str:
            """Generic handler for all tool calls."""
            logger.debug(f"Handling tool {tool_name}")
            result = await self.core.call_tool(tool_name, kwargs)

            if result and len(result) > 0 and result[0].type == "text":
                logger.debug(f"{tool_name} result (truncated): {result[0].text[:100]}...")
                return result[0].text

            error_msg = json.dumps({"error": f"Failed to execute {tool_name}"})
            logger.error(f"Failed to execute {tool_name}: {error_msg}")
            return error_msg

        handler.__name__ = tool_name

        tool_def = next((t for t in tool_catalogue.get_tools() if t.name == tool_name), None)
        if tool_def:
            handler.__doc__ = tool_def.description

        self.mcp.tool()(handler)

    def run(self) -> None:
        """Run the stdio server."""
        logger.debug("Starting FastMCP with stdio transport")
        self.mcp.run("stdio")
        logger.info("FastMCP stdio server completed")


def main() -> None:
    """Entry point for the stdio server."""
    try:
        logger.info("Starting RootSignals MCP Server with stdio transport")
        logger.info(f"Targeting API: {settings.root_signals_api_url}")
        logger.info(f"Environment: {settings.env}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"API Key set: {bool(settings.root_signals_api_key)}")

        ready_message = "RootSignals MCP Server (stdio) ready"
        logger.info(ready_message)
        print(ready_message, file=sys.stderr, flush=True)

        server = StdioMCPServer()
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
