"""Example of connecting to the RootSignals MCP Server using SSE transport.

This script demonstrates how to connect to the RootSignals MCP Server
when it's running with SSE transport, either locally or in Docker.
"""

import asyncio
import json
import sys
from typing import Any
from urllib.parse import urljoin, urlparse

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def list_evaluators(session: ClientSession) -> dict[str, Any]:
    """List all available evaluators using the MCP server.

    Args:
        session: The active MCP client session

    Returns:
        The parsed response from the server
    """
    print("Calling list_evaluators...")
    response = await session.call_tool("list_evaluators", {})

    # Extract content from the response
    text_content = next((item for item in response.content if item.type == "text"), None)
    if not text_content:
        raise ValueError("No text content in response")

    # Parse and return the JSON result
    result = json.loads(text_content.text)
    return result


async def run_example(server_url: str) -> None:
    """Run the example MCP client.

    Args:
        server_url: The URL of the SSE endpoint (base URL, not including /sse)
    """
    # Make sure we're connecting to the /sse endpoint
    parsed_url = urlparse(server_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    sse_url = urljoin(base_url, "/sse")

    print(f"Connecting to MCP server at {sse_url}...")

    # Connect to the server using SSE transport
    async with sse_client(sse_url) as transport:
        read_stream, write_stream = transport

        print("Creating client session...")
        # Create and initialize the client session
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session
            print("Initializing session...")
            await session.initialize()

            print("Session initialized successfully!")

            # List evaluators
            evaluators = await list_evaluators(session)

            # Print the results
            print("\nAvailable evaluators:")
            for evaluator in evaluators.get("evaluators", []):
                print(f"- {evaluator.get('name', 'Unknown')} ({evaluator.get('id', 'Unknown ID')})")

            print(f"\nTotal evaluators: {evaluators.get('count', 0)}")


if __name__ == "__main__":
    # Get server URL from command line or use default
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9090"

    # Run the example
    asyncio.run(run_example(server_url))
