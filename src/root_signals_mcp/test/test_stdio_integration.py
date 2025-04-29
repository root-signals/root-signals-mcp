"""Integration tests for the RootSignals MCP Server using stdio transport."""

import asyncio
import json
import logging
import os
import subprocess
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
async def test_subprocess_stdio_server():
    """Test the stdio server directly using a subprocess and basic JSON-RPC.

    This is a more direct test that validates the stdio server process works without
    using the MCP stdio client which might have its own issues.
    """
    # Ensure we have the API key in the environment for the subprocess
    env = os.environ.copy()
    env["ROOT_SIGNALS_API_KEY"] = settings.root_signals_api_key.get_secret_value()
    env["LOG_LEVEL"] = "debug"

    logger.info("Starting subprocess test for stdio server")

    # Start the stdio server in a subprocess
    process = subprocess.Popen(
        [sys.executable, "-m", "root_mcp_server.stdio_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,  # Use binary mode
        bufsize=0,  # No buffering
        env=env,
    )

    try:
        # Wait for the server to be ready by looking for the ready message in stderr
        while True:
            line = process.stderr.readline()
            if not line:
                pytest.fail("Server process exited unexpectedly")
                break
            if b"RootSignals MCP Server (stdio) ready" in line:
                logger.info("Subprocess stdio server ready")
                break

        # Let the server initialize completely
        await asyncio.sleep(0.5)

        # Send an initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"version": "0.1.0", "capabilities": {}},
        }

        # Write the request to stdin
        process.stdin.write(json.dumps(initialize_request).encode() + b"\n")
        process.stdin.flush()

        # Read the response
        response_line = process.stdout.readline()
        initialize_response = json.loads(response_line.decode())

        # Check that we got a valid response
        assert initialize_response["id"] == 1
        assert "result" in initialize_response
        assert "error" not in initialize_response

        logger.info("Initialization successful")

        # Send a request to list tools
        list_tools_request = {"jsonrpc": "2.0", "id": 2, "method": "listTools", "params": {}}

        # Write the request to stdin
        process.stdin.write(json.dumps(list_tools_request).encode() + b"\n")
        process.stdin.flush()

        # Read the response
        response_line = process.stdout.readline()
        list_tools_response = json.loads(response_line.decode())

        # Check that we got a valid response
        assert list_tools_response["id"] == 2
        assert "result" in list_tools_response
        assert "error" not in list_tools_response

        # Get tool names
        tool_names = {tool["name"] for tool in list_tools_response["result"]["tools"]}
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

    finally:
        # Cleanup process
        process.terminate()
        process.wait(timeout=5)


# Original client-based tests removed since we're now using
# direct core tests and subprocess tests instead


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
