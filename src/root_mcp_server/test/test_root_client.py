"""Tests for the RootSignals HTTP client."""

import logging
from unittest.mock import patch

import httpx
import pytest

from root_mcp_server.root_api_client import (
    ResponseValidationError,
    RootSignalsAPIError,
    RootSignalsEvaluatorRepository,
)
from root_mcp_server.schema import EvaluatorInfo
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


async def test_user_agent_header() -> None:
    """Test that the User-Agent header is properly set."""
    client = RootSignalsEvaluatorRepository()

    assert "User-Agent" in client.headers, "User-Agent header is missing"

    user_agent = client.headers["User-Agent"]
    assert user_agent.startswith("root-signals-mcp/"), f"Unexpected User-Agent format: {user_agent}"

    version = user_agent.split("/")[1]
    assert version, "Version part is missing in User-Agent"

    assert version == settings.version, "Version in User-Agent does not match settings.version"

    logger.info(f"User-Agent header: {user_agent}")
    logger.info(f"Package version from settings: {settings.version}")


@pytest.mark.asyncio
async def test_list_evaluators() -> None:
    """Test listing evaluators from the API."""
    client = RootSignalsEvaluatorRepository()

    evaluators = await client.list_evaluators()

    assert evaluators, "No evaluators returned"
    assert len(evaluators) > 0, "Empty evaluators list"

    first_evaluator = evaluators[0]
    assert first_evaluator.id, "Evaluator missing ID"
    assert first_evaluator.name, "Evaluator missing name"
    assert first_evaluator.created_at, "Evaluator missing created_at"

    assert isinstance(first_evaluator.requires_contexts, bool), "requires_contexts is not a boolean"
    assert isinstance(first_evaluator.requires_expected_output, bool), (
        "requires_expected_output is not a boolean"
    )

    logger.info(f"Found {len(evaluators)} evaluators")
    logger.info(f"First evaluator: {first_evaluator.name} (ID: {first_evaluator.id})")


@pytest.mark.asyncio
async def test_list_evaluators_with_count() -> None:
    """Test listing evaluators with a specific count limit."""
    client = RootSignalsEvaluatorRepository()

    max_count = 5
    evaluators = await client.list_evaluators(max_count=max_count)

    assert len(evaluators) <= max_count, f"Got more than {max_count} evaluators"
    logger.info(f"Retrieved {len(evaluators)} evaluators with max_count={max_count}")

    max_count_large = 30
    evaluators_large = await client.list_evaluators(max_count=max_count_large)

    assert len(evaluators_large) <= max_count_large, f"Got more than {max_count_large} evaluators"
    logger.info(f"Retrieved {len(evaluators_large)} evaluators with max_count={max_count_large}")

    if len(evaluators) == max_count:
        assert len(evaluators_large) > len(evaluators), (
            "Larger max_count didn't return more evaluators"
        )


@pytest.mark.asyncio
async def test_pagination_handling() -> None:
    """Test that pagination works correctly when more evaluators are available."""
    client = RootSignalsEvaluatorRepository()

    small_limit = 2
    evaluators = await client.list_evaluators(max_count=small_limit)

    assert len(evaluators) == small_limit, f"Expected exactly {small_limit} evaluators"
    assert isinstance(evaluators[0], EvaluatorInfo), "Result items are not EvaluatorInfo objects"


@pytest.mark.asyncio
async def test_run_evaluator() -> None:
    """Test running an evaluation with the API client."""
    client = RootSignalsEvaluatorRepository()

    evaluators = await client.list_evaluators()

    standard_evaluator = next((e for e in evaluators if not e.requires_contexts), None)

    assert standard_evaluator, "No standard evaluator found"
    logger.info(f"Using evaluator: {standard_evaluator.name} (ID: {standard_evaluator.id})")

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
    client = RootSignalsEvaluatorRepository()

    evaluators = await client.list_evaluators()

    rag_evaluator = next((e for e in evaluators if e.requires_contexts), None)

    if not rag_evaluator:
        pytest.skip("No RAG evaluator found")

    logger.info(f"Using RAG evaluator: {rag_evaluator.name} (ID: {rag_evaluator.id})")

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
    client = RootSignalsEvaluatorRepository()

    with pytest.raises(RootSignalsAPIError) as excinfo:
        await client.run_evaluator(
            evaluator_id="nonexistent-evaluator-id",
            request="Test request",
            response="Test response",
        )

    assert excinfo.value.status_code == 404, "Expected 404 status code"
    logger.info(f"Got expected error: {excinfo.value}")


@pytest.mark.asyncio
async def test_run_evaluator_with_expected_output() -> None:
    """Test running an evaluation with expected output."""
    client = RootSignalsEvaluatorRepository()

    evaluators = await client.list_evaluators()
    eval_with_expected = next(
        (e for e in evaluators if e.requires_expected_output), next((e for e in evaluators), None)
    )

    if not eval_with_expected:
        pytest.skip("No suitable evaluator found")

    try:
        result = await client.run_evaluator(
            evaluator_id=eval_with_expected.id,
            request="What is the capital of France?",
            response="The capital of France is Paris.",
            expected_output="Paris is the capital of France.",
        )

        assert result.evaluator_name, "Missing evaluator name in result"
        assert isinstance(result.score, float), "Score is not a float"
        logger.info(f"Evaluation with expected output - score: {result.score}")
    except RootSignalsAPIError as e:
        logger.warning(f"Could not run evaluator with expected output: {e}")
        assert e.status_code in (400, 422), f"Unexpected error code: {e.status_code}"


@pytest.mark.asyncio
async def test_run_evaluator_by_name() -> None:
    """Test running an evaluation using the evaluator name instead of ID."""
    client = RootSignalsEvaluatorRepository()

    evaluators = await client.list_evaluators()
    assert evaluators, "No evaluators returned"

    standard_evaluator = next((e for e in evaluators if not e.requires_contexts), None)
    if not standard_evaluator:
        pytest.skip("No standard evaluator found")

    logger.info(f"Using evaluator by name: {standard_evaluator.name}")

    result = await client.run_evaluator_by_name(
        evaluator_name=standard_evaluator.name,
        request="What is the capital of France?",
        response="The capital of France is Paris, which is known as the City of Light.",
    )

    assert result.evaluator_name, "Missing evaluator name in result"
    assert isinstance(result.score, float), "Score is not a float"
    assert 0 <= result.score <= 1, "Score outside expected range (0-1)"

    logger.info(f"Evaluation by name score: {result.score}")
    logger.info(f"Justification: {result.justification}")


@pytest.mark.asyncio
async def test_run_rag_evaluator_by_name() -> None:
    """Test running a RAG evaluation using the evaluator name instead of ID."""
    client = RootSignalsEvaluatorRepository()

    evaluators = await client.list_evaluators()
    rag_evaluator = next((e for e in evaluators if e.requires_contexts), None)

    if not rag_evaluator:
        pytest.skip("No RAG evaluator found")

    logger.info(f"Using RAG evaluator by name: {rag_evaluator.name}")

    result = await client.run_evaluator_by_name(
        evaluator_name=rag_evaluator.name,
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

    logger.info(f"RAG evaluation by name score: {result.score}")
    logger.info(f"Justification: {result.justification}")


@pytest.mark.asyncio
async def test_api_client_connection_error() -> None:
    """Test error handling when connection fails."""
    with patch("httpx.AsyncClient.request", side_effect=httpx.ConnectError("Connection failed")):
        client = RootSignalsEvaluatorRepository()
        with pytest.raises(RootSignalsAPIError) as excinfo:
            await client.list_evaluators()

        assert excinfo.value.status_code == 0, "Expected status code 0 for connection error"
        assert "Connection error" in str(excinfo.value), (
            "Error message should indicate connection error"
        )


@pytest.mark.asyncio
async def test_api_response_validation_error() -> None:
    """Test validation error handling with invalid responses."""
    with patch.object(RootSignalsEvaluatorRepository, "_make_request") as mock_request:
        client = RootSignalsEvaluatorRepository()

        # Case 1: Empty response when results field expected
        mock_request.return_value = {}
        with pytest.raises(ResponseValidationError) as excinfo:
            await client.list_evaluators()
        error_message = str(excinfo.value)
        assert "Could not find 'results' field" in error_message, (
            "Expected specific error about missing results field"
        )

        # Case 2: Wrong response type (string instead of dict/list)
        mock_request.return_value = "not a dict or list"
        with pytest.raises(ResponseValidationError) as excinfo:
            await client.list_evaluators()
        error_message = str(excinfo.value)
        assert "Expected response to be a dict or list" in error_message, (
            "Error should specify invalid response type"
        )
        assert "got str" in error_message.lower(), "Error should mention the actual type received"

        mock_request.return_value = "not a valid format"
        with pytest.raises(ResponseValidationError) as excinfo:
            await client.run_evaluator(
                evaluator_id="test-id", request="Test request", response="Test response"
            )
        error_message = str(excinfo.value)
        assert "Invalid evaluation response format" in error_message, (
            "Should indicate format validation error"
        )


@pytest.mark.asyncio
async def test_evaluator_missing_fields() -> None:
    """Test handling of evaluators with missing required fields."""
    with patch.object(RootSignalsEvaluatorRepository, "_make_request") as mock_request:
        client = RootSignalsEvaluatorRepository()

        mock_request.return_value = {
            "results": [
                {
                    "id": "valid-id",
                    "name": "Valid Evaluator",
                    "created_at": "2023-01-01T00:00:00Z",
                    "requires_contexts": False,
                    "requires_expected_output": False,
                },
                {
                    "created_at": "2023-01-01T00:00:00Z",
                    # Missing required fields: id, name
                },
            ]
        }

        with pytest.raises(ResponseValidationError) as excinfo:
            await client.list_evaluators()

        error_message = str(excinfo.value)
        assert "missing required field" in error_message.lower(), (
            "Error should mention missing required field"
        )
        assert "id" in error_message or "name" in error_message, (
            "Error should specify which field is missing"
        )

        mock_request.return_value = {
            "results": [
                {
                    "id": "valid-id",
                    "name": "Valid Evaluator",
                    "created_at": "2023-01-01T00:00:00Z",
                    "requires_contexts": False,
                    "requires_expected_output": False,
                }
            ]
        }

        evaluators = await client.list_evaluators()
        assert len(evaluators) == 1, "Should have one valid evaluator"
        assert evaluators[0].id == "valid-id", "Valid evaluator should be included"


@pytest.mark.asyncio
async def test_root_client_schema_compatibility__detects_api_schema_changes() -> None:
    """Test that our schema models detect changes in the API response format."""
    with patch.object(RootSignalsEvaluatorRepository, "_make_request") as mock_request:
        # Case 1: Missing required field (evaluator_name)
        mock_request.return_value = {
            "result": {
                "score": 0.9,
                "justification": "Some justification",
            }
        }

        client = RootSignalsEvaluatorRepository()
        with pytest.raises(ResponseValidationError) as excinfo:
            await client.run_evaluator(
                evaluator_id="test-id", request="Test request", response="Test response"
            )

        error_message = str(excinfo.value)
        assert "Invalid evaluation response format" in error_message, (
            "Should show validation error message"
        )
        # The exact error format will come from Pydantic now
        assert "evaluator_name" in error_message.lower(), "Should mention the missing field"

        # Case 2: Missing another required field (score)
        mock_request.return_value = {
            "result": {
                "evaluator_name": "Test Evaluator",
                "justification": "Some justification",
            }
        }

        with pytest.raises(ResponseValidationError) as excinfo:
            await client.run_evaluator(
                evaluator_id="test-id", request="Test request", response="Test response"
            )

        error_message = str(excinfo.value)
        assert "Invalid evaluation response format" in error_message, (
            "Should show validation error message"
        )
        assert "score" in error_message.lower(), "Should mention the missing field"

        # Case 3: Empty response
        mock_request.return_value = {}

        with pytest.raises(ResponseValidationError) as excinfo:
            await client.run_evaluator(
                evaluator_id="test-id", request="Test request", response="Test response"
            )

        assert "Invalid evaluation response format" in str(excinfo.value), (
            "Should show validation error for empty response"
        )


@pytest.mark.asyncio
async def test_root_client_run_evaluator__handles_unexpected_response_fields() -> None:
    """Test handling of extra fields in API response."""
    with patch.object(RootSignalsEvaluatorRepository, "_make_request") as mock_request:
        # Include extra fields that aren't in our schema
        mock_request.return_value = {
            "result": {
                "evaluator_name": "Test",
                "score": 0.9,
                "new_field_not_in_schema": "value",
                "another_new_field": {"nested": "data", "that": ["should", "be", "ignored"]},
            }
        }

        client = RootSignalsEvaluatorRepository()
        result = await client.run_evaluator(evaluator_id="test-id", request="Test", response="Test")

        assert result.evaluator_name == "Test", "Required field should be correctly parsed"
        assert result.score == 0.9, "Required field should be correctly parsed"

        # Extra fields should be ignored by Pydantic's model_validate
        assert not hasattr(result, "new_field_not_in_schema"), "Extra fields should be ignored"
        assert not hasattr(result, "another_new_field"), "Extra fields should be ignored"
