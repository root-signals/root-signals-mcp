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
    CodingPolicyAdherenceEvaluationRequest,
    EvaluationRequest,
    EvaluationRequestByName,
    EvaluationResponse,
    EvaluatorsListResponse,
    ListEvaluatorsRequest,
    RAGEvaluationByNameRequest,
    RAGEvaluationRequest,
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
            "run_coding_policy_adherence": self._handle_coding_style_evaluation,
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
                inputSchema=EvaluationRequest.model_json_schema(),
            ),
            Tool(
                name="run_rag_evaluation",
                description="Run a RAG evaluation with contexts using a RootSignals evaluator by ID",
                inputSchema=RAGEvaluationRequest.model_json_schema(),
            ),
            Tool(
                name="run_evaluation_by_name",
                description="Run a standard evaluation using a RootSignals evaluator by name",
                inputSchema=EvaluationRequestByName.model_json_schema(),
            ),
            Tool(
                name="run_rag_evaluation_by_name",
                description="Run a RAG evaluation with contexts using a RootSignals evaluator by name",
                inputSchema=RAGEvaluationByNameRequest.model_json_schema(),
            ),
            Tool(
                name="run_coding_policy_adherence",
                description="Evaluates that the code is written according to the coding policy defined in the current repository policy documents such as cursor/rules using RootSignals evaluators specifically designed for code quality and coding policy adherence",
                inputSchema=CodingPolicyAdherenceEvaluationRequest.model_json_schema(),
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
                request_model = EvaluationRequest(**arguments)
            elif name == "run_rag_evaluation":
                request_model = RAGEvaluationRequest(**arguments)
            elif name == "run_evaluation_by_name":
                request_model = EvaluationRequestByName(**arguments)
            elif name == "run_rag_evaluation_by_name":
                request_model = RAGEvaluationByNameRequest(**arguments)
            elif name == "run_coding_policy_adherence":
                request_model = CodingPolicyAdherenceEvaluationRequest(**arguments)
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

    async def _handle_run_evaluation(self, params: EvaluationRequest) -> EvaluationResponse:
        """Handle run_evaluation tool call."""
        logger.debug(f"Handling run_evaluation request for evaluator {params.evaluator_id}")

        # params is already an EvaluationRequestByID (alias). Pass through.
        return await self.evaluator_service.run_evaluation(params)

    async def _handle_run_evaluation_by_name(
        self, params: EvaluationRequestByName
    ) -> EvaluationResponse:
        """Handle run_evaluation_by_name tool call."""
        logger.debug(
            f"Handling run_evaluation_by_name request for evaluator {params.evaluator_name}"
        )

        # params is already an EvaluationRequestByName (alias). Pass through.
        return await self.evaluator_service.run_evaluation_by_name(params)

    async def _handle_run_rag_evaluation(self, params: RAGEvaluationRequest) -> EvaluationResponse:
        """Handle run_rag_evaluation tool call."""
        logger.debug(f"Handling run_rag_evaluation request for evaluator {params.evaluator_id}")

        return await self.evaluator_service.run_rag_evaluation(params)

    async def _handle_run_rag_evaluation_by_name(
        self, params: RAGEvaluationByNameRequest
    ) -> EvaluationResponse:
        """Handle run_rag_evaluation_by_name tool call."""
        logger.debug(
            f"Handling run_rag_evaluation_by_name request for evaluator {params.evaluator_name}"
        )

        return await self.evaluator_service.run_rag_evaluation_by_name(params)

    async def _handle_coding_style_evaluation(
        self, params: CodingPolicyAdherenceEvaluationRequest
    ) -> EvaluationResponse:
        """Handle run_coding_policy_adherence tool call."""
        logger.debug("Handling run_coding_policy_adherence request")

        rag_request = RAGEvaluationRequest(
            evaluator_id=settings.coding_policy_evaluator_id,
            request=settings.coding_policy_evaluator_request,
            response=params.code,
            contexts=params.policy_documents,
        )

        return await self.evaluator_service.run_rag_evaluation(rag_request)


def create_app(server: SSEMCPServer) -> Starlette:
    """Create a Starlette app with SSE routes.

    Includes the /sse endpoint from <1.5.0 for backward compatibility and the identical /mcp endpoint.
    """
    sse_transport = SseServerTransport("/sse/message/")
    mcp_transport = SseServerTransport("/mcp/message/")

    async def _run_server_app(
        request: Request, transport: SseServerTransport
    ) -> Any:  # pragma: no cover – trivial helper
        """Internal helper to bridge ASGI request with a given SSE transport."""
        logger.debug("SSE connection initiated")
        try:
            async with transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.app.run(
                    streams[0], streams[1], server.app.create_initialization_options()
                )
        except Exception as exc:
            logger.error("Error handling SSE/MCP connection", exc_info=True)
            return Response(f"Error: {exc}", status_code=500)

    async def handle_sse(request: Request) -> Any:  # /sse
        return await _run_server_app(request, sse_transport)

    async def handle_mcp(request: Request) -> Any:  # /mcp
        return await _run_server_app(request, mcp_transport)

    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/sse/message/", app=sse_transport.handle_post_message),
        Route("/mcp", endpoint=handle_mcp),
        Mount("/mcp/message/", app=mcp_transport.handle_post_message),
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
