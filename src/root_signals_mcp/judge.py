"""RootSignals judge service module.

This module handles the integration with RootSignals judges.
"""

import logging

from root_signals_mcp.root_api_client import (
    ResponseValidationError,
    RootSignalsAPIError,
    RootSignalsJudgeRepository,
)
from root_signals_mcp.schema import (
    JudgeInfo,
    JudgesListResponse,
    RunJudgeRequest,
    RunJudgeResponse,
)
from root_signals_mcp.settings import settings

logger = logging.getLogger("root_signals_mcp.judge")


class JudgeService:
    """Service for interacting with RootSignals judges."""

    def __init__(self) -> None:
        """Initialize the judge service."""
        self.async_client = RootSignalsJudgeRepository(
            api_key=settings.root_signals_api_key.get_secret_value(),
            base_url=settings.root_signals_api_url,
        )

    async def fetch_judges(self, max_count: int | None = None) -> list[JudgeInfo]:
        """Fetch available judges from the API.

        Args:
            max_count: Maximum number of judges to fetch

        Returns:
            List[JudgeInfo]: List of judge information.

        Raises:
            RuntimeError: If judges cannot be retrieved from the API.
        """
        logger.info(
            f"Fetching judges from RootSignals API (max: {max_count or settings.max_judges})"
        )

        try:
            judges_data = await self.async_client.list_judges(max_count)

            total = len(judges_data)
            logger.info(f"Retrieved {total} judges from RootSignals API")

            return judges_data

        except RootSignalsAPIError as e:
            logger.error(f"Failed to fetch judges from API: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Cannot fetch judges: {str(e)}") from e
        except ResponseValidationError as e:
            logger.error(f"Response validation error: {e}", exc_info=settings.debug)
            if e.response_data:
                logger.debug(f"Response data: {e.response_data}")
            raise RuntimeError(f"Invalid judges response: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching judges: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Cannot fetch judges: {str(e)}") from e

    async def list_judges(self, max_count: int | None = None) -> JudgesListResponse:
        """List all available judges.

        Args:
            max_count: Maximum number of judges to fetch

        Returns:
            JudgesListResponse: A response containing all available judges.
        """
        judges = await self.fetch_judges(max_count)

        return JudgesListResponse(
            judges=judges,
        )

    async def run_judge(self, request: RunJudgeRequest) -> RunJudgeResponse:
        """Run a judge by ID.

        Args:
            request: The judge request containing request, response, and judge ID.

        Returns:
            RunJudgeResponse: The judge result.

        Raises:
            RuntimeError: If the judge execution fails.
        """
        logger.info(f"Running judge with ID {request.judge_id}")

        try:
            result = await self.async_client.run_judge(request)

            logger.info("Judge execution completed")
            return result

        except RootSignalsAPIError as e:
            logger.error(f"Failed to run judge: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Judge execution failed: {str(e)}") from e
        except ResponseValidationError as e:
            logger.error(f"Response validation error: {e}", exc_info=settings.debug)
            if e.response_data:
                logger.debug(f"Response data: {e.response_data}")
            raise RuntimeError(f"Invalid judge response: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error running judge: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Judge execution failed: {str(e)}") from e
