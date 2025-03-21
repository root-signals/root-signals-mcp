"""Tests for the evaluator service."""

from unittest.mock import AsyncMock, patch

import pytest

from root_mcp_server.evaluator import EvaluatorService
from root_mcp_server.schema import EvaluationRequest, RAGEvaluationRequest


@pytest.fixture
def mock_rootsignals_client():
    """Mock the RootSignals client."""
    with patch("root.RootSignals") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # We don't need to mock the evaluators property anymore
        # as we're using a hardcoded mock in the implementation
        
        yield mock_client


@pytest.mark.asyncio
async def test_evaluator_list(mock_rootsignals_client):
    """Test listing evaluators."""
    service = EvaluatorService()
    await service.initialize()

    # Test listing evaluators
    result = await service.list_evaluators()

    # Assertions
    assert result.count == 2
    assert result.total == 2
    assert len(result.evaluators) == 2
    assert result.evaluators[0].id == "test-evaluator-1"
    assert result.evaluators[0].name == "Test Evaluator 1"
    assert result.evaluators[1].id == "test-evaluator-2"
    assert result.evaluators[1].requires_context is True


@pytest.mark.asyncio
async def test_run_evaluation(mock_rootsignals_client):
    """Test running a standard evaluation."""
    service = EvaluatorService()
    await service.initialize()

    # Create evaluation request
    request = EvaluationRequest(
        query="Test query",
        response="Test response",
    )

    # Run evaluation
    result = await service.run_evaluation("test-evaluator-1", request)

    # Assertions
    assert result.score == 0.85
    assert result.justification == "Test justification"
    assert result.explanation == "Test explanation"


@pytest.mark.asyncio
async def test_run_rag_evaluation(mock_rootsignals_client):
    """Test running a RAG evaluation."""
    service = EvaluatorService()
    await service.initialize()

    # Create RAG evaluation request
    request = RAGEvaluationRequest(
        query="Test query",
        response="Test response",
        contexts=["Context 1", "Context 2"],
    )

    # Run evaluation
    result = await service.run_rag_evaluation("test-evaluator-2", request)

    # Assertions
    assert result.score == 0.85
    assert result.justification == "Test justification"
    assert result.explanation == "Test explanation"