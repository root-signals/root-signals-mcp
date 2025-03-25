"""Integration tests for the RootSignals MCP Server using SSE transport."""

import logging
import os
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
from python_on_whales import DockerClient

from root_mcp_server.client import RootSignalsMCPClient

pytestmark = pytest.mark.skipif(
    os.environ.get("ROOT_SIGNALS_API_KEY") is None,
    reason="ROOT_SIGNALS_API_KEY environment variable not set",
)

docker = DockerClient()
PROJECT_ROOT = Path(__file__).parents[3]

logger = logging.getLogger("test_sse_integration")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


@pytest.fixture(scope="module")
def compose_up_mcp_server() -> Generator[None]:
    os.chdir(PROJECT_ROOT)

    try:
        containers = docker.compose.ps()
        if containers and any(c.state.running for c in containers):
            logger.info("Docker Compose service is already running, stopping it first")
            docker.compose.down(volumes=True)
            time.sleep(2)

        logger.info("Starting Docker Compose service")
        docker.compose.up(detach=True)

        healthy = False
        retries = 0
        max_retries = 15

        while not healthy and retries < max_retries:
            try:
                containers = docker.compose.ps()

                if containers:
                    container = containers[0]

                    if (
                        container.state
                        and container.state.health
                        and container.state.health.status == "healthy"
                    ):
                        logger.info("Docker Compose service is healthy")
                        healthy = True
                    else:
                        time.sleep(3)
                        retries += 1
                else:
                    time.sleep(3)
                    retries += 1
            except Exception as e:
                logger.error(f"Error checking service health: {e}")
                time.sleep(3)
                retries += 1

        if not healthy:
            logs = docker.compose.logs()
            logger.error(f"Docker Compose logs:\n{logs}")
            raise RuntimeError("Docker Compose service failed to start or become healthy")

        try:
            response = httpx.get("http://localhost:9090/health", timeout=5)
            logger.info(f"Health endpoint response: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to health endpoint: {e}")

        time.sleep(3)
        yield
    except Exception as e:
        logger.error(f"Failed to set up Docker Compose: {e}")
        raise
    finally:
        logger.info("Cleaning up Docker Compose service")
        docker.compose.down(volumes=True)


@pytest.mark.asyncio
async def test_list_tools(compose_up_mcp_server):
    """Test listing tools via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        # List tools
        tools = await client.list_tools()

        # Verify expected tools are available
        tool_names = {tool["name"] for tool in tools}
        expected_tools = {"list_evaluators", "run_evaluation", "run_rag_evaluation"}

        assert expected_tools.issubset(tool_names), f"Missing expected tools. Found: {tool_names}"
        logger.info(f"Found expected tools: {tool_names}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_list_evaluators(compose_up_mcp_server):
    """Test listing evaluators via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        # List evaluators
        evaluators = await client.list_evaluators()

        # Verify evaluators are available
        assert len(evaluators) > 0, "No evaluators found"
        logger.info(f"Found {len(evaluators)} evaluators")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_run_evaluation(compose_up_mcp_server):
    """Test running a standard evaluation via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        # Get evaluators
        evaluators = await client.list_evaluators()

        # Find a standard evaluator
        standard_evaluator = next(
            (e for e in evaluators if not e.get("requires_contexts", False)), None
        )

        if not standard_evaluator:
            pytest.skip("No standard evaluator found")

        logger.info(f"Using evaluator: {standard_evaluator['name']}")

        # Run evaluation
        result = await client.run_evaluation(
            evaluator_id=standard_evaluator["id"],
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
        )

        assert "score" in result, "No score in evaluation result"
        assert "justification" in result, "No justification in evaluation result"
        logger.info(f"Evaluation completed with score: {result['score']}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_run_rag_evaluation(compose_up_mcp_server):
    """Test running a RAG evaluation via SSE transport."""
    logger.info("Connecting to MCP server")
    client = RootSignalsMCPClient()

    try:
        await client.connect()

        # Get evaluators
        evaluators = await client.list_evaluators()

        # Find a RAG evaluator
        faithfulness_evaluators = [
            e
            for e in evaluators
            if any(
                kw in e.get("name", "").lower()
                for kw in ["faithfulness", "context", "rag", "relevance"]
            )
        ]

        rag_evaluator = next(iter(faithfulness_evaluators), None)

        if not rag_evaluator:
            pytest.skip("No RAG evaluator found")

        logger.info(f"Using evaluator: {rag_evaluator['name']}")

        # Run RAG evaluation
        result = await client.run_rag_evaluation(
            evaluator_id=rag_evaluator["id"],
            request="What is the capital of France?",
            response="The capital of France is Paris, which is known as the City of Light.",
            contexts=[
                "Paris is the capital and most populous city of France. It is located on the Seine River.",
                "France is a country in Western Europe with several overseas territories and regions.",
            ],
        )

        assert "score" in result, "No score in RAG evaluation result"
        assert "justification" in result, "No justification in RAG evaluation result"
        logger.info(f"RAG evaluation completed with score: {result['score']}")
    finally:
        await client.disconnect()
