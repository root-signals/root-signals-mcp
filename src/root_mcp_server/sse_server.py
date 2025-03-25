"""SSE transport for the RootSignals MCP Server.

This module provides a dedicated implementation of the MCP server using
Server-Sent Events (SSE) transport for network/Docker environments.
"""

import json
import logging
import os
import sys
from typing import Any

import uvicorn
from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from root_mcp_server.evaluator import EvaluatorService
from root_mcp_server.schema import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluatorsListResponse,
    RAGEvaluationRequest,
)
from root_mcp_server.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("root_mcp_server.sse")


class SSEMCPServer:
    """MCP server implementation with SSE transport for Docker/network environments."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.evaluator_service = EvaluatorService()
        self.app = Server("RootSignals Evaluators")

        # Register tool handlers with MCP server
        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            return await self.list_tools()

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            return await self.call_tool(name, arguments)

        self.function_map = {
            "list_evaluators": self._handle_list_evaluators,
            "run_evaluation": self._handle_run_evaluation,
            "run_rag_evaluation": self._handle_run_rag_evaluation,
        }

    async def initialize(self) -> None:
        """Initialize the server and required services."""
        logger.info("Initializing MCP server...")
        await self.evaluator_service.initialize()
        logger.info("MCP server initialized successfully")

    async def list_tools(self) -> list[Tool]:
        """List available tools for the MCP server."""
        return [
            Tool(
                name="list_evaluators",
                description="List all available evaluators from RootSignals",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="run_evaluation",
                description="Run a standard evaluation using a RootSignals evaluator",
                inputSchema=EvaluationRequest.model_json_schema(),
            ),
            Tool(
                name="run_rag_evaluation",
                description="Run a RAG evaluation with contexts using a RootSignals evaluator",
                inputSchema=RAGEvaluationRequest.model_json_schema(),
            ),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Call a tool by name with the given arguments."""
        logger.debug(f"Tool call: {name}, arguments: {arguments}")

        handler = self.function_map.get(name)
        if not handler:
            logger.warning(f"Unknown tool: {name}")
            error_result = {"error": f"Unknown tool: {name}"}
            return [TextContent(type="text", text=json.dumps(error_result))]


        try:
            result = await handler(arguments)
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}", exc_info=settings.debug)
            error_result = {"error": f"Error calling tool {name}: {e}"}
            return [TextContent(type="text", text=json.dumps(error_result))]

    async def _handle_list_evaluators(self, params: dict[str, Any]) -> EvaluatorsListResponse:
        """Handle list_evaluators tool call."""
        logger.debug("Handling list_evaluators request")
        response: EvaluatorsListResponse = await self.evaluator_service.list_evaluators()
        return response.model_dump(exclude_none=True)

    async def _handle_run_evaluation(self, params: dict[str, Any]) -> EvaluationResponse:
        """Handle run_evaluation tool call."""
        logger.debug(f"Handling run_evaluation request: {params}")

        try:
            request = EvaluationRequest.model_validate(params)

            evaluator = await self.evaluator_service.get_evaluator_by_id(request.evaluator_id)
            if not evaluator:
                return {"error": f"Evaluator with ID '{request.evaluator_id}' not found"}

            response: EvaluationResponse = await self.evaluator_service.run_evaluation(
                request
            )
            return response.model_dump(exclude_none=True)

        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"error": f"Validation error: {e}"}
        except Exception as e:
            logger.error(f"Error running evaluation: {e}", exc_info=True)
            return {"error": f"Error running evaluation: {e}"}

    async def _handle_run_rag_evaluation(self, params: dict[str, Any]) -> EvaluationResponse:
        """Handle run_rag_evaluation tool call."""
        logger.debug(f"Handling run_rag_evaluation request: {params}")

        try:
            request = RAGEvaluationRequest.model_validate(params)

            evaluator = await self.evaluator_service.get_evaluator_by_id(request.evaluator_id)
            if not evaluator:
                return {"error": f"Evaluator with ID '{request.evaluator_id}' not found"}

            requires_context = evaluator.requires_contexts
            if requires_context and not request.contexts:
                return {"error": "This evaluator requires context, but none was provided"}

            response: EvaluationResponse = await self.evaluator_service.run_rag_evaluation(
                request
            )
            return response.model_dump(exclude_none=True)

        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"error": f"Validation error: {e}"}
        except Exception as e:
            logger.error(f"Error running RAG evaluation: {e}", exc_info=True)
            return {"error": f"Error running RAG evaluation: {e}"}


def create_app(server: SSEMCPServer) -> Starlette:
    """Create a Starlette app with SSE routes."""
    sse_transport = SseServerTransport("/sse/message")

    async def handle_sse(request: Request) -> Any:
        """Handle SSE connections."""
        logger.debug("SSE connection initiated")
        try:
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.app.run(
                    streams[0], streams[1], server.app.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Error handling SSE connection: {e}", exc_info=True)
            return Response(f"Error: {e}", status_code=500)

    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/sse/message", app=sse_transport.handle_post_message),
        Route("/health", endpoint=lambda r: Response("OK", status_code=200)),
    ]

    return Starlette(routes=routes)


async def startup() -> SSEMCPServer:
    """Initialize the server during startup."""
    server = SSEMCPServer()
    await server.initialize()
    return server


def run_server(host: str = "0.0.0.0", port: int = 9090) -> None:
    """Run the MCP server with SSE transport."""
    import asyncio

    server = asyncio.run(startup())

    app = create_app(server)

    logger.info(f"SSE server listening on http://{host}:{port}/sse")
    uvicorn.run(app, host=host, port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    try:
        host = os.environ.get("HOST", settings.host)
        port = int(os.environ.get("PORT", settings.port))

        logger.info(f"Starting RootSignals MCP Server v{settings.version}")
        logger.info(f"Environment: {settings.env}")
        logger.info(f"Transport: {settings.transport}")
        logger.info(f"Host: {host}, Port: {port}")

        run_server(host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=settings.debug)
        sys.exit(1)
