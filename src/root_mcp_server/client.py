"""MCP client example implementation for connecting to the RootSignals MCP Server via SSE.

This module provides a client to interact with the MCP server using the
Server-Sent Events (SSE) transport

This is a simplified example implementation for testing purposes.
"""

import json
import logging
from contextlib import AsyncExitStack
from typing import Any, TypeVar

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger("root_mcp_server.client")

T = TypeVar("T")


class RootSignalsMCPClient:
    """Client for interacting with the RootSignals MCP Server via SSE transport."""

    def __init__(self, server_url: str = "http://localhost:9090/sse"):
        """Initialize the MCP client.

        Args:
            server_url: URL of the SSE endpoint of the MCP server
        """
        self.server_url = server_url
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self.connected = False

    async def connect(self) -> None:
        """Connect to the MCP server."""
        try:
            logger.info(f"Connecting to MCP server at {self.server_url}")

            # Connect to the SSE endpoint
            sse_transport = await self.exit_stack.enter_async_context(sse_client(self.server_url))
            read_stream, write_stream = sse_transport

            # Create and initialize client session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize the session
            await self.session.initialize()

            self.connected = True
            logger.info("Successfully connected to MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        try:
            logger.info("Disconnecting from MCP server")
            await self.exit_stack.aclose()
            self.session = None
            self.connected = False
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

    async def _ensure_connected(self) -> None:
        """Ensure the client is connected to the server."""
        if not self.connected or self.session is None:
            raise RuntimeError("Client is not connected to the MCP server")

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server.

        Returns:
            List of available tools with their details
        """
        await self._ensure_connected()
        assert self.session is not None

        response = await self.session.list_tools()

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
            }
            for tool in response.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool response as a dictionary
        """
        await self._ensure_connected()
        assert self.session is not None

        response = await self.session.call_tool(tool_name, arguments)

        text_content = next((item for item in response.content if item.type == "text"), None)
        if not text_content:
            raise ValueError("No text content found in the tool response")

        return json.loads(text_content.text)

    async def list_evaluators(self) -> list[dict[str, Any]]:
        """List available evaluators from the RootSignals API.

        Returns:
            List of available evaluators
        """
        result = await self.call_tool("list_evaluators", {})
        return result.get("evaluators", [])

    async def run_evaluation(
        self, evaluator_id: str, request: str, response: str
    ) -> dict[str, Any]:
        """Run a standard evaluation using a RootSignals evaluator by ID.

        Args:
            evaluator_id: ID of the evaluator to use
            request: The user request/query
            response: The model's response to evaluate

        Returns:
            Evaluation result with score and justification
        """
        arguments = {
            "evaluator_id": evaluator_id,
            "request": request,
            "response": response,
        }

        return await self.call_tool("run_evaluation", arguments)

    # Alias for compatibility with renamed methods
    run_evaluation_by_id = run_evaluation

    async def run_evaluation_by_name(
        self, evaluator_name: str, request: str, response: str
    ) -> dict[str, Any]:
        """Run a standard evaluation using a RootSignals evaluator by name.

        Args:
            evaluator_name: Name of the evaluator to use
            request: The user request/query
            response: The model's response to evaluate

        Returns:
            Evaluation result with score and justification
        """
        arguments = {
            "evaluator_name": evaluator_name,
            "request": request,
            "response": response,
        }

        return await self.call_tool("run_evaluation_by_name", arguments)

    async def run_rag_evaluation(
        self, evaluator_id: str, request: str, response: str, contexts: list[str]
    ) -> dict[str, Any]:
        """Run a RAG evaluation with contexts using a RootSignals evaluator by ID.

        Args:
            evaluator_id: ID of the evaluator to use
            request: The user request/query
            response: The model's response to evaluate
            contexts: List of context passages used for generation

        Returns:
            Evaluation result with score and justification
        """
        arguments = {
            "evaluator_id": evaluator_id,
            "request": request,
            "response": response,
            "contexts": contexts,
        }

        return await self.call_tool("run_rag_evaluation", arguments)

    # Alias for compatibility with renamed methods
    run_rag_evaluation_by_id = run_rag_evaluation

    async def run_rag_evaluation_by_name(
        self, evaluator_name: str, request: str, response: str, contexts: list[str]
    ) -> dict[str, Any]:
        """Run a RAG evaluation with contexts using a RootSignals evaluator by name.

        Args:
            evaluator_name: Name of the evaluator to use
            request: The user request/query
            response: The model's response to evaluate
            contexts: List of context passages used for generation

        Returns:
            Evaluation result with score and justification
        """
        arguments = {
            "evaluator_name": evaluator_name,
            "request": request,
            "response": response,
            "contexts": contexts,
        }

        return await self.call_tool("run_rag_evaluation_by_name", arguments)

    async def run_coding_policy_adherence(
        self, policy_documents: list[str], code: str
    ) -> dict[str, Any]:
        """Run a coding policy adherence evaluation using a RootSignals evaluator.
        Args:
            policy_documents: List of policy documents, such as the contents of the cursor/rules file which describe the coding policy
            code: The code to evaluate

        Returns:
            Evaluation result with score and justifications
        """
        arguments = {
            "policy_documents": policy_documents,
            "code": code,
        }

        return await self.call_tool("run_coding_policy_adherence", arguments)
