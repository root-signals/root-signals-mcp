"""Integration tests for the RootSignals MCP Server using SSE transport.

These tests verify the integration between the MCP client and server
using the SSE transport mechanism.
"""

import json
import os
import signal
import subprocess
import time
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# Skip tests if no API key is available
pytestmark = pytest.mark.skipif(
    os.environ.get("ROOT_SIGNALS_API_KEY") is None,
    reason="ROOT_SIGNALS_API_KEY environment variable not set",
)


@pytest_asyncio.fixture(scope="module")
async def sse_server_process():
    """Start an SSE server process for testing."""
    # Environment variables for the server process
    env = os.environ.copy()
    env["TRANSPORT"] = "sse"
    env["HOST"] = "127.0.0.1"  # Use localhost for tests
    env["PORT"] = "9999"  # Use a different port for tests

    # Start server as a subprocess - using sse_server directly
    server_process = subprocess.Popen(
        ["python", "-m", "src.root_mcp_server.sse_server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Allow time for server to start
    time.sleep(2)

    try:
        # Check if process is still running
        if server_process.poll() is not None:
            # Server failed to start
            stdout, stderr = server_process.communicate()
            raise RuntimeError(f"Server process failed to start: {stderr.decode('utf-8')}")

        # Server is running, yield it to the test
        yield server_process
    finally:
        # Ensure server is terminated
        if server_process.poll() is None:  # Process is still running
            server_process.terminate()
            server_process.wait(timeout=5)

            # If still running, force kill
            if server_process.poll() is None:
                if os.name == "nt":  # Windows
                    server_process.kill()
                else:  # Unix-like
                    os.kill(server_process.pid, signal.SIGKILL)


@pytest_asyncio.fixture(scope="function")
async def sse_client_session(sse_server_process) -> AsyncGenerator[ClientSession]:
    """Create an MCP client session using SSE transport.

    Args:
        sse_server_process: The running SSE server process

    Yields:
        An initialized MCP client session
    """
    # Connect to the SSE server
    server_url = "http://127.0.0.1:9999/sse"

    # Create client context manager
    async with sse_client(server_url) as sse_transport:
        read_stream, write_stream = sse_transport

        # Create and initialize the client session
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session
            await session.initialize()

            # Yield the session to the test
            yield session


@pytest.mark.asyncio
@pytest.mark.skip(reason="Proper integration test infrastructure not yet in place")
async def test_sse_list_evaluators(sse_client_session: ClientSession) -> None:
    """Test listing evaluators using SSE transport."""

    # Call the list_evaluators tool
    response = await sse_client_session.call_tool("list_evaluators", {})

    # Extract content and parse JSON
    text_content = next((item for item in response.content if item.type == "text"), None)
    assert text_content is not None

    # Parse the JSON response
    result = json.loads(text_content.text)

    # Assertions
    assert "evaluators" in result
    assert result["count"] > 0
