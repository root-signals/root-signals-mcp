"""Unit tests for the JudgeService module."""

import logging
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from root_signals_mcp.judge import JudgeService
from root_signals_mcp.root_api_client import RootSignalsAPIError

logger = logging.getLogger("test_judge")


@pytest.fixture
def mock_api_client() -> Generator[MagicMock]:
    """Create a mock API client for testing."""
    with patch("root_signals_mcp.judge.RootSignalsJudgeRepository") as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_judges = AsyncMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_fetch_judges_passes_max_count(mock_api_client: MagicMock) -> None:
    """Test that max_count is passed correctly to the API client."""
    service = JudgeService()
    await service.fetch_judges(max_count=75)
    mock_api_client.list_judges.assert_called_once_with(75)


@pytest.mark.asyncio
async def test_fetch_judges_handles_api_error(mock_api_client: MagicMock) -> None:
    """Test handling of RootSignalsAPIError in fetch_judges."""
    service = JudgeService()
    mock_api_client.list_judges.side_effect = RootSignalsAPIError(
        status_code=500, detail="Internal server error"
    )

    with pytest.raises(RuntimeError) as excinfo:
        await service.fetch_judges()

    assert "Cannot fetch judges" in str(excinfo.value)
    assert "Internal server error" in str(excinfo.value)
