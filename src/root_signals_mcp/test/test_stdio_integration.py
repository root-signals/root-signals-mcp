"""Integration tests for the RootSignals MCP Server using stdio transport."""

import json
import logging
import os
import sys
from pathlib import Path

import pytest

from root_signals_mcp.settings import settings

pytestmark = [
    pytest.mark.skipif(
        settings.root_signals_api_key.get_secret_value() == "",
        reason="ROOT_SIGNALS_API_KEY environment variable not set or empty",
    ),
    pytest.mark.integration,
    pytest.mark.asyncio,
]

logger = logging.getLogger("root_mcp_server_tests")
PROJECT_ROOT = Path(__file__).parents[4]


@pytest.mark.asyncio
async def test_direct_core_list_tools() -> None:
    """Test listing tools directly from the RootMCPServerCore."""
    from root_signals_mcp.core import RootMCPServerCore

    logger.info("Testing direct core tool listing")
    core = RootMCPServerCore()

    # Get the tools
    tools = await core.list_tools()

    # Verify the expected tools are included
    tool_names = {tool.name for tool in tools}
    expected_tools = {
        "list_evaluators",
        "run_evaluation",
        "run_evaluation_by_name",
        "run_rag_evaluation",
        "run_rag_evaluation_by_name",
        "run_coding_policy_adherence",
    }

    assert expected_tools.issubset(tool_names), f"Missing expected tools. Found: {tool_names}"
    logger.info(f"Found expected tools: {tool_names}")


@pytest.mark.asyncio
async def test_direct_core_list_evaluators() -> None:
    """Test calling the list_evaluators tool directly from the RootMCPServerCore."""
    from root_signals_mcp.core import RootMCPServerCore

    logger.info("Testing direct core list_evaluators")
    core = RootMCPServerCore()

    # Call the list_evaluators tool - note: the schema doesn't accept parameters
    result = await core.call_tool("list_evaluators", {})

    # Extract text content from result
    assert len(result) > 0, "No content in response"
    text_content = result[0]
    assert text_content.type == "text", "Response is not text type"

    # Parse the JSON response
    evaluators_response = json.loads(text_content.text)

    # Check the response structure
    assert "evaluators" in evaluators_response, "No evaluators in response"
    evaluators = evaluators_response["evaluators"]
    assert len(evaluators) > 0, "No evaluators found"

    # Verify evaluator format
    evaluator = evaluators[0]
    assert "id" in evaluator, "Evaluator missing ID"
    assert "name" in evaluator, "Evaluator missing name"

    logger.info(f"Found {len(evaluators)} evaluators")


@pytest.mark.asyncio
async def test_stdio_client_list_tools() -> None:
    """Use the upstream MCP stdio client to talk to our stdio server and list tools.

    This replaces the previous hand-rolled subprocess test with an end-to-end
    check that exercises the *actual* MCP handshake and client-side logic.
    """

    try:
        from mcp import client as _  # type: ignore  # noqa: F401 – ensure SDK present
        from mcp.client.session import ClientSession  # type: ignore
        from mcp.client.stdio import StdioServerParameters, stdio_client  # type: ignore
    except ModuleNotFoundError:
        pytest.skip("The 'mcp' Python SDK is not installed in the current environment")

    # Prepare environment and server launch parameters.
    server_env = os.environ.copy()
    server_env["ROOT_SIGNALS_API_KEY"] = settings.root_signals_api_key.get_secret_value()

    server_params = StdioServerParameters(  # type: ignore[call-arg]
        command=sys.executable,
        args=["-m", "root_signals_mcp.stdio_server"],
        env=server_env,
    )

    # Connect to the server using the stdio transport provided by the MCP SDK.
    async with stdio_client(server_params) as (read_stream, write_stream):  # type: ignore[attr-defined]
        async with ClientSession(read_stream, write_stream) as session:  # type: ignore
            await session.initialize()

            tools_response = await session.list_tools()
            tool_names = {tool.name for tool in tools_response.tools}

            expected_tools = {
                "list_evaluators",
                "run_evaluation",
                "run_evaluation_by_name",
                "run_rag_evaluation",
                "run_rag_evaluation_by_name",
                "run_coding_policy_adherence",
            }

            missing = expected_tools - tool_names
            assert not missing, f"Missing expected tools: {missing}"
            logger.info("stdio-client -> list_tools OK: %s", tool_names)
