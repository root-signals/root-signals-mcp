"""Tests for the MCP server."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from root_mcp_server.server import MCPServer


@pytest.fixture
def mock_mcp_server():
    """Mock the MCP Server class."""
    with patch("root_mcp_server.server.Server") as mock_server_class:
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Mock the list_tools and call_tool methods to return decorators
        mock_server.list_tools.return_value = lambda func: func
        mock_server.call_tool.return_value = lambda func: func
        
        yield mock_server


@pytest.fixture
def mock_evaluator_service():
    """Mock the evaluator service."""
    with patch("root_mcp_server.server.EvaluatorService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Create a proper mock for list_evaluators that returns a fully awaitable object
        mock_evaluators_response = MagicMock()
        mock_evaluators_response.model_dump.return_value = {
            "evaluators": [
                {
                    "id": "test-evaluator-1",
                    "name": "Test Evaluator 1",
                    "version_id": "v1",
                    "models": ["gpt-4"],
                    "intent": "test",
                    "requires_context": False,
                }
            ],
            "count": 1,
            "total": 1,
        }
        
        # Set up the mock to return the mock response when awaited
        mock_service.list_evaluators.return_value = mock_evaluators_response

        # Mock get_evaluator_by_id
        mock_service.get_evaluator_by_id.return_value = {
            "id": "test-evaluator-1",
            "name": "Test Evaluator 1",
            "version_id": "v1",
            "models": ["gpt-4"],
            "intent": "test",
            "requires_context": False,
        }

        # Mock run_evaluation
        mock_eval_response = MagicMock()
        mock_eval_response.model_dump.return_value = {
            "score": 0.85,
            "justification": "Test justification",
            "explanation": "Test explanation",
        }
        mock_service.run_evaluation.return_value = mock_eval_response

        # Mock run_rag_evaluation
        mock_rag_response = MagicMock()
        mock_rag_response.model_dump.return_value = {
            "score": 0.75,
            "justification": "RAG justification",
            "explanation": "RAG explanation",
        }
        mock_service.run_rag_evaluation.return_value = mock_rag_response

        yield mock_service


@pytest.mark.asyncio
async def test_handle_list_evaluators(mock_evaluator_service):
    """Test handling list_evaluators request."""
    server = MCPServer()

    # Call the tool directly
    response = await server.call_tool("list_evaluators", {})

    # Parse the response
    assert len(response) == 1
    assert isinstance(response[0], TextContent)
    result = json.loads(response[0].text)

    # Assertions
    assert "evaluators" in result
    assert result["count"] == 1
    assert result["total"] == 1
    assert result["evaluators"][0]["id"] == "test-evaluator-1"

    # Verify service was called
    mock_evaluator_service.list_evaluators.assert_called_once()


@pytest.mark.asyncio
async def test_handle_run_evaluation(mock_evaluator_service):
    """Test handling run_evaluation request."""
    server = MCPServer()

    # Call the tool directly
    params = {
        "evaluator_id": "test-evaluator-1",
        "query": "Test query",
        "response": "Test response",
    }
    response = await server.call_tool("run_evaluation", params)

    # Parse the response
    assert len(response) == 1
    assert isinstance(response[0], TextContent)
    result = json.loads(response[0].text)

    # Assertions
    assert result["score"] == 0.85
    assert result["justification"] == "Test justification"
    assert result["explanation"] == "Test explanation"

    # Verify service was called correctly
    mock_evaluator_service.get_evaluator_by_id.assert_called_once_with("test-evaluator-1")
    mock_evaluator_service.run_evaluation.assert_called_once()


@pytest.mark.asyncio
async def test_handle_run_rag_evaluation(mock_evaluator_service):
    """Test handling run_rag_evaluation request."""
    server = MCPServer()

    # Call the tool directly
    params = {
        "evaluator_id": "test-evaluator-1",
        "query": "Test query",
        "response": "Test response",
        "contexts": ["Context 1", "Context 2"],
    }
    response = await server.call_tool("run_rag_evaluation", params)

    # Parse the response
    assert len(response) == 1
    assert isinstance(response[0], TextContent)
    result = json.loads(response[0].text)

    # Assertions
    assert result["score"] == 0.75
    assert result["justification"] == "RAG justification"
    assert result["explanation"] == "RAG explanation"

    # Verify service was called correctly
    mock_evaluator_service.get_evaluator_by_id.assert_called_once_with("test-evaluator-1")
    mock_evaluator_service.run_rag_evaluation.assert_called_once()


@pytest.mark.asyncio
async def test_handle_unknown_function(mock_evaluator_service):
    """Test handling unknown function request."""
    server = MCPServer()

    # Call an unknown tool
    response = await server.call_tool("unknown_function", {})

    # Parse the response
    assert len(response) == 1
    assert isinstance(response[0], TextContent)
    result = json.loads(response[0].text)

    # Assertions
    assert "error" in result
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_list_tools(mock_evaluator_service):
    """Test listing available tools."""
    server = MCPServer()

    # Get tool definitions
    tools = await server.list_tools()

    # Assertions
    assert len(tools) == 3

    # Check tool names
    tool_names = [tool.name for tool in tools]
    assert "list_evaluators" in tool_names
    assert "run_evaluation" in tool_names
    assert "run_rag_evaluation" in tool_names

    # Check schemas
    for tool in tools:
        assert "inputSchema" in tool.model_dump()
        assert "properties" in tool.inputSchema


@pytest.mark.asyncio
async def test_mcp_server_initialization(mock_mcp_server, mock_evaluator_service):
    """Test MCP server initialization."""
    server = MCPServer()

    # Check tool handlers are registered
    mock_mcp_server.list_tools.assert_called_once()
    mock_mcp_server.call_tool.assert_called_once()

    # Test server initialization
    await server.initialize()
    mock_evaluator_service.initialize.assert_called_once()