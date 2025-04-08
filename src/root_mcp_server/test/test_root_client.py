"""Tests for the RootSignals HTTP client."""

import logging

import pytest

from root_mcp_server.root_api_client import (
    RootSignalsApiClient,
    RootSignalsAPIError,
)
from root_mcp_server.settings import settings

pytestmark = [
    pytest.mark.skipif(
        settings.root_signals_api_key.get_secret_value() == "",
        reason="ROOT_SIGNALS_API_KEY environment variable not set or empty",
    ),
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]

logger = logging.getLogger("root_mcp_server_tests")


def test_user_agent_header() -> None:
    """Test that the User-Agent header is properly set."""
    client = RootSignalsApiClient()

    # Check user agent is in headers
    assert "User-Agent" in client.headers, "User-Agent header is missing"

    user_agent = client.headers["User-Agent"]
    assert user_agent.startswith("root-signals-mcp/"), f"Unexpected User-Agent format: {user_agent}"

    # Extract version from user agent
    version = user_agent.split("/")[1]
    assert version, "Version part is missing in User-Agent"

    # Should match the version from settings
    assert version == settings.version, "Version in User-Agent does not match settings.version"

    logger.info(f"User-Agent header: {user_agent}")
    logger.info(f"Package version from settings: {settings.version}")


@pytest.mark.asyncio
async def test_list_evaluators() -> None:
    """Test listing evaluators from the API."""
    client = RootSignalsApiClient()

    evaluators = await client.list_evaluators()

    assert evaluators, "No evaluators returned"
    assert len(evaluators) > 0, "Empty evaluators list"

    # Check evaluator structure
    first_evaluator = evaluators[0]
    assert first_evaluator.id, "Evaluator missing ID"
    assert first_evaluator.name, "Evaluator missing name"
    assert first_evaluator.created_at, "Evaluator missing created_at"

    # Check boolean flags are actually booleans
    assert isinstance(first_evaluator.requires_contexts, bool), "requires_contexts is not a boolean"
    assert isinstance(first_evaluator.requires_expected_output, bool), (
        "requires_expected_output is not a boolean"
    )

    logger.info(f"Found {len(evaluators)} evaluators")
    logger.info(f"First evaluator: {first_evaluator.name} (ID: {first_evaluator.id})")


@pytest.mark.asyncio
async def test_run_evaluator() -> None:
    """Test running an evaluation with the API client."""
    client = RootSignalsApiClient()

    # First get an evaluator to test with
    evaluators = await client.list_evaluators()

    # Find a standard evaluator that doesn't require contexts
    standard_evaluator = next((e for e in evaluators if not e.requires_contexts), None)

    assert standard_evaluator, "No standard evaluator found"
    logger.info(f"Using evaluator: {standard_evaluator.name} (ID: {standard_evaluator.id})")

    # Run the evaluation
    result = await client.run_evaluator(
        evaluator_id=standard_evaluator.id,
        request="What is the capital of France?",
        response="The capital of France is Paris, which is known as the City of Light.",
    )

    assert result.evaluator_name, "Missing evaluator name in result"
    assert isinstance(result.score, float), "Score is not a float"
    assert 0 <= result.score <= 1, "Score outside expected range (0-1)"

    logger.info(f"Evaluation score: {result.score}")
    logger.info(f"Justification: {result.justification}")


@pytest.mark.asyncio
async def test_run_evaluator_with_contexts() -> None:
    """Test running a RAG evaluation with contexts."""
    client = RootSignalsApiClient()

    # First get an evaluator to test with
    evaluators = await client.list_evaluators()

    # Find an evaluator that supports contexts
    rag_evaluator = next((e for e in evaluators if e.requires_contexts), None)

    if not rag_evaluator:
        pytest.skip("No RAG evaluator found")

    logger.info(f"Using RAG evaluator: {rag_evaluator.name} (ID: {rag_evaluator.id})")

    # Run the evaluation with contexts
    result = await client.run_evaluator(
        evaluator_id=rag_evaluator.id,
        request="What is the capital of France?",
        response="The capital of France is Paris, which is known as the City of Light.",
        contexts=[
            "Paris is the capital and most populous city of France. It is located on the Seine River.",
            "France is a country in Western Europe with several overseas territories and regions.",
        ],
    )

    assert result.evaluator_name, "Missing evaluator name in result"
    assert isinstance(result.score, float), "Score is not a float"
    assert 0 <= result.score <= 1, "Score outside expected range (0-1)"

    logger.info(f"RAG evaluation score: {result.score}")
    logger.info(f"Justification: {result.justification}")


@pytest.mark.asyncio
async def test_evaluator_not_found() -> None:
    """Test error handling when evaluator is not found."""
    client = RootSignalsApiClient()

    with pytest.raises(RootSignalsAPIError) as excinfo:
        await client.run_evaluator(
            evaluator_id="nonexistent-evaluator-id",
            request="Test request",
            response="Test response",
        )

    assert excinfo.value.status_code == 404, "Expected 404 status code"
    logger.info(f"Got expected error: {excinfo.value}")
