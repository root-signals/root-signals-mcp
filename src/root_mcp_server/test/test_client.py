"""Integration tests for the RootSignals MCP Client."""

import logging
import os
from typing import Any

import pytest

from root_mcp_server.client import RootSignalsMCPClient

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("ROOT_SIGNALS_API_KEY", "") == "",
        reason="ROOT_SIGNALS_API_KEY environment variable not set or empty",
    ),
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]

logger = logging.getLogger("root_mcp_server_tests")


@pytest.mark.asyncio
async def test_client_connection(compose_up_mcp_server: Any) -> None:
    """Test client connection and disconnection with a real server."""
    logger.info("Testing client connection")
    client = RootSignalsMCPClient()

    try:
        await client.connect()
        assert client.connected is True
        assert client.session is not None

        await client._ensure_connected()
        logger.info("Successfully connected to the MCP server")
    finally:
        await client.disconnect()
        assert client.session is None
        assert client.connected is False
        logger.info("Successfully disconnected from the MCP server")


@pytest.mark.asyncio
async def test_client_list_tools(compose_up_mcp_server: Any) -> None:
    """Test client list_tools method with a real server."""
    logger.info("Testing list_tools")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        tools = await client.list_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            # The schema key could be either inputSchema or input_schema depending on the MCP version
            assert "inputSchema" in tool or "input_schema" in tool, (
                f"Missing schema in tool: {tool}"
            )

        tool_names = [tool["name"] for tool in tools]
        logger.info(f"Found tools: {tool_names}")

        expected_tools = {"list_evaluators", "run_evaluation", "run_rag_evaluation"}
        assert expected_tools.issubset(set(tool_names)), (
            f"Missing expected tools. Found: {tool_names}"
        )
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_client_list_evaluators(compose_up_mcp_server: Any) -> None:
    """Test client list_evaluators method with a real server."""
    logger.info("Testing list_evaluators")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        evaluators = await client.list_evaluators()

        assert isinstance(evaluators, list)
        assert len(evaluators) > 0

        first_evaluator = evaluators[0]
        assert "id" in first_evaluator
        assert "name" in first_evaluator

        logger.info(f"Found {len(evaluators)} evaluators")
        logger.info(f"First evaluator: {first_evaluator['name']}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_client_run_evaluation(compose_up_mcp_server: Any) -> None:
    """Test client run_evaluation method with a real server."""
    logger.info("Testing run_evaluation")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        evaluators = await client.list_evaluators()

        standard_evaluator = next(
            (e for e in evaluators if not e.get("requires_contexts", False)), None
        )

        assert standard_evaluator is not None, "No standard evaluator found"

        logger.info(f"Using evaluator: {standard_evaluator['name']}")

        result = await client.run_evaluation(
            evaluator_id=standard_evaluator["id"],
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
        )

        assert "score" in result
        assert "justification" in result
        logger.info(f"Evaluation score: {result['score']}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_client_run_rag_evaluation(compose_up_mcp_server: Any) -> None:
    """Test client run_rag_evaluation method with a real server."""
    logger.info("Testing run_rag_evaluation")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        evaluators = await client.list_evaluators()

        faithfulness_evaluators = [
            e
            for e in evaluators
            if any(
                kw in e.get("name", "").lower()
                for kw in ["faithfulness", "context", "rag", "relevance"]
            )
        ]

        rag_evaluator = next(iter(faithfulness_evaluators), None)

        if not rag_evaluator:
            pytest.skip("No RAG evaluator found")

        logger.info(f"Using evaluator: {rag_evaluator['name']}")

        result = await client.run_rag_evaluation(
            evaluator_id=rag_evaluator["id"],
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
            contexts=[
                "Paris is the capital and most populous city of France. It is located on the Seine River.",
                "France is a country in Western Europe with several overseas territories and regions.",
            ],
        )

        assert "score" in result
        assert "justification" in result
        logger.info(f"RAG evaluation score: {result['score']}")
    finally:
        await client.disconnect()
