"""Common pytest configuration and fixtures for tests."""

import logging
import os
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from python_on_whales import DockerClient

from root_mcp_server.sse_server import SSEMCPServer

# Setup logging
logger = logging.getLogger("root_mcp_server_tests")
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

docker = DockerClient()
PROJECT_ROOT = Path(__file__).parents[3]


@pytest_asyncio.fixture(scope="module")
async def compose_up_mcp_server() -> Generator[None]:
    """Start and stop Docker Compose for integration tests.

    Docker setup can be flaky in CI environments, so this fixture includes
    extensive health checking and error handling to make tests more reliable.
    """
    try:
        try:
            info = docker.info()
            logger.info(f"Docker is running, version: {info.server_version}")
        except Exception as e:
            logger.error(f"Docker is not running: {e}")
            pytest.skip("Docker is not running")
            return

        os.chdir(PROJECT_ROOT)

        try:
            containers = docker.compose.ps()
            if containers and any(c.state.running for c in containers):
                logger.info("Docker Compose service is already running, stopping it first")
                docker.compose.down(volumes=True)
                time.sleep(2)
        except Exception as e:
            logger.error(f"Error cleaning up existing containers: {e}")

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
                        logger.info(
                            f"Container not healthy yet, status: {container.state.health.status if container.state.health else 'unknown'}"
                        )
                        time.sleep(3)
                        retries += 1
                else:
                    logger.info("No containers found, waiting...")
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
            if response.status_code != 200:
                logger.error(f"Health endpoint not healthy: {response.status_code}")
                logs = docker.compose.logs()
                logger.error(f"Docker Compose logs:\n{logs}")
                raise RuntimeError(f"Health endpoint returned status code {response.status_code}")
            logger.info(f"Health endpoint response: {response.status_code}")
        except Exception as e:
            logger.error(f"Could not connect to health endpoint: {e}")
            logs = docker.compose.logs()
            logger.error(f"Docker Compose logs:\n{logs}")
            raise RuntimeError(f"Could not connect to health endpoint: {e}")

        time.sleep(3)  # Allow service to stabilize
        yield
    except Exception as e:
        logger.error(f"Failed to set up Docker Compose: {e}")
        raise
    finally:
        logger.info("Cleaning up Docker Compose service")
        try:
            docker.compose.down(volumes=True)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


@pytest_asyncio.fixture(scope="module")
async def mcp_server() -> Generator[SSEMCPServer]:
    """Create and initialize a real SSEMCPServer."""

    yield SSEMCPServer()

