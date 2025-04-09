"""Unit tests for the EvaluatorService module."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from root_mcp_server.evaluator import EvaluatorService
from root_mcp_server.root_api_client import ResponseValidationError, RootSignalsAPIError
from root_mcp_server.schema import (
    EvaluationRequestByID,
    EvaluationRequestByName,
    EvaluationResponse,
    EvaluatorInfo,
    RAGEvaluationByNameRequest,
    RAGEvaluationRequest,
)

logger = logging.getLogger("test_evaluator")


@pytest.fixture
def mock_api_client() -> MagicMock:
    """Create a mock API client for testing."""
    with patch("root_mcp_server.evaluator.RootSignalsApiClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_evaluators = AsyncMock()
        mock_client.run_evaluator = AsyncMock()
        mock_client.run_evaluator_by_name = AsyncMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_fetch_evaluators_passes_max_count(mock_api_client: MagicMock) -> None:
    """Test that max_count is passed correctly to the API client."""
    service = EvaluatorService()
    await service.fetch_evaluators(max_count=75)
    mock_api_client.list_evaluators.assert_called_once_with(75)


@pytest.mark.asyncio
async def test_fetch_evaluators_uses_default_when_max_count_is_none(
    mock_api_client: MagicMock,
) -> None:
    """Test that default max_count is used when not specified."""
    service = EvaluatorService()
    await service.fetch_evaluators()
    mock_api_client.list_evaluators.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_fetch_evaluators_handles_api_error(mock_api_client: MagicMock) -> None:
    """Test handling of RootSignalsAPIError in fetch_evaluators."""
    service = EvaluatorService()
    mock_api_client.list_evaluators.side_effect = RootSignalsAPIError(
        status_code=500, detail="Internal server error"
    )

    with pytest.raises(RuntimeError) as excinfo:
        await service.fetch_evaluators()

    assert "Cannot fetch evaluators" in str(excinfo.value)
    assert "Internal server error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_fetch_evaluators_handles_validation_error(mock_api_client: MagicMock) -> None:
    """Test handling of ResponseValidationError in fetch_evaluators."""
    service = EvaluatorService()
    mock_api_client.list_evaluators.side_effect = ResponseValidationError(
        "Missing required field: 'id'", {"name": "Test"}
    )

    with pytest.raises(RuntimeError) as excinfo:
        await service.fetch_evaluators()

    assert "Invalid evaluators response" in str(excinfo.value)
    assert "Missing required field" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_evaluator_by_id_returns_correct_evaluator(mock_api_client: MagicMock) -> None:
    """Test that get_evaluator_by_id returns the correct evaluator when found."""
    service = EvaluatorService()
    mock_evaluators = [
        EvaluatorInfo(
            id="eval-1",
            name="Evaluator 1",
            created_at="2024-01-01T00:00:00Z",
            intent=None,
            requires_contexts=False,
            requires_expected_output=False,
        ),
        EvaluatorInfo(
            id="eval-2",
            name="Evaluator 2",
            created_at="2024-01-02T00:00:00Z",
            intent=None,
            requires_contexts=True,
            requires_expected_output=False,
        ),
    ]
    mock_api_client.list_evaluators.return_value = mock_evaluators

    evaluator = await service.get_evaluator_by_id("eval-2")

    assert evaluator is not None
    assert evaluator.id == "eval-2"
    assert evaluator.name == "Evaluator 2"


@pytest.mark.asyncio
async def test_get_evaluator_by_id_returns_none_when_not_found(mock_api_client: MagicMock) -> None:
    """Test that get_evaluator_by_id returns None when the evaluator is not found."""
    service = EvaluatorService()
    mock_evaluators = [
        EvaluatorInfo(
            id="eval-1",
            name="Evaluator 1",
            created_at="2024-01-01T00:00:00Z",
            intent=None,
            requires_contexts=False,
            requires_expected_output=False,
        ),
        EvaluatorInfo(
            id="eval-2",
            name="Evaluator 2",
            created_at="2024-01-02T00:00:00Z",
            intent=None,
            requires_contexts=True,
            requires_expected_output=False,
        ),
    ]
    mock_api_client.list_evaluators.return_value = mock_evaluators

    evaluator = await service.get_evaluator_by_id("eval-3")

    assert evaluator is None


@pytest.mark.asyncio
async def test_run_evaluation_passes_correct_parameters(mock_api_client: MagicMock) -> None:
    """Test that parameters are passed correctly to the API client in run_evaluation."""
    service = EvaluatorService()
    mock_response = EvaluationResponse(
        evaluator_name="Test Evaluator",
        score=0.95,
        justification="This is a justification",
        execution_log_id=None,
        cost=None,
    )
    mock_api_client.run_evaluator.return_value = mock_response

    request = EvaluationRequestByID(
        evaluator_id="eval-123", request="Test request", response="Test response"
    )

    result = await service.run_evaluation(request)

    mock_api_client.run_evaluator.assert_called_once_with(
        evaluator_id="eval-123", request="Test request", response="Test response"
    )

    assert result.evaluator_name == "Test Evaluator"
    assert result.score == 0.95
    assert result.justification == "This is a justification"


@pytest.mark.asyncio
async def test_run_evaluation_by_name_passes_correct_parameters(mock_api_client: MagicMock) -> None:
    """Test that parameters are passed correctly to the API client in run_evaluation_by_name."""
    service = EvaluatorService()
    mock_response = EvaluationResponse(
        evaluator_name="Test Evaluator",
        score=0.95,
        justification="This is a justification",
        execution_log_id=None,
        cost=None,
    )
    mock_api_client.run_evaluator_by_name.return_value = mock_response

    request = EvaluationRequestByName(
        evaluator_name="Clarity", request="Test request", response="Test response"
    )

    result = await service.run_evaluation_by_name(request)

    mock_api_client.run_evaluator_by_name.assert_called_once_with(
        evaluator_name="Clarity", request="Test request", response="Test response"
    )

    assert result.evaluator_name == "Test Evaluator"
    assert result.score == 0.95
    assert result.justification == "This is a justification"


@pytest.mark.asyncio
async def test_run_rag_evaluation_with_contexts(mock_api_client: MagicMock) -> None:
    """Test that contexts are passed correctly in run_rag_evaluation."""
    service = EvaluatorService()
    mock_response = EvaluationResponse(
        evaluator_name="RAG Evaluator",
        score=0.85,
        justification="RAG evaluation result",
        execution_log_id=None,
        cost=None,
    )
    mock_api_client.run_evaluator.return_value = mock_response

    contexts = ["Context 1", "Context 2"]
    request = RAGEvaluationRequest(
        evaluator_id="eval-rag-123",
        request="Test RAG request",
        response="Test RAG response",
        contexts=contexts,
    )

    result = await service.run_rag_evaluation(request)

    mock_api_client.run_evaluator.assert_called_once_with(
        evaluator_id="eval-rag-123",
        request="Test RAG request",
        response="Test RAG response",
        contexts=contexts,
    )

    assert result.evaluator_name == "RAG Evaluator"
    assert result.score == 0.85
    assert result.justification == "RAG evaluation result"


@pytest.mark.asyncio
async def test_run_evaluation_handles_not_found_error(mock_api_client: MagicMock) -> None:
    """Test handling of 404 errors in run_evaluation."""
    service = EvaluatorService()
    mock_api_client.run_evaluator.side_effect = RootSignalsAPIError(
        status_code=404, detail="Evaluator not found"
    )

    request = EvaluationRequestByID(
        evaluator_id="nonexistent-id", request="Test request", response="Test response"
    )

    with pytest.raises(RuntimeError) as excinfo:
        await service.run_evaluation(request)

    assert "Failed to run evaluation" in str(excinfo.value)
    assert "Evaluator not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_run_rag_evaluation_by_name_with_contexts(mock_api_client: MagicMock) -> None:
    """Test that contexts are passed correctly in run_rag_evaluation_by_name."""
    service = EvaluatorService()
    mock_response = EvaluationResponse(
        evaluator_name="RAG Evaluator",
        score=0.85,
        justification="RAG evaluation result",
        execution_log_id=None,
        cost=None,
    )
    mock_api_client.run_evaluator_by_name.return_value = mock_response

    contexts = ["Context 1", "Context 2"]
    request = RAGEvaluationByNameRequest(
        evaluator_name="Faithfulness",
        request="Test RAG request",
        response="Test RAG response",
        contexts=contexts,
    )

    result = await service.run_rag_evaluation_by_name(request)

    mock_api_client.run_evaluator_by_name.assert_called_once_with(
        evaluator_name="Faithfulness",
        request="Test RAG request",
        response="Test RAG response",
        contexts=contexts,
    )

    assert result.evaluator_name == "RAG Evaluator"
    assert result.score == 0.85
    assert result.justification == "RAG evaluation result"


@pytest.mark.asyncio
async def test_transient_error_not_retried(mock_api_client: MagicMock) -> None:
    """Test that transient errors are not retried by default."""
    service = EvaluatorService()
    mock_api_client.run_evaluator.side_effect = RootSignalsAPIError(
        status_code=500, detail="Internal server error - may be transient"
    )

    request = EvaluationRequestByID(
        evaluator_id="eval-123", request="Test request", response="Test response"
    )

    with pytest.raises(RuntimeError):
        await service.run_evaluation(request)

    assert mock_api_client.run_evaluator.call_count == 1
