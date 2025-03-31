"""Integration tests for the SSEMCPServer module using a live server."""

import json
import logging
import os
from typing import Any

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
async def test_server_initialization(mcp_server: Any) -> None:
    """Test MCP server initialization."""
    assert mcp_server.evaluator_service is not None
    logger.info("MCP Server initialized successfully")


@pytest.mark.asyncio
async def test_list_tools(mcp_server: Any) -> None:
    """Test the list_tools method."""
    tools = await mcp_server.list_tools()
    assert len(tools) >= 3, f"Expected at least 3 tools, found {len(tools)}"

    tool_dict = {tool.name: tool for tool in tools}

    assert "list_evaluators" in tool_dict, "list_evaluators tool not found"
    assert "run_evaluation" in tool_dict, "run_evaluation tool not found"
    assert "run_rag_evaluation" in tool_dict, "run_rag_evaluation tool not found"

    for tool in tools:
        assert hasattr(tool, "name"), f"Tool missing name: {tool}"
        assert hasattr(tool, "description"), f"Tool missing description: {tool.name}"
        assert hasattr(tool, "inputSchema"), f"Tool missing inputSchema: {tool.name}"

    logger.info(f"Found {len(tools)} tools: {[tool.name for tool in tools]}")


@pytest.mark.asyncio
async def test_call_tool_list_evaluators__basic_api_response_includes_expected_fields(
    mcp_server: Any,
) -> None:
    """Test basic functionality of the list_evaluators tool."""
    result = await mcp_server.call_tool("list_evaluators", {})

    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    response_data = json.loads(result[0].text)
    assert "evaluators" in response_data, "Response missing evaluators list"
    assert len(response_data["evaluators"]) > 0, "No evaluators found"
    assert "count" in response_data, "Response missing count"
    assert "total" in response_data, "Response missing total"

    logger.info(f"Found {response_data['count']} evaluators")


@pytest.mark.asyncio
async def test_call_tool_list_evaluators__returns_newest_evaluators_first_by_default(
    mcp_server: Any,
) -> None:
    """Test that evaluators are sorted by created_at date in descending order (newest first)."""
    result = await mcp_server.call_tool("list_evaluators", {})
    response_data = json.loads(result[0].text)

    assert "evaluators" in response_data, "Response missing evaluators list"
    evaluators = response_data["evaluators"]

    assert len(evaluators) > 2, "API should return at least native evaluators, which is more than 2"

    for i in range(len(evaluators) - 1):
        current_date = evaluators[i].get("created_at", "")
        next_date = evaluators[i + 1].get("created_at", "")

        if not current_date or not next_date:
            continue

        assert current_date >= next_date, (
            f"Evaluators not sorted by created_at in descending order. "
            f"Found {current_date} before {next_date}"
        )

    logger.info("Verified evaluators are sorted with newest first")


@pytest.mark.asyncio
async def test_call_tool_run_evaluation(mcp_server: Any) -> None:
    """Test calling the run_evaluation tool."""
    list_result = await mcp_server.call_tool("list_evaluators", {})
    evaluators_data = json.loads(list_result[0].text)

    standard_evaluator = next(
        (e for e in evaluators_data["evaluators"] if e.get("name") == "Clarity"),
        next(
            (e for e in evaluators_data["evaluators"] if not e.get("requires_contexts", False)),
            None,
        ),
    )

    assert standard_evaluator is not None, "No standard evaluator found"

    logger.info(f"Using evaluator: {standard_evaluator['name']}")

    arguments = {
        "evaluator_id": standard_evaluator["id"],
        "request": "What is the capital of France?",
        "response": "The capital of France is Paris, which is known as the City of Light.",
    }

    result = await mcp_server.call_tool("run_evaluation", arguments)

    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    response_data = json.loads(result[0].text)
    assert "score" in response_data, "Response missing score"
    assert "justification" in response_data, "Response missing justification"

    logger.info(f"Evaluation completed with score: {response_data['score']}")


@pytest.mark.asyncio
async def test_call_tool_run_rag_evaluation(mcp_server: Any) -> None:
    """Test calling the run_rag_evaluation tool."""
    list_result = await mcp_server.call_tool("list_evaluators", {})
    evaluators_data = json.loads(list_result[0].text)

    rag_evaluator = next(
        (e for e in evaluators_data["evaluators"] if e.get("name") == "Faithfulness"),
        next(
            (e for e in evaluators_data["evaluators"] if e.get("requires_contexts") is True), None
        ),
    )

    assert rag_evaluator is not None, "No RAG evaluator found"

    logger.info(f"Using evaluator: {rag_evaluator['name']}")

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

    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    response_data = json.loads(result[0].text)
    assert "score" in response_data, "Response missing score"
    assert "justification" in response_data, "Response missing justification"

    logger.info(f"RAG evaluation completed with score: {response_data['score']}")


@pytest.mark.asyncio
async def test_call_unknown_tool(mcp_server: Any) -> None:
    """Test calling an unknown tool."""

    result = await mcp_server.call_tool("unknown_tool", {})

    assert len(result) == 1, "Expected single result content"
    assert result[0].type == "text", "Expected text content"

    response_data = json.loads(result[0].text)
    assert "error" in response_data, "Response missing error message"
    assert "Unknown tool" in response_data["error"], "Unexpected error message"

    logger.info("Unknown tool test passed with expected error")


@pytest.mark.asyncio
async def test_run_evaluation_validation_error(mcp_server: Any) -> None:
    """Test validation error in run_evaluation."""

    result = await mcp_server.call_tool("run_evaluation", {"evaluator_id": "some_id"})

    response_data = json.loads(result[0].text)
    assert "error" in response_data, "Response missing error message"

    logger.info(f"Validation error test passed with error: {response_data['error']}")


@pytest.mark.asyncio
async def test_run_rag_evaluation_missing_context(mcp_server: Any) -> None:
    """Test calling run_rag_evaluation with missing contexts."""

    list_result = await mcp_server.call_tool("list_evaluators", {})
    evaluators_data = json.loads(list_result[0].text)

    rag_evaluators = [
        e
        for e in evaluators_data["evaluators"]
        if any(
            kw in e.get("name", "").lower()
            for kw in ["faithfulness", "context", "rag", "relevance"]
        )
    ]

    rag_evaluator = next(iter(rag_evaluators), None)

    assert rag_evaluator is not None, "No RAG evaluator found"

    arguments = {
        "evaluator_id": rag_evaluator["id"],
        "request": "Test request",
        "response": "Test response",
        "contexts": [],
    }

    result = await mcp_server.call_tool("run_rag_evaluation", arguments)
    response_data = json.loads(result[0].text)

    if "error" in response_data:
        logger.info(f"Empty contexts test produced error as expected: {response_data['error']}")
    else:
        logger.info("Empty contexts were accepted by the evaluator")
