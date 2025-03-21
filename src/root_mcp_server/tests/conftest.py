"""Common pytest configuration and fixtures for tests."""

import pytest

# Configure pytest-asyncio to use function scope for fixtures
pytest.asyncio_fixture_loop_scope = "function"