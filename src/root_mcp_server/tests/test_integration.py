"""Integration tests for the RootSignals MCP Server.

These tests verify the integration between the MCP server and real RootSignals API.
"""

import asyncio
import json
import os
import subprocess
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import TextContent, Tool

# Skip tests if no API key is available
pytestmark = pytest.mark.skipif(
    os.environ.get("ROOT_SIGNALS_API_KEY") is None,
    reason="ROOT_SIGNALS_API_KEY environment variable not set",
)


@pytest_asyncio.fixture(scope="function")
async def mcp_client() -> AsyncGenerator[ClientSession, None]:
    """Create and initialize an MCP client for testing.
    
    This fixture manages the full lifecycle of both the server subprocess
    and the client connection.
    """
    # Set up environment
    env = os.environ.copy()
    
    # Define parameters for the server process
    server_params = StdioServerParameters(
        command="python",
        args=["main.py"],
        env=env,
    )
    
    # Create client context manager
    async with stdio_client(server_params) as stdio_transport:
        read_stream, write_stream = stdio_transport
        
        # Create and initialize the client session
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session (establish connection with server)
            await session.initialize()
            
            # Yield the session to the test
            yield session


@pytest.mark.asyncio
@pytest.mark.skip(reason="Proper integration test infrastructure not yet in place")
async def test_list_evaluators_integration(mcp_client: ClientSession) -> None:
    """Test listing evaluators integration."""
    
    # Call the list_evaluators tool
    response = await mcp_client.call_tool("list_evaluators", {})
    
    # Response from the call_tool method is a CallToolResult object, not a dict
    # We need to extract the content and parse any JSON strings
    assert response is not None
    
    # Get the first text content item 
    text_content = next((item for item in response.content if item.type == "text"), None)
    assert text_content is not None
    
    # Parse the JSON response
    result = json.loads(text_content.text)
    
    # Assertions
    assert "evaluators" in result
    assert result["count"] > 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="Proper integration test infrastructure not yet in place")
async def test_run_evaluation_integration(mcp_client: ClientSession) -> None:
    """Test running a standard evaluation integration."""
    
    # First, list evaluators to get an evaluator ID
    list_response = await mcp_client.call_tool("list_evaluators", {})
    text_content = next((item for item in list_response.content if item.type == "text"), None)
    evaluators_result = json.loads(text_content.text)
    
    # Get the first evaluator ID
    evaluator_id = evaluators_result["evaluators"][0]["id"]
    
    # Run evaluation
    eval_response = await mcp_client.call_tool(
        "run_evaluation",
        {
            "evaluator_id": evaluator_id,
            "query": "What is machine learning?",
            "response": "Machine learning is a subset of artificial intelligence that allows systems to learn and improve from experience without being explicitly programmed.",
        },
    )
    
    # Parse the response
    eval_text_content = next((item for item in eval_response.content if item.type == "text"), None)
    assert eval_text_content is not None
    evaluation_result = json.loads(eval_text_content.text)
    
    # Assertions
    assert evaluation_result is not None
    assert "score" in evaluation_result
    assert "justification" in evaluation_result or "explanation" in evaluation_result


@pytest.mark.asyncio
@pytest.mark.skip(reason="Proper integration test infrastructure not yet in place")
async def test_run_rag_evaluation_integration(mcp_client: ClientSession) -> None:
    """Test running a RAG evaluation integration."""
    
    # First, list evaluators to get an evaluator ID
    list_response = await mcp_client.call_tool("list_evaluators", {})
    text_content = next((item for item in list_response.content if item.type == "text"), None)
    evaluators_result = json.loads(text_content.text)
    
    # Get a RAG evaluator (one that requires context)
    rag_evaluator = None
    for evaluator in evaluators_result["evaluators"]:
        if evaluator.get("requires_context", False):
            rag_evaluator = evaluator
            break
    
    if not rag_evaluator:
        pytest.skip("No RAG evaluator available")
    
    # Run RAG evaluation
    eval_response = await mcp_client.call_tool(
        "run_rag_evaluation",
        {
            "evaluator_id": rag_evaluator["id"],
            "query": "Summarize the key points about machine learning.",
            "response": "Machine learning is a field of artificial intelligence where algorithms improve through experience. Key types include supervised, unsupervised, and reinforcement learning.",
            "contexts": [
                "Machine learning (ML) is a type of artificial intelligence (AI) that allows software applications to become more accurate at predicting outcomes without being explicitly programmed to do so. Machine learning algorithms use historical data as input to predict new output values.",
                "Types of machine learning: 1. Supervised learning: Uses labeled datasets to train algorithms. 2. Unsupervised learning: Uses unlabeled data to find patterns. 3. Reinforcement learning: A behavioral learning model where an agent learns to behave in an environment by performing actions and receiving rewards or penalties.",
            ],
        },
    )
    
    # Parse the response
    eval_text_content = next((item for item in eval_response.content if item.type == "text"), None)
    assert eval_text_content is not None
    evaluation_result = json.loads(eval_text_content.text)
    
    # Assertions
    assert evaluation_result is not None
    assert "score" in evaluation_result
    assert "justification" in evaluation_result or "explanation" in evaluation_result