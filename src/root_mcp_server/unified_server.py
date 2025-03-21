"""Unified MCP server entry point for RootSignals evaluators.

This module provides the main entry point for the RootSignals MCP server.
"""

import asyncio
import logging
import sys

from root_mcp_server.server import MCPServer
from root_mcp_server.settings import settings


async def run_server() -> None:
    """Run the MCP server."""
    server = MCPServer()
    await server.start()


def main() -> None:
    """Main entry point for the MCP server."""
    # Configure logging
    log_level = getattr(logging, settings.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger("root_mcp_server")
    logger.info(f"Starting RootSignals MCP Server v{settings.version}")
    logger.info(f"Environment: {settings.env}")

    try:
        # Run the server
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=settings.debug)
        sys.exit(1)


if __name__ == "__main__":
    main()
