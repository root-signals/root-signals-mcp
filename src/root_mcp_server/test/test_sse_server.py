"""Integration tests for the SSEMCPServer module using a live server."""

import json
import logging
import os

import pytest

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
async def test_server_initialization(mcp_server):
    """Test MCP server initialization."""
    # Just verify the server initialized successfully
    assert mcp_server.evaluator_service is not None
    logger.info("MCP Server initialized successfully")


@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    """Test the list_tools method."""
    # List tools
    tools = await mcp_server.list_tools()

    # Verify tools list format
    assert len(tools) >= 3, f"Expected at least 3 tools, found {len(tools)}"

    # Convert tool objects to dict for easier inspection
    tool_dict = {tool.name: tool for tool in tools}

    # Check required tools are available
    assert "list_evaluators" in tool_dict, "list_evaluators tool not found"
    assert "run_evaluation" in tool_dict, "run_evaluation tool not found"
    assert "run_rag_evaluation" in tool_dict, "run_rag_evaluation tool not found"

    # Verify tool schema for each tool
    for tool in tools:
        assert hasattr(tool, "name"), f"Tool missing name: {tool}"
        assert hasattr(tool, "description"), f"Tool missing description: {tool.name}"
        assert hasattr(tool, "inputSchema"), f"Tool missing inputSchema: {tool.name}"

    logger.info(f"Found {len(tools)} tools: {[tool.name for tool in tools]}")


@pytest.mark.asyncio
async def test_call_tool_list_evaluators(mcp_server):
    """Test calling the list_evaluators tool."""
    # Call the tool
    result = await mcp_server.call_tool("list_evaluators", {})

    # Check response format
    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    # Parse the JSON response
    response_data = json.loads(result[0].text)
    assert "evaluators" in response_data, "Response missing evaluators list"
    assert len(response_data["evaluators"]) > 0, "No evaluators found"
    assert "count" in response_data, "Response missing count"
    assert "total" in response_data, "Response missing total"

    logger.info(f"Found {response_data['count']} evaluators")


@pytest.mark.asyncio
async def test_call_tool_run_evaluation(mcp_server):
    """Test calling the run_evaluation tool."""
    list_result = await mcp_server.call_tool("list_evaluators", {})
    evaluators_data = json.loads(list_result[0].text)

    # Try to find Clarity evaluator first, or any non-context requiring evaluator
    standard_evaluator = next(
        (e for e in evaluators_data["evaluators"] if e.get("name") == "Clarity"),
        next(
            (e for e in evaluators_data["evaluators"] if not e.get("requires_contexts", False)),
            None,
        ),
    )

    if not standard_evaluator:
        pytest.skip("No standard evaluator found")

    logger.info(f"Using evaluator: {standard_evaluator['name']}")

    arguments = {
        "evaluator_id": standard_evaluator["id"],
        "request": "What is the capital of France?",
        "response": "The capital of France is Paris, which is known as the City of Light.",
    }

    result = await mcp_server.call_tool("run_evaluation", arguments)

    # Check response format
    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    # Parse the JSON response
    response_data = json.loads(result[0].text)
    assert "score" in response_data, "Response missing score"
    assert "justification" in response_data, "Response missing justification"

    logger.info(f"Evaluation completed with score: {response_data['score']}")


@pytest.mark.asyncio
async def test_call_tool_run_rag_evaluation(mcp_server):
    """Test calling the run_rag_evaluation tool."""
    # Get evaluators first
    list_result = await mcp_server.call_tool("list_evaluators", {})
    evaluators_data = json.loads(list_result[0].text)

    # Try to find Faithfulness evaluator first (common RAG evaluator)
    rag_evaluator = next(
        (e for e in evaluators_data["evaluators"] if e.get("name") == "Faithfulness"),
        next(
            (e for e in evaluators_data["evaluators"] if e.get("requires_contexts") is True), None
        ),
    )

    if not rag_evaluator:
        pytest.skip("No RAG evaluator found")

    logger.info(f"Using evaluator: {rag_evaluator['name']}")

    # Call the tool with both request and reference contexts
    arguments = {
        "evaluator_id": rag_evaluator["id"],
        "request": "What is the capital of France?",
        "response": "The capital of France is Paris, which is known as the City of Light.",
        "contexts": [
            "Paris is the capital and most populous city of France. It is located on the Seine River.",
            "France is a country in Western Europe with several overseas territories and regions.",
        ],
    }

    result = await mcp_server.call_tool("run_rag_evaluation", arguments)

    # Check response format
    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    # Parse the JSON response
    response_data = json.loads(result[0].text)
    assert "score" in response_data, "Response missing score"
    assert "justification" in response_data, "Response missing justification"

    logger.info(f"RAG evaluation completed with score: {response_data['score']}")


@pytest.mark.asyncio
async def test_call_unknown_tool(mcp_server):
    """Test calling an unknown tool."""
    # Call an unknown tool
    result = await mcp_server.call_tool("unknown_tool", {})

    # Check response format
    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    # Parse the JSON response
    response_data = json.loads(result[0].text)
    assert "error" in response_data, "Response missing error message"
    assert "Unknown tool" in response_data["error"], "Unexpected error message"

    logger.info("Unknown tool test passed with expected error")


@pytest.mark.asyncio
async def test_run_evaluation_validation_error(mcp_server):
    """Test validation error in run_evaluation."""
    # Call run_evaluation with missing required parameters
    result = await mcp_server.call_tool("run_evaluation", {"evaluator_id": "some_id"})

    # Check response format
    response_data = json.loads(result[0].text)
    assert "error" in response_data, "Response missing error message"

    logger.info(f"Validation error test passed with error: {response_data['error']}")


@pytest.mark.asyncio
async def test_run_rag_evaluation_missing_context(mcp_server):
    """Test calling run_rag_evaluation with missing contexts."""
    # First get list of evaluators to find a suitable one for testing
    list_result = await mcp_server.call_tool("list_evaluators", {})
    evaluators_data = json.loads(list_result[0].text)

    # Find a RAG evaluator that requires contexts
    rag_evaluators = [
        e
        for e in evaluators_data["evaluators"]
        if any(
            kw in e.get("name", "").lower()
            for kw in ["faithfulness", "context", "rag", "relevance"]
        )
    ]

    rag_evaluator = next(iter(rag_evaluators), None)

    if not rag_evaluator:
        pytest.skip("No RAG evaluator found")

    # Call run_rag_evaluation with empty contexts
    arguments = {
        "evaluator_id": rag_evaluator["id"],
        "request": "Test request",
        "response": "Test response",
        "contexts": [],  # Empty contexts
    }

    result = await mcp_server.call_tool("run_rag_evaluation", arguments)

    # Parse the JSON response
    response_data = json.loads(result[0].text)

    # It may or may not fail depending on the specific evaluator requirements
    # So we just log the result rather than asserting
    if "error" in response_data:
        logger.info(f"Empty contexts test produced error as expected: {response_data['error']}")
    else:
        logger.info("Empty contexts were accepted by the evaluator")
