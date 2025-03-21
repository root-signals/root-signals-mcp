"""Example of running the RootSignals MCP Server with SSE transport.

This script demonstrates how to configure and run the server with
Server-Sent Events (SSE) transport for use in network/Docker environments.
"""

import logging
import os
import sys
from typing import Any

import uvicorn
from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from root_mcp_server.evaluator import EvaluatorService
from root_mcp_server.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sse_server_example")


class SimpleMCPServer:
    """A simplified MCP server implementation focusing on SSE transport."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.evaluator_service = EvaluatorService()
        self.app = Server("RootSignals Evaluators")

        # Register tools with MCP server
        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            tools = [
                Tool(
                    name="list_evaluators",
                    description="List all available evaluators from RootSignals",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                )
            ]
            return tools

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            if name == "list_evaluators":
                result = {"evaluators": [], "count": 0, "total": 0}
                return [TextContent(type="text", text=str(result))]
            else:
                return [TextContent(type="text", text='{"error": "Unknown tool"}')]

    async def initialize(self) -> None:
        """Initialize the server and services."""
        logger.info("Initializing MCP server...")
        # In a real implementation, you would initialize services here
        logger.info("MCP server initialized successfully")

    async def handle_sse(self, request: Request) -> Any:
        """Handle SSE connections."""
        logger.debug("SSE connection initiated")
        async with self.sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await self.app.run(streams[0], streams[1], self.app.create_initialization_options())


def run_sse_server(host: str = "0.0.0.0", port: int = 9090) -> None:
    """Run the MCP server with SSE transport."""
    logger.info(f"Starting SSE server on {host}:{port}")

    # Create server instance and initialize
    server = SimpleMCPServer()

    # Create an SSE transport endpoint
    server.sse_transport = SseServerTransport("/sse/message")

    # Create Starlette routes
    routes = [
        Route("/sse", endpoint=server.handle_sse),
        Mount("/sse/message", app=server.sse_transport.handle_post_message),
        Route("/health", endpoint=lambda r: Response("OK", status_code=200)),
    ]

    # Create Starlette app
    app = Starlette(routes=routes)

    # Start the server (blocking call)
    logger.info(f"SSE server listening on http://{host}:{port}/sse")
    uvicorn.run(app, host=host, port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    try:
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "9090"))
        run_sse_server(host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)
