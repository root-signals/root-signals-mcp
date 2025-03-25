"""Integration tests for the RootSignals MCP Server using SSE transport."""

import logging
import os

import pytest

from root_mcp_server.client import RootSignalsMCPClient

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("ROOT_SIGNALS_API_KEY") is None,
        reason="ROOT_SIGNALS_API_KEY environment variable not set",
    ),
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]

logger = logging.getLogger("root_mcp_server_tests")


@pytest.mark.asyncio
async def test_list_tools(compose_up_mcp_server):
    """Test listing tools via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        # List tools
        tools = await client.list_tools()

        # Verify expected tools are available
        tool_names = {tool["name"] for tool in tools}
        expected_tools = {"list_evaluators", "run_evaluation", "run_rag_evaluation"}

        assert expected_tools.issubset(tool_names), f"Missing expected tools. Found: {tool_names}"
        logger.info(f"Found expected tools: {tool_names}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_list_evaluators(compose_up_mcp_server):
    """Test listing evaluators via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        # List evaluators
        evaluators = await client.list_evaluators()

        # Verify evaluators are available
        assert len(evaluators) > 0, "No evaluators found"
        logger.info(f"Found {len(evaluators)} evaluators")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_run_evaluation(compose_up_mcp_server):
    """Test running a standard evaluation via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()
        evaluators = await client.list_evaluators()

        # Try to find Clarity evaluator first as it's a standard non-context evaluator
        # Then fall back to any non-context evaluator if Clarity isn't available
        clarity_evaluator = next(
            (e for e in evaluators if e.get("name", "") == "Clarity"),
            next((e for e in evaluators if not e.get("requires_contexts", False)), None),
        )

        if not clarity_evaluator:
            pytest.skip("No standard evaluator found")

        logger.info(f"Using evaluator: {clarity_evaluator['name']}")

        result = await client.run_evaluation(
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
async def test_run_rag_evaluation(compose_up_mcp_server):
    """Test running a RAG evaluation via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()
        evaluators = await client.list_evaluators()

        # Try to find Faithfulness evaluator first as it's a standard RAG evaluator
        # Then fall back to any context-requiring evaluator if Faithfulness isn't available
        faithfulness_evaluator = next(
            (e for e in evaluators if e.get("name", "") == "Faithfulness"),
            next((e for e in evaluators if e.get("requires_contexts", False)), None),
        )

        if not faithfulness_evaluator:
            pytest.skip("No RAG evaluator found")

        logger.info(f"Using evaluator: {faithfulness_evaluator['name']}")

        result = await client.run_rag_evaluation(
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
async def test_evaluator_service_integration(compose_up_mcp_server):
    """Test the entire evaluator service directly without going through client.

    This tests the internal service API rather than the HTTP/SSE interface.
    """
    from root_mcp_server.evaluator import EvaluatorService

    logger.info("Initializing EvaluatorService")
    service = EvaluatorService()

    try:
        await service.initialize()

        # Verify we can list evaluators
        evaluators_response = await service.list_evaluators()
        assert evaluators_response.count > 0, "No evaluators returned"
        assert len(evaluators_response.evaluators) > 0, "No evaluator objects returned"

        # Verify we can fetch an evaluator by ID
        first_evaluator = evaluators_response.evaluators[0]
        retrieved_evaluator = await service.get_evaluator_by_id(first_evaluator.id)
        assert retrieved_evaluator is not None, "Failed to retrieve evaluator by ID"
        assert retrieved_evaluator.id == first_evaluator.id, "Retrieved wrong evaluator"

        # Test standard evaluation if available
        if not getattr(first_evaluator, "requires_contexts", False):
            from root_mcp_server.schema import EvaluationRequest

            eval_request = EvaluationRequest(
                evaluator_id=first_evaluator.id,
                request="What is the capital of France?",
                response="The capital of France is Paris, which is known as the City of Light.",
            )

            eval_result = await service.run_evaluation(eval_request)
            assert hasattr(eval_result, "score"), "No score in evaluation response"
            logger.info(f"Evaluation result: score={eval_result.score}")

        # Test RAG evaluation if available
        rag_evaluator = next(
            (e for e in evaluators_response.evaluators if getattr(e, "requires_contexts", False)),
            None,
        )

        if rag_evaluator:
            from root_mcp_server.schema import RAGEvaluationRequest

            rag_request = RAGEvaluationRequest(
                evaluator_id=rag_evaluator.id,
                request="What is the capital of France?",
                response="The capital of France is Paris, which is known as the City of Light.",
                contexts=[
                    "Paris is the capital and most populous city of France.",
                    "France is a country in Western Europe.",
                ],
            )

            rag_result = await service.run_rag_evaluation(rag_request)
            assert hasattr(rag_result, "score"), "No score in RAG evaluation response"
            logger.info(f"RAG evaluation result: score={rag_result.score}")

    except Exception as e:
        logger.error(f"EvaluatorService integration test failed: {e}")
        raise
