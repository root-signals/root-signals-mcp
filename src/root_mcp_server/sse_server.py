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
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from root_mcp_server.evaluator import EvaluatorService
from root_mcp_server.schema import (
    EvaluationRequestByID,
    EvaluationRequestByName,
    EvaluationResponse,
    EvaluatorsListResponse,
    ListEvaluatorsRequest,
    RAGEvaluationByNameRequest,
    RAGEvaluationRequest,
    RunEvaluationByNameToolRequest,
    RunEvaluationToolRequest,
    RunRAGEvaluationByNameToolRequest,
    RunRAGEvaluationToolRequest,
    UnknownToolRequest,
)
from root_mcp_server.settings import settings

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

        @self.app.list_tools()  # TODO: Check with MCP protocol if this is expected to be exposed to clients
        async def list_tools() -> list[Tool]:
            return await self.list_tools()

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            return await self.call_tool(name, arguments)

        self.function_map = {
            "list_evaluators": self._handle_list_evaluators,
            "run_evaluation": self._handle_run_evaluation,
            "run_rag_evaluation": self._handle_run_rag_evaluation,
            "run_evaluation_by_name": self._handle_run_evaluation_by_name,
            "run_rag_evaluation_by_name": self._handle_run_rag_evaluation_by_name,
        }

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
                description="Run a standard evaluation using a RootSignals evaluator by ID",
                inputSchema=EvaluationRequestByID.model_json_schema(),
            ),
            Tool(
                name="run_rag_evaluation",
                description="Run a RAG evaluation with contexts using a RootSignals evaluator by ID",
                inputSchema=RAGEvaluationRequest.model_json_schema(),
            ),
            Tool(
                name="run_evaluation_by_name",
                description="Run a standard evaluation using a RootSignals evaluator by name instead of ID",
                inputSchema=EvaluationRequestByName.model_json_schema(),
            ),
            Tool(
                name="run_rag_evaluation_by_name",
                description="Run a RAG evaluation with contexts using a RootSignals evaluator by name instead of ID",
                inputSchema=RAGEvaluationByNameRequest.model_json_schema(),
            ),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Call a tool by name with the given arguments."""
        logger.debug(f"Tool call: {name}, arguments: {arguments}")

        handler = self.function_map.get(name)
        if not handler:
            logger.warning(f"Unknown tool: {name}")
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        try:
            if name == "list_evaluators":
                request_model = ListEvaluatorsRequest(**arguments)
            elif name == "run_evaluation":
                request_model = RunEvaluationToolRequest(**arguments)
            elif name == "run_rag_evaluation":
                request_model = RunRAGEvaluationToolRequest(**arguments)
            elif name == "run_evaluation_by_name":
                request_model = RunEvaluationByNameToolRequest(**arguments)
            elif name == "run_rag_evaluation_by_name":
                request_model = RunRAGEvaluationByNameToolRequest(**arguments)
            else:
                request_model = UnknownToolRequest(**arguments)

            result = await handler(request_model)
            return [TextContent(type="text", text=result.model_dump_json(exclude_none=True))]

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}", exc_info=settings.debug)
            return [
                TextContent(
                    type="text", text=json.dumps({"error": f"Error calling tool {name}: {e}"})
                )
            ]

    async def _handle_list_evaluators(
        self, params: ListEvaluatorsRequest
    ) -> EvaluatorsListResponse:
        """Handle list_evaluators tool call."""
        logger.debug("Handling list_evaluators request")
        return await self.evaluator_service.list_evaluators()

    async def _handle_run_evaluation(self, params: RunEvaluationToolRequest) -> EvaluationResponse:
        """Handle run_evaluation tool call."""
        logger.debug(f"Handling run_evaluation request for evaluator {params.evaluator_id}")

        eval_request = EvaluationRequestByID(
            evaluator_id=params.evaluator_id, request=params.request, response=params.response
        )

        return await self.evaluator_service.run_evaluation(eval_request)

    async def _handle_run_evaluation_by_name(
        self, params: RunEvaluationByNameToolRequest
    ) -> EvaluationResponse:
        """Handle run_evaluation_by_name tool call."""
        logger.debug(
            f"Handling run_evaluation_by_name request for evaluator {params.evaluator_name}"
        )

        # Convert evaluator_name to evaluator_id for compatibility with existing service
        eval_request = EvaluationRequestByName(
            evaluator_name=params.evaluator_name,
            request=params.request,
            response=params.response,
        )

        return await self.evaluator_service.run_evaluation_by_name(eval_request)

    async def _handle_run_rag_evaluation(
        self, params: RunRAGEvaluationToolRequest
    ) -> EvaluationResponse:
        """Handle run_rag_evaluation tool call."""
        logger.debug(f"Handling run_rag_evaluation request for evaluator {params.evaluator_id}")

        rag_request = RAGEvaluationRequest(
            evaluator_id=params.evaluator_id,
            request=params.request,
            response=params.response,
            contexts=params.contexts,
        )

        return await self.evaluator_service.run_rag_evaluation(rag_request)

    async def _handle_run_rag_evaluation_by_name(
        self, params: RunRAGEvaluationByNameToolRequest
    ) -> EvaluationResponse:
        """Handle run_rag_evaluation_by_name tool call."""
        logger.debug(
            f"Handling run_rag_evaluation_by_name request for evaluator {params.evaluator_name}"
        )

        rag_request = RAGEvaluationByNameRequest(
            evaluator_name=params.evaluator_name,
            request=params.request,
            response=params.response,
            contexts=params.contexts,
        )

        return await self.evaluator_service.run_rag_evaluation_by_name(rag_request)


def create_app(server: SSEMCPServer) -> Starlette:
    """Create a Starlette app with SSE routes."""
    sse_transport = SseServerTransport("/sse/message/")

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
        Mount("/sse/message/", app=sse_transport.handle_post_message),
        Route("/health", endpoint=lambda r: Response("OK", status_code=200)),
    ]

    return Starlette(routes=routes)


async def startup() -> SSEMCPServer:
    """Initialize the server during startup."""
    server = SSEMCPServer()
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

        logger.info("Starting RootSignals MCP Server")
        logger.info(f"Targeting API: {settings.root_signals_api_url}")
        logger.info(f"Environment: {settings.env}")
        logger.info(f"Transport: {settings.transport}")
        logger.info(f"Host: {host}, Port: {port}")

        run_server(host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=settings.debug)
        sys.exit(1)
