"""Integration tests for the RootSignals MCP Server using SSE transport."""

import logging
import os
from typing import Any

import pytest

from root_mcp_server.client import RootSignalsMCPClient
from root_mcp_server.evaluator import EvaluatorService
from root_mcp_server.schema import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluatorInfo,
    EvaluatorsListResponse,
    RAGEvaluationRequest,
)

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
async def test_list_tools(compose_up_mcp_server: Any) -> None:
    """Test listing tools via SSE transport."""
    logger.info("Connecting to MCP server")
    client: RootSignalsMCPClient = RootSignalsMCPClient()

    try:
        await client.connect()

        # List tools
        tools: list[dict[str, Any]] = await client.list_tools()

        # Verify expected tools are available
        tool_names: set[str] = {tool["name"] for tool in tools}
        expected_tools: set[str] = {"list_evaluators", "run_evaluation", "run_rag_evaluation"}

        assert expected_tools.issubset(tool_names), f"Missing expected tools. Found: {tool_names}"
        logger.info(f"Found expected tools: {tool_names}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_list_evaluators(compose_up_mcp_server: Any) -> None:
    """Test listing evaluators via SSE transport."""
    logger.info("Connecting to MCP server")
    client: RootSignalsMCPClient = RootSignalsMCPClient()

    try:
        await client.connect()

        # List evaluators
        evaluators: list[dict[str, Any]] = await client.list_evaluators()

        # Verify evaluators are available
        assert len(evaluators) > 0, "No evaluators found"
        logger.info(f"Found {len(evaluators)} evaluators")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_run_evaluation(compose_up_mcp_server: Any) -> None:
    """Test running a standard evaluation via SSE transport."""
    logger.info("Connecting to MCP server")
    client: RootSignalsMCPClient = RootSignalsMCPClient()

    try:
        await client.connect()
        evaluators: list[dict[str, Any]] = await client.list_evaluators()

        # Try to find Clarity evaluator first as it's a standard non-context evaluator
        # Then fall back to any non-context evaluator if Clarity isn't available
        clarity_evaluator: dict[str, Any] | None = next(
            (e for e in evaluators if e.get("name", "") == "Clarity"),
            next((e for e in evaluators if not e.get("requires_contexts", False)), None),
        )

        if not clarity_evaluator:
            pytest.skip("No standard evaluator found")

        logger.info(f"Using evaluator: {clarity_evaluator['name']}")

        result: dict[str, Any] = await client.run_evaluation(
            evaluator_id=clarity_evaluator["id"],
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
        )

        assert "score" in result, "No score in evaluation result"
        assert "justification" in result, "No justification in evaluation result"
        logger.info(f"Evaluation completed with score: {result['score']}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_run_rag_evaluation(compose_up_mcp_server: Any) -> None:
    """Test running a RAG evaluation via SSE transport."""
    logger.info("Connecting to MCP server")
    client: RootSignalsMCPClient = RootSignalsMCPClient()

    try:
        await client.connect()
        evaluators: list[dict[str, Any]] = await client.list_evaluators()

        # Try to find Faithfulness evaluator first as it's a standard RAG evaluator
        # Then fall back to any context-requiring evaluator if Faithfulness isn't available
        faithfulness_evaluator: dict[str, Any] | None = next(
            (e for e in evaluators if e.get("name", "") == "Faithfulness"),
            next((e for e in evaluators if e.get("requires_contexts", False)), None),
        )

        assert faithfulness_evaluator is not None, "No RAG evaluator found"

        logger.info(f"Using evaluator: {faithfulness_evaluator['name']}")

        result: dict[str, Any] = await client.run_rag_evaluation(
            evaluator_id=faithfulness_evaluator["id"],
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
            contexts=[
                "Paris is the capital and most populous city of France. It is located on the Seine River.",
                "France is a country in Western Europe with several overseas territories and regions.",
            ],
        )

        assert "score" in result, "No score in RAG evaluation result"
        assert "justification" in result, "No justification in RAG evaluation result"
        logger.info(f"RAG evaluation completed with score: {result['score']}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_evaluator_service_integration__standard_evaluation(
    compose_up_mcp_server: Any,
) -> None:
    """Test the standard evaluation functionality directly through the evaluator service.

    This tests the internal service API rather than the HTTP/SSE interface.
    """
    logger.info("Initializing EvaluatorService")
    service: EvaluatorService = EvaluatorService()

    try:
        await service.initialize()

        evaluators_response: EvaluatorsListResponse = await service.list_evaluators()
        assert evaluators_response.count > 0, "No evaluators returned"
        assert len(evaluators_response.evaluators) > 0, "No evaluator objects returned"

        # Find a standard evaluator (one that doesn't require contexts)
        standard_evaluator: EvaluatorInfo | None = next(
            (
                e
                for e in evaluators_response.evaluators
                if not getattr(e, "requires_contexts", False)
            ),
            None,
        )

        assert standard_evaluator is not None, "No standard evaluator found"

        logger.info(f"Using standard evaluator: {standard_evaluator.name}")

        retrieved_evaluator: EvaluatorInfo | None = await service.get_evaluator_by_id(
            standard_evaluator.id
        )
        assert retrieved_evaluator is not None, "Failed to retrieve evaluator by ID"
        assert retrieved_evaluator.id == standard_evaluator.id, "Retrieved wrong evaluator"

        # Run a standard evaluation
        eval_request: EvaluationRequest = EvaluationRequest(
            evaluator_id=standard_evaluator.id,
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
        )

        eval_result: EvaluationResponse = await service.run_evaluation(eval_request)
        assert hasattr(eval_result, "score"), "No score in evaluation response"
        logger.info(f"Standard evaluation result: score={eval_result.score}")

    except Exception as e:
        logger.error(f"Standard evaluation test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_evaluator_service_integration__rag_evaluation(compose_up_mcp_server: Any) -> None:
    """Test the RAG evaluation functionality directly through the evaluator service.

    This tests the internal service API rather than the HTTP/SSE interface.
    """
    logger.info("Initializing EvaluatorService")
    service: EvaluatorService = EvaluatorService()

    try:
        await service.initialize()

        evaluators_response: EvaluatorsListResponse = await service.list_evaluators()
        assert evaluators_response.count > 0, "No evaluators returned"
        assert len(evaluators_response.evaluators) > 0, "No evaluator objects returned"

        # Find a RAG evaluator (one that requires contexts)
        rag_evaluator: EvaluatorInfo | None = next(
            (e for e in evaluators_response.evaluators if getattr(e, "requires_contexts", False)),
            None,
        )

        assert rag_evaluator is not None, "No RAG evaluator found"

        logger.info(f"Using RAG evaluator: {rag_evaluator.name}")

        retrieved_evaluator: EvaluatorInfo | None = await service.get_evaluator_by_id(
            rag_evaluator.id
        )
        assert retrieved_evaluator is not None, "Failed to retrieve evaluator by ID"
        assert retrieved_evaluator.id == rag_evaluator.id, "Retrieved wrong evaluator"

        rag_request: RAGEvaluationRequest = RAGEvaluationRequest(
            evaluator_id=rag_evaluator.id,
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
            contexts=[
                "Paris is the capital and most populous city of France.",
                "France is a country in Western Europe.",
            ],
        )

        rag_result: EvaluationResponse = await service.run_rag_evaluation(rag_request)
        assert hasattr(rag_result, "score"), "No score in RAG evaluation response"
        logger.info(f"RAG evaluation result: score={rag_result.score}")

    except Exception as e:
        logger.error(f"RAG evaluation test failed: {e}")
        raise
